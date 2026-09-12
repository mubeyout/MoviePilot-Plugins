from itertools import chain
from typing import Any, Generator, Callable

from pydantic import TypeAdapter

from app.core.cache import Cache
from app.db.plugindata_oper import PluginDataOper

from .config import PluginConfig
from .helper.clashrulemanager import ClashRuleManager
from .helper.utilsprovider import UtilsProvider
from .models import RuleProviderData, ProxyProviderData, ProxyGroupData, Hosts, ProxyGroups, RuleProviders, \
    RuleProvider, Metadata, Proxies, ProxyData
from .models.configuration import ClashConfig
from .models.types import DataSource, RuleSet, DataKey
from .models.datapatch import DataPatch
from .models.api import SubscriptionsInfo
from .models.datamodel import GeoRules, PersistState


class PluginState:
    """
    A DAL to manage the runtime state of ClashRuleProvider.
    """
    def __init__(self, plugin_id: str, config: PluginConfig = None):
        self.plugin_id = plugin_id
        self.config = config or PluginConfig()
        self.plugin_data = PluginDataOper()
        self.cache = Cache(maxsize=256, ttl=self.config.cache_ttl)
        self.cache_region = f"app.plugins.{self.plugin_id.lower()}"

        # Build schemas from PersistState model
        self._schemas: dict[str, tuple[TypeAdapter, Callable[[], Any]]] = {}
        for _, field in PersistState.model_fields.items():
            alias = field.alias
            if alias:
                self._schemas[alias] = (TypeAdapter(field.annotation), field.default_factory)

        # Rule and Proxy Managers (Runtime)
        self.top_rules_manager: ClashRuleManager = ClashRuleManager()
        self.ruleset_rules_manager: ClashRuleManager = ClashRuleManager()

        # Runtime variables (not persisted directly or persisted via config)
        self.clash_template: ClashConfig = ClashConfig()

    def validate_state_data(self) -> tuple[bool, str]:
        """
        验证状态数据的完整性
        返回: (是否有效, 错误信息)
        """
        try:
            # 测试访问关键数据
            _ = self.subscription_info
            _ = self.sub_configs
            _ = self.proxies
            _ = self.proxy_groups
            _ = self.rule_providers
            return True, ""
        except Exception as e:
            from app.log import logger
            error_msg = f"State data validation failed: {e}"
            logger.error(error_msg)
            return False, error_msg

    def clear_corrupted_cache(self):
        """清除可能损坏的缓存和数据库数据"""
        try:
            from app.log import logger
            # 清除缓存
            self.cache.clear(region=self.cache_region)
            logger.info(f"Cleared cache for region: {self.cache_region}")

            # 检查并修复损坏的订阅信息数据
            try:
                sub_info_data = self.plugin_data.get_data(self.plugin_id, DataKey.SUB_INFO)
                if sub_info_data is not None:
                    # 检查数据类型是否正确
                    if not isinstance(sub_info_data, dict):
                        logger.warning(f"发现损坏的订阅信息数据 (类型: {type(sub_info_data)})")
                        # 通过保存空数据来覆盖损坏的数据
                        from .models.api import SubscriptionsInfo
                        empty_sub_info = SubscriptionsInfo()
                        self.plugin_data.save(
                            self.plugin_id,
                            DataKey.SUB_INFO,
                            empty_sub_info.model_dump(mode="json", by_alias=True, exclude_none=True)
                        )
                        logger.info("已重置损坏的订阅信息数据为空对象")
            except Exception as check_err:
                logger.error(f"检查订阅信息数据时出错: {check_err}")

        except Exception as e:
            from app.log import logger
            logger.error(f"Failed to clear cache: {e}")

    def _get_val(self, key: str) -> Any:
        # Check cache
        if self.cache.exists(key, region=self.cache_region):
            return self.cache.get(key, region=self.cache_region)

        data = self.plugin_data.get_data(self.plugin_id, key)
        adapter, default_factory = self._schemas.get(key, (None, None))

        if data is None:
            if default_factory:
                val = default_factory()
                self.cache.set(key, val, region=self.cache_region)
                return val
            return None

        if adapter:
            try:
                val = adapter.validate_python(data)
            except Exception as e:
                # 数据验证失败,记录错误并返回默认值
                from app.log import logger
                logger.error(f"Failed to validate {key} from database: {e}")
                logger.error(f"Data type: {type(data)}, Data: {str(data)[:500]}...")

                # 特殊处理 SubscriptionsInfo 的错误数据格式
                if key == DataKey.SUB_INFO:
                    logger.warning(f"检测到 SubscriptionsInfo 数据格式错误,尝试修复...")
                    try:
                        # 如果数据是列表或字符串,创建空的 SubscriptionsInfo
                        if isinstance(data, (list, str)):
                            val = SubscriptionsInfo()
                            logger.info("已创建空的 SubscriptionsInfo")
                        # 如果数据是字典,尝试创建 SubscriptionsInfo
                        elif isinstance(data, dict):
                            val = SubscriptionsInfo(root=data)
                            logger.info("已从字典创建 SubscriptionsInfo")
                        else:
                            val = SubscriptionsInfo()
                            logger.warning(f"未知的数据格式 {type(data)},使用空 SubscriptionsInfo")

                        # 保存修复后的值
                        try:
                            self.plugin_data.save(self.plugin_id, key,
                                                  adapter.dump_python(val, mode="json", by_alias=True, exclude_none=True))
                            logger.info("已保存修复后的 SubscriptionsInfo")
                        except Exception as save_err:
                            logger.error(f"Failed to save fixed value for {key}: {save_err}")
                        self.cache.set(key, val, region=self.cache_region)
                        return val
                    except Exception as fix_err:
                        logger.error(f"修复 SubscriptionsInfo 失败: {fix_err}")
                        val = SubscriptionsInfo()

                if default_factory:
                    val = default_factory()
                    # 保存修复后的默认值
                    try:
                        self.plugin_data.save(self.plugin_id, key,
                                              adapter.dump_python(val, mode="json", by_alias=True, exclude_none=True))
                    except Exception as save_err:
                        logger.error(f"Failed to save default value for {key}: {save_err}")
                    self.cache.set(key, val, region=self.cache_region)
                    return val
                return None
        else:
            val = data

        self.cache.set(key, val, region=self.cache_region)
        return val

    def _set_val(self, key: str, value: Any):
        adapter, _ = self._schemas.get(key, (None, None))
        if adapter:
            try:
                data = adapter.dump_python(value, mode="json", by_alias=True, exclude_none=True)
            except Exception as e:
                from app.log import logger
                logger.error(f"Failed to serialize {key} for saving: {e}")
                # 序列化失败,不保存数据但更新缓存
                self.cache.set(key, value, region=self.cache_region)
                return
        else:
            data = value
        try:
            self.plugin_data.save(self.plugin_id, key, data)
        except Exception as e:
            from app.log import logger
            logger.error(f"Failed to save {key} to database: {e}")
        self.cache.set(key, value, region=self.cache_region)

    @property
    def proxies(self) -> Proxies:
        return self._get_val(DataKey.PROXIES)

    @proxies.setter
    def proxies(self, value: Proxies):
        self._set_val(DataKey.PROXIES, value)

    @property
    def proxy_groups(self) -> ProxyGroups:
        return self._get_val(DataKey.PROXY_GROUPS)

    @proxy_groups.setter
    def proxy_groups(self, value: ProxyGroups):
        self._set_val(DataKey.PROXY_GROUPS, value)

    @property
    def subscription_info(self) -> SubscriptionsInfo:
        return self._get_val(DataKey.SUB_INFO)

    @subscription_info.setter
    def subscription_info(self, value: SubscriptionsInfo):
        self._set_val(DataKey.SUB_INFO, value)

    @property
    def rule_provider(self) -> dict[str, RuleProvider]:
        return self._get_val(DataKey.AUTO_RULE_PROVIDERS)

    @rule_provider.setter
    def rule_provider(self, value: dict[str, RuleProvider]):
        self._set_val(DataKey.AUTO_RULE_PROVIDERS, value)

    @property
    def rule_providers(self) -> RuleProviders:
        return self._get_val(DataKey.RULE_PROVIDERS)

    @rule_providers.setter
    def rule_providers(self, value: RuleProviders):
        self._set_val(DataKey.RULE_PROVIDERS, value)

    @property
    def ruleset_names(self) -> dict[str, str]:
        return self._get_val(DataKey.RULESET_NAMES)

    @ruleset_names.setter
    def ruleset_names(self, value: dict[str, str]):
        self._set_val(DataKey.RULESET_NAMES, value)

    @property
    def acl4ssr_providers(self) -> RuleProviders:
        return self._get_val(DataKey.ACL4SSR)

    @acl4ssr_providers.setter
    def acl4ssr_providers(self, value: RuleProviders):
        self._set_val(DataKey.ACL4SSR, value)

    @property
    def sub_configs(self) -> dict[str, ClashConfig]:
        sub_conf = self._get_val(DataKey.SUB_CONFIGS)
        return sub_conf

    @sub_configs.setter
    def sub_configs(self, value: dict[str, ClashConfig]):
        self._set_val(DataKey.SUB_CONFIGS, value)

    @property
    def hosts(self) -> Hosts:
        return self._get_val(DataKey.HOSTS)

    @hosts.setter
    def hosts(self, value: Hosts):
        self._set_val(DataKey.HOSTS, value)

    @property
    def proxy_group_patch(self) -> DataPatch:
        return self._get_val(DataKey.PROXY_GROUP_PATCH)

    @proxy_group_patch.setter
    def proxy_group_patch(self, value: DataPatch):
        self._set_val(DataKey.PROXY_GROUP_PATCH, value)

    @property
    def proxy_patch(self) -> DataPatch:
        return self._get_val(DataKey.PROXY_PATCH)

    @proxy_patch.setter
    def proxy_patch(self, value: DataPatch):
        self._set_val(DataKey.PROXY_PATCH, value)

    @property
    def rule_provider_patch(self) -> DataPatch:
        return self._get_val(DataKey.RULE_PROVIDER_PATCH)

    @rule_provider_patch.setter
    def rule_provider_patch(self, value: DataPatch):
        self._set_val(DataKey.RULE_PROVIDER_PATCH, value)

    @property
    def geo_rules(self) -> GeoRules:
        return self._get_val(DataKey.GEO_RULES)

    @geo_rules.setter
    def geo_rules(self, value: GeoRules):
        self._set_val(DataKey.GEO_RULES, value)

    def get_data(self, key: str) -> Any:
        return self.plugin_data.get_data(self.plugin_id, key)

    def save_data(self, key: str, value: Any):
        self.plugin_data.save(self.plugin_id, key, value)

    def get_rule_manager(self, ruleset: RuleSet) -> ClashRuleManager:
        if ruleset == RuleSet.RULESET:
            return self.ruleset_rules_manager
        return self.top_rules_manager

    def get_sub_config(self, url: str) -> ClashConfig:
        conf = self.sub_configs.get(url)
        if conf is None:
            return ClashConfig()
        ret = ClashConfig()
        sub_options = self.config.get_sub_conf(url)
        for field_name in sub_options.model_fields.keys():
            if getattr(sub_options, field_name) is True and field_name in ret.model_fields:
                setattr(ret, field_name, getattr(conf, field_name))
        return ret

    def set_rule_providers(self, rule_providers: dict[str, dict[str, Any]]):
        self.rule_provider.clear()
        for name, rp in rule_providers.items():
            self.rule_providers[name] = RuleProvider(**rp)

    def rule_providers_from_subs(self) -> Generator[RuleProviderData, None, None]:
        for url, conf in self.sub_configs.items():
            if self.config.get_sub_conf(url).rule_providers:
                for name, rp in conf.rule_providers.items():
                    meta = Metadata(source=DataSource.SUB, remark=UtilsProvider.get_url_domain(url))
                    yield RuleProviderData(name=name, data=rp, meta=meta)

    def rule_providers_from_template(self) -> Generator[RuleProviderData, None, None]:
        for name, rp in self.clash_template.rule_providers.items():
            yield RuleProviderData(meta=Metadata(source=DataSource.TEMPLATE), name=name, data=rp)

    def proxy_providers_from_subs(self) -> Generator[ProxyProviderData, None, None]:
        for url, conf in self.sub_configs.items():
            if self.config.get_sub_conf(url).proxy_providers:
                for name, pp in conf.proxy_providers.items():
                    meta = Metadata(source=DataSource.SUB, remark=UtilsProvider.get_url_domain(url))
                    yield ProxyProviderData(meta=meta, name=name, data=pp)

    def proxy_providers_from_template(self) -> Generator[ProxyProviderData, None, None]:
        for name, pp in self.clash_template.proxy_providers.items():
            yield ProxyProviderData(meta=Metadata(source=DataSource.TEMPLATE), name=name, data=pp)

    def proxy_groups_from_subs(self) -> Generator[ProxyGroupData, None, None]:
        for url, conf in self.sub_configs.items():
            if self.config.get_sub_conf(url).proxy_groups:
                for pg in conf.proxy_groups:
                    meta = Metadata(source=DataSource.SUB, remark=UtilsProvider.get_url_domain(url))
                    yield ProxyGroupData(meta=meta, data=pg, name=pg.name)

    def proxy_groups_from_template(self) -> Generator[ProxyGroupData, None, None]:
        for pg in self.clash_template.proxy_groups:
            yield ProxyGroupData(meta=Metadata(source=DataSource.TEMPLATE), data=pg, name=pg.name)

    def proxies_from_subs(self) -> Generator[ProxyData, None, None]:
        for url, conf in self.sub_configs.items():
            for p in conf.proxies:
                meta = Metadata(source=DataSource.SUB, remark=UtilsProvider.get_url_domain(url))
                yield ProxyData(meta=meta, data=p.root if hasattr(p, 'root') else p, name=p.name, v2ray_link=conf.raw_proxies.get(p.name))

    def proxies_from_template(self) -> Generator[ProxyData, None, None]:
        for p in self.clash_template.proxies:
            yield ProxyData(meta=Metadata(source=DataSource.TEMPLATE), data=p.root if hasattr(p, 'root') else p, name=p.name)

    @property
    def all_rule_providers(self) -> list[RuleProviderData]:
        return list(chain(
            self.rule_providers,
            self.rule_providers_from_template(),
            self.rule_providers_from_subs(),
            self.acl4ssr_providers
        ))

    @property
    def all_proxy_providers(self) -> list[ProxyProviderData]:
        return list(chain(
            self.proxy_providers_from_subs(),
            self.proxy_providers_from_template()
        ))

    @property
    def all_proxy_groups(self) -> list[ProxyGroupData]:
        return list(chain(
            self.proxy_groups,
            self.proxy_groups_from_subs(),
            self.proxy_groups_from_template()
        ))

    @property
    def all_proxies(self) -> list[ProxyData]:
        return list(chain(
            self.proxies,
            self.proxies_from_subs(),
            self.proxies_from_template()
        ))
