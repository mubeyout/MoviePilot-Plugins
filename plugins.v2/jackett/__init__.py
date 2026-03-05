import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import ChainEventType
from app.core.event import eventmanager, Event
from app.helper.sites import SitesHelper
from .jackett_api import JackettAPI


class Jackett(_PluginBase):
    # 插件名称
    plugin_name = "Jackett聚合搜索"
    # 插件描述
    plugin_desc = "通过Jackett聚合多个种子站点进行搜索，支持统一的API接口和索引器管理。"
    # 插件图标
    plugin_icon = "jackett.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "Claudian"
    # 作者主页
    author_url = "https://github.com/jxxghp/MoviePilot-Plugins"
    # 插件配置项ID前缀
    plugin_config_prefix = "jackett_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled = False
    _jackett_url = ""
    _jackett_api_key = ""
    _api = None
    _default_search = False  # 是否默认使用 Jackett 搜索

    def init_plugin(self, config: dict = None):
        """
        插件初始化
        """
        logger.info("===== Jackett 插件开始初始化 =====")

        if config:
            logger.info(f"配置内容: {config}")
            self._enabled = config.get("enabled")
            self._jackett_url = config.get("url") or ""
            self._jackett_api_key = config.get("api_key") or ""
            self._default_search = config.get("default_search", False)

            logger.info(f"启用状态: {self._enabled}")
            logger.info(f"Jackett 地址: {self._jackett_url}")
            logger.info(f"默认搜索: {self._default_search}")

            if self._enabled and self._jackett_url and self._jackett_api_key:
                # 初始化 Jackett API
                try:
                    self._api = JackettAPI(
                        url=self._jackett_url,
                        api_key=self._jackett_api_key
                    )
                    logger.info(f"Jackett 插件初始化成功: {self._jackett_url}")

                    # 注册 Jackett 为站点
                    self._register_jackett_site()

                    # 测试连接
                    logger.info("开始测试 Jackett 连接...")
                    if self._api.test_connection():
                        logger.info("Jackett 连接测试成功")
                    else:
                        logger.warning("Jackett 连接测试失败")

                except Exception as err:
                    logger.error(f"Jackett 插件初始化失败: {err}")
                    self._enabled = False
            else:
                logger.warning("插件未启用或配置不完整")
        else:
            logger.warning("未收到配置信息")

        logger.info("===== Jackett 插件初始化完成 =====")

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return self._enabled

    def get_form(self) -> tuple[list[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'url',
                                            'label': 'Jackett 地址',
                                            'placeholder': 'http://localhost:9117',
                                            'hint': 'Jackett 服务的完整地址'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_key',
                                            'label': 'API Key',
                                            'placeholder': '输入 Jackett API Key',
                                            'hint': '在 Jackett 配置中查看 API Key'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '配置完成后，可使用插件提供的 API 进行搜索，或在仪表板中查看索引器状态。'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'default_search',
                                            'label': '默认使用 Jackett 搜索',
                                            'hint': '启用后，所有搜索都会包含 Jackett 结果（可通过 jackett: 前缀单独搜索）'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "url": "http://localhost:9117",
            "api_key": "",
            "default_search": False
        }

    def get_command(self) -> List[Dict[str, Any]]:
        """
        对外暴露的命令接口
        """
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        对外暴露的 API 接口
        """
        if not self._enabled or not self._api:
            return []

        return [
            {
                "path": "/search",
                "endpoint": self.search,
                "methods": ["GET"],
                "summary": "搜索种子",
                "description": "通过 Jackett 搜索种子资源"
            },
            {
                "path": "/indexers",
                "endpoint": self.get_indexers,
                "methods": ["GET"],
                "summary": "获取索引器列表",
                "description": "获取 Jackett 中已配置的索引器列表"
            },
            {
                "path": "/test",
                "endpoint": self.test_connection,
                "methods": ["GET"],
                "summary": "测试连接",
                "description": "测试与 Jackett 服务的连接状态"
            }
        ]

    def search(self, query: str, indexer: str = "all", category: str = None) -> Dict[str, Any]:
        """
        搜索种子

        :param query: 搜索关键词
        :param indexer: 索引器ID，默认 "all" 搜索所有
        :param category: 分类ID（可选）
        :return: 搜索结果
        """
        if not self._api:
            return {
                "success": False,
                "message": "插件未启用或配置错误",
                "data": []
            }

        try:
            # 调用 Jackett API 搜索
            results = self._api.search(query, indexer, category)

            return {
                "success": True,
                "message": f"搜索完成，找到 {len(results)} 个结果",
                "data": results,
                "total": len(results)
            }

        except Exception as err:
            logger.error(f"Jackett 搜索失败: {err}")
            return {
                "success": False,
                "message": f"搜索失败: {str(err)}",
                "data": []
            }

    def get_indexers(self) -> Dict[str, Any]:
        """
        获取索引器列表

        :return: 索引器列表
        """
        if not self._api:
            return {
                "success": False,
                "message": "插件未启用或配置错误",
                "data": []
            }

        try:
            indexers = self._api.get_indexers()

            return {
                "success": True,
                "message": f"获取到 {len(indexers)} 个索引器",
                "data": indexers,
                "total": len(indexers)
            }

        except Exception as err:
            logger.error(f"获取索引器列表失败: {err}")
            return {
                "success": False,
                "message": f"获取失败: {str(err)}",
                "data": []
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        :return: 测试结果
        """
        if not self._api:
            return {
                "success": False,
                "message": "插件未启用或配置错误"
            }

        try:
            # 测试连接
            is_connected = self._api.test_connection()

            if is_connected:
                # 获取索引器数量
                indexers = self._api.get_indexers()
                return {
                    "success": True,
                    "message": f"连接成功，当前配置了 {len(indexers)} 个索引器",
                    "data": {
                        "url": self._jackett_url,
                        "indexer_count": len(indexers)
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "连接失败或没有配置索引器"
                }

        except Exception as err:
            logger.error(f"测试连接失败: {err}")
            return {
                "success": False,
                "message": f"测试失败: {str(err)}"
            }

    def get_page(self) -> List[dict]:
        """
        插件详情页面
        """
        if not self._enabled:
            return []

        return [
            {
                'component': 'VContainer',
                'props': {
                    'fluid': True
                },
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VCard',
                                        'props': {
                                            'title': '连接状态',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardText',
                                                'props': {
                                                    'class': 'text-center pa-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'info',
                                                            'variant': 'tonal'
                                                        },
                                                        'events': {
                                                            'click': {
                                                                'api': 'plugin/jackett/test',
                                                                'method': 'get',
                                                                'params': {}
                                                            }
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-h6'
                                                                },
                                                                'content': '点击测试连接'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VCard',
                                        'props': {
                                            'title': 'API 文档',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardText',
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'content': '''
                                                            <h3>搜索种子</h3>
                                                            <p><code>GET /api/plugin/jackett/search</code></p>
                                                            <p>参数：</p>
                                                            <ul>
                                                                <li><code>query</code>: 搜索关键词</li>
                                                                <li><code>indexer</code>: 索引器ID（默认 all）</li>
                                                                <li><code>category</code>: 分类ID（可选）</li>
                                                            </ul>

                                                            <h3>获取索引器列表</h3>
                                                            <p><code>GET /api/plugin/jackett/indexers</code></p>
                                                        '''
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def stop_service(self):
        """
        停止插件服务
        """
        logger.info("Jackett 插件已停止")

    @eventmanager.register(ChainEventType.ResourceSelection)
    def resource_selection(self, event: Event):
        """
        资源选择事件处理 - 注入 Jackett 搜索结果
        当用户搜索资源时，如果满足条件，自动从 Jackett 搜索并注入结果
        """
        logger.info("===== ResourceSelection 事件触发 =====")

        if not self._enabled or not self._api:
            logger.info(f"插件未启用或 API 未初始化: enabled={self._enabled}, api={self._api is not None}")
            return

        try:
            event_data = event.event_data

            # 获取搜索关键词
            search_keyword = getattr(event_data, 'keyword', '')
            logger.info(f"搜索关键词: {search_keyword}")

            if not search_keyword:
                logger.info("没有搜索关键词，跳过")
                return

            # 判断是否应该使用 Jackett 搜索
            should_search = self._should_use_jackett(search_keyword, event_data)
            logger.info(f"是否触发 Jackett 搜索: {should_search}")

            if should_search:
                logger.info(f"触发 Jackett 搜索: {search_keyword}")

                # 从 Jackett 搜索并转换结果
                results = self._search_jackett(search_keyword)

                if results:
                    # 注入到搜索结果
                    if not hasattr(event_data, 'resource_list'):
                        event_data.resource_list = []
                    event_data.resource_list.extend(results)
                    logger.info(f"Jackett 注入了 {len(results)} 个搜索结果")
                else:
                    logger.info("Jackett 搜索无结果")

        except Exception as err:
            logger.error(f"Jackett 搜索注入失败: {err}", exc_info=True)

    def _should_use_jackett(self, keyword: str, event_data) -> bool:
        """
        判断是否应该使用 Jackett 搜索

        :param keyword: 搜索关键词
        :param event_data: 事件数据
        :return: 是否使用 Jackett
        """
        # 条件 1: 关键词包含 "jackett:" 前缀
        if keyword.lower().startswith("jackett:"):
            return True

        # 条件 2: 检查是否选择了 Jackett 站点
        if hasattr(event_data, 'sites'):
            sites = event_data.sites
            logger.info(f"当前选择的站点: {sites}")
            # 如果站点列表包含 jackett
            if sites and 'jackett' in str(sites).lower():
                return True

        # 条件 3: 事件标记为 Jackett
        if hasattr(event_data, 'source') and event_data.source == 'jackett':
            return True

        # 条件 4: 启用默认搜索
        if self._default_search:
            return True

        return False

    def _search_jackett(self, keyword: str) -> List[Dict[str, Any]]:
        """
        从 Jackett 搜索并转换为 MoviePilot 标准格式

        :param keyword: 搜索关键词
        :return: 种子列表
        """
        # 清理关键词，移除 "jackett:" 前缀
        real_keyword = keyword.lower().replace("jackett:", "").strip()

        if not real_keyword:
            return []

        try:
            # 调用 Jackett API
            jackett_results = self._api.search(real_keyword)

            # 转换为 MoviePilot 资源格式
            results = []
            for item in jackett_results:
                result = {
                    "site": "Jackett",
                    "site_order": 0,
                    "site_name": "Jackett",
                    "channel": item.get('indexer', 'unknown'),
                    "title": item['title'],
                    "enclosure": item['link'],
                    "size": item['size'],
                    "seeders": item['seeders'],
                    "peers": item['peers'],
                    "grabs": item.get('grabs', 0),
                    "page_url": item.get('comments', ''),
                    "upload_volume_factor": 1,
                    "download_volume_factor": 1,
                    "rss_rule": None,
                    "free_torrent": False,
                    "hr": False
                }

                results.append(result)

            logger.info(f"Jackett 搜索 '{real_keyword}' 返回 {len(results)} 个结果")
            return results

        except Exception as err:
            logger.error(f"Jackett 搜索失败: {err}")
            return []

    def _register_jackett_site(self):
        """
        将 Jackett 注册为 MoviePilot 站点
        使用虚拟索引器配置，实际搜索由插件 API 处理
        """
        try:
            # 创建一个虚拟的索引器配置
            # 这个配置不会被实际使用，因为我们会通过事件拦截搜索
            indexer_config = {
                "id": "jackett",
                "name": "Jackett",
                "domain": "http://jackett.local",
                "encoding": "UTF-8",
                "public": True,
                "enabled": True,
                "search": {
                    "paths": [
                        {
                            "path": "?q={keyword}",
                            "method": "get"
                        }
                    ]
                },
                "torrents": {
                    "list": {
                        "selector": "items"
                    },
                    "fields": {
                        "title": {"selector": "title"},
                        "download": {"selector": "link"},
                        "size": {"selector": "size"},
                        "seeders": {"selector": "seeders"}
                    }
                }
            }

            SitesHelper().add_indexer("jackett.local", indexer_config)
            logger.info("Jackett 站点注册成功")

        except Exception as e:
            logger.error(f"注册 Jackett 站点失败: {e}")
