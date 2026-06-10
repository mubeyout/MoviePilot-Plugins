"""
JavBus 站点 Spider - 通过 javbus-api 获取磁力链接
Parser 名称: JavBus
用于 MoviePilot 站点 indexer，搜索番号返回磁力链接资源

依赖：ovnrain/javbus-api Docker 容器 (http://10.0.0.1:8922)
"""
import json
import time
from typing import List, Optional, Tuple
from urllib.parse import quote

from app.log import logger


class JavBusSpider:
    """
    JavBus Spider
    数据来源：javbus-api (ovnrain/javbus-api)
    
    流程：
    1. /api/movies/search?keyword=CODE → 搜索番号
    2. /api/movies/{id} → 获取 gid/uc
    3. /api/magnets/{id}?gid=xxx&uc=xxx → 获取磁力链接
    """

    API_BASE = "http://10.0.0.1:8922"
    REQUEST_INTERVAL = 1.5

    def __init__(self, indexer: dict):
        self._indexerid = indexer.get('id')
        self._name = indexer.get('name', 'JavBus')
        self._domain = indexer.get('domain', 'www.javbus.com')
        self._ua = indexer.get('ua') or "Mozilla/5.0"
        self._timeout = int(indexer.get('timeout') or 20)
        self._last_request_time = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _api_get(self, path: str) -> Optional[dict]:
        """调用 javbus-api（不走 MoviePilot 代理）"""
        self._rate_limit()
        try:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            url = f"{self.API_BASE}{path}"
            req = urllib.request.Request(url, headers={
                "User-Agent": self._ua,
                "Accept": "application/json",
            })
            with opener.open(req, timeout=self._timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"[JavBus] API 请求失败: {path} -> {e}")
            return None

    def _parse_size(self, size_str: str) -> float:
        """解析文件大小字符串为 GB float"""
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

    def _get_magnets(self, movie_id: str, detail: dict) -> List[dict]:
        """获取指定番号的磁力链接，返回 dict 列表（与 __parse_result 兼容）"""
        gid = detail.get('gid', '')
        uc = detail.get('uc', 0)

        self._rate_limit()
        magnets_data = self._api_get(f"/api/magnets/{movie_id}?gid={gid}&uc={uc}")
        if not magnets_data:
            return []

        magnets_list = magnets_data if isinstance(magnets_data, list) else magnets_data.get('magnets', [])
        
        results = []
        for m in magnets_list:
            magnet = m.get('link') or m.get('magnet', '')
            if not magnet:
                continue
            
            name = m.get('title') or m.get('name', '')
            size_str = m.get('size', '') or ''
            date = m.get('shareDate') or m.get('date', '')
            
            results.append({
                "title": f"{name} [{size_str}]" if size_str else name,
                "enclosure": magnet,
                "size": self._parse_size(size_str),
                "description": f"{movie_id} | {name} | {size_str} | {date}",
            })

        return results

    def search(self, keyword: str = None, mtype=None, cat: Optional[str] = None,
                page: Optional[int] = 0) -> Tuple[bool, list]:
        """
        同步搜索，返回 (error_flag, dict_list)
        dict 格式与 TorrentInfo 的 __init__ 参数兼容
        """
        if not keyword:
            return False, []

        keyword = keyword.strip()
        # MoviePilot __clear_search_text 把连字符替换为空格，还原
        keyword = keyword.replace(' ', '-')

        result = self._api_get(f"/api/movies/search?keyword={quote(keyword)}")
        if not result:
            logger.info(f"[JavBus] 搜索 {keyword} 无结果")
            return False, []

        movies = result.get('movies', []) if isinstance(result, dict) else result
        if not movies:
            logger.info(f"[JavBus] 搜索 {keyword} 无匹配")
            return False, []

        logger.info(f"[JavBus] 搜索 {keyword}，找到 {len(movies)} 个结果，正在获取磁力链接...")

        all_torrents = []
        for movie in movies[:10]:
            movie_id = movie.get('id', '')
            if not movie_id:
                continue
            
            # 获取详情（含 gid/uc）
            self._rate_limit()
            detail = self._api_get(f"/api/movies/{movie_id}")
            if not detail or 'gid' not in detail:
                logger.warning(f"[JavBus] 获取详情失败: {movie_id}")
                continue

            magnets = self._get_magnets(movie_id, detail)
            all_torrents.extend(magnets)
            logger.info(f"[JavBus] {movie_id}: 获取到 {len(magnets)} 个磁力链接")

        logger.info(f"[JavBus] 搜索完成，共 {len(all_torrents)} 个磁力链接")
        return False, all_torrents

    async def async_search(self, keyword: str = None, mtype=None, cat: Optional[str] = None,
                           page: Optional[int] = 0) -> Tuple[bool, list]:
        """异步搜索（包装同步方法）"""
        from fastapi.concurrency import run_in_threadpool
        return await run_in_threadpool(self.search, keyword=keyword, mtype=mtype,
                                       cat=cat, page=page)
