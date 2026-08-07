# -*- coding: utf-8 -*-
"""
JavBus 扩展搜索插件
通过 javbus-api (ovnrain/javbus-api) 为 MoviePilot 添加 JavBus 番号搜索和磁力链接获取能力
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import quote

from app.helper.sites import SitesHelper
from app.log import logger
from app.core.context import TorrentInfo
from app.plugins import _PluginBase
from app.schemas import MediaType


class JavBusExtend(_PluginBase):
    plugin_name = "JavBusExtend"
    plugin_desc = "扩展检索以支持 JavBus 番号磁力搜索"
    plugin_icon = "JavBus.png"
    plugin_version = "1.2"
    plugin_author = "kai"
    author_url = ""
    plugin_config_prefix = "javbus_extend_"
    plugin_order = 16
    auth_level = 1

    _enabled = False
    _api_base = "http://10.0.0.1:8922"
    _request_interval = 1.0
    _last_request_time = 0.0
    _sites_helper = None
    _javbus_domain = "javbus.com"

    def init_plugin(self, config: dict = None):
        self._sites_helper = SitesHelper()
        if config:
            self._enabled = config.get("enabled")
            api_base = config.get("api_base", "")
            if api_base:
                self._api_base = api_base.rstrip('/')
        if not self._enabled:
            return
        # 注册 JavBus 站点到 indexer 系统
        self._register_indexer()

    def _register_indexer(self):
        """注册 JavBus 为可搜索站点"""
        domain = self._javbus_domain
        existing = self._sites_helper.get_indexer(domain)
        if existing:
            logger.info(f"【{self.plugin_name}】JavBus 站点已存在，跳过注册")
            return
        indexer = {
            "id": "javbus",
            "name": "JavBus",
            "domain": domain,
            "public": 1,
            "enabled": 1,
            "pri": 0,
        }
        self._sites_helper.add_indexer(domain, indexer)
        logger.info(f"【{self.plugin_name}】JavBus 站点注册成功")

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            time.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    def _api_get(self, path: str) -> Optional[Any]:
        """
        调用 javbus-api（不走代理）
        返回解析后的 JSON（dict 或 list），失败返回 None
        """
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
            with opener.open(req, timeout=20) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"【{self.plugin_name}】API 请求失败: {path} -> {e}")
            return None

    @staticmethod
    def _parse_size(size_str: str) -> float:
        """将 '6.30GB' 等字符串转为 MB float"""
        if not size_str:
            return 0.0
        try:
            val = float(''.join(c for c in size_str if c.isdigit() or c == '.'))
            if 'TB' in size_str.upper():
                val *= 1024
            elif 'MB' in size_str.upper():
                val /= 1024
            return val
        except (ValueError, TypeError):
            return 0.0

    def _fetch_magnets_for_movie(self, movie_id: str) -> List[dict]:
        """
        获取某部影片的所有磁力链接。
        1. 调用详情接口获取 gid/uc
        2. 用 gid/uc 调用磁力接口

        :return: 磁力 dict 列表 [{link, title, size, shareDate, ...}, ...]
        """
        if not movie_id:
            return []

        # 1) 获取详情（含 gid/uc）
        detail = self._api_get(f"/api/movies/{movie_id}")
        if not detail or not isinstance(detail, dict):
            logger.debug(f"【{self.plugin_name}】{movie_id} 详情获取失败")
            return []

        gid = detail.get('gid', '')
        uc = detail.get('uc', '')

        if not gid or not uc:
            logger.debug(f"【{self.plugin_name}】{movie_id} 缺少 gid/uc，无法获取磁力链接 (gid={gid}, uc={uc})")
            return []

        # 2) 获取磁力链接
        magnets_data = self._api_get(
            f"/api/magnets/{movie_id}?gid={gid}&uc={uc}"
        )
        if not magnets_data:
            return []

        # API 可能返回 list 或 {"magnets": [...]}
        if isinstance(magnets_data, list):
            return magnets_data
        if isinstance(magnets_data, dict):
            return magnets_data.get('magnets', [])
        return []

    @staticmethod
    def _magnet_to_torrent_dict(movie_id: str, m: dict) -> Optional[dict]:
        """将单个磁力信息转换为 indexer dict 格式"""
        magnet = m.get('link') or m.get('magnet', '')
        if not magnet:
            return None

        name = m.get('title') or m.get('name', '')
        size_str = m.get('size', '') or ''
        date = m.get('shareDate') or m.get('date', '')

        # 构建标签描述
        tags = []
        if m.get('isHD'):
            tags.append('HD')
        if m.get('hasSubtitle'):
            tags.append('字幕')
        tag_str = f" [{'/'.join(tags)}]" if tags else ''

        return {
            "title": f"{name}{tag_str} [{size_str}]" if size_str else f"{name}{tag_str}",
            "enclosure": magnet,
            "size": JavBusExtend._parse_size(size_str),
            "description": f"{movie_id} | {name} | {size_str} | {date}{tag_str}",
            "page_url": "",
        }

    # ==================== 搜索接口 ====================

    def search_torrents(self, site: dict, keyword: str,
                        mtype: MediaType = None, page: int = 0,
                        search_type: str = None) -> List[dict]:
        """
        搜索 JavBus 磁力资源（按番号关键词搜索）
        返回 dict 列表，每个 dict 含 title/enclosure/size/description/page_url
        """
        # 仅处理 JavBus 站点
        if self._javbus_domain not in str(site.get('domain', '')).lower():
            return []

        if not keyword:
            return []

        keyword = keyword.strip().replace(' ', '-')

        result = self._api_get(f"/api/movies/search?keyword={quote(keyword)}")
        if not result:
            return []

        movies = result.get('movies', []) if isinstance(result, dict) else result
        if not movies:
            logger.info(f"【{self.plugin_name}】搜索 {keyword}，未找到结果")
            return []

        logger.info(f"【{self.plugin_name}】搜索 {keyword}，找到 {len(movies)} 个结果")

        all_torrents = []
        for movie in movies[:10]:
            movie_id = movie.get('id', '')
            if not movie_id:
                continue

            magnets = self._fetch_magnets_for_movie(movie_id)
            if not magnets:
                continue

            for m in magnets:
                item = self._magnet_to_torrent_dict(movie_id, m)
                if item:
                    all_torrents.append(item)

            logger.info(f"【{self.plugin_name}】{movie_id}: 获取到 {len(magnets)} 个磁力链接")

        logger.info(f"【{self.plugin_name}】搜索完成，共 {len(all_torrents)} 个磁力链接")
        return all_torrents

    # ==================== 浏览/刷新接口 ====================

    def refresh_torrents(self, site: dict,
                         keyword: Optional[str] = None,
                         cat: Optional[str] = None,
                         page: Optional[int] = 0) -> List[dict]:
        """
        刷新 JavBus 最新磁力资源（browse 首页列表模式）
        使用 /api/movies?page=N&magnet=exist 获取有磁力的最新影片列表
        """
        if self._javbus_domain not in str(site.get('domain', '')).lower():
            return []

        page_num = (page or 0) + 1
        result = self._api_get(f"/api/movies?page={page_num}&magnet=exist")
        if not result:
            return []

        movies = result.get('movies', []) if isinstance(result, dict) else result
        if not movies:
            logger.info(f"【{self.plugin_name}】刷新第 {page_num} 页，未找到结果")
            return []

        logger.info(f"【{self.plugin_name}】刷新第 {page_num} 页，获取到 {len(movies)} 个影片")

        all_torrents = []
        movie_list = [m for m in movies[:15] if m.get('id')]

        def _process_movie(movie):
            movie_id = movie['id']
            magnets = self._fetch_magnets_for_movie(movie_id)
            items = []
            if magnets:
                for m in magnets:
                    item = self._magnet_to_torrent_dict(movie_id, m)
                    if item:
                        items.append(item)
            return movie_id, magnets, items

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_process_movie, m): m for m in movie_list}
            for future in as_completed(futures):
                movie_id, magnets, items = future.result()
                if magnets:
                    logger.debug(f"【{self.plugin_name}】{movie_id}: 获取到 {len(magnets)} 个磁力链接")
                all_torrents.extend(items)

        logger.info(f"【{self.plugin_name}】刷新完成，共 {len(all_torrents)} 个磁力链接")
        return all_torrents

    # ==================== 插件标准接口 ====================

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
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
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_base',
                                            'label': 'javbus-api 地址',
                                            'placeholder': 'http://10.0.0.1:8922',
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
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '需要先部署 javbus-api Docker 容器（ovnrain/javbus-api），默认端口 8922。JavBus 站点将自动注册到索引系统中。'
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
            "api_base": "http://10.0.0.1:8922",
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass

    def get_module(self) -> Dict[str, Any]:
        """
        注册模块方法，用于劫持系统的 search_torrents 和 refresh_torrents
        当目标是 JavBus 站点时，使用本插件的方法
        """
        return {
            "search_torrents": self.search_torrents,
            "refresh_torrents": self.refresh_torrents,
        }
