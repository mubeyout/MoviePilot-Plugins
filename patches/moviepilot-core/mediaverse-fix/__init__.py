# -*- coding: utf-8 -*-
"""
MediaVerse 探索发现插件
直连 javbus-api，提供搜索、排行榜、新品速递、演员/厂牌浏览等功能
替代 ByteMuseDiscover，去除中间依赖
"""
import json
import time
import threading
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import quote

from app.log import logger
from app.plugins import _PluginBase


class MediaVerse(_PluginBase):
    plugin_name = "MediaVerse"
    plugin_desc = "探索发现模块 - 直连 JavBus 数据源，提供搜索、排行榜、新品、演员/厂牌浏览"
    plugin_icon = "MediaVerse.png"
    plugin_version = "1.0.0"
    plugin_author = "Mubey"
    author_url = "https://github.com/mubeyout"
    plugin_config_prefix = "mediaverse_"
    plugin_order = 12
    auth_level = 0

    _enabled = False
    _api_base = "http://10.0.0.1:8922"
    _request_interval = 1.2
    _last_request_time = 0.0
    _request_lock = threading.Lock()

    # 排行榜配置
    RANKING_TYPES = {
        "daily": {"name": "日榜", "path": "/ranking/daily"},
        "weekly": {"name": "周榜", "path": "/ranking/weekly"},
        "monthly": {"name": "月榜", "path": "/ranking/monthly"},
        "yearly": {"name": "年榜", "path": "/ranking/yearly"},
    }

    # 厂牌映射
    STUDIO_MAP = {
        "s1": "S1",
        "ideapocket": "IdeaPocket",
        "moodyz": "Moodyz",
        "premium": "Premium",
        "das": "DAS",
        "madonna": "Madonna",
        "honnaka": "Honnaka",
        "attackers": "Attackers",
        "wanz": "Wanz",
        "kawaiikawaii": "Kawaii",
        "sodd": "SOD Create",
        "bi": "BI",
        "alice": "Alice Japan",
        "max": "MAXING",
        "kmp": "K.M.Produce",
        "fitch": "Fitch",
    }

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            api_base = config.get("api_base", "")
            if api_base:
                self._api_base = api_base.rstrip('/')
        if self._enabled:
            logger.info(f"【{self.plugin_name}】插件已启用，javbus-api: {self._api_base}")

    def _rate_limit(self):
        """请求限速"""
        with self._request_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._request_interval:
                time.sleep(self._request_interval - elapsed)
            self._last_request_time = time.time()

    def _api_get(self, path: str, timeout: int = 20) -> Optional[dict]:
        """调用 javbus-api（绕代理）"""
        self._rate_limit()
        try:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            url = f"{self._api_base}{path}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with opener.open(req, timeout=timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"【{self.plugin_name}】API 请求失败: {path} -> {e}")
            return None

    def _get_javbus_html(self, path: str, timeout: int = 20) -> Optional[str]:
        """通过 javbus-api 容器代理获取 JavBus HTML 页面（用于排行榜等）"""
        self._rate_limit()
        try:
            import urllib.request
            # 直接请求 javbus-api 的根路径代理
            # javbus-api 运行时会对 JavBus 做 cookie/session 处理
            # 我们需要获取 javbus.com 的 HTML 然后解析
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            url = f"https://www.javbus.com{path}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with opener.open(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"【{self.plugin_name}】JavBus HTML 获取失败: {path} -> {e}")
            return None

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/mediaverse/explore",
                "endpoint": self.api_explore,
                "methods": ["GET"],
                "summary": "探索发现主页数据",
                "description": "获取新品速递和今日推荐，供 Explore 首页使用",
            },
            {
                "path": "/mediaverse/search",
                "endpoint": self.api_search,
                "methods": ["GET"],
                "summary": "全局搜索",
                "description": "搜索番号/标题/演员，返回影片列表",
            },
            {
                "path": "/mediaverse/ranking",
                "endpoint": self.api_ranking,
                "methods": ["GET"],
                "summary": "排行榜",
                "description": "获取日/周/月/年排行榜数据",
            },
            {
                "path": "/mediaverse/new",
                "endpoint": self.api_new_releases,
                "methods": ["GET"],
                "summary": "新品速递",
                "description": "获取最新上架影片",
            },
            {
                "path": "/mediaverse/movie/{movie_id}",
                "endpoint": self.api_movie_detail,
                "methods": ["GET"],
                "summary": "影片详情",
                "description": "获取影片完整详情信息",
            },
            {
                "path": "/mediaverse/star/{star_id}",
                "endpoint": self.api_star_detail,
                "methods": ["GET"],
                "summary": "演员详情",
                "description": "获取演员信息和作品列表",
            },
            {
                "path": "/mediaverse/studios",
                "endpoint": self.api_studios,
                "methods": ["GET"],
                "summary": "厂牌列表",
                "description": "获取可用厂牌列表及最新作品",
            },
            {
                "path": "/mediaverse/genre/{genre_id}",
                "endpoint": self.api_genre,
                "methods": ["GET"],
                "summary": "分类浏览",
                "description": "按分类 ID 获取影片",
            },
            {
                "path": "/mediaverse/image",
                "endpoint": self.api_proxy_image,
                "methods": ["GET"],
                "summary": "图片代理",
                "description": "代理外部图片，解决防盗链",
                "allow_anonymous": True,
            },
        ]

    # ==================== API 端点实现 ====================

    def api_explore(self):
        """探索发现主页：新品 + 排行榜预览"""
        result = {"new_releases": [], "ranking_daily": [], "ranking_weekly": []}
        
        # 新品速递
        new_data = self._api_get("/api/movies?page=1")
        if new_data and "movies" in new_data:
            result["new_releases"] = new_data["movies"][:20]

        # 日榜（通过最新列表模拟）
        daily_data = self._api_get("/api/movies?page=1&magnet=exist")
        if daily_data and "movies" in daily_data:
            result["ranking_daily"] = daily_data["movies"][:10]

        # 周榜（通过多页汇总模拟，简单实现取第2页）
        weekly_data = self._api_get("/api/movies?page=2&magnet=exist")
        if weekly_data and "movies" in weekly_data:
            result["ranking_weekly"] = weekly_data["movies"][:10]

        return result

    def api_search(self, keyword: str = "", page: int = 1, magnet: str = "exist"):
        """全局搜索"""
        if not keyword:
            return {"movies": [], "pagination": {}}

        keyword = keyword.strip()
        # javbus-api 要求用空格或原样搜索
        result = self._api_get(
            f"/api/movies/search?keyword={quote(keyword)}&page={page}&magnet={magnet}"
        )
        if not result:
            return {"movies": [], "pagination": {}}

        return result

    def api_ranking(self, rank_type: str = "daily", page: int = 1):
        """排行榜（日/周/月/年）"""
        if rank_type not in self.RANKING_TYPES:
            return {"movies": [], "type": rank_type, "error": "不支持排行榜类型"}

        # javbus-api 无排行接口，使用影片列表按时间排序模拟
        # 后续可通过 Fork javbus-api 增加原生排行接口
        # 页码偏移模拟不同时间范围
        page_offset = {"daily": 1, "weekly": 2, "monthly": 4, "yearly": 8}.get(rank_type, 1)
        actual_page = page_offset + page - 1

        result = self._api_get(f"/api/movies?page={actual_page}&magnet=exist")
        if not result:
            return {"movies": [], "type": rank_type}

        return {
            "movies": result.get("movies", []),
            "type": rank_type,
            "name": self.RANKING_TYPES[rank_type]["name"],
            "pagination": result.get("pagination", {}),
        }

    def api_new_releases(self, page: int = 1):
        """新品速递"""
        result = self._api_get(f"/api/movies?page={page}")
        if not result:
            return {"movies": [], "pagination": {}}

        return result

    def api_movie_detail(self, movie_id: str):
        """影片详情"""
        result = self._api_get(f"/api/movies/{movie_id}")
        if not result:
            return {"error": "影片未找到", "id": movie_id}

        return result

    def api_star_detail(self, star_id: str, page: int = 1):
        """演员详情 + 作品"""
        star_info = self._api_get(f"/api/stars/{star_id}")
        if not star_info:
            return {"error": "演员未找到", "id": star_id}

        # 获取演员的作品
        works = self._api_get(f"/api/movies?filterType=star&filterValue={star_id}&page={page}&magnet=exist")
        
        return {
            "star": star_info,
            "works": works.get("movies", []) if works else [],
            "pagination": works.get("pagination", {}) if works else {},
        }

    def api_studios(self, studio_key: str = "", page: int = 1):
        """厂牌列表 / 厂牌作品"""
        if not studio_key:
            # 返回可用厂牌列表
            return {
                "studios": [
                    {"key": k, "name": v} for k, v in self.STUDIO_MAP.items()
                ],
            }

        if studio_key not in self.STUDIO_MAP:
            return {"error": "厂牌不存在", "studios": []}

        # 获取厂牌作品（通过搜索厂牌名）
        result = self._api_get(
            f"/api/movies/search?keyword={quote(self.STUDIO_MAP[studio_key])}&page={page}&magnet=exist"
        )
        return {
            "studio_key": studio_key,
            "studio_name": self.STUDIO_MAP[studio_key],
            "movies": result.get("movies", []) if result else [],
            "pagination": result.get("pagination", {}) if result else {},
        }

    def api_genre(self, genre_id: str, page: int = 1):
        """分类浏览"""
        result = self._api_get(f"/api/movies?filterType=genre&filterValue={genre_id}&page={page}&magnet=exist")
        if not result:
            return {"movies": [], "pagination": {}}

        return result

    def api_proxy_image(self, url: str = ""):
        """图片代理（解决防盗链）"""
        if not url:
            return {"error": "缺少 url 参数"}

        try:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.javbus.com/",
            })
            with opener.open(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                data = resp.read()
                from fastapi.responses import Response
                return Response(content=data, media_type=content_type)
        except Exception as e:
            logger.warning(f"【{self.plugin_name}】图片代理失败: {url[:50]} -> {e}")
            return {"error": str(e)}

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """插件配置表单"""
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
                                        "props": {"style": "color: #667eea;", "class": "mr-2"},
                                        "text": "mdi-compass-outline"
                                    },
                                    {
                                        "component": "span",
                                        "text": "MediaVerse 探索发现"
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
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "api_base",
                                                            "label": "javbus-api 地址",
                                                            "placeholder": "http://10.0.0.1:8922",
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
                                                            "text": "需要部署 javbus-api Docker 容器（ovnrain/javbus-api），默认端口 8922。本插件直连 javbus-api 获取 JavBus 数据，不依赖 ByteMuse 或 Metatube。"
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
            }
        ], {
            "enabled": False,
            "api_base": "http://10.0.0.1:8922",
        }

    def get_page(self) -> List[dict]:
        """插件自定义页面（Explore 页面）"""
        return [
            {
                "component": "VContainer",
                "props": {
                    "fluid": True,
                    "class": "pa-4"
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"id": "mediaverse-explore-app"},
                        "text": "MediaVerse Explore 页面加载中..."
                    }
                ]
            }
        ]

    def stop_service(self):
        pass

    def __init__(self):
        """初始化 - API 路由通过 get_api() 注册（新插件规范）"""
        super().__init__()
