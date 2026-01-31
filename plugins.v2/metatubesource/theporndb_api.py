"""
ThePornDB API 客户端
移植自 Jellyfin.Plugin.ThePornDB
"""
from typing import Optional, List, Dict
from urllib.parse import urljoin, quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import (
    ThePornDBScene, ThePornDBSearchResponse,
    ThePornDBSceneDetail, ThePornDBDetailResponse
)


class ThePornDBApiClient:
    """ThePornDB API 客户端"""

    # API 基础地址
    API_BASE_URL = "https://api.theporndb.net"

    # API 端点
    API_SCENE_SEARCH_URL = "/scenes"  # ?parse={}&hash={}&year={}
    API_MOVIE_SEARCH_URL = "/movies"  # ?parse={}&hash={}&year={}
    API_SCENE_URL = "/scenes/{}"
    API_MOVIE_URL = "/movies/{}"
    API_PERFORMER_SEARCH_URL = "/performers"  # ?q={}
    API_PERFORMER_URL = "/performers/{}"

    # User-Agent
    USER_AGENT = "MoviePilot-Plugins/ThePornDB/1.0"

    def __init__(self, api_token: str = "",
                 timeout: int = 30, proxies: Dict[str, str] = None):
        """
        初始化 ThePornDB API 客户端

        :param api_token: API Token (从 https://theporndb.net 获取)
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        self._api_token = api_token
        self._timeout = timeout
        self._proxies = proxies

    @property
    def api_token(self) -> str:
        return self._api_token

    @api_token.setter
    def api_token(self, value: str):
        self._api_token = value or ""

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        # 确保没有重复的斜杠
        base = self.API_BASE_URL.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search_scenes(self, search_title: str, year: int = None,
                      oshash: str = "") -> Optional[List[ThePornDBScene]]:
        """
        搜索场景

        :param search_title: 搜索标题
        :param year: 年份(可选)
        :param oshash: 文件哈希(可选)
        :return: 搜索结果列表
        """
        if not search_title:
            return None

        try:
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {
                "parse": search_title,
            }
            if oshash:
                params["hash"] = oshash
            if year:
                params["year"] = str(year)

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ThePornDB API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                result = ThePornDBSearchResponse.model_validate(data)
                return result.data
            elif isinstance(data, list):
                return [ThePornDBScene.model_validate(item) for item in data]

            return None

        except Exception as e:
            logger.error(f"ThePornDB 搜索场景异常: {str(e)}")
            return None

    async def async_search_scenes(self, search_title: str, year: int = None,
                                  oshash: str = "") -> Optional[List[ThePornDBScene]]:
        """
        异步搜索场景

        :param search_title: 搜索标题
        :param year: 年份(可选)
        :param oshash: 文件哈希(可选)
        :return: 搜索结果列表
        """
        if not search_title:
            return None

        try:
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {
                "parse": search_title,
            }
            if oshash:
                params["hash"] = oshash
            if year:
                params["year"] = str(year)

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ThePornDB API 异步请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                result = ThePornDBSearchResponse.model_validate(data)
                return result.data
            elif isinstance(data, list):
                return [ThePornDBScene.model_validate(item) for item in data]

            return None

        except Exception as e:
            logger.error(f"ThePornDB 异步搜索场景异常: {str(e)}")
            return None

    def get_scene_detail(self, scene_id: str) -> Optional[ThePornDBSceneDetail]:
        """
        获取场景详情

        :param scene_id: 场景ID (UUID)
        :return: 场景详情
        """
        if not scene_id:
            return None

        try:
            url = self._build_url(self.API_SCENE_URL.format(quote(scene_id)))

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB API 获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return ThePornDBSceneDetail.model_validate(data['data'])
                else:
                    return ThePornDBSceneDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"ThePornDB 获取详情异常: {str(e)}")
            return None

    async def async_get_scene_detail(self, scene_id: str) -> Optional[ThePornDBSceneDetail]:
        """
        异步获取场景详情

        :param scene_id: 场景ID (UUID)
        :return: 场景详情
        """
        if not scene_id:
            return None

        try:
            url = self._build_url(self.API_SCENE_URL.format(quote(scene_id)))

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB API 异步获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return ThePornDBSceneDetail.model_validate(data['data'])
                else:
                    return ThePornDBSceneDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"ThePornDB 异步获取详情异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """
        测试API连接

        :return: 连接是否成功
        """
        try:
            # 尝试一个简单的搜索请求
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {"parse": "test"}

            response = RequestUtils(
                timeout=5,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            # 200: 成功, 401: Token无效但API可达, 429: 限流但API可达
            return response is not None and response.status_code in [200, 401, 429]

        except Exception as e:
            logger.debug(f"ThePornDB 连接测试失败: {str(e)}")
            return False
