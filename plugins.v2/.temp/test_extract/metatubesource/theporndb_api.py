"""
ThePornDB API 客户端
移植自 Jellyfin.Plugin.ThePornDB
"""
import json
import re
from html import unescape
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
    WEB_BASE_URL = "https://theporndb.net"

    # API 端点
    API_SCENE_SEARCH_URL = "/scenes"  # ?parse={}&hash={}&year={}
    API_MOVIE_SEARCH_URL = "/movies"  # ?parse={}&hash={}&year={}
    API_SCENE_URL = "/scenes/{}"
    API_MOVIE_URL = "/movies/{}"
    API_PERFORMER_SEARCH_URL = "/performers"  # ?q={}
    API_PERFORMER_URL = "/performers/{}"

    # JAV API 端点 (日本成人视频)
    API_JAV_SEARCH_URL = "/jav"  # ?q={}&orderBy={}
    API_JAV_URL = "/jav/{}"

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

    def _build_url(self, endpoint: str, use_web: bool = False) -> str:
        """构建完整URL

        :param endpoint: API端点
        :param use_web: 是否使用网页基础URL (JAV搜索需要使用网页端点)
        """
        base = (self.WEB_BASE_URL if use_web else self.API_BASE_URL).rstrip('/')
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

    def search_javs(self, search_title: str, order_by: str = "most_relevant",
                    page: int = 1) -> Optional[List[Dict]]:
        """
        搜索 JAV (日本成人视频)
        注意：JAV 搜索使用网页端点，数据在 data-page 属性中（Laravel Inertia）

        :param search_title: 搜索标题/番号
        :param order_by: 排序方式 (most_relevant, recently_released, etc.)
        :param page: 页码
        :return: 搜索结果列表
        """
        if not search_title:
            return None

        try:
            # 使用网页端点，不是 API 端点
            url = self._build_url(self.API_JAV_SEARCH_URL, use_web=True)
            params = {
                "q": search_title,
                "orderBy": order_by,
                "page": page
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ThePornDB JAV API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV API 返回状态码: {response.status_code}")
                return None

            # JAV 网页返回 HTML，数据嵌入在 <div id="app" data-page="..."> 中
            # 数据使用 HTML 实体编码
            html = response.text

            # 查找 <div id="app" data-page="...">
            data_page_pattern = r'<div\s+id="app"[^>]*\sdata-page="([^"]*)"'
            data_page_match = re.search(data_page_pattern, html, re.DOTALL)

            if data_page_match:
                try:
                    # 解码 HTML 实体 (&quot; -> ", &amp; -> &, etc.)
                    encoded_json = data_page_match.group(1)
                    decoded_json = unescape(encoded_json)

                    # 解析 JSON
                    page_data = json.loads(decoded_json)

                    # 提取 props.scenes.data
                    if 'props' in page_data and 'scenes' in page_data['props']:
                        scenes_data = page_data['props']['scenes']
                        if 'data' in scenes_data:
                            scenes = scenes_data['data']
                            return scenes if scenes else None

                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.debug(f"ThePornDB JAV 解析数据失败: {e}")

            logger.warning(f"ThePornDB JAV 无法从 HTML 中提取数据")
            return None

        except Exception as e:
            logger.error(f"ThePornDB 搜索 JAV 异常: {str(e)}")
            return None

    async def async_search_javs(self, search_title: str, order_by: str = "most_relevant",
                                page: int = 1) -> Optional[List[Dict]]:
        """
        异步搜索 JAV
        注意：JAV 搜索使用网页端点，数据在 data-page 属性中（Laravel Inertia）

        :param search_title: 搜索标题/番号
        :param order_by: 排序方式
        :param page: 页码
        :return: 搜索结果列表
        """
        if not search_title:
            return None

        try:
            # 使用网页端点，不是 API 端点
            url = self._build_url(self.API_JAV_SEARCH_URL, use_web=True)
            params = {
                "q": search_title,
                "orderBy": order_by,
                "page": page
            }

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ThePornDB JAV API 异步请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV API 返回状态码: {response.status_code}")
                return None

            # JAV 网页返回 HTML，数据嵌入在 <div id="app" data-page="..."> 中
            html = response.text

            # 查找 <div id="app" data-page="...">
            data_page_pattern = r'<div\s+id="app"[^>]*\sdata-page="([^"]*)"'
            data_page_match = re.search(data_page_pattern, html, re.DOTALL)

            if data_page_match:
                try:
                    # 解码 HTML 实体
                    encoded_json = data_page_match.group(1)
                    decoded_json = unescape(encoded_json)

                    # 解析 JSON
                    page_data = json.loads(decoded_json)

                    # 提取 props.scenes.data
                    if 'props' in page_data and 'scenes' in page_data['props']:
                        scenes_data = page_data['props']['scenes']
                        if 'data' in scenes_data:
                            scenes = scenes_data['data']
                            return scenes if scenes else None

                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.debug(f"ThePornDB JAV 异步解析数据失败: {e}")

            logger.warning(f"ThePornDB JAV 异步无法从 HTML 中提取数据")
            return None

        except Exception as e:
            logger.error(f"ThePornDB 异步搜索 JAV 异常: {str(e)}")
            return None

    def get_jav_detail(self, jav_id: str) -> Optional[Dict]:
        """
        获取 JAV 详情

        :param jav_id: JAV ID (UUID格式，如 8661ab74-1922-49ec-a809-e64469d17d98)
        :return: JAV 详情
        """
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(jav_id))

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB JAV API 获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            logger.error(f"ThePornDB 获取 JAV 详情异常: {str(e)}")
            return None

    async def async_get_jav_detail(self, jav_id: str) -> Optional[Dict]:
        """
        异步获取 JAV 详情

        :param jav_id: JAV ID
        :return: JAV 详情
        """
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(jav_id))

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB JAV API 异步获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV API 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            logger.error(f"ThePornDB 异步获取 JAV 详情异常: {str(e)}")
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
