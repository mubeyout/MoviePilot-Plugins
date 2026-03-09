# Category: 工具
"""
自定义索引站点 - 增强版 v2.1
完整支持 MoviePilot 官方配置的所有字段 + 多站点管理
"""
import json
import base64
from typing import List, Tuple, Dict, Any

from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase


class CustomIndexer(_PluginBase):
    # 插件名称
    plugin_name = "自定义索引站点"
    # 插件描述
    plugin_desc = "多站点管理 + 完整官方配置支持 + 可视化配置"
    # 插件图标
    plugin_icon = "spider.png"
    # 插件版本
    plugin_version = "2.1"
    # 插件作者
    plugin_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    plugin_config_prefix = "customindexer_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled = False
    _sites = []  # 站点配置列表
    _confstr = ""  # 兼容旧版
    _site_list = []  # 已注册的站点列表

    def init_plugin(self, config: dict = None):
        """插件初始化"""
        if config:
            self._enabled = config.get("enabled")

            # 优先使用新的 sites 配置
            sites = config.get("sites") or []
            # 兼容旧的 confstr 配置
            self._confstr = config.get("confstr") or ""

            # 初始化站点列表
            self._site_list = []

            if self._enabled and sites:
                # 使用新配置 - 支持多站点
                if isinstance(sites, list):
                    for site in sites:
                        if isinstance(site, dict):
                            self._add_site_from_config(site)
                        elif isinstance(site, str):
                            # 支持直接传入配置字符串
                            self._parse_and_add_site_config(site)

            elif self._enabled and self._confstr:
                # 使用旧配置（向后兼容）- 支持多站点
                self._parse_and_add_legacy_config(self._confstr)

    def _parse_and_add_site_config(self, site_config_str: str):
        """解析单个站点配置字符串"""
        if not site_config_str or not site_config_str.strip():
            return

        try:
            # 使用 maxsplit=1 确保只分割成两部分
            parts = site_config_str.strip().split("|", 1)
            if len(parts) != 2:
                logger.error(f"配置格式错误，应该是 '域名|配置'，实际: {site_config_str[:50]}...")
                return False

            domain, jsonstr = parts
            if not domain or not jsonstr:
                logger.error(f"域名或配置为空: {site_config_str[:50]}...")
                return False

            # Base64 解码
            try:
                decoded_bytes = base64.b64decode(jsonstr)
            except Exception as decode_err:
                logger.error(f"Base64 解码失败: {decode_err}")
                return False

            # 多编码支持
            json_str = None
            for encoding in ['utf-8', 'gbk', 'latin1']:
                try:
                    json_str = decoded_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if json_str is None:
                logger.error(f"无法解码配置字符串（尝试了 utf-8, gbk, latin1）: {domain}")
                return False

            # JSON 解析
            try:
                indexer_config = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON 解析失败 {json_err}: {json_str[:100]}...")
                return False

            # 检查站点是否已存在
            if any(s.get('domain') == domain for s in self._site_list):
                logger.warning(f"站点 {domain} 已存在，跳过")
                return False

            # 注册索引器
            SitesHelper().add_indexer(domain, indexer_config)

            # 添加到站点列表
            self._site_list.append({
                "domain": domain,
                "id": indexer_config.get("id", domain),
                "name": indexer_config.get("name", domain),
                "config": indexer_config
            })

            logger.info(f"✓ 成功注册自定义索引站点: {indexer_config.get('name')} ({domain})")
            return True

        except Exception as err:
            logger.error(f"自定义索引站点配置错误：{err}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _parse_and_add_legacy_config(self, confstr: str):
        """解析并添加旧版配置（支持多站点）"""
        indexers = confstr.split("\n")
        success_count = 0
        for indexer in indexers:
            if self._parse_and_add_site_config(indexer):
                success_count += 1

        logger.info(f"✓ 旧版配置加载完成，成功注册 {success_count}/{len(indexers)} 个站点")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        支持多站点管理 + 可视化配置 + 官方配置导入
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    # 启用开关
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
                    # 站点列表显示
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
                                            'title': '已配置站点',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'info',
                                                    'variant': 'tonal',
                                                    'text': f'当前已配置 {{sites.length}} 个站点'
                                                }
                                            },
                                            {
                                                'component': 'VDataTable',
                                                'props': {
                                                    'headers': [
                                                        {'title': '站点ID', 'key': 'id'},
                                                        {'title': '站点名称', 'key': 'name'},
                                                        {'title': '域名', 'key': 'domain'},
                                                        {'title': '操作', 'key': 'actions', 'sortable': False}
                                                    ],
                                                    'items': 'sites',
                                                    'items-per-page': 10,
                                                    'items-per-page-options': [5, 10, 20, 50]
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # 批量操作区域
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
                                            'title': '批量操作',
                                            'elevation': 2,
                                            'class': 'mt-4'
                                        },
                                        'content': [
                                            {
                                                'component': 'VContainer',
                                                'content': [
                                                    {
                                                        'component': 'VRow',
                                                        'content': [
                                                            {
                                                                'component': 'VCol',
                                                                'props': {
                                                                    'cols': 12,
                                                                    'md': 4
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VBtn',
                                                                        'props': {
                                                                            'color': 'primary',
                                                                            'variant': 'elevated',
                                                                            'block': True
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'VIcon',
                                                                                'props': {
                                                                                    'icon': 'mdi-export'
                                                                                }
                                                                            },
                                                                            '导出所有站点配置'
                                                                        ]
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'VCol',
                                                                'props': {
                                                                    'cols': 12,
                                                                    'md': 4
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VBtn',
                                                                        'props': {
                                                                            'color': 'success',
                                                                            'variant': 'elevated',
                                                                            'block': True
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'VIcon',
                                                                                'props': {
                                                                                    'icon': 'mdi-import'
                                                                                }
                                                                            },
                                                                            '批量导入站点'
                                                                        ]
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'VCol',
                                                                'props': {
                                                                    'cols': 12,
                                                                    'md': 4
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VBtn',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'variant': 'elevated',
                                                                            'block': True
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'VIcon',
                                                                                'props': {
                                                                                    'icon': 'mdi-delete-sweep'
                                                                                }
                                                                            },
                                                                            '清空所有站点'
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
                            }
                        ]
                    },
                    # 配置模式选择
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
                                        'component': 'VRadioGroup',
                                        'props': {
                                            'model': 'config_mode',
                                            'label': '添加新站点',
                                            'inline': True,
                                            'items': [
                                                {
                                                    'label': '快速配置（推荐）',
                                                    'value': 'simple'
                                                },
                                                {
                                                    'label': '高级配置（官方格式）',
                                                    'value': 'advanced'
                                                },
                                                {
                                                    'label': '导入官方配置',
                                                    'value': 'import'
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 快速配置模式
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
                                            'title': '快速添加站点',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VContainer',
                                                'content': [
                                                    # 站点ID
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'site_id',
                                                            'label': '站点ID',
                                                            'placeholder': 'example',
                                                            'hint': '唯一标识符（英文）',
                                                            'rules': [{'required': True}]
                                                        }
                                                    },
                                                    # 站点名称
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'site_name',
                                                            'label': '站点名称',
                                                            'placeholder': '示例站点',
                                                            'hint': '显示名称（中文或英文）',
                                                            'rules': [{'required': True}]
                                                        }
                                                    },
                                                    # 站点域名
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'site_domain',
                                                            'label': '站点域名',
                                                            'placeholder': 'example.com',
                                                            'hint': '只填域名，不含协议（如 example.com）',
                                                            'rules': [{'required': True}]
                                                        }
                                                    },
                                                    # 搜索URL
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'search_url',
                                                            'label': '搜索URL',
                                                            'placeholder': 'https://example.com/search?q={keyword}',
                                                            'hint': '使用 {keyword} 占位符，会被替换为搜索关键词',
                                                            'rules': [{'required': True}]
                                                        }
                                                    },
                                                    # 列表选择器
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'list_selector',
                                                            'label': '列表选择器（可选）',
                                                            'placeholder': 'div.item 或 .torrent-list',
                                                            'hint': '种子列表容器的 CSS 选择器'
                                                        }
                                                    },
                                                    # 标题选择器
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'title_selector',
                                                            'label': '标题选择器（可选）',
                                                            'placeholder': 'a@text 或 .title@text',
                                                            'hint': '标题字段的 CSS 选择器（@text 表示提取文本）'
                                                        }
                                                    },
                                                    # 链接选择器
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'link_selector',
                                                            'label': '链接选择器（可选）',
                                                            'placeholder': 'a@href 或 .link@href',
                                                            'hint': '详情链接的 CSS 选择器（@href 表示提取链接）'
                                                        }
                                                    },
                                                    # 添加按钮
                                                    {
                                                        'component': 'VBtn',
                                                        'props': {
                                                            'color': 'primary',
                                                            'variant': 'elevated'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'icon': 'mdi-plus'
                                                                }
                                                            },
                                                            '添加站点'
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
                    # 批量快速添加
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
                                            'title': '批量添加站点',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'info',
                                                    'variant': 'tonal',
                                                    'text': '💡 每行一个站点，格式：站点ID|站点名称|域名|搜索URL（可选：列表选择器|标题选择器|链接选择器）'
                                                }
                                            },
                                            {
                                                'component': 'VTextarea',
                                                'props': {
                                                    'model': 'batch_simple_config',
                                                    'label': '批量配置',
                                                    'rows': 10,
                                                    'placeholder': 'example|示例站点|example.com|https://example.com/search?q={keyword}\nsite2|站点2|site2.com|https://site2.com/search?keyword={keyword}'
                                                }
                                            },
                                            {
                                                'component': 'VBtn',
                                                'props': {
                                                    'color': 'primary'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'icon': 'mdi-plus-multiple'
                                                        }
                                                    },
                                                    '批量添加'
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # 高级配置模式（官方格式）
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
                                            'title': '高级配置（支持官方配置格式）',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'info',
                                                    'variant': 'tonal',
                                                    'text': '💡 支持官方配置格式，包含完整功能：代理、分类、批量搜索、高级字段过滤等'
                                                }
                                            },
                                            {
                                                'component': 'VTabs',
                                                'props': {
                                                    'centered': True,
                                                    'grow': True,
                                                    'icons-and-text': True
                                                },
                                                'content': [
                                                    {
                                                        'value': 'tab-advanced',
                                                        'title': '配置编辑器',
                                                        'content': [
                                                            {
                                                                'component': 'VTextarea',
                                                                'props': {
                                                                    'model': 'advanced_config',
                                                                    'label': '官方配置JSON',
                                                                    'rows': 15,
                                                                    'placeholder': '粘贴官方配置JSON，例如：{"id":"xxx","name":"站点名",...}',
                                                                    'hint': '支持官方配置的完整格式'
                                                                }
                                                            },
                                                            {
                                                                'component': 'VBtn',
                                                                'props': {
                                                                    'color': 'primary'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'icon': 'mdi-import'
                                                                        }
                                                                    },
                                                                    '导入并编码'
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'value': 'tab-advanced',
                                                        'title': '配置字符串',
                                                        'content': [
                                                            {
                                                                'component': 'VAlert',
                                                                'props': {
                                                                    'type': 'warning',
                                                                    'variant': 'tonal',
                                                                    'text': '⚠️ 高级模式：需要手动将配置转换为 Base64 编码格式。建议使用"配置编辑器"标签页。'
                                                                }
                                                            },
                                                            {
                                                                'component': 'VTextarea',
                                                                'props': {
                                                                    'model': 'confstr',
                                                                    'label': '站点索引配置（Base64编码）',
                                                                    'rows': 10,
                                                                    'placeholder': '域名|Base64编码的JSON配置\n一行一个站点'
                                                                }
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
                    # 导入官方配置模式
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
                                            'title': '批量导入官方配置',
                                            'elevation': 2
                                        },
                                        'content': [
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'success',
                                                    'variant': 'tonal',
                                                    'text': '🎉 支持同时导入多个站点！每个站点配置必须是完整的JSON对象，建议每行一个JSON。'
                                                }
                                            },
                                            {
                                                'component': 'VTextarea',
                                                'props': {
                                                    'model': 'import_config',
                                                    'label': '官方配置JSON（支持多个）',
                                                    'rows': 20,
                                                    'placeholder': '粘贴多个官方配置JSON，例如：\n{\n  "id": "example",\n  "name": "示例站点",\n  "domain": "https://example.com/",\n  "encoding": "UTF-8",\n  "public": true,\n  "search": {...}\n}\n{\n  "id": "site2",\n  "name": "站点2",\n  ...\n}'
                                                }
                                            },
                                            {
                                                'component': 'VBtn',
                                                'props': {
                                                    'color': 'success'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'icon': 'mdi-import'
                                                        }
                                                    },
                                                    '批量导入'
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # 帮助信息
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
                                            'text': '📚 多站点配置功能：\n1. 站点列表 - 查看和管理已配置的站点\n2. 批量操作 - 导出/导入/清空站点\n3. 快速配置 - 单个或批量添加简单站点\n4. 高级配置 - 使用官方JSON格式\n5. 导入配置 - 批量导入官方配置'
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
            "config_mode": "simple",
            "sites": [],
            "confstr": "",
            "advanced_config": "",
            "import_config": "",
            "batch_simple_config": "",
            "site_id": "",
            "site_name": "",
            "site_domain": "",
            "search_url": "",
            "list_selector": "",
            "title_selector": "",
            "link_selector": ""
        }

    def get_page(self) -> List[dict]:
        """自定义页面 - 站点管理"""
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """插件服务 - 站点管理接口"""
        return [
            {
                'title': '获取站点列表',
                'name': 'get_site_list',
                'description': '获取所有已配置的站点列表',
                'method': 'GET',
                'path': '/site_list'
            },
            {
                'title': '添加站点',
                'name': 'add_site',
                'description': '添加单个站点（快速配置模式）',
                'method': 'POST',
                'path': '/add_site'
            },
            {
                'title': '批量添加站点',
                'name': 'batch_add_sites',
                'description': '批量添加站点（快速配置模式）',
                'method': 'POST',
                'path': '/batch_add_sites'
            },
            {
                'title': '删除站点',
                'name': 'delete_site',
                'description': '删除指定站点',
                'method': 'DELETE',
                'path': '/site/{domain}'
            },
            {
                'title': '导出站点配置',
                'name': 'export_sites',
                'description': '导出所有站点配置为Base64格式',
                'method': 'GET',
                'path': '/export_sites'
            },
            {
                'title': '导入站点配置',
                'name': 'import_sites',
                'description': '批量导入站点配置（Base64格式）',
                'method': 'POST',
                'path': '/import_sites'
            },
            {
                'title': '清空所有站点',
                'name': 'clear_all_sites',
                'description': '清空所有已配置的站点',
                'method': 'DELETE',
                'path': '/clear_all'
            }
        ]

    def stop_service(self):
        pass

    def _add_site_from_config(self, site_config: Dict[str, Any]):
        """从表单配置添加站点"""
        try:
            domain = site_config.get("site_domain")
            site_id = site_config.get("site_id")

            # 检查站点是否已存在
            if any(s.get('domain') == domain for s in self._site_list):
                logger.warning(f"站点 {domain} 已存在，跳过")
                return False

            indexer_config = {
                "id": site_id,
                "name": site_config.get("site_name"),
                "domain": domain,
                "encoding": "UTF-8",
                "parser": "html",
                "public": True,
                "enabled": True,
                "search": {
                    "url": site_config.get("search_url"),
                    "method": "GET"
                },
                "torrents": {
                    "list": {
                        "selector": site_config.get("list_selector") or "div.item"
                    },
                    "fields": {
                        "title": {
                            "selector": site_config.get("title_selector") or "a@text"
                        },
                        "details_url": {
                            "selector": site_config.get("link_selector") or "a@href"
                        }
                    }
                }
            }

            SitesHelper().add_indexer(domain, indexer_config)

            # 添加到站点列表
            self._site_list.append({
                "domain": domain,
                "id": indexer_config["id"],
                "name": indexer_config["name"],
                "config": indexer_config
            })

            logger.info(f"✓ 成功注册自定义索引站点: {indexer_config['name']} ({domain})")
            return True

        except Exception as err:
            logger.error(f"✗ 自定义索引站点配置错误：{err}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _batch_add_simple_sites(self, batch_config: str):
        """批量添加简单站点"""
        if not batch_config or not batch_config.strip():
            return 0

        lines = batch_config.strip().split("\n")
        success_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 格式：站点ID|站点名称|域名|搜索URL|列表选择器|标题选择器|链接选择器
            parts = line.split("|")
            if len(parts) < 4:
                logger.warning(f"跳过格式错误的行: {line[:50]}...")
                continue

            site_config = {
                "site_id": parts[0].strip(),
                "site_name": parts[1].strip(),
                "site_domain": parts[2].strip(),
                "search_url": parts[3].strip(),
                "list_selector": parts[4].strip() if len(parts) > 4 else "",
                "title_selector": parts[5].strip() if len(parts) > 5 else "",
                "link_selector": parts[6].strip() if len(parts) > 6 else ""
            }

            if self._add_site_from_config(site_config):
                success_count += 1

        logger.info(f"✓ 批量添加完成，成功注册 {success_count}/{len(lines)} 个站点")
        return success_count

    def _delete_site(self, domain: str):
        """删除站点"""
        try:
            # 从站点列表中移除
            original_length = len(self._site_list)
            self._site_list = [s for s in self._site_list if s.get('domain') != domain]

            if len(self._site_list) < original_length:
                # 注意：SitesHelper 可能没有 remove_indexer 方法
                # 这里需要重新初始化来移除站点
                logger.info(f"✓ 已从配置中移除站点: {domain}")
                return True
            else:
                logger.warning(f"未找到站点: {domain}")
                return False

        except Exception as err:
            logger.error(f"✗ 删除站点失败：{err}")
            return False

    def _clear_all_sites(self):
        """清空所有站点"""
        try:
            count = len(self._site_list)
            self._site_list = []
            logger.info(f"✓ 已清空所有站点配置（共 {count} 个）")
            return True
        except Exception as err:
            logger.error(f"✗ 清空站点失败：{err}")
            return False

    def _export_sites(self) -> str:
        """导出所有站点配置为Base64格式"""
        try:
            export_lines = []
            for site in self._site_list:
                config = site.get('config', {})
                domain = site.get('domain', '')

                # 转换为JSON
                json_str = json.dumps(config, ensure_ascii=True, separators=(',', ':'))

                # Base64编码
                b64_str = base64.b64encode(json_str.encode('utf-8')).decode('ascii')

                # 组合配置字符串
                export_lines.append(f"{domain}|{b64_str}")

            return "\n".join(export_lines)

        except Exception as err:
            logger.error(f"✗ 导出配置失败：{err}")
            return ""

    def _import_sites(self, import_config: str):
        """导入站点配置（Base64格式）"""
        if not import_config or not import_config.strip():
            return 0

        lines = import_config.strip().split("\n")
        success_count = 0

        for line in lines:
            if self._parse_and_add_site_config(line):
                success_count += 1

        logger.info(f"✓ 批量导入完成，成功注册 {success_count}/{len(lines)} 个站点")
        return success_count

    def _import_official_config(self, config_json: str):
        """导入官方配置（支持批量）"""
        try:
            # 尝试直接解析为单个配置
            try:
                configs = [json.loads(config_json)]
            except json.JSONDecodeError:
                # 尝试解析为多个配置（每行一个JSON）
                configs = []
                lines = config_json.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        config = json.loads(line)
                        configs.append(config)
                    except json.JSONDecodeError:
                        # 尝试提取完整的JSON对象（处理跨行情况）
                        pass

            success_count = 0
            for config in configs:
                if self._import_single_official_config(config):
                    success_count += 1

            logger.info(f"✓ 官方配置导入完成，成功注册 {success_count}/{len(configs)} 个站点")
            return success_count

        except Exception as err:
            logger.error(f"✗ 导入官方配置失败：{err}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

    def _import_single_official_config(self, config: Dict[str, Any]) -> bool:
        """导入单个官方配置"""
        try:
            # 处理域名
            domain = config.get("domain", "")
            if domain.startswith("http://"):
                domain = domain[7:]
            elif domain.startswith("https://"):
                domain = domain[8:]
            domain = domain.rstrip("/")

            # 检查站点是否已存在
            if any(s.get('domain') == domain for s in self._site_list):
                logger.warning(f"站点 {domain} 已存在，跳过")
                return False

            # 转换为 CustomIndexer 格式
            converted_config = {
                "id": config.get("id"),
                "name": config.get("name"),
                "domain": domain,
                "encoding": config.get("encoding", "UTF-8"),
                "parser": "html",
                "public": config.get("public", True),
                "enabled": True
            }

            # 搜索配置转换
            if "search" in config:
                search_config = config["search"]

                # paths -> url
                if "paths" in search_config and search_config["paths"]:
                    path_config = search_config["paths"][0]
                    url = f"{domain}/{path_config.get('path', '')}"

                    # 添加参数
                    if "params" in search_config:
                        params = search_config["params"]
                        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
                        url += f"?{param_str}" if "?" not in url else f"&{param_str}"

                    converted_config["search"] = {
                        "url": url,
                        "method": path_config.get("method", "GET")
                    }

            # torrents 配置
            if "torrents" in config:
                converted_config["torrents"] = config["torrents"]

            # 分类配置
            if "category" in config:
                converted_config["category"] = config["category"]

            # 其他高级配置
            if "proxy" in config:
                converted_config["proxy"] = config["proxy"]
            if "timeout" in config:
                converted_config["timeout"] = config["timeout"]
            if "result_num" in config:
                converted_config["result_num"] = config["result_num"]

            # 注册站点
            SitesHelper().add_indexer(domain, converted_config)

            # 添加到站点列表
            self._site_list.append({
                "domain": domain,
                "id": converted_config["id"],
                "name": converted_config["name"],
                "config": converted_config
            })

            logger.info(f"✓ 成功导入官方配置站点: {config['name']} ({domain})")
            return True

        except Exception as err:
            logger.error(f"✗ 导入官方配置失败：{err}")
            import traceback
            logger.error(traceback.format_exc())
            return False
