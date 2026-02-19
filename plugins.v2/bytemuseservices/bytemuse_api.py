"""
ByteMuse 扩展 API 客户端
提供演员、上新、推荐、榜单、厂牌等接口
"""
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import ByteMuseMovie, ByteMuseActor


class ByteMuseExtendedClient:
    """ByteMuse 扩展 API 客户端"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "DNT": "1",
        "Content-Type": "application/json",
    }

    def __init__(self, base_url: str = "http://127.0.0.1:3750",
                 api_token: str = "", timeout: int = 30,
                 proxies: Dict[str, str] = None):
        """
        初始化 ByteMuse 扩展 API 客户端

        :param base_url: API 基础地址
        :param api_token: API Token
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        self._base_url = base_url.rstrip('/')
        self._api_token = api_token
        self._timeout = timeout
        self._proxies = proxies

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

    def _safe_validate_movie(self, data: Any) -> Optional[ByteMuseMovie]:
        """安全地验证电影数据"""
        if not isinstance(data, dict):
            return None
        try:
            return ByteMuseMovie.model_validate(data)
        except Exception as e:
            logger.debug(f"ByteMuse 电影数据验证失败: {str(e)}")
            try:
                field_names = set(ByteMuseMovie.model_fields.keys())
                filtered_data = {k: v for k, v in data.items() if k in field_names}
                return ByteMuseMovie.model_validate(filtered_data)
            except Exception:
                return None

    # ==================== 演员相关接口 ====================

    def get_hot_actors(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取热门演员

        :param limit: 返回数量限制
        :return: 演员列表
        """
        try:
            url = self._build_url("/api/v1/actors/hot")
            params = {"limit": limit}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取热门演员失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取热门演员异常: {str(e)}")
            return None

    def get_subscribed_actors(self, user_id: str = "default") -> Optional[List[Dict[str, Any]]]:
        """
        获取订阅中的演员

        :param user_id: 用户ID
        :return: 演员列表
        """
        try:
            url = self._build_url(f"/api/v1/actors/subscribed")
            params = {"user_id": user_id}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取订阅演员失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取订阅演员异常: {str(e)}")
            return None

    def get_actor_works(self, actor_name: str, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取演员作品

        :param actor_name: 演员名称
        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        try:
            url = self._build_url("/api/v1/actors/works")
            params = {
                "actor": actor_name,
                "page": page,
                "page_size": page_size
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                movies = []
                for item in data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                return movies if movies else None
            elif isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取演员作品异常: {str(e)}")
            return None

    # ==================== 上新相关接口 ====================

    def get_new_releases(self, days: int = 7, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取最新上架

        :param days: 天数
        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        try:
            url = self._build_url("/api/v1/releases/new")
            params = {
                "days": days,
                "page": page,
                "page_size": page_size
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                movies = []
                for item in data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                return movies if movies else None
            elif isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取最新上架异常: {str(e)}")
            return None

    # ==================== 推荐相关接口 ====================

    def get_recommendations(self, category: str = "all", page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取推荐内容

        :param category: 分类 (all/high_rated/popular/trending)
        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        try:
            url = self._build_url("/api/v1/recommendations")
            params = {
                "category": category,
                "page": page,
                "page_size": page_size
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                movies = []
                for item in data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                return movies if movies else None
            elif isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取推荐内容异常: {str(e)}")
            return None

    # ==================== 榜单相关接口 ====================

    def get_javdb_hot(self, period: str = "daily", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取 JavDB 热门榜

        :param period: 周期 (daily/weekly/monthly)
        :param limit: 返回数量限制
        :return: 榜单列表
        """
        try:
            url = self._build_url(f"/api/v1/rankings/javdb/hot/{period}")
            params = {"limit": limit}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取 JavDB 热门榜失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取 JavDB 热门榜异常: {str(e)}")
            return None

    def get_javlibrary_wanted(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取 JavLibrary 想要榜

        :param limit: 返回数量限制
        :return: 榜单列表
        """
        try:
            url = self._build_url("/api/v1/rankings/javlibrary/wanted")
            params = {"limit": limit}

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取 JavLibrary 想要榜失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取 JavLibrary 想要榜异常: {str(e)}")
            return None

    # ==================== 厂牌相关接口 ====================

    STUDIOS = [
        "S1", "IdeaPocket", "Moodyz", "Premium",
        "DAS", "Madonna", "Honnaka", "Attackers", "Wanz"
    ]

    def get_studio_works(self, studio: str, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取厂牌作品

        :param studio: 厂牌名称
        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        try:
            url = self._build_url("/api/v1/studios/works")
            params = {
                "studio": studio,
                "page": page,
                "page_size": page_size
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                movies = []
                for item in data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                return movies if movies else None
            elif isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取厂牌作品异常: {str(e)}")
            return None

    def get_all_studios(self) -> List[str]:
        """获取所有支持的厂牌列表"""
        return self.STUDIOS.copy()

    # ==================== 异步接口 ====================

    async def async_get_hot_actors(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """异步获取热门演员"""
        try:
            url = self._build_url("/api/v1/actors/hot")
            params = {"limit": limit}

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 异步获取热门演员异常: {str(e)}")
            return None

    async def async_get_new_releases(self, days: int = 7, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """异步获取最新上架"""
        try:
            url = self._build_url("/api/v1/releases/new")
            params = {
                "days": days,
                "page": page,
                "page_size": page_size
            }

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, list):
                movies = []
                for item in data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                return movies if movies else None
            elif isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 异步获取最新上架异常: {str(e)}")
            return None
