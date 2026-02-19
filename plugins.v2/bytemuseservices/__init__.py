"""
ByteMuseServices - ByteMuse探索服务聚合模块

基于 ThePornDB API 的探索数据源插件
提供演员、上新、推荐、榜单、厂牌等探索服务
"""
from typing import Any, List, Dict, Tuple
from app.plugins import _PluginBase
from app.core.event import eventmanager, Event
from app.schemas.types import ChainEventType
from app.schemas import DiscoverSourceEventData
from app.log import logger

# 导入子模块
from .modules import (
    actors,
    new_releases,
    recommendations,
    rankings,
    studios
)

MODULE_LABELS = {
    "actors": "演员",
    "new_releases": "上新",
    "recommendations": "推荐",
    "rankings": "榜单",
    "studios": "厂牌",
}


class ByteMuseServices(_PluginBase):
    # 插件名称
    plugin_name = "ByteMuse探索服务聚合"
    # 插件描述
    plugin_desc = "基于 ThePornDB API 的探索数据源插件，提供演员、上新、推荐、榜单、厂牌等探索服务。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ExploreServices.png"
    # 插件版本
    plugin_version = "2.0.0"
    # 插件作者
    plugin_author = "Mubey"
    # 作者主页
    author_url = "https://github.com/mubey"
    # 插件配置项ID前缀
    plugin_config_prefix = "bytemuseservices_"
    # 加载顺序
    plugin_order = 13
    # 可使用的用户级别
    auth_level = 1

    # 子模块注册表
    modules = {
        "actors": actors,
        "new_releases": new_releases,
        "recommendations": recommendations,
        "rankings": rankings,
        "studios": studios,
    }
    enabled_modules: Dict[str, bool] = {}

    # ThePornDB API 配置
    _theporndb_api_token: str = ""

    def init_plugin(self, config: dict = None):
        if config:
            # 读取模块开关配置
            for name in self.modules:
                self.enabled_modules[name] = config.get(f"{name}_enabled", False)

            # 读取 ThePornDB API 配置
            self._theporndb_api_token = config.get("theporndb_api_token", "")
        else:
            for name in self.modules:
                self.enabled_modules[name] = False

        logger.info(f"ByteMuseServices 插件初始化完成，已启用模块: {[name for name, enabled in self.enabled_modules.items() if enabled]}")

    def get_state(self) -> bool:
        return any(self.enabled_modules.values())

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        plugin_names = "、".join(MODULE_LABELS.values())
        form = [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VCard",
                        "props": {"class": "mt-0"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {"style": "color: #16b1ff;", "class": "mr-2"},
                                        "text": "mdi-compass-outline"
                                    },
                                    {
                                        "component": "span",
                                        "text": "探索源开关"
                                    }
                                ]
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": f"{name}_enabled",
                                                            "label": f"启用{MODULE_LABELS.get(name, name)}探索源",
                                                        },
                                                    }
                                                ],
                                            }
                                            for name in self.modules
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mt-3',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-api'
                                            },
                                            {
                                                'component': 'span',
                                                'text': 'API 配置'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6'
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'theporndb_api_token',
                                            'label': 'ThePornDB API Token',
                                            'placeholder': '请输入API Token',
                                            'hint': 'ThePornDB API的认证Token（必填），从 https://theporndb.net 获取',
                                            'persistent-hint': True,
                                        }
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mt-3',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-information'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '使用说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1'
                                        },
                                        'text': '开启对应探索服务将在MoviePilot探索服务中展示对应探索页面，可根据需要进行开启。'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'text': f'当前聚合模块：{plugin_names}'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'content': [
                                            {
                                                'component': 'span',
                                                'text': '数据源: '
                                            },
                                            {
                                                'component': 'a',
                                                'props': {
                                                    'href': 'https://theporndb.net',
                                                    'target': '_blank',
                                                    'style': 'color: #16b1ff; text-decoration: underline;'
                                                },
                                                'text': 'ThePornDB'
                                            },
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'text': 'API 端点结构:'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-2 mt-1'
                                        },
                                        'content': [
                                            {
                                                'component': 'ul',
                                                'props': {'class': 'ml-4'},
                                                'content': [
                                                    {'component': 'li', 'text': '/bytemuse_actors_subscribed - 订阅中演员'},
                                                    {'component': 'li', 'text': '/bytemuse_actors_hot - 热门演员'},
                                                    {'component': 'li', 'text': '/bytemuse_new_releases - 最新上架'},
                                                    {'component': 'li', 'text': '/bytemuse_recommendations - 精选推荐'},
                                                    {'component': 'li', 'text': '/bytemuse_rankings_javdb_daily - JavDB 日榜'},
                                                    {'component': 'li', 'text': '/bytemuse_rankings_javdb_weekly - JavDB 周榜'},
                                                    {'component': 'li', 'text': '/bytemuse_rankings_javdb_monthly - JavDB 月榜'},
                                                    {'component': 'li', 'text': '/bytemuse_rankings_javlibrary - JavLibrary 想要榜'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_s1 - S1 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_ideapocket - IdeaPocket 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_moodyz - Moodyz 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_premium - Premium 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_das - DAS 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_madonna - Madonna 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_honnaka - Honnaka 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_attackers - Attackers 厂牌'},
                                                    {'component': 'li', 'text': '/bytemuse_studio_wanz - Wanz 厂牌'},
                                                ]
                                            }
                                        ]
                                    },
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        default_data = {
            f"{name}_enabled": False for name in self.modules
        }
        default_data.update({
            "theporndb_api_token": "",
        })
        return form, default_data

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API列表"""
        apis = []
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                module_apis = mod.get_api(self)
                if module_apis:
                    apis.extend(module_apis)
        return apis

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """注册探索源事件"""
        event_data: DiscoverSourceEventData = event.event_data
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                try:
                    mod.discover_source(self, event_data)
                except Exception as e:
                    logger.error(f"注册 {name} 探索源失败: {str(e)}")

    def stop_service(self):
        """停止服务"""
        for name, mod in self.modules.items():
            if hasattr(mod, "stop_service"):
                try:
                    mod.stop_service()
                except Exception as e:
                    logger.error(f"停止 {name} 模块服务失败: {str(e)}")

    # ===== 属性访问器 =====

    @property
    def theporndb_api_token(self) -> str:
        return self._theporndb_api_token
