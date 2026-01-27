"""
Metatube 媒体识别插件
通过 Metatube API 识别番号媒体信息
"""
import re
from collections import deque
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional, List, Tuple

from app import schemas
from app.chain import ChainBase
from app.core.config import settings
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
    plugin_version = "1.0.1"
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

    # 插件配置
    _enabled: bool = False
    _api_url: str = "http://127.0.0.1:8080"
    _recognition_mode: str = "auxiliary"  # auxiliary: 系统失败后识别, hijacking: 劫持识别
    _timeout: int = 10
    _max_logs: int = 100

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
            # 系统识别失败时使用 Metatube 识别
            if result is None and MetatubeSource._enabled:
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
            # 系统识别失败时使用 Metatube 识别
            if result is None and MetatubeSource._enabled:
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
            self._recognition_mode = config.get("recognition_mode") or "auxiliary"
            self._timeout = int(config.get("timeout") or 10)
            self._max_logs = int(config.get("max_logs") or 100)
            # 更新日志队列大小
            if self._log_entries.maxlen != self._max_logs:
                old_logs = list(self._log_entries)
                self._log_entries = deque(old_logs[-self._max_logs:], maxlen=self._max_logs)
            self._update_config()

        # 初始化API客户端
        self._metatube_client = MetatubeApiClient(
            base_url=self._api_url,
            timeout=self._timeout
        )

        if self._enabled:
            if self._recognition_mode == 'auxiliary':
                # 辅助模式：系统识别失败后使用
                if not (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self)):
                    ChainBase.recognize_media = patched_recognize_media
                if not getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self):
                    ChainBase.async_recognize_media = patched_async_recognize_media
            else:
                # 恢复原始方法(劫持模式使用 get_module)
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
        return [log.model_dump() for log in list(self._log_entries)]

    def clear_logs(self) -> Dict[str, Any]:
        """清空识别日志"""
        self._log_entries.clear()
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
                                            "label": "识别工作模式",
                                            "items": [
                                                {"title": "系统识别失败后接管", "value": "auxiliary"},
                                                {"title": "劫持系统识别", "value": "hijacking"}
                                            ]
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "timeout",
                                            "label": "请求超时",
                                            "type": "number",
                                            "placeholder": "10",
                                            "suffix": "秒",
                                            "hint": "API请求超时时间"
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
                                            "label": "Metatube API 地址",
                                            "placeholder": "http://127.0.0.1:8080",
                                            "hint": "Metatube 服务的API地址，例如: http://192.168.1.100:8080"
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
                                                        "text": "本插件通过 Metatube API 识别番号媒体信息。"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 系统识别失败后接管: 仅当 MoviePilot 原生识别失败时才使用 Metatube 识别"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 劫持系统识别: 优先使用 Metatube 进行识别"
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
            "recognition_mode": "auxiliary",
            "timeout": 10,
            "max_logs": 100
        }

    def get_page(self) -> List[dict]:
        """插件详情页面 - 日志查看"""
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
                                "text": "识别日志"
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
                                        "api": "plugin/MetatubeSource/logs",
                                        "method": "get"
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
                                        "api": "plugin/MetatubeSource/clear_logs",
                                        "method": "post"
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
            "max_logs": self._max_logs
        })

    def _add_log(self, keyword: str, result: str, status: str, message: str):
        """添加日志条目"""
        log_entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level="INFO" if status == "success" else "WARNING",
            keyword=keyword,
            result=result,
            status=status,
            message=message
        )
        self._log_entries.append(log_entry)

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

        # 设置分类
        mediainfo.set_category("番号")

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
                self._add_log(number, "", "failed", "未找到匹配结果")
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")
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
            self._add_log(number, "", "failed", str(e))
            logger.error(f"Metatube: 识别异常 - {str(e)}")
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
                self._add_log(number, "", "failed", "未找到匹配结果")
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")
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
            self._add_log(number, "", "failed", str(e))
            logger.error(f"Metatube: 异步识别异常 - {str(e)}")
            return None
