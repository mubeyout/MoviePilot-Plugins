"""
ByteMuse API 客户端
基于 ByteMuse 数据源
"""
from typing import Optional, List, Dict, Any
import threading
import time
import datetime

from app.log import logger
from app.utils.http import RequestUtils


class ByteMuseApiClient:
    """ByteMuse API 客户端"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "DNT": "1",
        "Content-Type": "application/json",
    }

    # 探索类型映射
    DISCOVER_TYPES = {
        "actors": "actors",
        "new_releases": "new",
        "recommendations": "recommend",
        "rankings_daily": "daily",
        "rankings_weekly": "weekly",
        "rankings_monthly": "monthly",
        "rankings_javlibrary": "javlibrary",
        "studio_s1": "s1-0",
        "studio_ideapocket": "ip-0",
        "studio_moodyz": "moodyz-0",
        "studio_premium": "premium-0",
        "studio_das": "das-0",
        "studio_madonna": "madonna-0",
        "studio_honnaka": "honnaka-0",
        "studio_attackers": "attackers-0",
        "studio_wanz": "wanz-0",
    }

    def __init__(self, base_url: str = "",
                 username: str = "", password: str = "",
                 api_token: str = "", timeout: int = 30):
        """
        初始化 ByteMuse API 客户端

        :param base_url: API 基础地址
        :param username: 用户名
        :param password: 密码
        :param api_token: API Token (备用,推荐使用 username/password)
        :param timeout: 请求超时时间(秒)
        """
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._api_token = api_token
        self._timeout = timeout

        # JWT Token 相关
        self._jwt_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._token_lock = threading.Lock()

        logger.debug(f"ByteMuse API 初始化: base_url={self._base_url}, has_credentials={bool(username and password)}")

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

    # ==================== 探索接口 ====================

    def get_discover_data(self, discover_type: str = "new_releases",
                         page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        获取探索数据

        :param discover_type: 探索类型 (actors/new_releases/recommendations/rankings_*/studio_*)
        :param page: 页码
        :param page_size: 每页数量
        :return: 数据列表
        """
        # 确保已认证
        if not self._ensure_authenticated():
            logger.warning("ByteMuse 获取探索数据失败: 认证失败")
            return None

        try:
            # 根据类型调用不同的接口
            if discover_type == "actors":
                return self._get_actors(page, page_size)
            elif discover_type == "new_releases":
                return self._get_release_today(page, page_size)
            elif discover_type == "recommendations":
                return self._get_recommend(page, page_size)
            elif discover_type.startswith("rankings_"):
                rank_type = discover_type.replace("rankings_", "")
                result = self._get_ranks(rank_type, page_size)
                if not result:
                    logger.info(f"ByteMuse {rank_type}榜无数据，回退到 release_today")
                    result = self._get_release_today(page, page_size)
                return result
            elif discover_type.startswith("studio_"):
                studio = discover_type.replace("studio_", "")
                result = self._get_studio_ranks(studio, page_size)
                if not result:
                    logger.info(f"ByteMuse {studio}厂牌无数据，回退到 release_today")
                    result = self._get_release_today(page, page_size)
                return result
            else:
                logger.warning(f"不支持的探索类型: {discover_type}")
                return None

        except Exception as e:
            logger.error(f"ByteMuse 获取探索数据异常: {str(e)}")
            return None

    def _get_actors(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """获取演员列表"""
        try:
            url = self._build_url("/api/v1/actors")
            params = {"page": page, "page_size": page_size}

            response = RequestUtils(
                timeout=self._timeout,
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
            logger.error(f"ByteMuse 获取演员列表异常: {str(e)}")
            return None

    def _get_release_today(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """获取今日上新"""
        try:
            url = self._build_url("/api/v1/codes/release_today")
            data = {"page": page, "page_size": page_size}

            response = RequestUtils(
                timeout=self._timeout,
                headers=self._get_headers()
            ).post_res(url, json=data)

            if response is None or response.status_code != 200:
                return None

            resp_data = response.json()
            if isinstance(resp_data, list):
                return resp_data
            elif isinstance(resp_data, dict) and "data" in resp_data:
                return resp_data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取今日上新异常: {str(e)}")
            return None

    def _get_recommend(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict[str, Any]]]:
        """获取推荐"""
        try:
            url = self._build_url("/api/v1/codes/recommend")
            data = {"category": "all", "page": page, "page_size": page_size}

            response = RequestUtils(
                timeout=self._timeout,
                headers=self._get_headers()
            ).post_res(url, json=data)

            if response is None or response.status_code != 200:
                return None

            resp_data = response.json()
            if isinstance(resp_data, list):
                return resp_data
            elif isinstance(resp_data, dict) and "data" in resp_data:
                return resp_data["data"]
            return None

        except Exception as e:
            logger.error(f"ByteMuse 获取推荐异常: {str(e)}")
            return None

    def _get_ranks(self, rank_type: str = "daily", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """获取榜单（基于 release_today 多页数据 + 时间范围过滤）"""
        try:
            # ByteMuse /api/v1/ranks 返回空数据，改用 release_today 模拟榜单
            rank_days = {
                "daily": 1,
                "weekly": 7,
                "monthly": 30,
                "javlibrary": 30,
            }.get(rank_type, 1)
            cutoff = datetime.date.today() - datetime.timedelta(days=rank_days)

            # 拉取多页数据以覆盖时间范围
            all_items = []
            for page in range(1, 11):
                page_data = self._get_release_today(page, 100)
                if not page_data:
                    break
                all_items.extend(page_data)
                if len(page_data) < 100:
                    break

            # 按 release_date 过滤
            filtered = []
            for item in all_items:
                date_str = item.get("release_date", "") or ""
                if date_str:
                    try:
                        item_date = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                        if item_date >= cutoff:
                            filtered.append(item)
                    except (ValueError, TypeError):
                        pass

            logger.info(f"ByteMuse {rank_type}榜: 拉取 {len(all_items)} 条，过滤后 {len(filtered)} 条（{rank_days}天内）")
            return filtered[:limit] if filtered else None

        except Exception as e:
            logger.error(f"ByteMuse 获取榜单异常: {str(e)}")
            return None

    def _get_studio_ranks(self, studio: str = "s1", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """获取厂牌榜单（基于 release_today 多页数据 + 厂牌过滤）"""
        try:
            # ByteMuse /api/v1/ranks 对厂牌也返回空，改用 release_today 过滤
            # 解析厂牌名（如 s1-0 → S1, moodyz-0 → Moodyz）
            studio_key = studio.lower().replace(" ", "")
            # 尝试从 DISCOVER_TYPES 获取，或直接用 studio 参数
            type_param = self.DISCOVER_TYPES.get(f"studio_{studio_key}", f"{studio_key}-0")
            # 从 type_param 提取厂牌关键词（去掉 -0 后缀）
            studio_keyword = type_param.split("-")[0].upper() if "-" in type_param else type_param.upper()

            # 拉取多页数据
            all_items = []
            for page in range(1, 11):
                page_data = self._get_release_today(page, 100)
                if not page_data:
                    break
                all_items.extend(page_data)
                if len(page_data) < 100:
                    break

            # 按厂牌/厂牌关键字匹配过滤
            filtered = []
            for item in all_items:
                item_code = (item.get("code", "") or "").upper()
                item_studio = (item.get("studio", "") or "").upper()
                # 匹配番号前缀（如 SSIS 开头属于 S1）或 studio 字段
                if item_code.startswith(studio_keyword) or studio_keyword in item_studio:
                    filtered.append(item)

            logger.info(f"ByteMuse {studio}厂牌: 拉取 {len(all_items)} 条，匹配 {len(filtered)} 条（关键词: {studio_keyword}）")
            return filtered[:limit] if filtered else None

        except Exception as e:
            logger.error(f"ByteMuse 获取厂牌榜单异常: {str(e)}")
            return None

    def get_supported_types(self) -> List[str]:
        """获取所有支持的探索类型"""
        return list(self.DISCOVER_TYPES.keys())

    def search_by_code(self, query: str) -> Optional[Dict[str, Any]]:
        """
        按番号搜索（用于详情查询）

        :param query: 番号
        :return: 搜索结果字典
        """
        # 确保已认证
        if not self._ensure_authenticated():
            logger.warning("ByteMuse search_by_code 失败: 认证失败")
            return None

        try:
            url = self._build_url("/api/v1/codes/search")
            params = {"query": query}

            logger.debug(f"ByteMuse 搜索番号: {query}, URL: {url}")

            response = RequestUtils(
                timeout=self._timeout,
                headers=self._get_headers()
            ).get_res(url, params=params)

            if response is None:
                logger.warning(f"ByteMuse search_by_code 请求失败: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"ByteMuse search_by_code 返回状态码: {response.status_code}")
                return None

            data = response.json()
            if not data:
                return None

            # 兼容新旧 API 响应格式
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                data = data["data"]

            logger.debug(f"ByteMuse search_by_code 搜索成功: 找到 {len(data.get('codes', []))} 条结果")
            return data

        except Exception as e:
            logger.error(f"ByteMuse search_by_code 异常: {str(e)}")
            return None
