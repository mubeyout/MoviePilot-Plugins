"""
Byte-Muse API 客户端
通过 Byte-Muse 服务识别番号媒体信息
"""
from typing import Optional, List, Dict
from urllib.parse import quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import (
    ByteMuseMovie, ByteMuseActor,
    ByteMuseSearchData, ByteMuseSearchResponse
)


# ==================== Byte-Muse API 客户端 ====================

class ByteMuseApiClient:
    """Byte-Muse API 客户端"""

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "DNT": "1",
        "Content-Type": "application/json",
    }

    def __init__(self, base_url: str = "http://10.0.0.1:3750",
                 api_token: str = "", timeout: int = 30,
                 proxies: Dict[str, str] = None):
        """
        初始化 Byte-Muse API 客户端

        :param base_url: API 基础地址
        :param api_token: API Token (用于 Authorization Bearer)
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        self._base_url = base_url.rstrip('/')
        self._api_token = api_token
        self._timeout = timeout
        self._proxies = proxies

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value.rstrip('/') if value else "http://127.0.0.1:3750"

    @property
    def api_token(self) -> str:
        return self._api_token

    @api_token.setter
    def api_token(self, value: str):
        self._api_token = value or ""

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = self.DEFAULT_HEADERS.copy()
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        base = self._base_url.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search(self, query: str) -> Optional[List[ByteMuseMovie]]:
        """
        搜索番号

        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"Byte-Muse API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Byte-Muse API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            result = ByteMuseSearchResponse.model_validate(data)
            if result.success and result.data:
                return result.data.codes

            return None

        except Exception as e:
            logger.error(f"Byte-Muse 搜索异常: {str(e)}")
            return None

    async def async_search(self, query: str) -> Optional[List[ByteMuseMovie]]:
        """
        异步搜索番号

        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"Byte-Muse API 异步请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Byte-Muse API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            result = ByteMuseSearchResponse.model_validate(data)
            if result.success and result.data:
                return result.data.codes

            return None

        except Exception as e:
            logger.error(f"Byte-Muse 异步搜索异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """
        测试API连接

        :return: 连接是否成功
        """
        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": "TEST-001"}

            response = RequestUtils(
                timeout=5,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            # 200: 成功, 404: 未找到但API可达
            return response is not None and response.status_code in [200, 404]

        except Exception as e:
            logger.debug(f"Byte-Muse 连接测试失败: {str(e)}")
            return False
