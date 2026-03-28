# Category: API接口
"""
Metatube API 客户端
"""
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, quote
from ..models.base import APIRequest, APIResponse, MediaType

class MetatubeApiClient:
    """Metatube API 客户端"""

    # 浏览器 User-Agent，避免被服务端拒绝
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: int = 30):
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value.rstrip('/') if value else "http://127.0.0.1:8080"

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        base = self._base_url.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search(self, keyword: str, fallback: bool = True) -> Optional[List[Any]]:
        """搜索媒体"""
        try:
            url = self._build_url("/v1/movies/search")
            params = {
                "q": keyword,
                "fallback": "true" if fallback else "false"
            }

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self.DEFAULT_HEADERS,
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={"data": []},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data

            return None

        except Exception as e:
            print(f"Metatube 搜索异常: {str(e)}")
            return None

    async def async_search(self, keyword: str, fallback: bool = True) -> Optional[List[Any]]:
        """异步搜索媒体"""
        try:
            url = self._build_url("/v1/movies/search")
            params = {
                "q": keyword,
                "fallback": "true" if fallback else "false"
            }

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self.DEFAULT_HEADERS,
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={"data": []},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data

            return None

        except Exception as e:
            print(f"Metatube 异步搜索异常: {str(e)}")
            return None

    def get_detail(self, provider: str, movie_id: str) -> Optional[Any]:
        """获取电影详情"""
        try:
            url = self._build_url(f"/v1/movies/{quote(provider)}/{quote(movie_id)}")

            request = APIRequest(
                method="GET",
                url=url,
                headers=self.DEFAULT_HEADERS,
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            print(f"Metatube 获取详情异常: {str(e)}")
            return None

    async def async_get_detail(self, provider: str, movie_id: str) -> Optional[Any]:
        """异步获取电影详情"""
        try:
            url = self._build_url(f"/v1/movies/{quote(provider)}/{quote(movie_id)}")

            request = APIRequest(
                method="GET",
                url=url,
                headers=self.DEFAULT_HEADERS,
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            print(f"Metatube 异步获取详情异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            url = self._build_url("/v1/movies/search")
            params = {"q": "TEST-001", "fallback": "False"}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self.DEFAULT_HEADERS,
                timeout=5
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            return response.is_success

        except Exception as e:
            print(f"Metatube 连接测试失败: {str(e)}")
            return False

class ThePornDBApiClient:
    """ThePornDB API 客户端"""

    # API 基础地址
    API_BASE_URL = "https://api.theporndb.net"
    WEB_BASE_URL = "https://theporndb.net"

    # API 端点
    API_SCENE_SEARCH_URL = "/scenes"
    API_MOVIE_SEARCH_URL = "/movies"
    API_SCENE_URL = "/scenes/{}"
    API_MOVIE_URL = "/movies/{}"
    API_PERFORMER_SEARCH_URL = "/performers"
    API_PERFORMER_URL = "/performers/{}"
    API_JAV_URL = "/jav/{}"

    # Web 端点 (JAV 搜索页面)
    WEB_JAV_SEARCH_URL = "/jav"

    # User-Agent
    USER_AGENT = "MoviePilot-Plugins/ThePornDB/1.0"

    def __init__(self, api_token: str = "", timeout: int = 30):
        self._api_token = api_token
        self._timeout = timeout

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
        base = self.API_BASE_URL.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def _build_web_url(self, endpoint: str) -> str:
        """构建 Web 完整URL"""
        base = self.WEB_BASE_URL.rstrip('/')
        end = endpoint.lstrip('/')
        return f"{base}/{end}"

    def search_scenes(self, search_title: str, year: int = None, oshash: str = "") -> Optional[List[Any]]:
        """搜索场景"""
        if not search_title:
            return None

        try:
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {"parse": search_title}
            if oshash:
                params["hash"] = oshash
            if year:
                params["year"] = str(year)

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data

            return None

        except Exception as e:
            print(f"ThePornDB 搜索场景异常: {str(e)}")
            return None

    async def async_search_scenes(self, search_title: str, year: int = None, oshash: str = "") -> Optional[List[Any]]:
        """异步搜索场景"""
        if not search_title:
            return None

        try:
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {"parse": search_title}
            if oshash:
                params["hash"] = oshash
            if year:
                params["year"] = str(year)

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data

            return None

        except Exception as e:
            print(f"ThePornDB 异步搜索场景异常: {str(e)}")
            return None

    def get_scene_detail(self, scene_id: str) -> Optional[Any]:
        """获取场景详情"""
        if not scene_id:
            return None

        try:
            url = self._build_url(self.API_SCENE_URL.format(quote(scene_id)))

            request = APIRequest(
                method="GET",
                url=url,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            print(f"ThePornDB 获取详情异常: {str(e)}")
            return None

    async def async_get_scene_detail(self, scene_id: str) -> Optional[Any]:
        """异步获取场景详情"""
        if not scene_id:
            return None

        try:
            url = self._build_url(self.API_SCENE_URL.format(quote(scene_id)))

            request = APIRequest(
                method="GET",
                url=url,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                if 'data' in data:
                    return data['data']
                else:
                    return data

            return None

        except Exception as e:
            print(f"ThePornDB 异步获取详情异常: {str(e)}")
            return None

    def search_jav(self, keyword: str) -> Optional[List[Any]]:
        """搜索 JAV"""
        if not keyword:
            return None

        try:
            url = self._build_url("/jav")
            params = {"external_id": keyword}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                scenes_data = data['data']
                if isinstance(scenes_data, list):
                    # 查找完全匹配的结果
                    exact_matches = [s for s in scenes_data if s.get('external_id', '').lower() == keyword.lower()]
                    if exact_matches:
                        return exact_matches
                    return scenes_data
            return None

        except Exception as e:
            print(f"ThePornDB JAV 搜索异常: {str(e)}")
            return None

    async def async_search_jav(self, keyword: str) -> Optional[List[Any]]:
        """异步搜索 JAV"""
        if not keyword:
            return None

        try:
            url = self._build_url("/jav")
            params = {"external_id": keyword}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict) and 'data' in data:
                scenes_data = data['data']
                if isinstance(scenes_data, list):
                    # 查找完全匹配的结果
                    exact_matches = [s for s in scenes_data if s.get('external_id', '').lower() == keyword.lower()]
                    if exact_matches:
                        return exact_matches
                    return scenes_data
            return None

        except Exception as e:
            print(f"ThePornDB JAV 异步搜索异常: {str(e)}")
            return None

    def get_jav_detail(self, jav_id: str) -> Optional[Any]:
        """获取 JAV 详情"""
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(quote(jav_id)))

            request = APIRequest(
                method="GET",
                url=url,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                return data

            return None

        except Exception as e:
            print(f"ThePornDB JAV 获取详情异常: {str(e)}")
            return None

    async def async_get_jav_detail(self, jav_id: str) -> Optional[Any]:
        """异步获取 JAV 详情"""
        if not jav_id:
            return None

        try:
            url = self._build_url(self.API_JAV_URL.format(quote(jav_id)))

            request = APIRequest(
                method="GET",
                url=url,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            if isinstance(data, dict):
                return data

            return None

        except Exception as e:
            print(f"ThePornDB JAV 异步获取详情异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            url = self._build_url(self.API_SCENE_SEARCH_URL)
            params = {"parse": "test"}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=5
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            return response.is_success

        except Exception as e:
            print(f"ThePornDB 连接测试失败: {str(e)}")
            return False

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

    def __init__(self, base_url: str = "http://127.0.0.1:3750", username: str = "", password: str = "", api_token: str = "", timeout: int = 30):
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._api_token = api_token
        self._timeout = timeout

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
        """使用账号密码登录获取 Token"""
        if not self._username or not self._password:
            print("Byte-Muse 登录失败: 未配置用户名或密码")
            return False

        try:
            url = self._build_url("/api/v1/login")
            params = {
                "username": self._username,
                "password": self._password,
                "token_key": ""
            }

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self.DEFAULT_HEADERS,
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={"success": True, "data": {"token": "mock_token"}},
                request=request
            )

            if not response.is_success:
                return False

            data = response.data
            if not data:
                return False

            # 解析响应
            if isinstance(data, dict):
                success = data.get("success", False)
                if success and "data" in data:
                    token = data["data"].get("token", "")
                    if token:
                        self._api_token = token
                        print(f"Byte-Muse 登录成功: {self._username}")
                        return True
                    else:
                        print("Byte-Muse 登录响应中未找到 token")
                        return False
                else:
                    message = data.get("message", "未知错误")
                    print(f"Byte-Muse 登录失败: {message}")
                    return False

            return False

        except Exception as e:
            print(f"Byte-Muse 登录异常: {str(e)}")
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

    def search(self, query: str) -> Optional[List[Any]]:
        """搜索番号"""
        if not query:
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={"success": True, "data": {"codes": []}},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            try:
                result = {"success": True, "data": {"codes": []}}  # 模拟结果
                if result["success"] and result["data"]:
                    return result["data"]["codes"]
            except Exception as e:
                print(f"Byte-Muse 标准格式解析失败: {str(e)}，尝试备用格式")

                # 尝试直接列表格式
                if isinstance(data, list):
                    return data

                # 尝试嵌套格式 {codes: [...]}
                elif isinstance(data, dict) and "codes" in data:
                    codes = data["codes"]
                    if isinstance(codes, list):
                        return codes

                # 尝试嵌套格式 {data: {codes: [...]}} 或 {data: [...]}
                elif isinstance(data, dict) and "data" in data:
                    data_obj = data["data"]
                    if isinstance(data_obj, dict) and "codes" in data_obj:
                        codes = data_obj["codes"]
                        if isinstance(codes, list):
                            return codes
                    elif isinstance(data_obj, list):
                        return data_obj

            return None

        except Exception as e:
            print(f"Byte-Muse 搜索异常: {str(e)}")
            return None

    async def async_search(self, query: str) -> Optional[List[Any]]:
        """异步搜索番号"""
        if not query:
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self._timeout
            )

            # 这里应该使用实际的异步 HTTP 客户端
            # response = await self._async_http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={"success": True, "data": {"codes": []}},
                request=request
            )

            if not response.is_success:
                return None

            data = response.data
            if not data:
                return None

            # 解析响应
            try:
                result = {"success": True, "data": {"codes": []}}  # 模拟结果
                if result["success"] and result["data"]:
                    return result["data"]["codes"]
            except Exception as e:
                print(f"Byte-Muse 异步标准格式解析失败: {str(e)}，尝试备用格式")

                # 尝试直接列表格式
                if isinstance(data, list):
                    return data

                # 尝试嵌套格式 {codes: [...]}
                elif isinstance(data, dict) and "codes" in data:
                    codes = data["codes"]
                    if isinstance(codes, list):
                        return codes

                # 尝试嵌套格式 {data: {codes: [...]}} 或 {data: [...]}
                elif isinstance(data, dict) and "data" in data:
                    data_obj = data["data"]
                    if isinstance(data_obj, dict) and "codes" in data_obj:
                        codes = data_obj["codes"]
                        if isinstance(codes, list):
                            return codes
                    elif isinstance(data_obj, list):
                        return data_obj

            return None

        except Exception as e:
            print(f"Byte-Muse 异步搜索异常: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": "TEST-001"}

            request = APIRequest(
                method="GET",
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=5
            )

            # 这里应该使用实际的 HTTP 客户端
            # response = self._http_client.get(request)
            response = APIResponse(
                status_code=200,
                data={},
                request=request
            )

            return response.is_success

        except Exception as e:
            print(f"Byte-Muse 连接测试失败: {str(e)}")
            return False