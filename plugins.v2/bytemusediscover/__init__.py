from typing import Any, List, Dict, Tuple

from app import schemas
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.core.cache import cached
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import DiscoverSourceEventData, MediaRecognizeConvertEventData
from app.schemas.types import ChainEventType
from app.utils.http import RequestUtils

from .bytemuse_api import ByteMuseApiClient
from .schema import ByteMuseMovie, ByteMuseActor


# 探索类型配置
DISCOVER_TYPES = {
    "actors": {
        "name": "演员",
        "media_type": "tv",
    },
    "new_releases": {
        "name": "今日上新",
        "media_type": "movie",
    },
    "recommendations": {
        "name": "个性化推荐",
        "media_type": "movie",
    },
    "rankings_daily": {
        "name": "日榜",
        "media_type": "movie",
    },
    "rankings_weekly": {
        "name": "周榜",
        "media_type": "movie",
    },
    "rankings_monthly": {
        "name": "月榜",
        "media_type": "movie",
    },
    "rankings_javlibrary": {
        "name": "JavLibrary榜单",
        "media_type": "movie",
    },
    "studio_s1": {
        "name": "S1厂牌",
        "media_type": "movie",
    },
    "studio_ideapocket": {
        "name": "IdeaPocket厂牌",
        "media_type": "movie",
    },
    "studio_moodyz": {
        "name": "Moodyz厂牌",
        "media_type": "movie",
    },
    "studio_premium": {
        "name": "Premium厂牌",
        "media_type": "movie",
    },
    "studio_das": {
        "name": "DAS厂牌",
        "media_type": "movie",
    },
    "studio_madonna": {
        "name": "Madonna厂牌",
        "media_type": "movie",
    },
    "studio_honnaka": {
        "name": "Honnaka厂牌",
        "media_type": "movie",
    },
    "studio_attackers": {
        "name": "Attackers厂牌",
        "media_type": "movie",
    },
    "studio_wanz": {
        "name": "Wanz厂牌",
        "media_type": "movie",
    },
}


