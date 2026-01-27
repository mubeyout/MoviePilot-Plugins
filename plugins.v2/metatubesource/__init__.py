import re
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from app import schemas
from app.chain import ChainBase
from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.core.meta import MetaBase
from app.plugins import _PluginBase
from app.plugins.metatubesource.metatubehelper import MetatubeHelper
from app.log import logger
from app.schemas.types import ChainEventType, EventType, MediaType


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
    plugin_author = "mubey"
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
    _api_url: str = None
    _proxy: bool = False
    _recognize_media: bool = False

    # 私有属性
    _metatube_helper: MetatubeHelper = None
    _original_method: Optional[Callable] = None
    _original_async_method: Optional[Callable[..., Coroutine[Any, Any, Optional[MediaInfo]]]] = None

    def init_plugin(self, config: dict = None):
        logger.info(f"{self.plugin_name} 插件初始化...")

        plugin_instance: MetatubeSource = self

        def patched_recognize_media(chain_self, meta: MetaBase = None,
                                    mtype: Optional[MediaType] = None,
                                    tmdbid: Optional[int] = None,
                                    doubanid: Optional[str] = None,
                                    bangumiid: Optional[int] = None,
                                    episode_group: Optional[str] = None,
                                    cache: bool = True):
            # 调用原始方法
            if not plugin_instance._original_method:
                return None
            result = plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                      episode_group, cache)
            if result is None and MetatubeSource._enabled and MetatubeSource._recognize_media:
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
            # 调用原始方法
            if not plugin_instance._original_async_method:
                return None
            result = await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                  episode_group, cache)
            if result is None and MetatubeSource._enabled and MetatubeSource._recognize_media:
                logger.info(f"通过插件 {MetatubeSource.plugin_name} 执行：async_recognize_media ...")
                return await plugin_instance.async_recognize_media(meta, mtype)
            return result

        # 给 patch 函数加唯一标记
        setattr(patched_recognize_media, '_patched_by', id(self))
        # 保存原始方法
        if not getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self):
            self._original_method = getattr(ChainBase, "recognize_media", None)

        setattr(patched_async_recognize_media, '_patched_by', id(self))
        # 保存原始方法
        if not getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self):
            self._original_async_method = getattr(ChainBase, "async_recognize_media", None)

        # 设置默认值
        self._enabled = False
        self._api_url = "http://op.mubey.top:3244"
        self._proxy = False
        self._recognize_media = False

        # 加载配置
        if config:
            self._enabled = bool(config.get("enabled", False))
            self._api_url = config.get("api_url") or "http://op.mubey.top:3244"
            self._proxy = bool(config.get("proxy", False))
            self._recognize_media = bool(config.get("recognize_media", False))

        logger.info(f"{self.plugin_name} 配置加载: enabled={self._enabled}, "
                   f"api_url={self._api_url}, proxy={self._proxy}, "
                   f"recognize_media={self._recognize_media}")

        # 更新配置
        self._update_config()

        # 初始化 Metatube Helper
        self._metatube_helper = MetatubeHelper(
            api_url=self._api_url,
            proxies=settings.PROXY if self._proxy else None
        )

        if self._enabled and self._recognize_media:
            # 替换 ChainBase.recognize_media
            if not (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self)):
                ChainBase.recognize_media = patched_recognize_media
            # 替换 ChainBase.async_recognize_media
            if not getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self):
                ChainBase.async_recognize_media = patched_async_recognize_media
            logger.info(f"{self.plugin_name} 已启用媒体识别功能")
        else:
            self.stop_service()

    def get_state(self) -> bool:
        return self._enabled

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
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
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "recognize_media",
                                            "label": "媒体识别"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "proxy",
                                            "label": "使用代理服务器"
                                        },
                                    }
                                ],
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
                                            "label": "Metatube API地址",
                                            "placeholder": "http://op.mubey.top:3244",
                                            "hint": "Metatube API 服务地址"
                                        }
                                    }
                                ],
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
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "title": "使用说明",
                                            "text": "此插件通过 Metatube API 识别番号媒体信息。当 MoviePilot 无法识别时，会自动调用此插件进行识别。支持常见番号格式，如：SONE-702, ABC-123 等。"
                                        }
                                    }
                                ],
                            }
                        ],
                    },
                ]
            }
        ], {
            "enabled": False,
            "api_url": "http://op.mubey.top:3244",
            "proxy": False,
            "recognize_media": False
        }

    def get_page(self) -> List[dict]:
        pass

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                self._original_method):
            ChainBase.recognize_media = self._original_method
        if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                self._original_async_method):
            ChainBase.async_recognize_media = self._original_async_method

    def get_module(self) -> Dict[str, Any]:
        """
        获取插件模块声明
        """
        return {
            "recognize_media": self.recognize_media,
            "async_recognize_media": self.async_recognize_media
        }

    def _update_config(self):
        self.update_config(
            {
                "enabled": self._enabled,
                "api_url": self._api_url,
                "proxy": self._proxy,
                "recognize_media": self._recognize_media
            }
        )

    def recognize_media(self, meta: MetaBase = None,
                        mtype: MediaType = None,
                        **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息（同步）
        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None
        if kwargs.get('tmdbid') or kwargs.get('doubanid') or kwargs.get('bangumiid'):
            return None
        if not meta or not meta.name:
            logger.warn("识别媒体信息时未提供元数据名称")
            return None

        # 提取番号
        number = MetatubeHelper.extract_number(meta.name)
        if not number:
            logger.info(f"未从文件名中提取到番号: {meta.name}")
            return None

        logger.info(f"提取到番号: {number}")

        # 调用 Metatube API 搜索
        results = self._metatube_helper.search_movie(number)
        if not results:
            return None

        # 使用第一个结果
        movie = results[0]

        # 转换为 MediaInfo
        return self._convert_to_mediainfo(movie, meta)

    async def async_recognize_media(self, meta: MetaBase = None,
                                    mtype: MediaType = None,
                                    **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息（异步）
        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None
        if kwargs.get('tmdbid') or kwargs.get('doubanid') or kwargs.get('bangumiid'):
            return None
        if not meta or not meta.name:
            logger.warn("识别媒体信息时未提供元数据名称")
            return None

        # 提取番号
        number = MetatubeHelper.extract_number(meta.name)
        if not number:
            logger.info(f"未从文件名中提取到番号: {meta.name}")
            return None

        logger.info(f"提取到番号: {number}")

        # 调用 Metatube API 搜索
        results = await self._metatube_helper.async_search_movie(number)
        if not results:
            return None

        # 使用第一个结果
        movie = results[0]

        # 转换为 MediaInfo
        return self._convert_to_mediainfo(movie, meta)

    def _convert_to_mediainfo(self, movie, meta: MetaBase) -> MediaInfo:
        """
        将 Metatube 电影信息转换为 MediaInfo
        :param movie: Metatube 电影信息
        :param meta: 原始元数据
        :return: MediaInfo 对象
        """
        mediainfo = MediaInfo()

        # 基本信息
        mediainfo.title = movie.title
        mediainfo.type = MediaType.MOVIE

        # 番号作为年份字段存储（临时方案）
        mediainfo.year = movie.number

        # 设置名称（使用番号）
        mediainfo.name = movie.number
        mediainfo.en_name = movie.number

        # 演员
        if movie.actors:
            mediainfo.actors = movie.actors

        # 发布日期
        if movie.release_date:
            try:
                release_date = datetime.fromisoformat(movie.release_date.replace('Z', '+00:00'))
                mediainfo.release_date = release_date.strftime('%Y-%m-%d')
                mediainfo.year = release_date.strftime('%Y')
            except:
                pass

        # 评分
        if movie.score > 0:
            mediainfo.vote_average = movie.score * 2  # 转换为10分制

        # 链接
        if movie.homepage:
            mediainfo.home_url = movie.homepage

        # 图片
        if movie.cover_url:
            mediainfo.poster_path = movie.cover_url
        if movie.thumb_url:
            mediainfo.backdrop_path = movie.thumb_url

        # 保存原始信息
        mediainfo.overview = f"提供者: {movie.provider}\n番号: {movie.number}"

        logger.info(f"Metatube 识别成功: {movie.number} - {movie.title}")

        return mediainfo

    @eventmanager.register(EventType.PluginReload)
    def reload(self, event):
        """
        响应插件重载事件
        """
        plugin_id = event.event_data.get("plugin_id")
        if plugin_id == self.__class__.__name__:
            from app.scheduler import Scheduler
            Scheduler().update_plugin_job(plugin_id)
