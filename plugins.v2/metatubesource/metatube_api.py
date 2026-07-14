# Category: API客户端
"""
Metatube API 客户端
"""
import re
import os
from typing import Optional, List, Dict
from urllib.parse import urljoin, quote

import time
import asyncio
from functools import wraps

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils

from .schema import MetatubeMovie, MetatubeSearchResponse, MetatubeMovieDetail, MetatubeDetailResponse


def _retry_sync(max_retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt >= max_retries - 1:
                        raise
                    logger.warning(f"{func.__name__} 失败，{current_delay:.1f}s后重试 ({attempt+1}/{max_retries}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


def _retry_async(max_retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt >= max_retries - 1:
                        raise
                    logger.warning(f"{func.__name__} 异步失败，{current_delay:.1f}s后重试 ({attempt+1}/{max_retries}): {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


class MetatubeApiClient:
    """Metatube API 客户端"""

    # 浏览器 User-Agent，避免被服务端拒绝
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 默认 API 地址（支持环境变量覆盖）
    DEFAULT_API_URL = os.getenv(
        "METATUBE_API_URL",
        "http://127.0.0.1:8080"
    )

    # 番号正则表达式列表（按优先级排序，更具体的规则在前）
    NUMBER_PATTERNS = [
        # ===== FC2 系列（最高优先级，防止被通用规则误匹配）=====
        # FC2格式: FC2-PPV-1234567, FC2-1234567, FC2PPV-1234567
        r'(FC2)[-_]?(PPV)?[-_]?(\d{5,7})',

        # ===== HEYZO 系列 =====
        # HEYZO格式: HEYZO-1234
        r'(HEYZO)[-_]?(\d{4})',

        # ===== Tokyo Hot 系列 =====
        # Tokyo Hot: n1234, k1234, k12345, K1234, KD1234
        r'([nNK]|K|KD)[-_]?(\d{4,5})',

        # ===== 主流标准格式 =====
        # 标准格式: ABC-123, ABC123, ABC-0123
        r'([A-Z]{2,10})[-_]?(\d{2,5})',

        # ===== 素人/单体系列 =====
        # 10musume: 10musume-1234, 10mu-123
        r'(10MUSUME|10MU)[-_]?(\d{2,4})',
        # PacoPaco: paco-123, pacopaco-1234
        r'(PACO|PACOPACO)[-_]?(\d{3,5})',
        # XXX-AV: xxx-av-12345, xxxav-12345
        r'(XXX[-_]?AV|AV)[-_]?(\d{5})',

        # ===== 网站系列 =====
        # Caribbean系列: carib-123456-123, caribpr-123456-123
        r'(CARIB|CARIBPR|CARIBBEANCOM)[-_]?(\d{6})[-_]?(\d{3})',
        # 1Pondo: 1pondo-123456_123, 1p-123456_123
        r'(\d{6})[_-](\d{3})',
        # Sky High: s2m-123, sky-123, sky-252
        r'(S2M|SKY|SKYHIGH)[-_]?(\d{3,4})',
        # Red Hot: red-123
        r'(RED|REDHOT)[-_]?(\d{3})',

        # ===== 数字编号系列 =====
        # H系列: H0930-123, H4610-123
        r'(H\d{4})[-_]?(\d{3})',
        # C系列: C0930-123
        r'(C\d{4})[-_]?(\d{3})',
        # 纯数字系列: 123456-123, 123456_123
        r'(\d{6})[-_](\d{3})',

        # ===== 特殊厂商 =====
        # Kin8tengoku: kin8-123, eng-123
        r'(KIN8|TENGOKU|ENG)[-_]?(\d{3,5})',
        # Gold系列: gold-123
        r'(GOLD)[-_]?(\d{3,4})',
        # CWP: cwp-123
        r'(CWP)[-_]?(\d{3,5})',
        # Prestige系列: abp-123, abw-123
        r'(ABP|ABW|BKSP)[-_]?(\d{3,4})',
        # S1系列: ssis-123, stars-123
        r'(SSIS|STARS|SSND|SNIS)[-_]?(\d{3,4})',
        # IdeaPocket: ipx-123, ipzz-123
        r'(IPX|IPZ|IPZZ)[-_]?(\d{3,4})',
        # Moodyz: mide-123, midv-123, mipx-123
        r'(MIDE|MIDV|MIPX|MIAE|MIRD)[-_]?(\d{3,4})',
        # E-BODY: ebod-123
        r'(EBOD|EBODY)[-_]?(\d{3,4})',
        # WanZ: wanz-123
        r'(WANZ|WAAA)[-_]?(\d{3,4})',

        # ===== VR系列 =====
        # VR: vr-123, 3dvr-123
        r'(VR|3DVR|VRVR)[-_]?(\d{3,5})',

        # ===== 欧美系列 =====
        # RealityKings: rk-12345
        r'(RK)[-_]?(\d{4,5})',
        # XEmpire: xempire-12345
        r'(XEMPIRE|DARKX|EROTICAX|HARDX|LESBIANX)[-_]?(\d{3,5})',
        # 21Sextury: 21naturals-12345, 21footart-12345
        r'(21SEXTURY|21NATURALS|21FOOTART|21EROTICA)[-_]?(\d{3,5})',

        # ===== 中文系列 =====
        # MDTV/MDX: mdtv-1234, mdx-1234
        r'(MDTV|MDX|MD|JD)[-_]?(\d{3,4})',

        # ===== 复合格式(后置匹配) =====
        # 包含字母数字组合的三段式: ABC-123-DEF, ABC123-DEF
        r'([A-Z]{2,6})[-_]?(\d{3,5})[-_]?([A-Z]{0,4})',
        # 特殊数字格式: 062123-123
        r'(\d{5,6})[-_](\d{3})',
    ]

    def __init__(self, base_url: str = None,
                 timeout: int = 10, proxies: Dict[str, str] = None):
        """
        初始化 Metatube API 客户端

        :param base_url: API 基础地址（为空则使用环境变量或默认值）
        :param timeout: 请求超时时间(秒)
        :param proxies: 代理配置
        """
        # 优先使用传入的 URL，否则使用环境变量，最后使用默认值
        self._base_url = (base_url or self.DEFAULT_API_URL).rstrip('/')
        self._timeout = timeout
        self._proxies = proxies

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        """设置 API 基础地址"""
        self._base_url = value.rstrip('/') if value else self.DEFAULT_API_URL

    @staticmethod
    def extract_number(filename: str) -> Optional[str]:
        """
        从文件名中提取番号

        :param filename: 文件名
        :return: 提取的番号，未找到返回None
        """
        if not filename:
            return None

        # 清理文件名（先清理再大写，避免 .com 等小写匹配失效）
        name = filename.strip()

        # 移除常见的无关前缀和后缀
        name = re.sub(r'\[.*?\]', ' ', name)
        name = re.sub(r'\(.*?\)', ' ', name)
        name = re.sub(r'\d{3,}\.com[@＠]', '', name)
        name = re.sub(r'[a-zA-Z0-9_-]+\.[a-z]+[@＠]', '', name)
        name = re.sub(r'[@＠].*', '', name)

        # 清理完成后再大写化
        name = name.upper()

        # 尝试匹配各种番号格式
        for pattern in MetatubeApiClient.NUMBER_PATTERNS:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # 标准两段式: ABC-123
                    return f"{groups[0]}-{groups[1]}".upper()
                elif len(groups) == 3:
                    # 三段式格式判断
                    if groups[0] == 'FC2':
                        # FC2格式: FC2-PPV-1234567 (中间可选)
                        if groups[1]:  # PPV存在
                            return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                        else:  # PPV不存在
                            return f"{groups[0]}-{groups[2]}".upper()
                    elif groups[0] in ['CARIB', 'CARIBPR', 'CARIBBEANCOM']:
                        # Caribbean格式: CARIB-123456-123
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                    elif groups[1] is None or groups[1] == '':
                        # 中间组为空，实际是两段式
                        return f"{groups[0]}-{groups[2]}".upper()
                    else:
                        # 通用三段式: ABC-123-DEF
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()

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

    @_retry_sync(max_retries=3, delay=1.0, backoff=2.0)
    def search(self, keyword: str, fallback: bool = True) -> Optional[List[MetatubeMovie]]:
        """
        搜索媒体（带自动重试）

        :param keyword: 搜索关键词(番号)
        :param fallback: 是否启用回退搜索
        :return: 搜索结果列表
        """
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

    @_retry_async(max_retries=3, delay=1.0, backoff=2.0)
    async def async_search(self, keyword: str, fallback: bool = True) -> Optional[List[MetatubeMovie]]:
        """
        异步搜索媒体（带自动重试）

        :param keyword: 搜索关键词(番号)
        :param fallback: 是否启用回退搜索
        :return: 搜索结果列表
        """
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

    @_retry_sync(max_retries=3, delay=1.0, backoff=2.0)
    def get_detail(self, provider: str, movie_id: str) -> Optional[MetatubeMovieDetail]:
        """
        获取电影详情（带自动重试）

        :param provider: 数据来源
        :param movie_id: 电影ID
        :return: 电影详情
        """
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

    @_retry_async(max_retries=3, delay=1.0, backoff=2.0)
    async def async_get_detail(self, provider: str, movie_id: str) -> Optional[MetatubeMovieDetail]:
        """
        异步获取电影详情（带自动重试）

        :param provider: 数据来源
        :param movie_id: 电影ID
        :return: 电影详情
        """
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
