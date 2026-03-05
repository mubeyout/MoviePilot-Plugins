"""
Jackett API 封装
"""
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

import requests
from requests.exceptions import RequestException
from app.log import logger


class JackettAPI:
    """Jackett API 封装类"""

    def __init__(self, url: str, api_key: str, timeout: int = 30):
        """
        初始化 Jackett API

        :param url: Jackett 服务地址，如 http://localhost:9117
        :param api_key: Jackett API Key
        :param timeout: 请求超时时间（秒）
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, indexer: str = "all", category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索种子

        :param query: 搜索关键词
        :param indexer: 索引器ID，默认 "all" 搜索所有
        :param category: 分类ID（可选）
        :return: 种子列表
        """
        endpoint = f"/api/v2.0/indexers/{indexer}/results/torznab/api"
        params = {
            "apikey": self.api_key,
            "q": query
        }
        if category:
            params["cat"] = category

        response = self._request("GET", endpoint, params=params)
        if not response:
            return []

        return self._parse_search_results(response)

    def get_indexers(self) -> List[Dict[str, str]]:
        """
        获取已配置的索引器列表

        :return: 索引器列表
        """
        # Jackett 返回 JSON 格式
        endpoint = "/api/v2.0/indexers/all/results"
        params = {
            "apikey": self.api_key,
            "t": "indexers",
            "configured": "true"
        }

        logger.info(f"请求 Jackett API: {self.url}{endpoint}")
        logger.info(f"参数: {params}")

        response = self._request("GET", endpoint, params=params)
        if not response:
            logger.warning("未收到响应")
            return []

        logger.info(f"收到响应，长度: {len(response)}")
        logger.info(f"响应前100字符: {response[:100]}")

        return self._parse_indexers(response)

    def test_connection(self) -> bool:
        """
        测试连接

        :return: 连接是否成功
        """
        try:
            # 尝试获取索引器列表
            logger.info("测试连接: 尝试获取索引器列表...")
            indexers = self.get_indexers()
            logger.info(f"获取到 {len(indexers)} 个索引器")
            return len(indexers) > 0
        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return False

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[str]:
        """
        发起 HTTP 请求

        :param method: 请求方法
        :param endpoint: API 端点
        :param params: 请求参数
        :param headers: 请求头
        :return: 响应文本
        """
        url = f"{self.url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            else:
                response = requests.post(url, data=params, headers=headers, timeout=self.timeout)

            response.raise_for_status()
            return response.text

        except RequestException as e:
            raise Exception(f"请求 Jackett API 失败: {str(e)}")

    def _parse_search_results(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        解析搜索结果 XML

        :param xml_text: XML 文本
        :return: 种子列表
        """
        results = []
        try:
            root = ET.fromstring(xml_text)

            # 查找所有 item
            for item in root.findall('.//item'):
                try:
                    result = {
                        'title': self._get_text(item, 'title'),
                        'link': self._get_text(item, 'link'),
                        'size': self._parse_size(self._get_text(item, 'size')),
                        'seeders': self._get_torznab_attr(item, 'seeders'),
                        'peers': self._get_torznab_attr(item, 'peers'),
                        'grabs': self._get_torznab_attr(item, 'grabs'),
                        'comments': self._get_text(item, 'comments'),
                        'pubDate': self._get_text(item, 'pubDate'),
                        'description': self._get_text(item, 'description'),
                        'indexer': self._get_text(item, 'jackettindexer')
                    }

                    # 跳过没有标题的结果
                    if not result['title']:
                        continue

                    results.append(result)

                except Exception as e:
                    # 跳过解析失败的项
                    continue

        except ET.ParseError as e:
            raise Exception(f"解析 XML 失败: {str(e)}")

        return results

    def _parse_indexers(self, xml_text: str) -> List[Dict[str, str]]:
        """
        解析索引器列表 XML

        :param xml_text: XML 文本
        :return: 索引器列表
        """
        indexers = []
        try:
            root = ET.fromstring(xml_text)
            for indexer in root.findall('.//indexer'):
                indexers.append({
                    'id': indexer.get('id', ''),
                    'name': indexer.get('name', ''),
                    'type': indexer.get('type', ''),
                    'link': indexer.get('link', '')
                })
        except ET.ParseError as e:
            raise Exception(f"解析索引器列表失败: {str(e)}")

        return indexers

    @staticmethod
    def _get_text(element, tag: str) -> str:
        """
        安全获取元素的文本内容

        :param element: XML 元素
        :param tag: 标签名
        :return: 文本内容，如果不存在返回空字符串
        """
        child = element.find(tag)
        return child.text if child is not None and child.text else ''

    @staticmethod
    def _get_torznab_attr(element, name: str) -> int:
        """
        获取 torznab 属性值

        :param element: XML 元素
        :param name: 属性名
        :return: 属性值，如果不存在返回 0
        """
        attr = element.find(f'.//{{http://torznab.com/schemas/2015/feed}}attr[@name="{name}"]')
        if attr is not None:
            value = attr.get('value', '0')
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """
        解析大小字符串为字节数

        :param size_str: 大小字符串，如 "1.5 GB"
        :return: 字节数
        """
        if not size_str:
            return 0

        size_str = size_str.strip().upper()
        try:
            # 已经是纯数字
            if size_str.isdigit():
                return int(size_str)

            # 解析单位
            multipliers = {
                'GB': 1024**3,
                'MB': 1024**2,
                'KB': 1024,
                'B': 1,
                'GIB': 1024**3,
                'MIB': 1024**2,
                'KIB': 1024
            }

            for unit, multiplier in multipliers.items():
                if size_str.endswith(unit):
                    number = size_str[:-len(unit)].strip()
                    try:
                        return int(float(number) * multiplier)
                    except ValueError:
                        return 0

            # 如果没有匹配的单位，尝试直接转换
            return int(float(size_str))

        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _parse_indexers(json_text: str) -> List[Dict[str, str]]:
        """
        解析索引器列表 JSON

        :param json_text: JSON 文本
        :return: 索引器列表
        """
        indexers = []
        try:
            data = json.loads(json_text)
            # Jackett 返回格式: {"Results": [...]}
            if "Results" in data:
                for item in data["Results"]:
                    indexers.append({
                        'id': item.get('TrackerId', ''),
                        'name': item.get('Tracker', ''),
                        'type': item.get('TrackerType', ''),
                        'link': item.get('Tracker', '')
                    })
            logger.info(f"成功解析 {len(indexers)} 个索引器")
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            raise Exception(f"解析索引器列表失败: {str(e)}")

        return indexers
