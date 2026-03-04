"""
ByteMuse API 客户端
基于 MoviePilot API 快速参考文档

服务地址: http://10.0.0.1:3750
认证方式: 账号密码登录获取 JWT Token
"""
from typing import Optional, List, Dict, Any
from urllib.parse import quote
import threading
import time

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import ByteMuseMovie, ByteMuseActor


class ByteMuseApiClient:
    """ByteMuse API 客户端"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "DNT": "1",
        "Content-Type": "application/json",
    }

    # 厂牌类型映射
    STUDIO_TYPES = {
        "s1": "s1-0",
        "ideapocket": "ip-0",
        "ip": "ip-0",
        "moodyz": "moodyz-0",
        "premium": "premium-0",
        "das": "das-0",
        "madonna": "madonna-0",
        "honnaka": "honnaka-0",
        "attackers": "attackers-0",
        "wanz": "wanz-0",
    }

    # 榜单类型映射
    RANK_TYPES = {
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "javlibrary": "1",
    }

    def __init__(self, base_url: str = "http://10.0.0.1:3750",
                 username: str = "", password: str = "",
                 api_token: str = "", timeout: int = 30,
                 proxies: Dict[str, str] = None,
                 proxy_url: str = "http://10.0.0.1:7890"):
        """
        初始化 ByteMuse API 客户端

        :param base_url: API 基础地址
        :param username: 用户名
        :param password: 密码
        :param api_token: API Token (已弃用，保留兼容性，推荐使用 username/password)
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置 (已弃用，使用 proxy_url)
        :param proxy_url: 代理服务器地址
        """
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._api_token = api_token  # 保留兼容性
        self._timeout = timeout

        # JWT Token 相关
        self._jwt_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._token_lock = threading.Lock()

        # 处理代理配置
        if proxies:
            self._proxies = proxies
        elif proxy_url:
            self._proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        else:
            self._proxies = None

        logger.debug(f"ByteMuse API 初始化: base_url={self._base_url}, proxy={self._proxies is not None}, has_credentials={bool(username and password)}")

        # 如果提供了用户名和密码，自动登录
        if self._username and self._password:
            self._ensure_authenticated()

    def _ensure_authenticated(self) -> bool:
        """
        确保已认证（自动登录）
        :return: 是否认证成功
        """
        # 如果 token 有效，直接返回
        if self._jwt_token and self._token_expiry:
            if time.time() < self._token_expiry:
                return True

        # 需要重新登录
        return self.login()

    def login(self) -> bool:
        """
        登录获取 JWT Token

        接口: GET /api/v1/login?username={username}&password={password}&token_key=

        :return: 是否登录成功
        """
        if not self._username or not self._password:
            logger.warning("ByteMuse 登录失败: 未提供用户名或密码")
            return False

        try:
            url = self._build_url("/api/v1/login")
            params = {
                "username": self._username,
                "password": self._password,
                "token_key": ""
            }

            logger.debug(f"ByteMuse 登录请求: {url}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.error(f"ByteMuse 登录失败: 无法连接到服务 {self._base_url}")
                return False

            if response.status_code != 200:
                logger.warning(f"ByteMuse 登录失败: HTTP {response.status_code} - {response.text[:200]}")
                return False

            data = response.json()

            # 检查响应格式
            if isinstance(data, dict) and data.get("success"):
                token = data.get("data", {}).get("token")
                if token:
                    with self._token_lock:
                        self._jwt_token = token
                        # Token 有效期设为 24 小时（提前刷新）
                        self._token_expiry = time.time() + 23 * 60 * 60
                    logger.info(f"ByteMuse 登录成功: 用户 {self._username}")
                    return True
                else:
                    logger.warning("ByteMuse 登录失败: 响应中未找到 token")
            elif isinstance(data, dict) and "token" in data:
                # 直接返回 token 的格式
                with self._token_lock:
                    self._jwt_token = data["token"]
                    self._token_expiry = time.time() + 23 * 60 * 60
                logger.info(f"ByteMuse 登录成功: 用户 {self._username}")
                return True
            else:
                logger.warning(f"ByteMuse 登录失败: 意外的响应格式 {data}")

            return False

        except Exception as e:
            logger.error(f"ByteMuse 登录异常: {str(e)}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（包含认证信息）"""
        headers = self.DEFAULT_HEADERS.copy()

        # 优先使用 JWT Token
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        # 兼容旧的 api_token 方式
        elif self._api_token:
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

    # ==================== 1. 演员相关接口 ====================

    def get_actors(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        获取演员列表（订阅中）

        接口: GET /api/v1/actors

        :param page: 页码
        :param page_size: 每页数量
        :return: 演员列表
        """
        # 确保已认证
        if not self._ensure_authenticated():
            logger.warning("ByteMuse 获取演员列表失败: 认证失败")
            return None

        try:
            url = self._build_url("/api/v1/actors")
            params = {
                "page": page,
                "page_size": page_size
            }

            logger.debug(f"ByteMuse 请求: GET {url} params={params}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            logger.debug(f"ByteMuse 响应: response={response is not None}, status={response.status_code if response else 'N/A'}")

            if response is None:
                logger.error(f"ByteMuse 获取演员列表失败: 无法连接到服务 {self._base_url}，请检查服务是否运行或代理配置")
                return None

            if response.status_code != 200:
                logger.warning(f"ByteMuse 获取演员列表失败: HTTP {response.status_code}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取演员列表异常: {str(e)}")
            return None

    def get_actors_rank(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取热门演员

        接口: GET /api/v1/actors/rank

        :param limit: 返回数量限制
        :return: 演员列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/actors/rank")
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

    # ==================== 2. 上新相关接口 ====================

    def get_release_today(self, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取今日上新

        接口: POST /api/v1/codes/release_today

        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/codes/release_today")
            data = {
                "page": page,
                "page_size": page_size
            }

            logger.debug(f"ByteMuse 请求今日上新: {url}, data={data}")
            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).post_res(url, json=data)

            if response is None or response.status_code != 200:
                return None

            resp_data = response.json()
            logger.debug(f"ByteMuse 今日上新响应: type={type(resp_data)}, has_data={'data' in resp_data if isinstance(resp_data, dict) else 'N/A'}")

            if isinstance(resp_data, list):
                movies = []
                for item in resp_data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                    else:
                        logger.warning(f"跳过无效的电影数据: {item}")
                return movies if movies else None
            elif isinstance(resp_data, dict) and "data" in resp_data:
                data_obj = resp_data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                        else:
                            logger.warning(f"跳过无效的电影数据: {item}")
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取今日上新异常: {str(e)}")
            return None

    # ==================== 3. 推荐相关接口 ====================

    def get_recommend(self, category: str = "all", page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """
        获取个性化推荐

        接口: POST /api/v1/codes/recommend

        :param category: 分类 (all/high_rated/popular/trending)
        :param page: 页码
        :param page_size: 每页数量
        :return: 作品列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/codes/recommend")
            data = {
                "category": category,
                "page": page,
                "page_size": page_size
            }

            logger.debug(f"ByteMuse 请求推荐: {url}, data={data}")
            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).post_res(url, json=data)

            if response is None or response.status_code != 200:
                return None

            resp_data = response.json()
            logger.debug(f"ByteMuse 推荐响应: type={type(resp_data)}, has_data={'data' in resp_data if isinstance(resp_data, dict) else 'N/A'}")

            if isinstance(resp_data, list):
                movies = []
                for item in resp_data:
                    movie = self._safe_validate_movie(item)
                    if movie:
                        movies.append(movie)
                    else:
                        logger.warning(f"跳过无效的电影数据: {item}")
                return movies if movies else None
            elif isinstance(resp_data, dict) and "data" in resp_data:
                data_obj = resp_data["data"]
                if isinstance(data_obj, list):
                    movies = []
                    for item in data_obj:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                        else:
                            logger.warning(f"跳过无效的电影数据: {item}")
                    return movies if movies else None

            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取推荐内容异常: {str(e)}")
            return None

    # ==================== 4. 榜单相关接口 ====================

    def get_ranks(self, rank_type: str = "daily", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取榜单

        接口: GET /api/v1/ranks?type={type}

        :param rank_type: 榜单类型 (daily/weekly/monthly/javlibrary)
        :param limit: 返回数量限制
        :return: 榜单列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            # 映射榜单类型
            type_param = self.RANK_TYPES.get(rank_type, rank_type)

            url = self._build_url("/api/v1/ranks")
            params = {
                "type": type_param,
                "limit": limit
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取榜单失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取榜单异常: {str(e)}")
            return None

    # ==================== 5. 厂牌相关接口 ====================

    def get_studio_ranks(self, studio: str = "s1", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """
        获取厂牌榜单

        接口: GET /api/v1/ranks?type={studio_type}

        :param studio: 厂牌名称 (s1/ideapocket/moodyz/premium/das/madonna/honnaka/attackers/wanz)
        :param limit: 返回数量限制
        :return: 厂牌榜单列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            # 映射厂牌类型
            studio_key = studio.lower().replace(" ", "")
            type_param = self.STUDIO_TYPES.get(studio_key, f"{studio_key}-0")

            url = self._build_url("/api/v1/ranks")
            params = {
                "type": type_param,
                "limit": limit
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 获取厂牌榜单失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取厂牌榜单异常: {str(e)}")
            return None

    # ==================== 工具方法 ====================

    def get_supported_studios(self) -> List[str]:
        """获取所有支持的厂牌列表"""
        return list(self.STUDIO_TYPES.keys())

    def get_supported_rank_types(self) -> List[str]:
        """获取所有支持的榜单类型"""
        return list(self.RANK_TYPES.keys())

    # ==================== 异步接口 ====================

    async def async_get_actors(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """异步获取演员列表"""
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/actors")
            params = {
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
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 异步获取演员列表异常: {str(e)}")
            return None

    async def async_get_release_today(self, page: int = 1, page_size: int = 20) -> Optional[List[ByteMuseMovie]]:
        """异步获取今日上新"""
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/codes/release_today")
            data = {
                "page": page,
                "page_size": page_size
            }

            response = await AsyncRequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).post_res(url, json=data)

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
            logger.error(f"ByteMuse 异步获取今日上新异常: {str(e)}")
            return None

    # ==================== 6. 搜索接口 ====================

    def search_by_code(self, query: str) -> Optional[Dict[str, Any]]:
        """
        根据番号搜索

        接口: GET /api/v1/codes/search?query={query}

        :param query: 搜索关键词(番号)
        :return: 搜索结果
        """
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            logger.debug(f"ByteMuse 搜索: query={query}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 搜索失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data

        except Exception as e:
            logger.error(f"ByteMuse 搜索异常: {str(e)}")
            return None

    def search_torrents(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        搜索种子

        接口: GET /api/v1/torrents/search?query={query}

        :param query: 搜索关键词(番号)
        :return: 种子列表
        """
        if not self._ensure_authenticated():
            return None

        try:
            url = self._build_url("/api/v1/torrents/search")
            params = {"query": query}

            logger.debug(f"ByteMuse 搜索种子: query={query}")

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None or response.status_code != 200:
                logger.warning(f"ByteMuse 搜索种子失败: {response.status_code if response else 'No response'}")
                return None

            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            elif isinstance(data, list):
                return data
            return data

        except Exception as e:
            logger.error(f"ByteMuse 搜索种子异常: {str(e)}")
            return None
