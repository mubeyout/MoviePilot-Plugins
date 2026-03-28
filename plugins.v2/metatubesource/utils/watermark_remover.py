# Category: 工具函数
"""
增强的网站水印移除器
支持多种水印模式和智能识别
"""
import re
from typing import Optional, Tuple, List


class EnhancedWatermarkRemover:
    """增强的网站水印移除器"""

    # 已知成人内容网站域名（持续更新）
    ADULT_DOMAINS = [
        'hhd800', 'javhd', 'javlibrary', 'javlib', 'javlib',
        'fanza', 'fanza', 'dmm', 'dmm', 'fc2', 'fc2club',
        'caribbean', 'carib', 'heyzo', 'tokyohot', 'skyhigh',
        '1pondo', '10musume', 'pacopacomama', 'javbus',
        'javmost', 'avgle', 'javgg', 'javmex', 'javarchive',
        'jav365', 'javhd', 'avsock', 'avmoo', 'avwiki'
    ]

    # 网站编号模式（这些不是作品番号，需要排除）
    SITE_ID_PATTERNS = [
        r'^H\d{4}(-\d{3})?$',      # H1234 或 H1234-567（网站内部编号）
        r'^C\d{4}(-\d{3})?$',      # C1234（网站内部编号）
        r'^L\d{4}(-\d{3})?$',      # L1234（网站内部编号）
        r'^S\d{4}(-\d{3})?$',      # S1234（网站内部编号）
        r'^\d{6}[-_]\d{3}$',       # 123456-123（纯数字，可能是Caribbean）
    ]

    # 清理模式（按优先级排序）
    CLEANUP_PATTERNS = [
        # 模式1: @ 符号分隔（最高优先级，最常见）
        {
            'pattern': r'^.*?[@＠]',
            'name': 'at_sign',
            'description': '@符号分隔的水印'
        },
        # 模式2: [网站域名] 方括号
        {
            'pattern': r'^\[(' + '|'.join(re.escape(d) for d in ADULT_DOMAINS) + r')(\.com?)?\]',
            'name': 'bracket_domain',
            'description': '方括号包裹的域名'
        },
        # 模式3: 网站域名 + 下划线/连字符
        {
            'pattern': r'^(' + '|'.join(re.escape(d) for d in ADULT_DOMAINS) + r')[._-]+',
            'name': 'domain_separator',
            'description': '域名加分隔符'
        },
        # 模式4: 域名.xxx格式
        {
            'pattern': r'^[A-Z0-9-]+\.(COM|NET|ORG|TV|CC|IO)[._-]+',
            'name': 'full_domain',
            'description': '完整域名加分隔符'
        },
    ]

    @classmethod
    def clean_filename(cls, filename: str) -> Tuple[str, Optional[str]]:
        """
        清理文件名中的水印

        Args:
            filename: 原始文件名

        Returns:
            Tuple[str, Optional[str]]: (清理后的文件名, 移除的水印)
        """
        if not filename:
            return filename, None

        name = filename.upper().strip()
        watermark = None

        # 按优先级尝试各种清理模式
        for pattern_info in cls.CLEANUP_PATTERNS:
            pattern = pattern_info['pattern']
            if re.search(pattern, name):
                # 提取水印内容
                match = re.search(pattern, name)
                if match:
                    watermark = match.group()

                # 移除水印
                name = re.sub(pattern, '', name)
                break  # 只应用第一个匹配的模式

        # 移除文件扩展名
        name = re.sub(r'\.[A-Z0-9]{2,4}$', '', name)

        # 清理多余的空格和分隔符
        name = name.strip(' ._-')

        return name, watermark

    @classmethod
    def is_site_id(cls, text: str) -> bool:
        """
        判断是否为网站编号（非作品番号）

        Args:
            text: 待判断的文本

        Returns:
            bool: True 表示是网站编号，应该被排除
        """
        if not text:
            return False

        text = text.upper().strip()

        for pattern in cls.SITE_ID_PATTERNS:
            if re.match(pattern, text):
                return True

        return False

    @classmethod
    def is_valid_adult_number(cls, text: str) -> bool:
        """
        判断是否为有效的成人内容番号

        Args:
            text: 待判断的文本

        Returns:
            bool: True 表示是有效的番号
        """
        if not text:
            return False

        text = text.upper().strip()

        # 排除网站编号
        if cls.is_site_id(text):
            return False

        # 检查基本格式
        valid_patterns = [
            # 标准格式: ABC-123
            r'^[A-Z]{2,5}-\d{3,5}$',
            # FC2格式: FC2-PPV-1234567
            r'^FC2(-PPV)?-\d{5,7}$',
            # HEYZO格式: HEYZO-1234
            r'^HEYZO-\d{4}$',
            # Caribbean格式: 123456-123
            r'^\d{6}-\d{3}$',
            # 带后缀: ABC-123-DEF
            r'^[A-Z]{2,5}-\d{3,5}-[A-Z0-9]{1,4}$',
        ]

        for pattern in valid_patterns:
            if re.match(pattern, text):
                return True

        return False

    @classmethod
    def extract_number_with_validation(cls, filename: str) -> Optional[str]:
        """
        提取番号并进行验证

        Args:
            filename: 文件名

        Returns:
            Optional[str]: 验证通过的番号，无效则返回 None
        """
        # 清理水印
        cleaned, watermark = cls.clean_filename(filename)

        # 如果是网站编号，直接返回 None
        if cls.is_site_id(cleaned):
            return None

        # 验证是否为有效番号
        if cls.is_valid_adult_number(cleaned):
            return cleaned

        # 尝试从文件名中提取番号
        # 这里可以集成 NumberExtractor 的逻辑
        return None

    @classmethod
    def add_custom_domain(cls, domain: str):
        """
        添加自定义域名到水印列表

        Args:
            domain: 域名（不需要 .com 等后缀）
        """
        domain_lower = domain.lower()
        if domain_lower not in cls.ADULT_DOMAINS:
            cls.ADULT_DOMAINS.append(domain_lower)
            # 更新清理模式
            cls._update_patterns()

    @classmethod
    def add_custom_site_id_pattern(cls, pattern: str):
        """
        添加自定义网站编号模式

        Args:
            pattern: 正则表达式模式
        """
        if pattern not in cls.SITE_ID_PATTERNS:
            cls.SITE_ID_PATTERNS.append(pattern)

    @classmethod
    def _update_patterns(cls):
        """更新清理模式（当域名列表改变时）"""
        # 重新生成清理模式
        cls.CLEANUP_PATTERNS = [
            {
                'pattern': r'^.*?[@＠]',
                'name': 'at_sign',
                'description': '@符号分隔的水印'
            },
            {
                'pattern': r'^\[(' + '|'.join(re.escape(d) for d in cls.ADULT_DOMAINS) + r')(\.com?)?\]',
                'name': 'bracket_domain',
                'description': '方括号包裹的域名'
            },
            {
                'pattern': r'^(' + '|'.join(re.escape(d) for d in cls.ADULT_DOMAINS) + r')[._-]+',
                'name': 'domain_separator',
                'description': '域名加分隔符'
            },
            {
                'pattern': r'^[A-Z0-9-]+\.(COM|NET|ORG|TV|CC|IO)[._-]+',
                'name': 'full_domain',
                'description': '完整域名加分隔符'
            },
        ]

    @classmethod
    def get_watermark_info(cls, filename: str) -> dict:
        """
        获取水印信息

        Args:
            filename: 文件名

        Returns:
            dict: 包含水印详情的字典
        """
        cleaned, watermark = cls.clean_filename(filename)

        return {
            'original': filename,
            'cleaned': cleaned,
            'watermark': watermark,
            'has_watermark': watermark is not None,
            'is_site_id': cls.is_site_id(cleaned),
            'is_valid_number': cls.is_valid_adult_number(cleaned)
        }


# 便捷函数
def remove_watermark(filename: str) -> str:
    """移除文件名中的水印（便捷函数）"""
    cleaned, _ = EnhancedWatermarkRemover.clean_filename(filename)
    return cleaned


def is_site_id(text: str) -> bool:
    """判断是否为网站编号（便捷函数）"""
    return EnhancedWatermarkRemover.is_site_id(text)


def is_valid_adult_number(text: str) -> bool:
    """判断是否为有效番号（便捷函数）"""
    return EnhancedWatermarkRemover.is_valid_adult_number(text)
