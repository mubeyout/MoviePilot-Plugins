"""
Metatube 媒体识别插件
通过 Metatube API 识别番号媒体信息
"""
import re
from collections import deque
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional, List, Tuple

from app.chain import ChainBase
from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.plugins import _PluginBase
from app.log import logger
from app.schemas.types import MediaType

from .metatube_api import MetatubeApiClient
from .schema import MetatubeMovie, MetatubeMovieDetail, LogEntry


class MetatubeSource(_PluginBase):
    # 插件名称
    plugin_name = "Metatube源"
    # 插件描述
    plugin_desc = "通过Metatube API识别番号媒体信息。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/Metatube.png"
    # 插件版本
    plugin_version = "2.0.1"
    # 插件作者
    plugin_author = "MUBEY"
    # 作者主页
    author_url = "https://github.com/mubeyout"
    # 插件配置项ID前缀
    plugin_config_prefix = "metatubesource_"
    # 加载顺序
    plugin_order = 23
    # 可使用的用户级别
    auth_level = 1

    # 内置关键字库（按分类组织）
    # 日系关键词
    BUILT_IN_JAPANESE_KEYWORDS = [
        "SSIS", "SONE", "MIDV", "STARS", "IPX", "CAWD", "SSIS", "MIDE",
        "JUL", "VENX", "ADN", "URE", "WAAA", "DLDSS", "JUQ", "MIMK",
        "FC2", "FC2-PPV", "HEYZO", "CARIB", "CARIBPR", "1PONDO",
        "PACOPACOMAMA", "H0930", "H4610", "C0930", "SKY", "RED",
        "MEYD", "MIAA", "ABW", "DOCP", "KTRA", "HMN", "MOODYZ",
        "OPUD", "KAWD", "OKAX", "SW", "SDMT", "SDDE", "SOE",
        "一本道", "加勒比", "Tokyo-Hot", "红番区", "Caribbeancom",
        "10musume", "Pcolle", "Gcolle", "Skyhigh", "Redhot", "JAV",
        "AVOP", "AVOPEN", "JavHD", "Javbus"
    ]

    # 欧美系关键词
    BUILT_IN_WESTERN_KEYWORDS = [
        "BRAZZERS", "NAUGHTY", "REALITYKINGS", "MOFOS", "TEENSLOVEBLACKCOCKS",
        "BLACKED", "BLACKEDRAW", "TUSHY", "TUSHYRAW", "VOYEURHIT",
        "VICAT", "XEV", "Missa", "PervMom", "SisLovesMe",
        "Pornhub", "Xvideos"
    ]

    # 中文系关键词
    BUILT_IN_CHINESE_KEYWORDS = [
        "MD", "MX", "MDX", "PMC", "TM", "TW", "AV",
        "JK", "HT", "约炮", "网红", "探花", "大尺寸", "小宝寻花"
    ]

    # 其他关键词（通用特征）
    BUILT_IN_OTHER_KEYWORDS = [
        "高清", "无码", "有码", "中文字幕", "原声", "完整版", "流出", "泄露"
    ]

    # 插件配置
    _enabled: bool = False
    _api_url: str = "http://127.0.0.1:8080"
    _recognition_mode: str = ""  # hijacking: 劫持模式, keyword: 关键字触发模式
    _timeout: int = 5
    _max_logs: int = 100

    # 关键字相关配置（分类管理）
    _custom_japanese_keywords: str = ""  # 自定义日系关键字
    _custom_western_keywords: str = ""  # 自定义欧美系关键字
    _custom_chinese_keywords: str = ""  # 自定义中文系关键字
    _custom_other_keywords: str = ""  # 自定义其他关键字
    _strict_match: bool = False  # 是否严格匹配

    # 劫持模式专属配置
    _hijack_fallback_system: bool = False  # 劫持模式 - 识别失败返回系统默认

    # 关键字触发模式专属配置
    _keyword_failed_download: bool = True  # 关键字触发模式 - 识别失败直接下载

    # 通用配置
    _show_failure_detail: bool = True  # 识别失败提示开关

    # 私有属性
    _metatube_client: MetatubeApiClient = None
    _original_method: Optional[Callable] = None
    _original_async_method: Optional[Callable[..., Coroutine[Any, Any, Optional[MediaInfo]]]] = None
    _log_entries: deque = None

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        plugin_instance: MetatubeSource = self

        def patched_recognize_media(chain_self, meta: MetaBase = None,
                                    mtype: Optional[MediaType] = None,
                                    tmdbid: Optional[int] = None,
                                    doubanid: Optional[str] = None,
                                    bangumiid: Optional[int] = None,
                                    episode_group: Optional[str] = None,
                                    cache: bool = True):
            """劫持系统媒体识别方法"""
            if not plugin_instance._original_method:
                return None
            # 调用原始方法
            result = plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                      episode_group, cache)
            # 系统识别失败时使用 Metatube 识别（仅关键字触发模式）
            if result is None and plugin_instance._enabled and plugin_instance._recognition_mode == 'keyword':
                # 检查是否包含关键字
                if plugin_instance._match_keywords(meta):
                    logger.info(f"通过插件 {MetatubeSource.plugin_name} 执行：recognize_media ...")
                    return plugin_instance.recognize_media(meta, mtype)
            return result

        async def patched_async_recognize_media(chain_self, meta: MetaBase = None,
                                                mtype: Optional[MediaType] = None,
                                                tmdbid: Optional[int] = None,
                                                doubanid: Optional[str] = None,
                                                bangumiid: Optional[int] = None,
                                                episode_group: Optional[str] = None,
                                                cache: bool = True):
            """异步劫持系统媒体识别方法"""
            if not plugin_instance._original_async_method:
                return None
            # 调用原始方法
            result = await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                  episode_group, cache)
            # 系统识别失败时使用 Metatube 识别（仅关键字触发模式）
            if result is None and plugin_instance._enabled and plugin_instance._recognition_mode == 'keyword':
                # 检查是否包含关键字
                if plugin_instance._match_keywords(meta):
                    logger.info(f"通过插件 {MetatubeSource.plugin_name} 执行：async_recognize_media ...")
                    return await plugin_instance.async_recognize_media(meta, mtype)
            return result

        # 给 patch 函数加唯一标记
        setattr(patched_recognize_media, '_patched_by', id(self))
        setattr(patched_async_recognize_media, '_patched_by', id(self))

        # 保存原始方法
        if not getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self):
            self._original_method = getattr(ChainBase, "recognize_media", None)
        if not getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self):
            self._original_async_method = getattr(ChainBase, "async_recognize_media", None)

        # 初始化日志队列
        if self._log_entries is None:
            self._log_entries = deque(maxlen=self._max_logs)

        if config:
            self._enabled = bool(config.get("enabled"))
            self._api_url = config.get("api_url") or "http://127.0.0.1:8080"
            self._recognition_mode = config.get("recognition_mode") or ""
            self._timeout = int(config.get("timeout") or 5)
            self._max_logs = int(config.get("max_logs") or 100)
            self._custom_japanese_keywords = config.get("custom_japanese_keywords") or ""
            self._custom_western_keywords = config.get("custom_western_keywords") or ""
            self._custom_chinese_keywords = config.get("custom_chinese_keywords") or ""
            self._custom_other_keywords = config.get("custom_other_keywords") or ""
            self._strict_match = bool(config.get("strict_match") or False)
            self._hijack_fallback_system = bool(config.get("hijack_fallback_system") or False)
            self._keyword_failed_download = bool(config.get("keyword_failed_download") if config.get("keyword_failed_download") is not None else True)
            self._show_failure_detail = bool(config.get("show_failure_detail") if config.get("show_failure_detail") is not None else True)
            # 更新日志队列大小
            if self._log_entries and self._log_entries.maxlen != self._max_logs:
                old_logs = list(self._log_entries)
                self._log_entries = deque(old_logs[-self._max_logs:], maxlen=self._max_logs)
            self._update_config()

        # 初始化API客户端
        self._metatube_client = MetatubeApiClient(
            base_url=self._api_url,
            timeout=self._timeout
        )

        if self._enabled:
            if self._recognition_mode == 'hijacking':
                # 劫持模式：通过 get_module 劫持系统识别
                # 恢复原始方法（劫持模式使用 get_module）
                if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                        self._original_method):
                    ChainBase.recognize_media = self._original_method
                if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                        self._original_async_method):
                    ChainBase.async_recognize_media = self._original_async_method
            elif self._recognition_mode == 'keyword':
                # 关键字触发模式：系统识别失败后接管，但只处理包含关键字的内容
                if not (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self)):
                    ChainBase.recognize_media = patched_recognize_media
                if not (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self)):
                    ChainBase.async_recognize_media = patched_async_recognize_media
            else:
                # 未选择模式或插件被禁用，恢复原始方法
                if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                        self._original_method):
                    ChainBase.recognize_media = self._original_method
                if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                        self._original_async_method):
                    ChainBase.async_recognize_media = self._original_async_method
        else:
            self.stop_service()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取插件API"""
        return [
            {
                "path": "/logs",
                "endpoint": self.get_logs,
                "methods": ["GET"],
                "summary": "获取识别日志",
                "description": "获取 Metatube 识别日志",
            },
            {
                "path": "/clear_logs",
                "endpoint": self.clear_logs,
                "methods": ["POST"],
                "summary": "清空识别日志",
                "description": "清空 Metatube 识别日志",
            },
            {
                "path": "/test_connection",
                "endpoint": self.test_connection,
                "methods": ["GET"],
                "summary": "测试API连接",
                "description": "测试 Metatube API 连接状态",
            }
        ]

    def get_logs(self) -> List[Dict[str, Any]]:
        """获取识别日志"""
        if self._log_entries:
            return [log.model_dump() for log in list(self._log_entries)]
        return []

    def clear_logs(self) -> Dict[str, Any]:
        """清空识别日志"""
        if self._log_entries:
            self._log_entries.clear()
        logger.info("Metatube: 识别日志已清空")
        return {"success": True, "message": "日志已清空"}

    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        if self._metatube_client and self._metatube_client.test_connection():
            return {"success": True, "message": "连接成功"}
        return {"success": False, "message": "连接失败"}

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
        return [
            {
                "component": "VForm",
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
                                            "model": "enabled",
                                            "label": "启用插件"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "recognition_mode",
                                            "label": "识别模式",
                                            "items": [
                                                {"title": "劫持模式", "value": "hijacking"},
                                                {"title": "关键字触发", "value": "keyword"}
                                            ],
                                            "hint": "劫持：全部交由Metatube；关键字：仅处理包含关键字的内容"
                                        }
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "timeout",
                                            "label": "超时时间",
                                            "type": "number",
                                            "placeholder": "5",
                                            "suffix": "秒",
                                            "hint": "API请求超时（1-30秒）",
                                            "min": 1,
                                            "max": 30
                                        }
                                    }
                                ]
                            }
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "api_url",
                                            "label": "API地址",
                                            "placeholder": "http://127.0.0.1:8080",
                                            "hint": "Metatube服务地址，如：http://192.168.1.100:8080"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2"},
                                        "text": "自定义关键词配置（按分类管理）"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_japanese_keywords",
                                            "label": "日系关键词",
                                            "placeholder": "SSIS, FC2, HEYZO...",
                                            "rows": 2,
                                            "hint": "日系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_western_keywords",
                                            "label": "欧美系关键词",
                                            "placeholder": "BRAZZERS, BLACKED, TUSHY...",
                                            "rows": 2,
                                            "hint": "欧美系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_chinese_keywords",
                                            "label": "中文系关键词",
                                            "placeholder": "MD, 约炮, 探花...",
                                            "rows": 2,
                                            "hint": "中文系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_other_keywords",
                                            "label": "其他关键词",
                                            "placeholder": "高清, 无码, 有码...",
                                            "rows": 2,
                                            "hint": "其他通用特征关键词，逗号分隔"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "strict_match",
                                            "label": "严格匹配",
                                            "hint": "区分大小写和全半角"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "show_failure_detail",
                                            "label": "显示失败详情",
                                            "hint": "在日志中显示详细失败原因"
                                        },
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "hijack_fallback_system",
                                            "label": "识别失败回退系统",
                                            "hint": "劫持模式：识别失败时回退到themoviedb"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "keyword_failed_download",
                                            "label": "失败自动下载",
                                            "hint": "关键字模式：识别失败时归类为'成人'并自动下载"
                                        },
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "title": "使用说明"
                                        },
                                        "content": [
                                            {
                                                "component": "div",
                                                "content": [
                                                    {
                                                        "component": "p",
                                                        "text": "• 劫持模式：拦截所有识别请求，全部交由 Metatube 处理"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 关键字触发：标题包含指定关键字才使用 Metatube 识别"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 二级分类：自动识别内容类型并归类为「成人/日系」、「成人/欧美系」、「成人/中文系」、「成人/其他」"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 分类关键词：内置关键词库包含常用番号前缀和平台标识，可按需自定义各分类关键词"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 优先级：日系 > 欧美系 > 中文系 > 其他（匹配到第一个即停止）"
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
        ], {
            "enabled": False,
            "api_url": "http://127.0.0.1:8080",
            "recognition_mode": "",
            "timeout": 5,
            "max_logs": 100,
            "custom_japanese_keywords": "",
            "custom_western_keywords": "",
            "custom_chinese_keywords": "",
            "custom_other_keywords": "",
            "strict_match": False,
            "hijack_fallback_system": False,
            "keyword_failed_download": True,
            "show_failure_detail": True
        }

    def get_page(self) -> List[dict]:
        """插件详情页面 - 日志查看"""
        # 获取当前日志
        logs_data = self.get_logs()

        return [
            {
                "component": "VCard",
                "props": {"class": "mb-4"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "props": {"class": "d-flex align-center"},
                        "content": [
                            {
                                "component": "span",
                                "text": "识别记录"
                            },
                            {
                                "component": "VSpacer"
                            },
                            {
                                "component": "VBtn",
                                "props": {
                                    "color": "primary",
                                    "variant": "tonal",
                                    "size": "small",
                                    "class": "mr-2"
                                },
                                "text": "刷新",
                                "events": {
                                    "click": {
                                        "action": "refresh",
                                        "api": "/plugin/v1/metatubesource/logs",
                                        "method": "GET"
                                    }
                                }
                            },
                            {
                                "component": "VBtn",
                                "props": {
                                    "color": "error",
                                    "variant": "tonal",
                                    "size": "small"
                                },
                                "text": "清空",
                                "events": {
                                    "click": {
                                        "action": "submit",
                                        "api": "/plugin/v1/metatubesource/clear_logs",
                                        "method": "POST"
                                    }
                                }
                            }
                        ]
                    },
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VTable",
                                "props": {
                                    "hover": True,
                                    "density": "compact"
                                },
                                "content": [
                                    {
                                        "component": "thead",
                                        "content": [
                                            {
                                                "component": "tr",
                                                "content": [
                                                    {"component": "th", "text": "时间"},
                                                    {"component": "th", "text": "关键词"},
                                                    {"component": "th", "text": "结果"},
                                                    {"component": "th", "text": "状态"},
                                                    {"component": "th", "text": "详情"}
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "tbody",
                                        "content": self._build_log_rows()
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def _build_log_rows(self) -> List[dict]:
        """构建日志表格行"""
        rows = []
        if self._log_entries:
            for log in reversed(list(self._log_entries)):
                status_color = "success" if log.status == "success" else "error"
                rows.append({
                    "component": "tr",
                    "content": [
                        {"component": "td", "text": log.timestamp},
                        {"component": "td", "text": log.keyword},
                        {"component": "td", "text": log.result[:30] + "..." if len(log.result) > 30 else log.result},
                        {
                            "component": "td",
                            "content": [
                                {
                                    "component": "VChip",
                                    "props": {"color": status_color, "size": "x-small"},
                                    "text": log.status
                                }
                            ]
                        },
                        {"component": "td", "text": log.message[:50] + "..." if len(log.message) > 50 else log.message}
                    ]
                })
        if not rows:
            rows.append({
                "component": "tr",
                "content": [
                    {
                        "component": "td",
                        "props": {"colspan": 5, "class": "text-center text-disabled"},
                        "text": "暂无识别日志"
                    }
                ]
            })
        return rows

    def stop_service(self):
        """退出插件"""
        if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                self._original_method):
            ChainBase.recognize_media = self._original_method
        if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                self._original_async_method):
            ChainBase.async_recognize_media = self._original_async_method

    def get_module(self) -> Dict[str, Any]:
        """获取插件模块声明，用于劫持系统模块实现"""
        modules = {}
        if self._enabled and self._recognition_mode == 'hijacking':
            modules['async_recognize_media'] = self.async_recognize_media
            modules['recognize_media'] = self.recognize_media
        return modules

    def _update_config(self):
        """更新配置"""
        self.update_config({
            "enabled": self._enabled,
            "api_url": self._api_url,
            "recognition_mode": self._recognition_mode,
            "timeout": self._timeout,
            "max_logs": self._max_logs,
            "custom_japanese_keywords": self._custom_japanese_keywords,
            "custom_western_keywords": self._custom_western_keywords,
            "custom_chinese_keywords": self._custom_chinese_keywords,
            "custom_other_keywords": self._custom_other_keywords,
            "strict_match": self._strict_match,
            "hijack_fallback_system": self._hijack_fallback_system,
            "keyword_failed_download": self._keyword_failed_download,
            "show_failure_detail": self._show_failure_detail
        })

    def _add_log(self, keyword: str, result: str, status: str, message: str):
        """添加日志条目"""
        if self._log_entries is None:
            self._log_entries = deque(maxlen=self._max_logs)
        log_entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level="INFO" if status == "success" else "WARNING",
            keyword=keyword,
            result=result,
            status=status,
            message=message
        )
        self._log_entries.append(log_entry)

    def _get_all_keywords(self) -> List[str]:
        """获取所有关键字（内置 + 自定义）"""
        keywords = []

        # 添加所有分类的内置关键字
        keywords.extend(self.BUILT_IN_JAPANESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_WESTERN_KEYWORDS)
        keywords.extend(self.BUILT_IN_CHINESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_OTHER_KEYWORDS)

        # 添加自定义关键字
        if self._custom_japanese_keywords:
            custom_list = [kw.strip() for kw in self._custom_japanese_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_western_keywords:
            custom_list = [kw.strip() for kw in self._custom_western_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_chinese_keywords:
            custom_list = [kw.strip() for kw in self._custom_chinese_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_other_keywords:
            custom_list = [kw.strip() for kw in self._custom_other_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)

        return list(set(keywords))  # 去重

    def _detect_category_type(self, title: str) -> str:
        """
        检测标题匹配的关键字类型，返回二级分类名称

        :param title: 标题文本
        :return: 二级分类名称：日系/欧美系/中文系/其他
        """
        if not title:
            return "其他"

        # 标准化标题
        search_title = title
        if not self._strict_match:
            search_title = title.upper()
            search_title = search_title.replace('－', '-').replace('＿', '_')

        # 按优先级检测：日系 > 欧美系 > 中文系 > 其他
        categories = [
            ("日系", self.BUILT_IN_JAPANESE_KEYWORDS, self._custom_japanese_keywords),
            ("欧美系", self.BUILT_IN_WESTERN_KEYWORDS, self._custom_western_keywords),
            ("中文系", self.BUILT_IN_CHINESE_KEYWORDS, self._custom_chinese_keywords),
            ("其他", self.BUILT_IN_OTHER_KEYWORDS, self._custom_other_keywords),
        ]

        for category_name, built_in_keywords, custom_keywords in categories:
            # 检查内置关键字
            for keyword in built_in_keywords:
                search_keyword = keyword.upper() if not self._strict_match else keyword
                if search_keyword in search_title:
                    logger.debug(f"Metatube: 匹配到{category_name}关键字 '{keyword}' 在标题 '{title}' 中")
                    return category_name

            # 检查自定义关键字
            if custom_keywords:
                custom_list = [kw.strip() for kw in custom_keywords.split(',') if kw.strip()]
                for keyword in custom_list:
                    search_keyword = keyword.upper() if not self._strict_match else keyword
                    if search_keyword in search_title:
                        logger.debug(f"Metatube: 匹配到{category_name}自定义关键字 '{keyword}' 在标题 '{title}' 中")
                        return category_name

        return "其他"

    def _match_keywords(self, meta: MetaBase) -> bool:
        """
        检查元数据是否匹配关键字

        :param meta: 元数据对象
        :return: 是否匹配
        """
        if not meta:
            return False

        # 获取所有关键字
        keywords = self._get_all_keywords()
        if not keywords:
            return False

        # 获取标题（优先级：原始名称 > 中文名 > 英文名）
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or ""
        if not title:
            return False

        # 标准化标题
        if not self._strict_match:
            # 非严格模式：转大写，统一全半角
            title = title.upper()
            title = title.replace('－', '-').replace('＿', '_')
            keywords = [kw.upper() for kw in keywords]

        # 检查是否包含任意关键字
        for keyword in keywords:
            if keyword in title:
                logger.debug(f"Metatube: 匹配到关键字 '{keyword}' 在标题 '{title}' 中")
                return True

        return False

    def _extract_number_from_meta(self, meta: MetaBase) -> Optional[str]:
        """从元数据中提取番号"""
        if not meta:
            return None

        # 优先从原始名称提取
        name = meta.org_string or meta.name or ""
        number = MetatubeApiClient.extract_number(name)
        if number:
            return number

        # 尝试从中文名提取
        if meta.cn_name:
            number = MetatubeApiClient.extract_number(meta.cn_name)
            if number:
                return number

        # 尝试从英文名提取
        if meta.en_name:
            number = MetatubeApiClient.extract_number(meta.en_name)
            if number:
                return number

        return None

    def _convert_to_mediainfo(self, movie: MetatubeMovie, detail: Optional[MetatubeMovieDetail] = None) -> MediaInfo:
        """将 Metatube 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'metatube'
        mediainfo.type = MediaType.MOVIE  # 番号内容通常作为电影处理

        # 基础信息
        mediainfo.title = movie.title or movie.number
        mediainfo.original_title = movie.number

        # 解析发布日期获取年份
        if movie.release_date:
            try:
                # 处理 ISO 格式日期: 2025-09-05T00:00:00Z
                date_str = movie.release_date.split('T')[0]
                mediainfo.year = date_str[:4]
                mediainfo.release_date = date_str
            except Exception:
                pass

        # 使用番号作为标识
        mediainfo.imdb_id = movie.number

        # 封面和海报
        if movie.cover_url:
            mediainfo.poster_path = movie.cover_url
        if movie.thumb_url:
            mediainfo.backdrop_path = movie.thumb_url

        # 评分
        if movie.score:
            mediainfo.vote_average = round(float(movie.score), 1)

        # 演员
        if movie.actors:
            mediainfo.actor = [{"name": actor} for actor in movie.actors]

        # 如果有详情，补充更多信息
        if detail:
            if detail.summary:
                mediainfo.overview = detail.summary
            if detail.director:
                mediainfo.director = [{"name": detail.director}]
            if detail.genres:
                mediainfo.genres = [{"id": g, "name": g} for g in detail.genres]
            if detail.runtime:
                mediainfo.runtime = detail.runtime
            if detail.poster_url:
                mediainfo.poster_path = detail.poster_url
            if detail.images:
                mediainfo.backdrop_path = detail.images[0] if detail.images else mediainfo.backdrop_path

        # 检测二级分类
        title = movie.title or movie.number or ""
        subcategory = self._detect_category_type(title)
        category = f"成人/{subcategory}"

        # 设置分类（使用二级分类）
        mediainfo.set_category(category)
        logger.info(f"Metatube: 分类设置为 '{category}' (基于标题: {title})")

        return mediainfo

    def recognize_media(self, meta: MetaBase = None,
                        mtype: MediaType = None,
                        **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息

        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None

        if not meta:
            return None

        # 关键字触发模式：检查是否匹配关键字
        if self._recognition_mode == 'keyword':
            if not self._match_keywords(meta):
                logger.debug(f"Metatube: 标题不包含关键字，跳过识别")
                return None

        # 提取番号
        number = self._extract_number_from_meta(meta)
        if not number:
            logger.debug(f"Metatube: 无法从 '{meta.name}' 中提取番号")
            return None

        logger.info(f"Metatube: 正在识别番号 {number} ...")

        try:
            # 搜索
            results = self._metatube_client.search(number, fallback=True)
            if not results:
                # 识别失败处理
                failure_msg = "未找到匹配结果" if self._show_failure_detail else "识别失败"
                self._add_log(number, "", "failed", failure_msg)
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")

                # 关键字触发模式：识别失败直接归类为"成人/其他"并返回
                if self._recognition_mode == 'keyword' and self._keyword_failed_download:
                    # 检测分类
                    subcategory = self._detect_category_type(number)
                    category = f"成人/{subcategory}"
                    logger.info(f"Metatube: 关键字触发模式识别失败，归类为'{category}'分类")
                    mediainfo = MediaInfo()
                    mediainfo.source = 'metatube'
                    mediainfo.type = MediaType.MOVIE
                    mediainfo.title = number
                    mediainfo.original_title = number
                    mediainfo.imdb_id = number
                    mediainfo.set_category(category)
                    self._add_log(number, f"{category} ({number})", "success", "识别失败但已归类为" + subcategory)
                    return mediainfo

                return None

            # 取第一个结果
            movie = results[0]

            # 尝试获取详情(可选)
            detail = None
            if movie.provider and movie.id:
                try:
                    detail = self._metatube_client.get_detail(movie.provider, movie.id)
                except Exception as e:
                    logger.debug(f"Metatube: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(movie, detail)

            self._add_log(number, f"{mediainfo.title} ({mediainfo.year})", "success",
                          f"来源: {movie.provider}")
            logger.info(f"Metatube: 识别成功 - {number} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            # 异常处理
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            self._add_log(number, "", "failed", failure_msg)
            logger.error(f"Metatube: 识别异常 - {str(e)}")

            # 关键字触发模式：识别异常直接归类为"成人/其他"并返回
            if self._recognition_mode == 'keyword' and self._keyword_failed_download:
                # 检测分类
                subcategory = self._detect_category_type(number)
                category = f"成人/{subcategory}"
                logger.info(f"Metatube: 关键字触发模式识别异常，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'metatube'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "识别异常但已归类为" + subcategory)
                return mediainfo

            return None

    async def async_recognize_media(self, meta: MetaBase = None,
                                    mtype: MediaType = None,
                                    **kwargs) -> Optional[MediaInfo]:
        """
        异步识别媒体信息

        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None

        if not meta:
            return None

        # 关键字触发模式：检查是否匹配关键字
        if self._recognition_mode == 'keyword':
            if not self._match_keywords(meta):
                logger.debug(f"Metatube: 标题不包含关键字，跳过识别")
                return None

        # 提取番号
        number = self._extract_number_from_meta(meta)
        if not number:
            logger.debug(f"Metatube: 无法从 '{meta.name}' 中提取番号")
            return None

        logger.info(f"Metatube: 正在异步识别番号 {number} ...")

        try:
            # 异步搜索
            results = await self._metatube_client.async_search(number, fallback=True)
            if not results:
                # 识别失败处理
                failure_msg = "未找到匹配结果" if self._show_failure_detail else "识别失败"
                self._add_log(number, "", "failed", failure_msg)
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")

                # 关键字触发模式：识别失败直接归类为"成人/其他"并返回
                if self._recognition_mode == 'keyword' and self._keyword_failed_download:
                    # 检测分类
                    subcategory = self._detect_category_type(number)
                    category = f"成人/{subcategory}"
                    logger.info(f"Metatube: 关键字触发模式识别失败，归类为'{category}'分类")
                    mediainfo = MediaInfo()
                    mediainfo.source = 'metatube'
                    mediainfo.type = MediaType.MOVIE
                    mediainfo.title = number
                    mediainfo.original_title = number
                    mediainfo.imdb_id = number
                    mediainfo.set_category(category)
                    self._add_log(number, f"{category} ({number})", "success", "识别失败但已归类为" + subcategory)
                    return mediainfo

                return None

            # 取第一个结果
            movie = results[0]

            # 尝试获取详情(可选)
            detail = None
            if movie.provider and movie.id:
                try:
                    detail = await self._metatube_client.async_get_detail(movie.provider, movie.id)
                except Exception as e:
                    logger.debug(f"Metatube: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(movie, detail)

            self._add_log(number, f"{mediainfo.title} ({mediainfo.year})", "success",
                          f"来源: {movie.provider}")
            logger.info(f"Metatube: 识别成功 - {number} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            # 异常处理
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            self._add_log(number, "", "failed", failure_msg)
            logger.error(f"Metatube: 异步识别异常 - {str(e)}")

            # 关键字触发模式：识别异常直接归类为"成人/其他"并返回
            if self._recognition_mode == 'keyword' and self._keyword_failed_download:
                # 检测分类
                subcategory = self._detect_category_type(number)
                category = f"成人/{subcategory}"
                logger.info(f"Metatube: 关键字触发模式识别异常，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'metatube'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "识别异常但已归类为" + subcategory)
                return mediainfo

            return None
