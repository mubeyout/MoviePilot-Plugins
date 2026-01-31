"""
Metatube API 客户端
"""
import re
from typing import Optional, List, Dict
from urllib.parse import urljoin, quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import MetatubeMovie, MetatubeSearchResponse, MetatubeMovieDetail, MetatubeDetailResponse


class MetatubeApiClient:
    """Metatube API 客户端"""

    # 浏览器 User-Agent，避免被服务端拒绝
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 番号正则表达式列表
    NUMBER_PATTERNS = [
        # 标准格式: ABC-123, ABC123
        r'([A-Z]{2,10})[-_]?(\d{2,5})',
        # FC2格式: FC2-PPV-1234567, FC2-1234567
        r'(FC2)[-_]?(PPV)?[-_]?(\d{5,7})',
        # 特殊格式: n1234, k1234
        r'([nk])(\d{4})',
        # HEYZO格式: HEYZO-1234
        r'(HEYZO)[-_]?(\d{4})',
        # Carib格式: 123456-123
        r'(\d{6})[-_](\d{3})',
        # 1Pondo格式: 123456_123
        r'(\d{6})[_](\d{3})',
    ]

    def __init__(self, base_url: str = "http://127.0.0.1:8080",
                 timeout: int = 10, proxies: Dict[str, str] = None):
        """
        初始化 Metatube API 客户端

        :param base_url: API 基础地址
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._proxies = proxies

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value.rstrip('/') if value else "http://127.0.0.1:8080"

    @staticmethod
    def extract_number(filename: str) -> Optional[str]:
        """
        从文件名中提取番号

        :param filename: 文件名
        :return: 提取的番号，未找到返回None
        """
        if not filename:
            return None

        # 清理文件名
        name = filename.upper().strip()

        # 移除常见的无关前缀和后缀
        name = re.sub(r'\[.*?\]', ' ', name)
        name = re.sub(r'\(.*?\)', ' ', name)
        name = re.sub(r'[@＠].*', '', name)

        # 尝试匹配各种番号格式
        for pattern in MetatubeApiClient.NUMBER_PATTERNS:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return f"{groups[0]}-{groups[1]}".upper()
                elif len(groups) == 3:
                    # FC2格式
                    if groups[1]:
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                    else:
                        return f"{groups[0]}-{groups[2]}".upper()

        return None

    @staticmethod
    def normalize_number(number: str) -> str:
        """
        标准化番号格式

        :param number: 原始番号
        :return: 标准化后的番号
        """
        if not number:
            return ""

        # 转大写并清理空格
        number = number.upper().strip()

        # 替换全角字符
        number = number.replace('－', '-').replace('＿', '_')

        return number

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        # 确保没有重复的斜杠
        base = self._base_url.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search(self, keyword: str, fallback: bool = True) -> Optional[List[MetatubeMovie]]:
        """
        搜索媒体

        :param keyword: 搜索关键词(番号)
        :param fallback: 是否启用回退搜索
        :return: 搜索结果列表
        """
        try:
            url = self._build_url(f"/v1/movies/search")
            params = {
                "q": keyword,
                "fallback": "true" if fallback else "false"
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"Metatube API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Metatube API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                result = MetatubeSearchResponse.model_validate(data)
                return result.data
            elif isinstance(data, list):
                return [MetatubeMovie.model_validate(item) for item in data]

            return None

        except Exception as e:
            logger.error(f"Metatube 搜索异常: {str(e)}")
            return None

    async def async_search(self, keyword: str, fallback: bool = True) -> Optional[List[MetatubeMovie]]:
        """
        异步搜索媒体

        :param keyword: 搜索关键词(番号)
        :param fallback: 是否启用回退搜索
        :return: 搜索结果列表
        """
        try:
            url = self._build_url(f"/v1/movies/search")
            params = {
                "q": keyword,
                "fallback": "true" if fallback else "false"
            }

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"Metatube API 异步请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Metatube API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                result = MetatubeSearchResponse.model_validate(data)
                return result.data
            elif isinstance(data, list):
                return [MetatubeMovie.model_validate(item) for item in data]

            return None

        except Exception as e:
            logger.error(f"Metatube 异步搜索异常: {str(e)}")
            return None

    def get_detail(self, provider: str, movie_id: str) -> Optional[MetatubeMovieDetail]:
        """
        获取电影详情

        :param provider: 数据来源
        :param movie_id: 电影ID
        :return: 电影详情
        """
        try:
            url = self._build_url(f"/v1/movies/{quote(provider)}/{quote(movie_id)}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url)

            if response is None:
                logger.warning(f"Metatube API 获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Metatube API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return MetatubeMovieDetail.model_validate(data['data'])
                else:
                    return MetatubeMovieDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"Metatube 获取详情异常: {str(e)}")
            return None

    async def async_get_detail(self, provider: str, movie_id: str) -> Optional[MetatubeMovieDetail]:
        """
        异步获取电影详情

        :param provider: 数据来源
        :param movie_id: 电影ID
        :return: 电影详情
        """
        try:
            url = self._build_url(f"/v1/movies/{quote(provider)}/{quote(movie_id)}")

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url)

            if response is None:
                logger.warning(f"Metatube API 异步获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Metatube API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return MetatubeMovieDetail.model_validate(data['data'])
                else:
                    return MetatubeMovieDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"Metatube 异步获取详情异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """
        测试API连接

        :return: 连接是否成功
        """
        try:
            # 尝试一个简单的搜索请求
            url = self._build_url("/v1/movies/search")
            params = {"q": "TEST-001", "fallback": "False"}

            response = RequestUtils(
                timeout=5,
                proxies=self._proxies
            ).get_res(url, params=params)

            return response is not None and response.status_code in [200, 404]

        except Exception as e:
            logger.debug(f"Metatube 连接测试失败: {str(e)}")
            return False
