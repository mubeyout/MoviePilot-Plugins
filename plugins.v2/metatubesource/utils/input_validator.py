# Category: 工具函数
"""
输入验证和清理工具
"""
import re
from typing import Optional, List
from urllib.parse import quote


class InputSanitizer:
    """输入清理和验证器"""

    # 危险字符模式
    DANGEROUS_CHARS_PATTERN = re.compile(r'[<>\"\'\\]')

    # 番号格式模式（用于验证）
    NUMBER_PATTERN = re.compile(
        r'^[A-Z]{2,10}-\d{2,5}(-[A-Z]{0,4})?$|'
        r'^FC2(-PPV)?-\d{5,7}$|'
        r'^HEYZO-\d{4}$|'
        r'^\d{6}-\d{3}$',
        re.IGNORECASE
    )

    @staticmethod
    def sanitize_string(value: str, max_length: int = 200) -> str:
        """
        清理字符串输入

        Args:
            value: 原始字符串
            max_length: 最大长度限制

        Returns:
            str: 清理后的字符串
        """
        if not value:
            return ""

        # 类型转换
        value = str(value)

        # 长度限制
        value = value[:max_length]

        # 移除危险字符
        value = InputSanitizer.DANGEROUS_CHARS_PATTERN.sub('', value)

        # 移除控制字符
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

        # 去除首尾空白
        value = value.strip()

        return value

    @staticmethod
    def sanitize_number(number: str) -> str:
        """
        清理番号输入

        Args:
            number: 原始番号

        Returns:
            str: 清理后的番号
        """
        if not number:
            return ""

        # 基础清理
        number = InputSanitizer.sanitize_string(number, max_length=50)

        # 转大写
        number = number.upper()

        # 统一分隔符
        number = number.replace('＿', '_').replace('－', '-')

        # 移除多余空格
        number = re.sub(r'\s+', '', number)

        return number

    @staticmethod
    def sanitize_url_param(param: str) -> str:
        """
        清理 URL 参数（用于 URL 编码前）

        Args:
            param: 原始参数

        Returns:
            str: 清理后的参数
        """
        if not param:
            return ""

        # 基础清理
        param = InputSanitizer.sanitize_string(param, max_length=100)

        # URL 编码
        try:
            return quote(param)
        except Exception:
            # 编码失败，返回清理后的字符串
            return param

    @staticmethod
    def validate_number(number: str) -> tuple[bool, Optional[str]]:
        """
        验证番号格式

        Args:
            number: 待验证的番号

        Returns:
            tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        if not number:
            return False, "番号不能为空"

        # 清理后验证
        clean_number = InputSanitizer.sanitize_number(number)

        if not clean_number:
            return False, "番号格式无效"

        # 检查长度
        if len(clean_number) < 3:
            return False, "番号过短"

        if len(clean_number) > 50:
            return False, "番号过长"

        # 检查是否包含有效字符（字母+数字+分隔符）
        if not re.match(r'^[A-Z0-9\-_]+$', clean_number, re.IGNORECASE):
            return False, "番号包含非法字符"

        return True, None

    @staticmethod
    def validate_url(url: str) -> tuple[bool, Optional[str]]:
        """
        验证 URL 格式

        Args:
            url: 待验证的 URL

        Returns:
            tuple[bool, Optional[str]]: (是否有效, 错误消息)
        """
        if not url:
            return False, "URL 不能为空"

        # 基础清理
        url = url.strip()

        # 检查协议
        if not url.startswith(('http://', 'https://')):
            return False, "URL 必须以 http:// 或 https:// 开头"

        # 检查长度
        if len(url) > 2000:
            return False, "URL 过长"

        # 检查格式
        url_pattern = re.compile(
            r'^https?://'  # 协议
            r'[a-zA-Z0-9\-\.]+'  # 主机名
            r'(?::\d+)?'  # 端口
            r'(?:/.*)?$',  # 路径
            re.IGNORECASE
        )

        if not url_pattern.match(url):
            return False, "URL 格式无效"

        return True, None

    @staticmethod
    def sanitize_keywords(keywords: List[str]) -> List[str]:
        """
        批量清理关键字列表

        Args:
            keywords: 原始关键字列表

        Returns:
            List[str]: 清理后的关键字列表
        """
        if not keywords:
            return []

        sanitized = []
        for kw in keywords:
            clean_kw = InputSanitizer.sanitize_string(kw, max_length=50)
            if clean_kw and len(clean_kw) >= 2:  # 过滤单字符
                sanitized.append(clean_kw)

        return list(set(sanitized))  # 去重

    @staticmethod
    def is_safe_input(value: str) -> bool:
        """
        检查输入是否安全（不包含危险字符）

        Args:
            value: 待检查的输入

        Returns:
            bool: True 表示安全
        """
        if not value:
            return True

        # 检查危险字符
        if InputSanitizer.DANGEROUS_CHARS_PATTERN.search(value):
            return False

        # 检查控制字符（排除换行、制表符）
        for char in value:
            if ord(char) < 32 and char not in '\n\r\t':
                return False

        return True
