# Category: API客户端
"""
JavBus API 客户端
通过 javbus-api (ovnrain/javbus-api) 识别番号媒体信息
"""
import re
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import (
    JavBusMovie, JavBusMovieDetail, JavBusEntity,
    JavBusSample, JavBusSearchResponse
)


# ==================== JavBus API 客户端 ====================

class JavBusApiClient:
    """JavBus API 客户端"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def __init__(self, base_url: str = "http://10.0.0.1:8922",
                 timeout: int = 30,
                 proxies: Dict[str, str] = None):
        """
        初始化 JavBus API 客户端

        :param base_url: javbus-api 基础地址
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置（javbus-api 通常不走代理）
        """
        self._base_url = base_url.rstrip('/') if base_url else "http://10.0.0.1:8922"
        self._timeout = timeout
        # javbus-api 部署在内网，不走代理
        self._proxies = None

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value.rstrip('/') if value else "http://10.0.0.1:8922"

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        base = self._base_url.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def _safe_validate_detail(self, data: Any) -> Optional[JavBusMovieDetail]:
        """
        安全验证详情数据，忽略多余字段
        """
        if not isinstance(data, dict):
            return None

        try:
            return JavBusMovieDetail.model_validate(data)
        except Exception as e:
            logger.debug(f"JavBus 详情标准验证失败: {e}")
            try:
                field_names = set(JavBusMovieDetail.model_fields.keys())
                filtered_data = {k: v for k, v in data.items() if k in field_names}
                return JavBusMovieDetail.model_validate(filtered_data)
            except Exception as e2:
                logger.warning(f"JavBus 详情字段提取也失败: {e2}")
                return None

    # ==================== 搜索 ====================

    def search(self, query: str) -> Optional[List[JavBusMovie]]:
        """
        搜索番号

        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = self._build_url("/api/movies/search")
            params = {"keyword": query}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"JavBus API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"JavBus API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            logger.debug(f"JavBus API 搜索响应: {data}")

            # 解析响应
            movies_data = []
            if isinstance(data, dict) and 'movies' in data:
                movies_data = data['movies']
            elif isinstance(data, list):
                movies_data = data

            movies = []
            for item in movies_data:
                if isinstance(item, dict):
                    try:
                        movie = JavBusMovie.model_validate(item)
                        movies.append(movie)
                    except Exception as e:
                        logger.debug(f"JavBus 解析搜索条目失败: {e}")

            return movies if movies else None

        except Exception as e:
            logger.error(f"JavBus 搜索异常: {str(e)}")
            return None

    async def async_search(self, query: str) -> Optional[List[JavBusMovie]]:
        """
        异步搜索番号

        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = self._build_url("/api/movies/search")
            params = {"keyword": query}

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"JavBus API 异步请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"JavBus API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            logger.debug(f"JavBus API 异步搜索响应: {data}")

            movies_data = []
            if isinstance(data, dict) and 'movies' in data:
                movies_data = data['movies']
            elif isinstance(data, list):
                movies_data = data

            movies = []
            for item in movies_data:
                if isinstance(item, dict):
                    try:
                        movie = JavBusMovie.model_validate(item)
                        movies.append(movie)
                    except Exception as e:
                        logger.debug(f"JavBus 解析搜索条目失败: {e}")

            return movies if movies else None

        except Exception as e:
            logger.error(f"JavBus 异步搜索异常: {str(e)}")
            return None

    # ==================== 详情 ====================

    def get_detail(self, movie_id: str) -> Optional[JavBusMovieDetail]:
        """
        获取影片详情

        :param movie_id: 番号 (如 JUQ-434)
        :return: 详情对象
        """
        if not movie_id:
            return None

        try:
            url = self._build_url(f"/api/movies/{quote(movie_id)}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url)

            if response is None:
                logger.warning(f"JavBus 详情请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"JavBus 详情返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            logger.debug(f"JavBus 详情响应: {data}")

            return self._safe_validate_detail(data)

        except Exception as e:
            logger.error(f"JavBus 获取详情异常: {str(e)}")
            return None

    async def async_get_detail(self, movie_id: str) -> Optional[JavBusMovieDetail]:
        """
        异步获取影片详情

        :param movie_id: 番号
        :return: 详情对象
        """
        if not movie_id:
            return None

        try:
            url = self._build_url(f"/api/movies/{quote(movie_id)}")

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url)

            if response is None:
                logger.warning(f"JavBus 异步详情请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"JavBus 详情返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            return self._safe_validate_detail(data)

        except Exception as e:
            logger.error(f"JavBus 异步获取详情异常: {str(e)}")
            return None

    # ==================== 连接测试 ====================

    def test_connection(self) -> bool:
        """
        测试API连接

        :return: 连接是否成功
        """
        try:
            url = self._build_url("/api/movies/search")
            params = {"keyword": "TEST-001"}

            response = RequestUtils(
                timeout=5,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            return response is not None and response.status_code in [200, 404]

        except Exception as e:
            logger.debug(f"JavBus 连接测试失败: {str(e)}")
            return False

    # ==================== 搜索并获取详情 ====================

    def search_with_detail(self, query: str) -> Optional[JavBusMovieDetail]:
        """
        搜索并直接返回第一个结果的详情

        :param query: 搜索关键词(番号)
        :return: 详情对象
        """
        results = self.search(query)
        if not results:
            return None

        movie = results[0]
        return self.get_detail(movie.id)

    async def async_search_with_detail(self, query: str) -> Optional[JavBusMovieDetail]:
        """
        异步搜索并直接返回第一个结果的详情

        :param query: 搜索关键词(番号)
        :return: 详情对象
        """
        results = await self.async_search(query)
        if not results:
            return None

        movie = results[0]
        return await self.async_get_detail(movie.id)
