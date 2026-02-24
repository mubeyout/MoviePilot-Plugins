# Category: API客户端
"""
Byte-Muse API 客户端
通过 Byte-Muse 服务识别番号媒体信息
"""
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

# Pydantic v2 兼容性处理
try:
    from pydantic import ValidationError
    PYDANTIC_V2 = True
except ImportError:
    PYDANTIC_V2 = False

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
                 username: str = "", password: str = "",
                 api_token: str = "", timeout: int = 30,
                 proxies: Dict[str, str] = None):
        """
        初始化 Byte-Muse API 客户端

        :param base_url: API 基础地址
        :param username: 登录用户名
        :param password: 登录密码
        :param api_token: API Token (可直接提供，跳过登录)
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._api_token = api_token
        self._timeout = timeout
        self._proxies = proxies

        # 如果提供了用户名密码但没有 token，自动登录
        if username and password and not api_token:
            self._login()

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value.rstrip('/') if value else "http://127.0.0.1:3750"

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value or ""

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, value: str):
        self._password = value or ""

    @property
    def api_token(self) -> str:
        return self._api_token

    @api_token.setter
    def api_token(self, value: str):
        self._api_token = value or ""

    def _login(self) -> bool:
        """
        使用账号密码登录获取 Token

        :return: 登录是否成功
        """
        if not self._username or not self._password:
            logger.warning("Byte-Muse 登录失败: 未配置用户名或密码")
            return False

        try:
            url = self._build_url("/api/v1/login")
            params = {
                "username": self._username,
                "password": self._password,
                "token_key": ""
            }

            response = RequestUtils(
                timeout=self._timeout,
                proxies=self._proxies,
                headers=self.DEFAULT_HEADERS
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"Byte-Muse 登录请求失败: {url}")
                return False

            if response.status_code != 200:
                logger.warning(f"Byte-Muse 登录返回状态码: {response.status_code}")
                return False

            data = response.json()
            if not data:
                logger.warning("Byte-Muse 登录响应为空")
                return False

            # 解析响应
            if isinstance(data, dict):
                success = data.get("success", False)
                if success and "data" in data:
                    token = data["data"].get("token", "")
                    if token:
                        self._api_token = token
                        logger.info(f"Byte-Muse 登录成功: {self._username}")
                        return True
                    else:
                        logger.warning("Byte-Muse 登录响应中未找到 token")
                        return False
                else:
                    message = data.get("message", "未知错误")
                    logger.warning(f"Byte-Muse 登录失败: {message}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Byte-Muse 登录异常: {str(e)}")
            return False

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
        """
        安全地验证电影数据，忽略多余字段

        :param data: 原始数据
        :return: 验证后的电影对象或 None
        """
        if not isinstance(data, dict):
            return None

        try:
            # 尝试标准验证
            return ByteMuseMovie.model_validate(data)
        except Exception as e:
            # 标准验证失败，记录详细错误并尝试提取需要的字段
            error_msg = str(e)
            # 获取详细错误信息（Pydantic v2）
            if hasattr(e, 'errors'):
                errors_list = e.errors()
                error_details = "; ".join([f"{err.get('loc', ['unknown'])[0]}: {err.get('msg', '')}" for err in errors_list])
                logger.debug(f"Byte-Muse 标准验证失败详情: {error_details}")
            else:
                logger.debug(f"Byte-Muse 标准验证失败: {error_msg}")

            logger.debug(f"Byte-Muse 原始数据字段: {list(data.keys())}")

            try:
                # Pydantic v2 兼容：model_fields.keys() 直接获取字段名
                field_names = set(ByteMuseMovie.model_fields.keys())
                filtered_data = {k: v for k, v in data.items() if k in field_names}
                logger.debug(f"Byte-Muse 过滤后数据: {filtered_data}")
                return ByteMuseMovie.model_validate(filtered_data)
            except Exception as e2:
                if hasattr(e2, 'errors'):
                    errors_list = e2.errors()
                    error_details = "; ".join([f"{err.get('loc', ['unknown'])[0]}: {err.get('msg', '')}" for err in errors_list])
                    logger.warning(f"Byte-Muse 字段提取也失败详情: {error_details}")
                else:
                    logger.warning(f"Byte-Muse 字段提取也失败: {str(e2)}")
                return None

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

            # 记录原始响应数据用于调试
            logger.debug(f"Byte-Muse API 原始响应: {data}")

            # 解析响应 - 使用更灵活的方式
            try:
                result = ByteMuseSearchResponse.model_validate(data)
                if result.success and result.data:
                    return result.data.codes
            except Exception as e:
                # 如果标准格式解析失败，尝试直接解析列表
                logger.warning(f"Byte-Muse 标准格式解析失败: {str(e)}，尝试备用格式")

                # 尝试直接列表格式
                if isinstance(data, list):
                    movies = []
                    for item in data:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

                # 尝试嵌套格式 {codes: [...]}
                elif isinstance(data, dict) and "codes" in data:
                    codes = data["codes"]
                    if isinstance(codes, list):
                        movies = []
                        for item in codes:
                            movie = self._safe_validate_movie(item)
                            if movie:
                                movies.append(movie)
                        return movies if movies else None

                # 尝试嵌套格式 {data: {codes: [...]}} 或 {data: [...]}
                elif isinstance(data, dict) and "data" in data:
                    data_obj = data["data"]
                    if isinstance(data_obj, dict) and "codes" in data_obj:
                        codes = data_obj["codes"]
                        if isinstance(codes, list):
                            movies = []
                            for item in codes:
                                movie = self._safe_validate_movie(item)
                                if movie:
                                    movies.append(movie)
                            return movies if movies else None
                    elif isinstance(data_obj, list):
                        movies = []
                        for item in data_obj:
                            movie = self._safe_validate_movie(item)
                            if movie:
                                movies.append(movie)
                        return movies if movies else None

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

            # 记录原始响应数据用于调试
            logger.debug(f"Byte-Muse API 异步原始响应: {data}")

            # 解析响应 - 使用更灵活的方式
            try:
                result = ByteMuseSearchResponse.model_validate(data)
                if result.success and result.data:
                    return result.data.codes
            except Exception as e:
                # 如果标准格式解析失败，尝试直接解析列表
                logger.warning(f"Byte-Muse 异步标准格式解析失败: {str(e)}，尝试备用格式")

                # 尝试直接列表格式
                if isinstance(data, list):
                    movies = []
                    for item in data:
                        movie = self._safe_validate_movie(item)
                        if movie:
                            movies.append(movie)
                    return movies if movies else None

                # 尝试嵌套格式 {codes: [...]}
                elif isinstance(data, dict) and "codes" in data:
                    codes = data["codes"]
                    if isinstance(codes, list):
                        movies = []
                        for item in codes:
                            movie = self._safe_validate_movie(item)
                            if movie:
                                movies.append(movie)
                        return movies if movies else None

                # 尝试嵌套格式 {data: {codes: [...]}} 或 {data: [...]}
                elif isinstance(data, dict) and "data" in data:
                    data_obj = data["data"]
                    if isinstance(data_obj, dict) and "codes" in data_obj:
                        codes = data_obj["codes"]
                        if isinstance(codes, list):
                            movies = []
                            for item in codes:
                                movie = self._safe_validate_movie(item)
                                if movie:
                                    movies.append(movie)
                            return movies if movies else None
                    elif isinstance(data_obj, list):
                        movies = []
                        for item in data_obj:
                            movie = self._safe_validate_movie(item)
                            if movie:
                                movies.append(movie)
                        return movies if movies else None

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
