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
    ThePornDBSceneDetail, ThePornDBDetailResponse,
    ThePornDBJAVScene, ThePornDBJAVSearchResponse,
    ThePornDBJAVDetail
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
    API_JAV_URL = "/jav/{}"  # JAV 详情 API

    # Web 端点 (JAV 搜索页面)
    WEB_JAV_SEARCH_URL = "/jav"  # ?q={}&orderBy={}&page={}

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

    def _build_web_url(self, endpoint: str) -> str:
        """构建 Web 完整URL"""
        base = self.WEB_BASE_URL.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search_jav(self, keyword: str, page: int = 1,
                   order_by: str = "most_relevant") -> Optional[List[ThePornDBJAVScene]]:
        """
        搜索 JAV

        使用 ThePornDB API 的 /jav 端点，通过 external_id 参数搜索
        API Token 必须配置才能使用

        :param keyword: 搜索关键词（番号，如 MIAB-427）
        :param page: 页码(默认1)
        :param order_by: 排序方式(此API不支持，保留参数兼容性)
        :return: 搜索结果列表
        """
        if not keyword:
            return None

        try:
            # 使用 API 的 /jav 端点，通过 external_id 参数搜索
            url = self._build_url("/jav")
            params = {"external_id": keyword}

            logger.debug(f"ThePornDB JAV 搜索 URL: {url}?external_id={keyword}")

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
                # 401 表示 API Token 无效
                if response.status_code == 401:
                    logger.error("ThePornDB API Token 无效或已过期，请检查配置")
                return None

            import json

            data = response.json()
            if not data:
                return None

            logger.debug(f"ThePornDB JAV API 搜索响应: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            # 解析响应 - API 返回 {"data": [...], "links": {...}, "meta": {...}}
            if isinstance(data, dict) and 'data' in data:
                scenes_data = data['data']
                if isinstance(scenes_data, list) and scenes_data:
                    # 查找完全匹配的结果
                    exact_matches = [s for s in scenes_data if s.get('external_id', '').lower() == keyword.lower()]

                    scenes_to_validate = exact_matches if exact_matches else scenes_data

                    try:
                        validated_scenes = []
                        for item in scenes_to_validate:
                            try:
                                validated_scenes.append(ThePornDBJAVScene.model_validate(item))
                            except Exception as ve:
                                logger.debug(f"单个场景验证失败，跳过: {str(ve)}, 数据: {item}")
                                continue

                        if validated_scenes:
                            if exact_matches:
                                logger.info(f"ThePornDB JAV: 找到 {len(validated_scenes)} 个完全匹配结果")
                            else:
                                logger.debug(f"ThePornDB JAV: 验证了 {len(validated_scenes)}/{len(scenes_to_validate)} 个场景")
                            return validated_scenes
                        else:
                            # 所有场景验证失败，返回空列表
                            logger.debug(f"ThePornDB JAV: 所有 {len(scenes_to_validate)} 个场景验证失败")
                            return []
                    except Exception as e:
                        logger.error(f"ThePornDB JAV 场景验证失败: {str(e)}")
                        return []

            logger.warning(f"ThePornDB JAV API 搜索未找到结果")
            return None

        except Exception as e:
            logger.error(f"ThePornDB JAV 搜索异常: {str(e)}")
            return None

    async def async_search_jav(self, keyword: str, page: int = 1,
                              order_by: str = "most_relevant") -> Optional[List[ThePornDBJAVScene]]:
        """
        异步搜索 JAV

        使用 ThePornDB API 的 /jav 端点，通过 external_id 参数搜索
        API Token 必须配置才能使用

        :param keyword: 搜索关键词（番号，如 MIAB-427）
        :param page: 页码(默认1)
        :param order_by: 排序方式(此API不支持，保留参数兼容性)
        :return: 搜索结果列表
        """
        if not keyword:
            return None

        try:
            # 使用 API 的 /jav 端点，通过 external_id 参数搜索
            url = self._build_url("/jav")
            params = {"external_id": keyword}

            logger.debug(f"ThePornDB JAV 异步搜索 URL: {url}?external_id={keyword}")

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ThePornDB JAV 异步 API 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV 异步 API 返回状态码: {response.status_code}")
                # 401 表示 API Token 无效
                if response.status_code == 401:
                    logger.error("ThePornDB API Token 无效或已过期，请检查配置")
                return None

            import json

            data = response.json()
            if not data:
                return None

            logger.debug(f"ThePornDB JAV 异步 API 搜索响应: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            # 解析响应 - API 返回 {"data": [...], "links": {...}, "meta": {...}}
            if isinstance(data, dict) and 'data' in data:
                scenes_data = data['data']
                if isinstance(scenes_data, list) and scenes_data:
                    # 查找完全匹配的结果
                    exact_matches = [s for s in scenes_data if s.get('external_id', '').lower() == keyword.lower()]

                    if exact_matches:
                        logger.info(f"ThePornDB JAV 异步: 找到 {len(exact_matches)} 个完全匹配结果")
                        return [ThePornDBJAVScene.model_validate(item) for item in exact_matches]

                    logger.debug(f"ThePornDB JAV 异步: 找到 {len(scenes_data)} 个结果，无完全匹配")
                    return [ThePornDBJAVScene.model_validate(item) for item in scenes_data]

            logger.warning(f"ThePornDB JAV 异步 API 搜索未找到结果")
            return None

        except Exception as e:
            logger.error(f"ThePornDB JAV 异步搜索异常: {str(e)}")
            return None

    def get_jav_detail(self, jav_id: str) -> Optional[ThePornDBJAVDetail]:
        """
        获取 JAV 详情

        通过 API 获取 JAV 详细信息
        支持 ID（数字）、slug 或 UUID

        :param jav_id: JAV 标识符 (UUID、slug 或数字ID字符串)
        :return: JAV 详情
        """
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(quote(jav_id)))
            logger.debug(f"ThePornDB JAV 详情请求 URL: {url}")
            logger.debug(f"ThePornDB JAV API Token: {'已设置' if self._api_token else '未设置'}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB JAV 获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV 获取详情返回状态码: {response.status_code}, URL: {url}")
                # 如果是 404，尝试使用 /scenes/ 端点
                if response.status_code == 404:
                    logger.debug(f"ThePornDB JAV 404，尝试备用端点 /scenes/")
                    try:
                        alt_url = self._build_url(f"/scenes/{quote(jav_id)}")
                        logger.debug(f"ThePornDB JAV 备用 URL: {alt_url}")
                        alt_response = RequestUtils(
                            timeout=self._timeout,
                            proxies=self._proxies,
                            headers=self._get_headers()
                        ).get_res(alt_url)
                        if alt_response and alt_response.status_code == 200:
                            response = alt_response
                            logger.debug(f"ThePornDB JAV 备用端点成功")
                        else:
                            logger.warning(f"ThePornDB JAV 备用端点也失败: {alt_response.status_code if alt_response else 'No response'}")
                            return None
                    except Exception as e:
                        logger.warning(f"ThePornDB JAV 备用端点请求异常: {str(e)}")
                        return None
                else:
                    return None

            data = response.json()
            if not data:
                return None

            # 解析响应 - JAV API 返回 {"data": {...}}
            if isinstance(data, dict):
                if 'data' in data:
                    return ThePornDBJAVDetail.model_validate(data['data'])
                else:
                    return ThePornDBJAVDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"ThePornDB JAV 获取详情异常: {str(e)}")
            return None

    async def async_get_jav_detail(self, jav_id: str) -> Optional[ThePornDBJAVDetail]:
        """
        异步获取 JAV 详情

        通过 API 获取 JAV 详细信息
        支持 ID（数字）、slug 或 UUID

        :param jav_id: JAV 标识符 (UUID、slug 或数字ID字符串)
        :return: JAV 详情
        """
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(quote(jav_id)))
            logger.debug(f"ThePornDB JAV 异步详情请求 URL: {url}")
            logger.debug(f"ThePornDB JAV API Token: {'已设置' if self._api_token else '未设置'}")

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url)

            if response is None:
                logger.warning(f"ThePornDB JAV 异步获取详情失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ThePornDB JAV 异步获取详情返回状态码: {response.status_code}, URL: {url}")
                # 如果是 404，尝试使用 /scenes/ 端点
                if response.status_code == 404:
                    logger.debug(f"ThePornDB JAV 异步 404，尝试备用端点 /scenes/")
                    try:
                        alt_url = self._build_url(f"/scenes/{quote(jav_id)}")
                        logger.debug(f"ThePornDB JAV 异步备用 URL: {alt_url}")
                        alt_response = await AsyncRequestUtils(
                            timeout=self._timeout,
                            proxies=self._proxies,
                            headers=self._get_headers()
                        ).get_res(alt_url)
                        if alt_response and alt_response.status_code == 200:
                            response = alt_response
                            logger.debug(f"ThePornDB JAV 异步备用端点成功")
                        else:
                            logger.warning(f"ThePornDB JAV 异步备用端点也失败: {alt_response.status_code if alt_response else 'No response'}")
                            return None
                    except Exception as e:
                        logger.warning(f"ThePornDB JAV 异步备用端点请求异常: {str(e)}")
                        return None
                else:
                    return None

            data = response.json()
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                return ThePornDBJAVDetail.model_validate(data)

            return None

        except Exception as e:
            logger.error(f"ThePornDB JAV 异步获取详情异常: {str(e)}")
            return None

    def search_jav_to_detail(self, keyword: str, page: int = 1,
                            order_by: str = "most_relevant") -> Optional[List[ThePornDBJAVDetail]]:
        """
        搜索 JAV 并获取详情（两步法）

        1. 通过网页搜索获取 JAV 列表（含 ID 和 slug）
        2. 通过 API 获取每个 JAV 的详细信息

        :param keyword: 搜索关键词
        :param page: 页码(默认1)
        :param order_by: 排序方式(most_relevant, recently_created, recently_released等)
        :return: JAV 详情列表
        """
        scenes = self.search_jav(keyword, page, order_by)
        if not scenes:
            return None

        logger.debug(f"ThePornDB JAV: 找到 {len(scenes)} 个场景，开始获取详情")
        details = []
        for i, scene in enumerate(scenes):
            # 优先使用 slug，如果 slug 不存在则使用数字 ID
            identifier = scene.slug if scene.slug else str(scene.id)
            logger.debug(f"ThePornDB JAV: 场景 {i+1}/{len(scenes)} - ID={scene.id}, slug={scene.slug}, 使用标识符={identifier}")
            detail = self.get_jav_detail(identifier)
            if detail:
                details.append(detail)
            else:
                logger.debug(f"ThePornDB JAV: 场景 {i+1} 详情获取失败")

        logger.debug(f"ThePornDB JAV: 成功获取 {len(details)}/{len(scenes)} 个场景的详情")
        return details if details else None

    async def async_search_jav_to_detail(self, keyword: str, page: int = 1,
                                         order_by: str = "most_relevant") -> Optional[List[ThePornDBJAVDetail]]:
        """
        异步搜索 JAV 并获取详情（两步法）

        1. 通过网页搜索获取 JAV 列表（含 ID 和 slug）
        2. 通过 API 获取每个 JAV 的详细信息

        :param keyword: 搜索关键词
        :param page: 页码(默认1)
        :param order_by: 排序方式(most_relevant, recently_created, recently_released等)
        :return: JAV 详情列表
        """
        scenes = await self.async_search_jav(keyword, page, order_by)
        if not scenes:
            return None

        logger.debug(f"ThePornDB JAV 异步: 找到 {len(scenes)} 个场景，开始获取详情")
        details = []
        for i, scene in enumerate(scenes):
            # 优先使用 slug，如果 slug 不存在则使用数字 ID
            identifier = scene.slug if scene.slug else str(scene.id)
            logger.debug(f"ThePornDB JAV 异步: 场景 {i+1}/{len(scenes)} - ID={scene.id}, slug={scene.slug}, 使用标识符={identifier}")
            detail = await self.async_get_jav_detail(identifier)
            if detail:
                details.append(detail)
            else:
                logger.debug(f"ThePornDB JAV 异步: 场景 {i+1} 详情获取失败")

        logger.debug(f"ThePornDB JAV 异步: 成功获取 {len(details)}/{len(scenes)} 个场景的详情")
        return details if details else None