class ByteMuseDiscover(_PluginBase):
    # 插件名称
    plugin_name = "ByteMuse探索"
    # 插件描述
    plugin_desc = "基于 ByteMuse API 的探索数据源插件，提供演员、上新、推荐、榜单、厂牌等探索服务。"
    # 插件图标
    plugin_icon = "ExploreServices.png"
    # 插件版本
    plugin_version = "2.0.0"
    # 插件作者
    plugin_author = "Mubey"
    # 作者主页
    author_url = "https://github.com/mubey"
    # 插件配置项ID前缀
    plugin_config_prefix = "bytemusediscover_"
    # 加载顺序
    plugin_order = 13
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False

    # ByteMuse API 配置
    _bytemuse_base_url: str = ""
    _bytemuse_username: str = ""
    _bytemuse_password: str = ""
    _bytemuse_api_token: str = ""

    # API 客户端
    _api_client: ByteMuseApiClient = None

    @staticmethod
    def _proxy_image_url(url: str) -> str:
        """
        将图片 URL 转换为 MoviePilot 图片代理路径
        解决 DMM 等外部图片源防盗链问题
        """
        if not url:
            return ""
        if not url.startswith("http"):
            return url
        from urllib.parse import quote
        # 使用 /api/v1/cache/image 代理（无域名白名单限制）
        # 但需要服务端支持 DMM Referer，所以通过插件自身 API 代理
        return f"/api/v1/plugin/ByteMuseDiscover/image?url={quote(url, safe='')}"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)

            # 读取 ByteMuse API 配置
            self._bytemuse_base_url = config.get("bytemuse_base_url", "")
            self._bytemuse_username = config.get("bytemuse_username", "")
            self._bytemuse_password = config.get("bytemuse_password", "")
            self._bytemuse_api_token = config.get("bytemuse_api_token", "")

            # 初始化 API 客户端
            if self._bytemuse_base_url:
                self._api_client = ByteMuseApiClient(
                    base_url=self._bytemuse_base_url,
                    username=self._bytemuse_username,
                    password=self._bytemuse_password,
                    api_token=self._bytemuse_api_token,
                )
                logger.info(f"ByteMuse API 客户端初始化成功: {self._bytemuse_base_url}")
            else:
                logger.warning("ByteMuse API 地址未配置")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/bytemuse_discover",
                "endpoint": self.bytemuse_discover,
                "methods": ["GET"],
                "summary": "ByteMuse探索数据源",
                "description": "获取ByteMuse探索数据",
            },
            {
                "path": "/bytemuse_media/<string:mediaid>",
                "endpoint": self.bytemuse_media,
                "methods": ["GET"],
                "summary": "ByteMuse媒体详情",
                "description": "获取ByteMuse媒体详情信息",
            },
            {
                "path": "/image",
                "endpoint": self.proxy_image,
                "methods": ["GET"],
                "summary": "图片代理",
                "description": "代理DMM等外部图片，解决防盗链",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        return [
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
                                        "text": "基础设置"
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
                                                            "model": "enabled",
                                                            "label": "启用插件",
                                                        },
                                                    }
                                                ],
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VCard",
                        "props": {
                            "variant": "flat",
                            "class": "mt-3",
                            "color": "surface"
                        },
                        "content": [
                            {
                                "component": "VCardItem",
                                "props": {
                                    "class": "px-6 pb-0"
                                },
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {
                                            "class": "d-flex align-center text-h6"
                                        },
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {
                                                    "style": "color: #16b1ff;",
                                                    "class": "mr-2"
                                                },
                                                "text": "mdi-api"
                                            },
                                            {
                                                "component": "span",
                                                "text": "ByteMuse API 配置"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VDivider"
                            },
                            {
                                "component": "VCardText",
                                "props": {
                                    "class": "px-6"
                                },
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            # API 地址
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "bytemuse_base_url",
                                                            "label": "ByteMuse API 地址",
                                                            "placeholder": "http://10.0.0.1:3750",
                                                            "variant": "outlined",
                                                            "density": "compact",
                                                            "hint": "ByteMuse API 服务地址",
                                                        }
                                                    }
                                                ],
                                            },
                                            # 用户名
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "bytemuse_username",
                                                            "label": "用户名",
                                                            "placeholder": "mubey",
                                                            "variant": "outlined",
                                                            "density": "compact",
                                                            "hint": "ByteMuse API 用户名",
                                                        }
                                                    }
                                                ],
                                            },
                                            # 密码
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "bytemuse_password",
                                                            "label": "密码",
                                                            "placeholder": "••••••",
                                                            "variant": "outlined",
                                                            "density": "compact",
                                                            "type": "password",
                                                            "hint": "ByteMuse API 密码",
                                                        }
                                                    }
                                                ],
                                            },
                                            # API Token (备用)
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "bytemuse_api_token",
                                                            "label": "API Token (可选)",
                                                            "placeholder": "Bearer Token",
                                                            "variant": "outlined",
                                                            "density": "compact",
                                                            "hint": "可选,推荐使用用户名密码登录",
                                                            "clearable": True,
                                                        }
                                                    }
                                                ],
                                            },
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VDivider"
                            },
                            {
                                "component": "VCardText",
                                "props": {
                                    "class": "px-6"
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {
                                            "class": "text-body-2 text-grey"
                                        },
                                        "content": [
                                            {
                                                "component": "p",
                                                "text": "认证方式："
                                            },
                                            {
                                                "component": "ul",
                                                "props": {"class": "ml-4"},
                                                "content": [
                                                    {"component": "li", "text": "推荐使用用户名密码登录，系统会自动获取和管理 JWT Token"},
                                                    {"component": "li", "text": "API Token 为可选配置,用于兼容旧版认证方式"},
                                                ]
                                            },
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VCard",
                        "props": {
                            "variant": "flat",
                            "class": "mt-3",
                            "color": "surface"
                        },
                        "content": [
                            {
                                "component": "VCardItem",
                                "props": {
                                    "class": "px-6 pb-0"
                                },
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {
                                            "class": "d-flex align-center text-h6"
                                        },
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {
                                                    "style": "color: #16b1ff;",
                                                    "class": "mr-2"
                                                },
                                                "text": "mdi-information"
                                            },
                                            {
                                                "component": "span",
                                                "text": "使用说明"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VDivider"
                            },
                            {
                                "component": "VCardText",
                                "props": {
                                    "class": "px-6"
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {
                                            "class": "text-body-1"
                                        },
                                        "text": "基于 ByteMuse API 的探索数据源插件，提供演员、上新、推荐、榜单、厂牌等探索服务。"
                                    },
                                    {
                                        "component": "div",
                                        "props": {
                                            "class": "text-body-1 mt-2"
                                        },
                                        "content": [
                                            {
                                                "component": "span",
                                                "text": "数据源: "
                                            },
                                            {
                                                "component": "a",
                                                "props": {
                                                    "href": "https://github.com/ByteDance/ByteMuse",
                                                    "target": "_blank",
                                                    "style": "color: #16b1ff; text-decoration: underline;"
                                                },
                                                "text": "ByteMuse"
                                            },
                                        ]
                                    },
                                    {
                                        "component": "div",
                                        "props": {
                                            "class": "text-body-2 mt-2"
                                        },
                                        "text": "探索类型: 演员、今日上新、个性化推荐、日榜/周榜/月榜、JavLibrary榜单、9个厂牌榜单"
                                    },
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "bytemuse_base_url": "",
            "bytemuse_username": "",
            "bytemuse_password": "",
            "bytemuse_api_token": "",
        }

    def get_page(self) -> List[dict]:
        pass

    def proxy_image(self, url: str = ""):
        """
        图片代理端点 - 为 DMM 等外部图片源添加 Referer 头
        """
        if not url:
            return {"error": "url parameter required"}, 400

        from starlette.responses import StreamingResponse
        try:
            # 根据域名设置对应的 Referer
            referer = None
            if "dmm.co.jp" in url or "awsimgsrc.dmm.co.jp" in url:
                referer = "https://www.dmm.co.jp/"
            elif "javbus.com" in url:
                referer = "https://www.javbus.com/"

            headers = self._api_client.DEFAULT_HEADERS.copy() if self._api_client else {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            if referer:
                headers["Referer"] = referer

            response = RequestUtils(
                timeout=15,
                headers=headers,
            ).get_res(url=url)

            if response is None or response.status_code != 200:
                return {"error": "failed to fetch image"}, 502

            content = response.content
            content_type = response.headers.get("Content-Type", "image/jpeg")

            return StreamingResponse(
                iter([content]),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        except Exception as e:
            logger.error(f"图片代理失败: {str(e)}")
            return {"error": str(e)}, 500

    def bytemuse_discover(
        self,
        discover_type: str = "new_releases",
        page: int = 1,
        count: int = 20,
    ) -> List[schemas.MediaInfo]:
        """
        获取 ByteMuse 探索数据
        """

        def __movie_to_media(movie_info: dict) -> schemas.MediaInfo:
            """
            电影数据转换为 MediaInfo
            """
            try:
                # 番号（必须先提取，其他地方会用到）
                code = movie_info.get("code", "")

                # 提取演员信息
                actor_names = []
                if movie_info.get("actors"):
                    if isinstance(movie_info["actors"], list):
                        actor_names = [a.get("name", "") if isinstance(a, dict) else str(a)
                                      for a in movie_info["actors"] if a]
                    elif isinstance(movie_info["actors"], str):
                        actor_names = [movie_info["actors"]]
                elif movie_info.get("casts"):
                    actor_names = [name.strip() for name in movie_info["casts"].split(',') if name.strip()]

                # 提取年份（保持为字符串，参考 bytemuseservices）
                year = None
                if movie_info.get("release_date"):
                    try:
                        year = movie_info["release_date"][:4]  # ✅ 字符串，不是 int
                    except (IndexError, TypeError):
                        year = None

                # 评分
                vote_average = movie_info.get("score")

                # 海报 - ByteMuse API 返回字段为 poster/banner（非 poster_url/cover_url）
                raw_poster = (movie_info.get("poster") or
                              movie_info.get("poster_url") or
                              movie_info.get("banner") or
                              movie_info.get("cover_url") or
                              movie_info.get("thumb_url") or
                              movie_info.get("preview_url") or "")
                # 通过 MoviePilot 图片代理，解决 DMM 防盗链问题
                poster_path = self._proxy_image_url(raw_poster) if raw_poster else ""

                # 调试：记录图片 URL
                if poster_path:
                    logger.debug(f"图片 URL [{code}]: {poster_path[:100]}")
                else:
                    logger.warning(f"未找到图片 URL: {code}, 可用字段: poster={bool(movie_info.get('poster_url'))}, cover={bool(movie_info.get('cover_url'))}, thumb={bool(movie_info.get('thumb_url'))}, banner={bool(movie_info.get('banner'))}")

                # 标题
                title = movie_info.get("title") or movie_info.get("cn_title") or code

                # 厂牌
                studio = movie_info.get("studio") or movie_info.get("publisher") or ""

                # 导演列表（注意是复数 directors）
                directors_list = []
                if movie_info.get("director"):
                    directors_list = [movie_info.get("director")]

                # 类型标签
                genres = []
                if movie_info.get("genres"):
                    if isinstance(movie_info["genres"], str):
                        genres = [g.strip() for g in movie_info["genres"].split(',') if g.strip()]
                    elif isinstance(movie_info["genres"], list):
                        genres = [str(g) for g in movie_info["genres"] if g]

                # 确保 media_id 不为空
                media_id = code or title or f"unknown"

                # 构建 MediaInfo（参考 metatubesource 的 _convert_bytemuse_to_mediainfo）
                mediainfo = schemas.MediaInfo(
                    type="电影",
                    title=title,
                    mediaid_prefix="bytemuse",
                    media_id=code,  # 番号
                    imdb_id=code,  # ✅ 直接使用番号，不带前缀（与 metatubesource 一致）
                    poster_path=poster_path,
                    vote_average=vote_average,
                    year=year,
                    overview=movie_info.get("summary") or f"番号: {code}",
                    studio=studio,
                )

                # 设置 source（与 metatubesource 一致）
                if hasattr(mediainfo, 'source'):
                    mediainfo.source = 'bytemuse'

                # 设置 original_title
                if hasattr(mediainfo, 'original_title'):
                    mediainfo.original_title = code

                # 调试：记录关键字段
                logger.debug(f"MediaInfo 创建: media_id={mediainfo.media_id}, imdb_id={mediainfo.imdb_id}, source={getattr(mediainfo, 'source', 'N/A')}")

                # 通过属性设置可选字段（与官方 metatubesource 保持一致）
                # director（单数，单个对象）
                if directors_list:
                    try:
                        # 如果有多个导演，只取第一个（与官方一致）
                        mediainfo.director = {"name": directors_list[0]}
                    except Exception as e:
                        logger.debug(f"设置 director 失败: {e}")

                # actor（单数，列表格式，与官方一致）
                if actor_names:
                    try:
                        mediainfo.actor = [{"name": name} for name in actor_names]
                    except Exception as e:
                        logger.debug(f"设置 actor 失败: {e}")

                if genres:
                    try:
                        mediainfo.genres = genres
                    except Exception as e:
                        logger.debug(f"设置 genres 失败: {e}")

                return mediainfo

            except Exception as e:
                logger.error(f"__movie_to_media 转换失败: {str(e)}, code={movie_info.get('code')}")
                import traceback
                logger.debug(f"错误详情: {traceback.format_exc()}")
                # 返回最小可用的 MediaInfo
                return schemas.MediaInfo(
                    type="电影",
                    title=movie_info.get("title") or movie_info.get("code") or "未知",
                    mediaid_prefix="bytemuse",
                    media_id=movie_info.get("code") or "unknown",
                )

        try:
            if not self._api_client:
                logger.error("ByteMuse API 客户端未初始化")
                return []

            result = self._api_client.get_discover_data(
                discover_type=discover_type,
                page=page,
                page_size=count
            )

            if not result:
                return []

            results = [__movie_to_media(movie) for movie in result]

            # 调试：记录返回结果
            logger.info(f"bytemuse_discover 返回 {len(results)} 条数据")
            if results:
                first = results[0]
                logger.info(f"第一条数据: title={first.title}, media_id={first.media_id}, poster_exists={bool(first.poster_path)}, poster_length={len(first.poster_path) if first.poster_path else 0}")
                if first.poster_path:
                    logger.info(f"海报 URL: {first.poster_path[:150]}")

            return results

        except Exception as err:
            logger.error(f"获取 ByteMuse 数据失败: {str(err)}")
            return []

    def bytemuse_media(self, mediaid: str, **kwargs) -> schemas.MediaInfo:
        """
        获取媒体详情（API 端点）

        :param mediaid: 媒体ID (格式: bytemuse:SSIS-123 或 SSIS-123)
        :return: MediaInfo 对象
        """
        logger.info(f"bytemuse_media 被调用: mediaid={mediaid}")

        # 提取番号
        if mediaid.startswith("bytemuse:"):
            code = mediaid.replace("bytemuse:", "", 1)
        else:
            code = mediaid

        if not code:
            logger.warning("bytemuse_media: 番号不能为空")
            return None

        # 获取详情
        mediainfo = self._fetch_bytemuse_detail(code)

        if mediainfo:
            logger.info(f"bytemuse_media: 成功获取详情 - {mediainfo.title}")
        else:
            logger.warning(f"bytemuse_media: 未找到番号 - {code}")

        return mediainfo

    def recognize_media(self, meta=None, mtype=None, **kwargs):
        """
        识别媒体信息（用于点击探索项时显示详情）
        """
        if not meta:
            return None

        # 获取 mediaid
        mediaid = kwargs.get("mediaid", "")
        imdb_id = kwargs.get("imdb_id", "")

        logger.debug(f"recognize_media 被调用: mediaid={mediaid}, imdb_id={imdb_id}")

        # 提取番号（优先使用 mediaid，其次 imdb_id）
        # 注意：现在 imdb_id 已经是纯番号，不带 "bytemuse:" 前缀
        code = None
        if mediaid:
            if mediaid.startswith("bytemuse:"):
                code = mediaid.replace("bytemuse:", "", 1)
            else:
                code = mediaid
        elif imdb_id:
            # 直接使用 imdb_id（已经是纯番号）
            code = imdb_id

        if not code:
            return None

        logger.info(f"recognize_media: 识别 ByteMuse 番号: {code}")

        # 调用详情获取
        return self._fetch_bytemuse_detail(code)

    async def async_recognize_media(self, meta=None, mtype=None, **kwargs):
        """
        异步识别媒体信息（用于点击探索项时显示详情）
        """
        if not meta:
            return None

        # 获取 mediaid
        mediaid = kwargs.get("mediaid", "")
        imdb_id = kwargs.get("imdb_id", "")

        logger.debug(f"async_recognize_media 被调用: mediaid={mediaid}, imdb_id={imdb_id}")

        # 检查是否是 ByteMuse 的数据（通过 mediaid_prefix 或 imdb_id）
        # 注意：imdb_id 现在是纯番号（如 SSIS-123），没有前缀
        # 我们通过其他方式判断，比如检查番号格式

        # 提取番号（优先使用 mediaid）
        code = None
        if mediaid:
            # mediaid 可能是 "bytemuse:SSIS-123" 或 "SSIS-123"
            if mediaid.startswith("bytemuse:"):
                code = mediaid.replace("bytemuse:", "", 1)
            else:
                code = mediaid
        elif imdb_id:
            # 直接使用 imdb_id（已经是纯番号）
            code = imdb_id

        if not code:
            return None

        logger.info(f"async_recognize_media: 识别 ByteMuse 番号: {code}")

        # 异步调用详情获取
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = await loop.run_in_executor(pool, self._fetch_bytemuse_detail, code)
                return result
        except Exception as err:
            logger.error(f"async_recognize_media 获取详情失败: {str(err)}")
            return None

    def _fetch_bytemuse_detail(self, code: str):
        """
        从 ByteMuse API 获取详情
        """
        if not code:
            return None

        if not self._api_client:
            logger.warning("_fetch_bytemuse_detail: API 客户端未初始化")
            return None

        try:
            # 使用搜索接口获取详情
            result = self._api_client.search_by_code(query=code)

            if not result:
                logger.warning(f"_fetch_bytemuse_detail: 未找到番号: {code}")
                return None

            # 解析返回的数据
            codes = result.get("codes", [])
            if not codes:
                logger.warning(f"_fetch_bytemuse_detail: codes 列表为空: {code}")
                return None

            # 取第一个匹配结果
            movie_data = codes[0]
            logger.info(f"_fetch_bytemuse_detail: 找到详情: {movie_data.get('title') or movie_data.get('code')}")

            # 转换为 MediaInfo（使用 __movie_to_media）
            return self._movie_to_media_dict(movie_data)

        except Exception as err:
            logger.error(f"_fetch_bytemuse_detail 获取失败: {str(err)}")
            return None

    def _movie_to_media_dict(self, movie_info: dict):
        """
        将字典转换为 MediaInfo（与 __movie_to_media 相同的逻辑）
        """
        try:
            # 番号（必须先提取）
            code = movie_info.get("code", "")

            # 提取演员信息
            actor_names = []
            if movie_info.get("actors"):
                if isinstance(movie_info["actors"], list):
                    actor_names = [a.get("name", "") if isinstance(a, dict) else str(a)
                                  for a in movie_info["actors"] if a]
                elif isinstance(movie_info["actors"], str):
                    actor_names = [movie_info["actors"]]
            elif movie_info.get("casts"):
                actor_names = [name.strip() for name in movie_info["casts"].split(',') if name.strip()]

            # 提取年份
            year = None
            if movie_info.get("release_date"):
                try:
                    year = movie_info["release_date"][:4]
                except (IndexError, TypeError):
                    year = None

            # 评分
            vote_average = movie_info.get("score")

            # 海报 - ByteMuse API 返回字段为 poster/banner
            raw_poster = (movie_info.get("poster") or
                          movie_info.get("poster_url") or
                          movie_info.get("banner") or
                          movie_info.get("cover_url") or
                          movie_info.get("thumb_url") or
                          movie_info.get("preview_url") or "")
            # 通过 MoviePilot 图片代理，解决 DMM 防盗链问题
            poster_path = self._proxy_image_url(raw_poster) if raw_poster else ""

            # 标题
            title = movie_info.get("title") or movie_info.get("cn_title") or code

            # 厂牌
            studio = movie_info.get("studio") or movie_info.get("publisher") or ""

            # 导演列表
            directors_list = []
            if movie_info.get("director"):
                directors_list = [movie_info.get("director")]

            # 类型标签
            genres = []
            if movie_info.get("genres"):
                if isinstance(movie_info["genres"], str):
                    genres = [g.strip() for g in movie_info["genres"].split(',') if g.strip()]
                elif isinstance(movie_info["genres"], list):
                    genres = [str(g) for g in movie_info["genres"] if g]

            # 确保 media_id 不为空
            media_id = code or title or f"unknown"

            # 构建 MediaInfo
            mediainfo = schemas.MediaInfo(
                type="电影",
                title=title,
                mediaid_prefix="bytemuse",
                media_id=media_id,
                imdb_id=code,  # ✅ 直接使用番号，不带前缀（与 metatubesource 一致）
                poster_path=poster_path,
                vote_average=vote_average,
                year=year,
                overview=movie_info.get("summary") or f"番号: {code}",
                studio=studio,
            )

            # 设置可选字段（与官方 metatubesource 保持一致）
            # source 字段
            if hasattr(mediainfo, 'source'):
                mediainfo.source = 'bytemuse'

            # original_title
            if hasattr(mediainfo, 'original_title'):
                mediainfo.original_title = code

            # director（单数，单个对象）
            if directors_list:
                try:
                    mediainfo.director = {"name": directors_list[0]}
                except Exception:
                    pass

            # actor（单数，列表格式）
            if actor_names:
                try:
                    mediainfo.actor = [{"name": name} for name in actor_names]
                except Exception:
                    pass

            if genres:
                try:
                    mediainfo.genres = genres
                except Exception:
                    pass

            # 时长
            if movie_info.get("runtime"):
                try:
                    mediainfo.runtime = movie_info["runtime"]
                except Exception:
                    pass

            return mediainfo

        except Exception as e:
            logger.error(f"_movie_to_media_dict 转换失败: {str(e)}")
            return None

    @staticmethod
    def bytemuse_filter_ui() -> List[dict]:
        """
        ByteMuse 过滤参数UI配置
        """
        discover_type_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": value},
                "text": DISCOVER_TYPES[value]["name"],
            }
            for value in DISCOVER_TYPES
        ]

        ui = [
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "探索类型"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "discover_type"},
                        "content": discover_type_ui,
                    },
                ],
            },
        ]

        return ui

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        注册探索源事件
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        bytemuse_source = schemas.DiscoverMediaSource(
            name="ByteMuse",
            mediaid_prefix="bytemuse",
            api_path=f"plugin/ByteMuseDiscover/bytemuse_discover?apikey={settings.API_TOKEN}",
            filter_params={
                "discover_type": "new_releases",
            },
            filter_ui=self.bytemuse_filter_ui(),
            depends={},
        )
        if not event_data.extra_sources:
            event_data.extra_sources = [bytemuse_source]
        else:
            event_data.extra_sources.append(bytemuse_source)

    @eventmanager.register(ChainEventType.MediaRecognizeConvert)
    async def async_media_recognize_convert(self, event: Event):
        """
        监听媒体识别转换事件，处理详情页查询
        """
        if not self._enabled:
            return

        event_data: MediaRecognizeConvertEventData = event.event_data
        if not event_data:
            return

        # 检查是否是 ByteMuse 的 mediaid
        mediaid = event_data.mediaid or ""
        if not mediaid.startswith("bytemuse:"):
            return

        logger.info(f"ByteMuse: 处理媒体识别转换 - {mediaid}")

        # 提取番号
        code = mediaid.replace("bytemuse:", "", 1)

        # 获取详情
        mediainfo = await self.async_recognize_media(
            meta=event_data.meta,
            mtype=event_data.mtype,
            mediaid=mediaid
        )

        if mediainfo:
            logger.info(f"ByteMuse: 成功获取详情 - {mediainfo.title}")
            # 更新事件数据
            event_data.mediainfo = mediainfo

    def stop_service(self):
        """
        退出插件
        """
        pass
