from typing import Any, List, Dict, Tuple
import json

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
    # 插件名称属性（用于事件处理）
    @property
    def name(self) -> str:
        return self.__class__.__name__
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

    def get_state(self) -> bool:
        return self._enabled

    # ByteMuse API 配置
    _bytemuse_base_url: str = ""
    _bytemuse_username: str = ""
    _bytemuse_password: str = ""
    _bytemuse_api_token: str = ""

    # API 客户端
    _api_client: ByteMuseApiClient = None

    # JavBus API 配置
    _javbus_api_base: str = ""

    @staticmethod
    def _proxy_image_url(url: str) -> str:
        if not url:
            return ""
        if not url.startswith("http"):
            return url
        from urllib.parse import quote
        return f"/api/v1/plugin/ByteMuseDiscover/image?url={quote(url, safe='')}"

    @staticmethod
    def _dmm_poster(code: str) -> str:
        """从番号构造 DMM poster URL"""
        if not code or '-' not in code:
            return ""
        parts = code.split('-', 1)
        prefix = parts[0].lower()
        num = parts[1].lower()
        if num.isdigit():
            num = num.zfill(5)
        from urllib.parse import quote
        return f"/api/v1/plugin/ByteMuseDiscover/image?url={quote('https://pics.dmm.co.jp/digital/video/' + prefix + num + '/' + prefix + num + 'ps.jpg', safe='')}"

    @staticmethod
    def _poster_or_dmm(img_url: str, code: str) -> str:
        """javbus.com 图片 403，回退到 DMM poster"""
        if img_url and "javbus.com" not in img_url:
            return ByteMuseDiscoverPlugin._proxy_image_url(img_url)
        return ByteMuseDiscoverPlugin._dmm_poster(code)

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

            # 读取 JavBus API 配置
            self._javbus_api_base = config.get("javbus_api_base", "")
            if self._javbus_api_base:
                logger.info(f"JavBus API 已配置: {self._javbus_api_base}")

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
                "path": "/bytemuse_media/{mediaid}",
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
                "allow_anonymous": True,
            },
            {
                "path": "/bytemuse_extra/{mediaid}",
                "endpoint": self.bytemuse_extra,
                "methods": ["GET"],
                "summary": "ByteMuse演员和剧照",
                "description": "获取演员阵容和剧照列表",
            },
            {
                "path": "/bytemuse_credits/{mediaid}",
                "endpoint": self.bytemuse_credits,
                "methods": ["GET"],
                "summary": "ByteMuse演员阵容",
                "description": "获取演员阵容（List[MediaPerson]格式）",
                "allow_anonymous": True,
            },
            {
                "path": "/bytemuse_similar/{mediaid}",
                "endpoint": self.bytemuse_similar,
                "methods": ["GET"],
                "summary": "ByteMuse类似作品",
                "description": "获取同演员作品（List[MediaInfo]格式）",
                "allow_anonymous": True,
            },
            {
                "path": "/bytemuse_recommend/{mediaid}",
                "endpoint": self.bytemuse_recommend,
                "methods": ["GET"],
                "summary": "ByteMuse推荐",
                "description": "获取热门推荐作品（List[MediaInfo]格式）",
                "allow_anonymous": True,
            },
            {
                "path": "/bytemuse_detail/{mediaid}",
                "endpoint": self.bytemuse_detail_public,
                "methods": ["GET"],
                "summary": "ByteMuse媒体详情（匿名）",
                "description": "获取剧照、同演员作品、今日上新，供前端注入使用",
                "allow_anonymous": True,
            },
            {
                "path": "/javbus_discover",
                "endpoint": self.javbus_discover,
                "methods": ["GET"],
                "summary": "JavBus探索数据",
                "description": "JavBus搜索和排行榜数据",
            },
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
                                "props": {"class": "px-6 pb-0"},
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {"class": "d-flex align-center text-h6"},
                                        "content": [
                                            {"component": "VIcon", "props": {"style": "color: #ff9800;", "class": "mr-2"}, "text": "mdi-magnify"},
                                            {"component": "span", "text": "JavBus 数据源"}
                                        ]
                                    }
                                ]
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "props": {"class": "px-6"},
                                "content": [
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
                                                            "model": "javbus_api_base",
                                                            "label": "JavBus API 地址",
                                                            "placeholder": "http://10.0.0.1:8922",
                                                            "variant": "outlined",
                                                            "density": "compact",
                                                            "hint": "javbus-api Docker 服务地址，启用后将额外注册 JavBus 搜索和排行榜探索源"
                                                        }
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
            "javbus_api_base": "",
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

    # ==================== JavBus 数据源 ====================

    def _javbus_get(self, path: str, timeout: int = 10) -> dict:
        """调用 javbus-api 获取数据"""
        if not self._javbus_api_base:
            return {}
        import http.client as _hc
        try:
            host = self._javbus_api_base.replace("http://", "").replace("https://", "").split(":")[0]
            port = int(self._javbus_api_base.split(":")[-1]) if ":" in self._javbus_api_base else 80
            conn = _hc.HTTPConnection(host, port, timeout=timeout)
            conn.request("GET", path)
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            return data
        except Exception as e:
            logger.error(f"[JAVBUS] API 请求失败: {e}")
            return {}

    def _javbus_detail_public(self, code: str) -> Dict[str, Any]:
        """JavBus 详情（供 stills-inject.js 调用）"""
        from urllib.parse import quote as _mquote
        if not code:
            return {"stills": [], "similar": [], "monthly": [], "description": "", "actors": []}
        try:
            d = self._javbus_get(f"/api/movies/{_mquote(code)}", timeout=15)
            if not d:
                return {"stills": [], "similar": [], "monthly": [], "description": "", "actors": []}

            stills = []
            for s in (d.get('samples', []) or [])[:15]:
                if isinstance(s, dict):
                    src = s.get('src', '') or s.get('thumbnail', '')
                    if src:
                        stills.append(self._proxy_image_url(src))

            stars = d.get('stars', []) or []
            actors_list = [
                {"name": s.get('name', '') if isinstance(s, dict) else str(s),
                 "photo": s.get('photo', '') if isinstance(s, dict) else ''}
                for s in stars[:10]
            ]

            _parts = [f"番号: {d.get('id', code)}"]
            if d.get('date'): _parts.append(f"发行日期: {d['date']}")
            if d.get('director'): _parts.append(f"导演: {d['director']}")
            if d.get('videoLength'): _parts.append(f"时长: {d['videoLength']}分钟")
            if stars:
                _parts.append(f"演员: {', '.join(s.get('name','') if isinstance(s,dict) else str(s) for s in stars[:5])}")
            if d.get('tags'): _parts.append(f"分类: {', '.join(d['tags'][:10])}")
            description = '\n'.join(_parts)

            # similar = 同系列作品
            similar = []
            series_name = d.get('series') if isinstance(d.get('series'), str) else (d.get('series', {}) or {}).get('name', '')
            if series_name:
                sim_data = self._javbus_get(f"/api/movies/search?keyword={_mquote(series_name)}&page=1&count=12")
                for m in (sim_data.get('movies', []) or []):
                    mid = m.get('id', '')
                    if mid and mid.upper() != code.upper():
                        similar.append({
                            'media_id': mid, 'id': mid,
                            'title': (m.get('title', '') or mid),
                            'poster_path': self._poster_or_dmm(m.get('img', ''), mid),
                        })
                        if len(similar) >= 12:
                            break

            # recommendations = 同演员作品
            recommendations = []
            sim_ids = set(s['media_id'].upper() for s in similar)
            main_star = actors_list[0].get('name', '') if actors_list else ''
            if main_star:
                rec_data = self._javbus_get(f"/api/movies/search?keyword={_mquote(main_star)}&page=1&count=12")
                for m in (rec_data.get('movies', []) or []):
                    mid = m.get('id', '')
                    if mid and mid.upper() != code.upper() and mid.upper() not in sim_ids:
                        recommendations.append({
                            'media_id': mid, 'id': mid,
                            'title': (m.get('title', '') or mid),
                            'poster_path': self._poster_or_dmm(m.get('img', ''), mid),
                        })
                        if len(recommendations) >= 12:
                            break

            return {'code': code, 'stills': stills, 'similar': similar, 'recommendations': recommendations,
                    'description': description, 'actors': actors_list}
        except Exception as e:
            logger.error(f"[JAVBUS] _javbus_detail_public 失败: {e}")
            return {"stills": [], "similar": [], "monthly": [], "description": "", "actors": []}

    @cached(region="javbus_discover", ttl=1800, skip_none=True)
    def javbus_discover(self, mode: str = "search", keyword: str = "", rank_type: str = "daily",
                       page: int = 1, count: int = 30) -> List[schemas.MediaInfo]:
        """JavBus 搜索和排行榜
        rank_type: daily=今日发行, weekly=近7天, monthly=近30天, yearly=近365天
        """
        if not self._javbus_api_base:
            return []
        from urllib.parse import quote
        try:
            if mode == "search" and keyword:
                data = self._javbus_get(f"/api/movies/search?keyword={quote(keyword)}&page={page}&count={count}")
                movies = data.get('movies', []) or []
            else:
                # 排行榜模式：拉取更多数据后按 date 过滤
                import datetime as _dt
                now = _dt.date.today()
                rank_days = {
                    "daily": 3, "weekly": 7, "monthly": 30, "yearly": 365
                }.get(rank_type, 3)
                cutoff = now - _dt.timedelta(days=rank_days)
                # 拉取多页以获取足够的时间范围内数据
                all_movies = []
                for pg in range(1, 11):  # 最多拉 10 页
                    d = self._javbus_get(f"/api/movies?page={pg}&count=100")
                    all_movies.extend(d.get('movies', []) or [])
                    if not d.get('movies'):
                        break
                # 按 date 过滤
                movies = []
                for m in all_movies:
                    mdate_str = m.get('date', '') or ''
                    if mdate_str:
                        try:
                            mdate = _dt.datetime.strptime(mdate_str, "%Y-%m-%d").date()
                            if mdate >= cutoff:
                                movies.append(m)
                        except (ValueError, TypeError):
                            pass
                # 分页
                start = (page - 1) * count
                movies = movies[start:start + count]
            results = []
            for m in movies:
                mid = m.get('id', '')
                mimg = m.get('img', '') or ''
                mtitle = m.get('title', '') or mid
                mdate = (m.get('date', '') or '')[:4] or '2026'
                mi = schemas.MediaInfo(
                    type="电影",
                    title=f"{mid} {mtitle}".strip() if mid not in mtitle else mtitle,
                    mediaid_prefix="metatube_search",
                    media_id=mid,
                    poster_path=self._proxy_image_url(mimg) if mimg else '',
                    year=mdate,
                )
                if hasattr(mi, 'source'): mi.source = 'themoviedb'
                if hasattr(mi, 'original_title'): mi.original_title = mid
                if hasattr(mi, 'adult'): mi.adult = True
                results.append(mi)
            logger.info(f"[JAVBUS] javbus_discover 返回 {len(results)} 条 (mode={mode}, rank_type={rank_type})")
            return results
        except Exception as e:
            logger.error(f"[JAVBUS] javbus_discover 失败: {e}")
            return []

    @cached(region="bytemuse_discover", ttl=1800, skip_none=True)
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

                # 海报 - ByteMuse API 返回字段为 poster_url/banner（或 poster/banner 别名）
                raw_poster = (movie_info.get("poster") or
                              movie_info.get("poster_url") or
                              movie_info.get("banner") or
                              movie_info.get("cover_url") or
                              movie_info.get("thumb_url") or
                              movie_info.get("preview_url") or "")
                # 调试：记录图片 URL
                if raw_poster:
                    poster_path = self._proxy_image_url(raw_poster) if raw_poster else ""
                    logger.debug(f"图片 URL [{code}]: {poster_path[:100] if poster_path else 'N/A'}")
                else:
                    poster_path = ""
                    logger.warning(f"未找到图片 URL: {code}, 可用字段: {list(movie_info.keys())}")

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

                # title 必须包含番号，否则前端搜索资源时用纯日文标题搜不到
                display_title = title or code
                if code and code not in display_title:
                    display_title = f"{code} {display_title}".strip()
                elif not display_title:
                    display_title = code or ""

                # 构建 MediaInfo（参考 metatubesource 的 _convert_metatube_search_to_mediainfo）
                mediainfo = schemas.MediaInfo(
                    type="电影",
                    title=display_title,
                    mediaid_prefix="metatube_search",
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
                        mediainfo.directors = [{"name": directors_list[0]}]
                    except Exception as e:
                        logger.debug(f"设置 director 失败: {e}")

                # actor（包含 profile_path，前端通过此字段显示演员照片）
                if actor_names:
                    try:
                        # 列表 API 的 actors 可能是含 photo 的 dict 列表
                        actors_raw = movie_info.get("actors")
                        if isinstance(actors_raw, list) and actors_raw and isinstance(actors_raw[0], dict):
                            actors_list = []
                            for a in actors_raw:
                                actor_dict = {"name": a.get("name", "") if isinstance(a, dict) else str(a)}
                                photo = a.get("photo", "") if isinstance(a, dict) else ""
                                if photo:
                                    actor_dict["profile_path"] = self._proxy_image_url(photo)
                                if actor_dict["name"]:
                                    actors_list.append(actor_dict)
                            mediainfo.actors = actors_list
                        else:
                            mediainfo.actors = [{"name": name} for name in actor_names]
                    except Exception as e:
                        logger.debug(f"设置 actor 失败: {e}")

                if genres:
                    try:
                        mediainfo.genres = [{"name": g} for g in genres]
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
                    mediaid_prefix="metatube_search",
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

    def bytemuse_media(self, mediaid: str) -> schemas.MediaInfo:
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

    def bytemuse_extra(self, mediaid: str) -> Dict[str, Any]:
        """
        获取媒体详情扩展信息：演员阵容和剧照

        :param mediaid: 媒体ID (格式: bytemuse:SSIS-123 或 SSIS-123)
        :return: {"actors": [...], "stills": [...]}
        """
        logger.info(f"bytemuse_extra 被调用: mediaid={mediaid}")

        # 提取番号
        if mediaid.startswith("bytemuse:"):
            code = mediaid.replace("bytemuse:", "", 1)
        else:
            code = mediaid

        if not code:
            logger.warning("bytemuse_extra: 番号不能为空")
            return {"actors": [], "stills": []}

        # 获取完整数据
        result = self._api_client.search_by_code(query=code)
        if not result:
            logger.warning(f"bytemuse_extra: 未找到番号: {code}")
            return {"actors": [], "stills": []}

        codes = result.get("codes", [])
        actors_data = result.get("actors", [])
        
        if not codes:
            return {"actors": [], "stills": []}

        movie_data = codes[0]
        
        # 构建演员列表（person卡片）
        actors = []
        for actor in actors_data:
            if isinstance(actor, dict):
                name = actor.get("name", "")
                photo = actor.get("photo", "")
                if name:
                    actors.append({
                        "type": "person",
                        "media_id": f"person:{name}",
                        "title": name,
                        "poster_path": self._proxy_image_url(photo) if photo else "",
                        "role": actor.get("role", ""),
                        "source": "bytemuse"
                    })

        # 构建剧照列表（still卡片）
        stills = []
        still_photo_str = movie_data.get("still_photo") or ""
        if still_photo_str:
            still_urls = [url.strip() for url in still_photo_str.split(',') if url.strip()]
            for i, url in enumerate(still_urls):
                stills.append({
                    "type": "still",
                    "media_id": f"still:{i}",
                    "title": f"剧照 {i+1}",
                    "poster_path": self._proxy_image_url(url),
                    "source": "bytemuse"
                })

        logger.info(f"bytemuse_extra: 返回 {len(actors)} 演员, {len(stills)} 剧照")
        return {"actors": actors, "stills": stills}

    def bytemuse_credits(self, mediaid: str) -> List[Dict[str, Any]]:
        """
        获取演员阵容（List[MediaPerson] 格式，供前端 PersonCardSlideView 使用）

        :param mediaid: 媒体ID (格式: bytemuse:SSIS-123 或 SSIS-123)
        :return: List[MediaPerson] 格式的演员列表
        """
        logger.info(f"bytemuse_credits 被调用: mediaid={mediaid}")

        # 提取番号
        code = mediaid.replace("bytemuse:", "", 1) if mediaid.startswith("bytemuse:") else mediaid
        if not code:
            return []

        result = self._api_client.search_by_code(query=code)
        if not result:
            return []

        actors_data = result.get("actors", [])
        credits = []
        for idx, actor in enumerate(actors_data):
            if not isinstance(actor, dict) or not actor.get("name"):
                continue
            photo = actor.get("photo", "")
            proxy_url = self._proxy_image_url(photo) if photo else ""
            credits.append({
                "id": idx + 1,
                "name": actor.get("name", ""),
                "character": actor.get("role", ""),
                "profile_path": "",
                "avatar": proxy_url,
                "source": "douban",
                "images": {},
                "type": 1,
            })

        logger.info(f"bytemuse_credits: 返回 {len(credits)} 演员")
        return credits

    def bytemuse_recommend(self, mediaid: str) -> List[Dict[str, Any]]:
        """
        获取今日上新作品（List[MediaInfo] 格式，供前端 MediaCardSlideView 使用）
        从 ByteMuse 今日上新列表中返回作品，排除当前番号
        与 similar（同演员）区分，避免内容重复

        :param mediaid: 媒体ID
        :return: List[MediaInfo] 格式的推荐作品列表
        """
        logger.info(f"bytemuse_recommend 被调用: mediaid={mediaid}")

        # 提取番号
        code = mediaid.replace("bytemuse:", "", 1) if mediaid.startswith("bytemuse:") else mediaid
        if not code:
            return []

        current_code = code.upper()

        # 获取当前作品演员，用于排除同演员作品（避免与 similar 重复）
        current_actors = set()
        try:
            detail = self._api_client.search_by_code(query=code)
            if detail:
                for actor in detail.get("actors", []):
                    if isinstance(actor, dict) and actor.get("name"):
                        current_actors.add(actor.get("name"))
        except Exception as e:
            logger.debug(f"bytemuse_recommend: 获取演员失败: {e}")

        # 获取今日上新列表（与 similar 的同演员搜索区分）
        new_releases = self._api_client.get_discover_data(discover_type="new_releases", page=1, page_size=20)
        if not new_releases:
            # fallback 到推荐列表
            new_releases = self._api_client.get_discover_data(discover_type="recommendations", page=1, page_size=20)
        if not new_releases:
            return []

        result = []
        for item in new_releases:
            if not isinstance(item, dict):
                continue
            item_code = (item.get("code") or "").upper()
            if item_code == current_code:
                continue
            # 排除同演员作品（留给 similar）
            item_actors = set()
            for a in (item.get("actors") or []):
                name = a.get("name", "") if isinstance(a, dict) else str(a)
                if name:
                    item_actors.add(name)
            if current_actors & item_actors:
                continue
            media = self._movie_to_media_dict(item)
            if media:
                result.append(media.model_dump())

        logger.info(f"bytemuse_recommend: 返回 {len(result)} 个推荐作品")
        return result

    def bytemuse_similar(self, mediaid: str) -> List[Dict[str, Any]]:
        """
        获取同演员作品（List[MediaInfo] 格式，供前端 MediaCardSlideView 使用）
        从 ByteMuse 按主演员搜索，排除当前番号和推荐列表中的作品

        :param mediaid: 媒体ID
        :return: List[MediaInfo] 格式的同演员作品列表
        """
        logger.info(f"bytemuse_similar 被调用: mediaid={mediaid}")

        code = mediaid.replace("bytemuse:", "", 1) if mediaid.startswith("bytemuse:") else mediaid
        code = code.replace("metatube_search:", "", 1) if code.startswith("metatube_search:") else code
        if not code:
            return []

        current_code = code.upper()

        # 获取当前作品主演员
        main_actor = ""
        try:
            detail = self._api_client.search_by_code(query=code)
            if detail:
                actors_data = detail.get("actors", [])
                if actors_data and isinstance(actors_data[0], dict):
                    main_actor = actors_data[0].get("name", "")
        except Exception as e:
            logger.debug(f"bytemuse_similar: 获取演员失败: {e}")

        if not main_actor:
            return []

        # 按主演员搜索
        result = []
        try:
            actor_result = self._api_client.search_by_code(query=main_actor)
            if actor_result:
                for c in (actor_result.get("codes") or [])[:12]:
                    c_code = (c.get("code", "") or "").upper()
                    if c_code and c_code != current_code:
                        media = self._movie_to_media_dict(c)
                        if media:
                            result.append(media.model_dump())
                    if len(result) >= 12:
                        break
        except Exception as e:
            logger.debug(f"bytemuse_similar: bytemuse search failed: {e}")

        # 回退：javbus-api 搜索
        if not result and self._javbus_api_base and main_actor:
            try:
                from urllib.parse import quote as _jq
                sim_data = self._javbus_get(
                    f"/api/movies/search?keyword={_jq(main_actor)}&page=1&count=12"
                )
                for m in (sim_data.get('movies', []) or []):
                    mid = (m.get('id', '') or '')
                    if mid and mid.upper() != current_code:
                        mimg = m.get('img', '') or ''
                        mtitle = (m.get('title', '') or mid)
                        mdate = (m.get('date', '') or '')[:4] or '2026'
                        mi = schemas.MediaInfo(
                            type="电影",
                            title=f"{mid} {mtitle}".strip() if mid not in mtitle else mtitle,
                            mediaid_prefix="javbus_search",
                            media_id=mid,
                            poster_path=self._proxy_image_url(mimg) if mimg else '',
                            year=mdate,
                        )
                        if hasattr(mi, 'source'): mi.source = 'themoviedb'
                        if hasattr(mi, 'original_title'): mi.original_title = mid
                        result.append(mi.model_dump())
                    if len(result) >= 12:
                        break
                logger.info(f"bytemuse_similar: 回退 javbus-api, {len(result)} 条")
            except Exception as e:
                logger.debug(f"bytemuse_similar: javbus fallback failed: {e}")

        logger.info(f"bytemuse_similar: 返回 {len(result)} 个同演员作品")
        return result

    def bytemuse_detail_public(self, mediaid: str) -> Dict[str, Any]:
        """
        匿名端点：获取媒体详情数据（剧照 + 推荐 + 类似）
        供前端注入使用；ByteMuse 走稳定老逻辑，JavBus 走独立分支
        """
        code = mediaid
        is_javbus = False
        for prefix in ("javbus_search:", "javbus_ranking:", "bytemuse:", "metatube_search:"):
            if code.startswith(prefix):
                code = code.replace(prefix, "", 1)
                if prefix.startswith("javbus"):
                    is_javbus = True
                break
        if not code:
            return {"stills": [], "similar": [], "recommendations": [], "monthly": []}

        if is_javbus and self._javbus_api_base:
            data = self._javbus_detail_public(code)
            if 'monthly' in data and 'recommendations' not in data:
                data['recommendations'] = data.pop('monthly')
            return data

        if not self._api_client:
            return {"stills": [], "similar": [], "recommendations": [], "monthly": []}

        try:
            result = self._api_client.search_by_code(query=code)
            if not result:
                return {"stills": [], "similar": [], "recommendations": []}

            codes = result.get("codes", [])
            actors_data = result.get("actors", [])
            if not codes:
                return {"stills": [], "similar": [], "recommendations": []}

            movie_data = codes[0]
            current_code_upper = code.upper()

            stills = []
            still_photo_str = movie_data.get("still_photo") or ""
            if still_photo_str:
                from urllib.parse import quote
                for s in still_photo_str.split(','):
                    s = s.strip()
                    if s and s.startswith("http"):
                        stills.append(f"/api/v1/plugin/ByteMuseDiscover/image?url={quote(s, safe='')}")

            actors_list = []
            for actor in (actors_data or []):
                if isinstance(actor, dict):
                    actors_list.append({
                        "name": actor.get("name", ""),
                        "photo": actor.get("photo", ""),
                    })

            recommendations = []
            main_actor = actors_list[0].get('name', '') if actors_list else ''
            if main_actor:
                try:
                    actor_result = self._api_client.search_by_code(query=main_actor)
                    if actor_result:
                        for c in (actor_result.get("codes") or [])[:24]:
                            c_code = (c.get("code", "") or "")
                            if c_code and c_code.upper() != current_code_upper:
                                c_poster = c.get("poster") or c.get("banner") or ""
                                c_title = (c.get("cn_title") or c.get("title") or c_code)
                                recommendations.append({
                                    "media_id": c_code,
                                    "id": c_code,
                                    "title": c_title,
                                    "poster_path": self._proxy_image_url(c_poster) if c_poster else "",
                                })
                                if len(recommendations) >= 12:
                                    break
                except Exception as e:
                    logger.debug(f"bytemuse_detail_public: recommendations fetch failed: {e}")

            similar = []
            used = set((item.get('media_id') or '').upper() for item in recommendations)
            try:
                series_name = (movie_data.get("series") or "").strip()
                if series_name:
                    series_result = self._api_client.search_by_code(query=series_name)
                    if series_result:
                        for c in (series_result.get("codes") or [])[:24]:
                            c_code = (c.get("code", "") or "")
                            if c_code and c_code.upper() != current_code_upper and c_code.upper() not in used:
                                c_poster = c.get("poster") or c.get("banner") or ""
                                c_title = (c.get("cn_title") or c.get("title") or c_code)
                                similar.append({
                                    "media_id": c_code,
                                    "id": c_code,
                                    "title": c_title,
                                    "poster_path": self._proxy_image_url(c_poster) if c_poster else "",
                                })
                                if len(similar) >= 12:
                                    break
            except Exception as e:
                logger.debug(f"bytemuse_detail_public: similar fetch failed: {e}")

            if not similar:
                for item in recommendations[:12]:
                    similar.append(dict(item))

            description = movie_data.get("description") or ""
            mediainfo = self._fetch_bytemuse_detail(code)
            media_info = None
            if mediainfo:
                media_info = mediainfo.model_dump() if hasattr(mediainfo, 'model_dump') else dict(mediainfo)

            return {
                "code": code,
                "stills": stills,
                "similar": similar,
                "recommendations": recommendations,
                "description": description,
                "actors": actors_list,
                "media_info": media_info,
            }
        except Exception as e:
            logger.error(f"bytemuse_detail_public failed: {e}")
            return {"stills": [], "similar": [], "recommendations": []}

    def _extract_code_from_mediaid(self, mediaid: str, imdb_id: str = "") -> Tuple[str, str]:
        """从 mediaid/imdb_id 提取纯番号和数据源类型
        返回 (code, source)，source 为 'bytemuse' 或 'javbus'
        """
        raw = mediaid or imdb_id or ""
        if not raw:
            return "", ""
        # 处理带前缀的 mediaid
        for prefix in ("javbus_search:", "javbus_ranking:", "bytemuse:", "metatube_search:", "bytemuse:", "metatube:"):
            if raw.startswith(prefix):
                code = raw.replace(prefix, "", 1)
                source = "javbus" if prefix.startswith("javbus") else "bytemuse"
                return code, source
        # 无前缀，尝试识别格式
        return raw, "bytemuse"

    def recognize_media(self, meta=None, mtype=None, **kwargs):
        """识别媒体信息（用于点击探索项时显示详情）"""
        mediaid = kwargs.get("mediaid", "")
        imdb_id = kwargs.get("imdb_id", "")
        code, source = self._extract_code_from_mediaid(mediaid, imdb_id)
        if not code:
            return None
        logger.info(f"recognize_media: code={code}, source={source}")
        if source == "javbus" and self._javbus_api_base:
            return self._fetch_javbus_detail(code)
        return self._fetch_bytemuse_detail(code)

    async def async_recognize_media(self, meta=None, mtype=None, **kwargs):
        """异步识别媒体信息（用于点击探索项时显示详情）"""
        mediaid = kwargs.get("mediaid", "")
        imdb_id = kwargs.get("imdb_id", "")
        code, source = self._extract_code_from_mediaid(mediaid, imdb_id)
        if not code:
            return None
        logger.info(f"async_recognize_media: code={code}, source={source}")
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        try:
            loop = asyncio.get_event_loop()
            fetcher = (self._fetch_javbus_detail if source == "javbus" and self._javbus_api_base else self._fetch_bytemuse_detail)
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = await loop.run_in_executor(pool, fetcher, code)
                return result
        except Exception as err:
            logger.error(f"async_recognize_media 获取详情失败: {str(err)}")
            return None

    def _fetch_javbus_detail(self, code: str) -> schemas.MediaInfo:
        """从 javbus-api 获取详情，返回完整 MediaInfo"""
        if not code or not self._javbus_api_base:
            return None
        from urllib.parse import quote as _mquote
        try:
            d = self._javbus_get(f"/api/movies/{_mquote(code)}", timeout=15)
            if not d:
                return None
            mid = d.get('id', '') or code
            mtitle = d.get('title', '') or mid
            mimg = d.get('img', '') or ''
            mdate = (d.get('date', '') or '')[:4] or '2026'
            stars = d.get('stars', []) or []
            tags = d.get('tags', []) or []
            _parts = []
            if d.get('date'): _parts.append(f"发行日期: {d['date']}")
            if d.get('director'): _parts.append(f"导演: {d['director']}")
            if d.get('videoLength'): _parts.append(f"时长: {d['videoLength']}分钟")
            if tags: _parts.append(f"分类: {', '.join(tags[:10])}")
            overview = '\n'.join(_parts) or f"番号: {mid}"
            mi = schemas.MediaInfo(
                type="电影",
                title=f"{mid} {mtitle}".strip() if mid not in mtitle else mtitle,
                mediaid_prefix="javbus_search",
                media_id=mid,
                imdb_id=mid,
                poster_path=self._proxy_image_url(mimg) if mimg else '',
                year=mdate,
                overview=overview,
            )
            if hasattr(mi, 'source'): mi.source = 'themoviedb'
            if hasattr(mi, 'original_title'): mi.original_title = mid
            if hasattr(mi, 'adult'): mi.adult = True
            if d.get('director'):
                try: mi.directors = [{"name": d['director']}]
                except: pass
            if stars:
                try:
                    mi.actors = [{"name": s.get('name','') if isinstance(s,dict) else str(s)} for s in stars[:10] if s]
                except: pass
            if tags:
                try: mi.genres = [{"name": t} for t in tags[:10]]
                except: pass
            return mi
        except Exception as e:
            logger.error(f"_fetch_javbus_detail 失败: {e}")
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
            # 获取演员信息（含头像）
            actors_data = result.get("actors", [])
            if not codes:
                logger.warning(f"_fetch_bytemuse_detail: codes 列表为空: {code}")
                return None

            # 取第一个匹配结果
            movie_data = codes[0]
            logger.info(f"_fetch_bytemuse_detail: 找到详情: {movie_data.get('title') or movie_data.get('code')}")

            # 转换为 MediaInfo（使用 __movie_to_media）
            return self._movie_to_media_dict(movie_data, actors_data)

        except Exception as err:
            logger.error(f"_fetch_bytemuse_detail 获取失败: {str(err)}")
            return None

    def _movie_to_media_dict(self, movie_info: dict, actors_data: list = None):
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

            # 海报 - ByteMuse API 返回字段为 poster/banner（或 poster_url/banner）
            raw_poster = (movie_info.get("poster") or
                          movie_info.get("poster_url") or
                          movie_info.get("banner") or
                          movie_info.get("cover_url") or
                          movie_info.get("thumb_url") or
                          movie_info.get("preview_url") or "")
            # 通过 MoviePilot 图片代理，解决 DMM 防盗链问题
            if raw_poster:
                poster_path = self._proxy_image_url(raw_poster)
            else:
                poster_path = ""

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

            # title 必须包含番号
            display_title = title or code
            if code and code not in display_title:
                display_title = f"{code} {display_title}".strip()
            elif not display_title:
                display_title = code or ""

            # 构建 MediaInfo
            mediainfo = schemas.MediaInfo(
                type="电影",
                title=display_title,
                mediaid_prefix="metatube_search",
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
                    mediainfo.directors = [{"name": directors_list[0]}]
                except Exception:
                    pass

            # 演员（包含头像 profile_path，前端通过此字段显示演员照片）
            if actor_names:
                try:
                    # 构建 actor_name -> photo_url 映射（从 actors_data 中获取）
                    actor_photo_map = {}
                    if actors_data:
                        for actor in actors_data:
                            if isinstance(actor, dict):
                                a_name = actor.get("name", "")
                                a_photo = actor.get("photo", "")
                                if a_name and a_photo:
                                    actor_photo_map[a_name] = a_photo

                    # 同时兼容 actor_names 和 actors_data 中的名字
                    actors_list = []
                    for name in actor_names:
                        actor_dict = {"name": name}
                        # 查找演员头像
                        photo = actor_photo_map.get(name)
                        if photo:
                            actor_dict["profile_path"] = self._proxy_image_url(photo)
                        actors_list.append(actor_dict)
                    mediainfo.actors = actors_list
                except Exception as e:
                    logger.debug(f"设置 actors 失败: {e}")

            if genres:
                try:
                    mediainfo.genres = [{"name": g} for g in genres]
                except Exception as e:
                    logger.debug(f"设置 genres 失败: {e}")

            # 时长
            if movie_info.get("runtime"):
                try:
                    mediainfo.runtime = movie_info["runtime"]
                except Exception:
                    pass

            # 剧照（存入 backdrop_path 作为背景图，前端可展示）
            still_photo_str = movie_info.get("still_photo") or ""
            if still_photo_str:
                still_photo_list = [url.strip() for url in still_photo_str.split(',') if url.strip()]
                if still_photo_list:
                    # 取第一张剧照作为 backdrop
                    first_still = still_photo_list[0]
                    if not mediainfo.backdrop_path:
                        mediainfo.backdrop_path = first_still

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
            mediaid_prefix="metatube_search",
            api_path=f"plugin/ByteMuseDiscover/bytemuse_discover?apikey={settings.API_TOKEN}",
            filter_params={"discover_type": "new_releases"},
            filter_ui=self.bytemuse_filter_ui(),
            depends={},
        )
        if not event_data.extra_sources:
            event_data.extra_sources = [bytemuse_source]
        else:
            event_data.extra_sources.append(bytemuse_source)

        # JavBus 数据源（如果配置了 javbus_api_base）
        if self._javbus_api_base:
            javbus_source = schemas.DiscoverMediaSource(
                name="JavBus",
                mediaid_prefix="javbus_search",
                api_path=f"plugin/ByteMuseDiscover/javbus_discover?apikey={settings.API_TOKEN}",
                filter_params={'mode': 'ranking'},
                filter_ui=[
                    {
                        "component": "div",
                        "props": {"class": "flex justify-start items-center gap-4"},
                        "content": [
                            {
                                "component": "VSelect",
                                "props": {"model": "mode", "label": "模式", "variant": "outlined", "density": "compact",
                                          "items": [{"title":"排行榜","value":"ranking"},{"title":"搜索","value":"search"}]},
                            },
                            {
                                "component": "VSelect",
                                "props": {"model": "rank_type", "label": "榜单", "variant": "outlined", "density": "compact",
                                          "items": [{"title":"日榜","value":"daily"},{"title":"周榜","value":"weekly"},
                                                   {"title":"月榜","value":"monthly"},{"title":"年榜","value":"yearly"}]},
                            },
                        ],
                    },
                    {
                        "component": "VTextField",
                        "props": {"model": "keyword", "label": "搜索番号/标题",
                                  "variant": "outlined", "density": "compact", "clearable": True,
                                  "placeholder": "切换到搜索模式后输入，如 SSIS-001"},
                    },
                ],
            )
            event_data.extra_sources.append(javbus_source)
            logger.info("【ByteMuse探索】已注册 JavBus 探索源")

    def stop_service(self):
        """
        退出插件
        """
        pass
