import re
from typing import Optional, List
from urllib.parse import quote

from app.log import logger
from app.utils.http import RequestUtils, AsyncRequestUtils
from app.plugins.metatubesource.schema import MetatubeMovie, MetatubeSearchResponse


class MetatubeHelper:
    """Metatube API 辅助类"""

    def __init__(self, api_url: str = None, proxies: dict = None):
        """
        初始化 Metatube 辅助类
        :param api_url: Metatube API 地址
        :param proxies: 代理设置
        """
        self.api_url = api_url or "http://op.mubey.top:3244"
        self.proxies = proxies

    def search_movie(self, query: str) -> Optional[List[MetatubeMovie]]:
        """
        搜索电影
        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = f"{self.api_url}/v1/movies/search"
            params = {
                "q": query,
                "provider": "",
                "fallback": "True"
            }

            logger.info(f"正在调用 Metatube API 搜索: {query}")

            req = RequestUtils(
                accept_type="application/json",
                proxies=self.proxies
            )

            result = req.get_res(
                url=url,
                params=params
            )

            if result and result.status_code == 200:
                try:
                    data = result.json()
                    response = MetatubeSearchResponse(**data)
                    if response.data:
                        logger.info(f"Metatube API 返回 {len(response.data)} 条结果")
                        return response.data
                    else:
                        logger.info(f"Metatube API 未找到结果: {query}")
                        return []
                except Exception as e:
                    logger.error(f"解析 Metatube API 响应失败: {str(e)}")
                    return None
            else:
                logger.error(f"Metatube API 请求失败: {result.status_code if result else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"调用 Metatube API 异常: {str(e)}")
            return None

    async def async_search_movie(self, query: str) -> Optional[List[MetatubeMovie]]:
        """
        异步搜索电影
        :param query: 搜索关键词(番号)
        :return: 搜索结果列表
        """
        if not query:
            return None

        try:
            url = f"{self.api_url}/v1/movies/search"
            params = {
                "q": query,
                "provider": "",
                "fallback": "True"
            }

            logger.info(f"正在异步调用 Metatube API 搜索: {query}")

            req = AsyncRequestUtils(
                accept_type="application/json",
                proxies=self.proxies
            )

            result = await req.get_res(
                url=url,
                params=params
            )

            if result and result.status_code == 200:
                try:
                    data = result.json()
                    response = MetatubeSearchResponse(**data)
                    if response.data:
                        logger.info(f"Metatube API 返回 {len(response.data)} 条结果")
                        return response.data
                    else:
                        logger.info(f"Metatube API 未找到结果: {query}")
                        return []
                except Exception as e:
                    logger.error(f"解析 Metatube API 响应失败: {str(e)}")
                    return None
            else:
                logger.error(f"Metatube API 请求失败: {result.status_code if result else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"调用 Metatube API 异常: {str(e)}")
            return None

    @staticmethod
    def extract_number(text: str) -> Optional[str]:
        """
        从文本中提取番号
        :param text: 输入文本
        :return: 提取的番号
        """
        if not text:
            return None

        # 常见番号格式: XXX-123, XXX123, n1234 等
        patterns = [
            r'[A-Z0-9]{2,5}-\d{3,5}',  # XXX-123 格式
            r'[A-Z0-9]{2,5}\d{3,5}',   # XXX123 格式
            r'n\d{4}',                  # n1234 格式
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return None

    @staticmethod
    def normalize_number(number: str) -> str:
        """
        标准化番号格式
        :param number: 原始番号
        :return: 标准化后的番号
        """
        if not number:
            return number

        # 统一转大写
        number = number.upper()

        # 移除特殊字符
        number = re.sub(r'[^\w-]', '', number)

        return number
