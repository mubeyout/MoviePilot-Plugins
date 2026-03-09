# Category: 工具函数
"""
统一的番号提取器
整合所有番号提取逻辑
"""
import re
from typing import Optional
from .watermark_remover import EnhancedWatermarkRemover


class NumberExtractor:
    """统一的番号提取器"""

    # 番号正则表达式列表（按优先级排序）
    NUMBER_PATTERNS = [
        # ===== FC2 系列（最高优先级，防止被通用规则误匹配）=====
        r'(FC2)[-_]?(PPV)?[-_]?(\d{5,7})',

        # ===== HEYZO 系列 =====
        r'(HEYZO)[-_]?(\d{4})',

        # ===== Tokyo Hot 系列 =====
        r'([nNK]|K|KD)[-_]?(\d{4,5})',

        # ===== 主流标准格式 =====
        r'([A-Z]{2,10})[-_]?(\d{2,5})',

        # ===== 素人/单体系列 =====
        r'(10MUSUME|10MU)[-_]?(\d{2,4})',
        r'(PACO|PACOPACO)[-_]?(\d{3,5})',
        r'(XXX[-_]?AV|AV)[-_]?(\d{5})',

        # ===== 网站系列 =====
        r'(CARIB|CARIBPR|CARIBBEANCOM)[-_]?(\d{6})[-_]?(\d{3})',
        r'(\d{6})[_-](\d{3})',
        r'(S2M|SKY|SKYHIGH)[-_]?(\d{3,4})',
        r'(RED|REDHOT)[-_]?(\d{3})',

        # ===== 数字编号系列 =====
        r'(H\d{4})[-_]?(\d{3})',
        r'(C\d{4})[-_]?(\d{3})',
        r'(\d{6})[-_](\d{3})',

        # ===== 特殊厂商 =====
        r'(KIN8|TENGOKU|ENG)[-_]?(\d{3,5})',
        r'(GOLD)[-_]?(\d{3,4})',
        r'(CWP)[-_]?(\d{3,5})',
        r'(ABP|ABW|BKSP)[-_]?(\d{3,4})',
        r'(SSIS|STARS|SSND|SNIS)[-_]?(\d{3,4})',
        r'(IPX|IPZ|IPZZ|MIAE|MIRD)[-_]?(\d{3,4})',
        r'(EBOD|EBODY)[-_]?(\d{3,4})',
        r'(WANZ|WAAA)[-_]?(\d{3,4})',

        # ===== VR系列 =====
        r'(VR|3DVR|VRVR)[-_]?(\d{3,5})',

        # ===== 欧美系列 =====
        r'(RK)[-_]?(\d{4,5})',
        r'(XEMPIRE|DARKX|EROTICAX|HARDX|LESBIANX)[-_]?(\d{3,5})',
        r'(21SEXTURY|21NATURALS|21FOOTART|21EROTICA)[-_]?(\d{3,5})',

        # ===== 中文系列 =====
        r'(MDTV|MDX|MD|JD)[-_]?(\d{3,4})',

        # ===== 复合格式(后置匹配) =====
        r'([A-Z]{2,6})[-_]?(\d{3,5})[-_]?([A-Z]{0,4})',
        r'(\d{5,6})[-_](\d{3})',
    ]

    @classmethod
    def extract(cls, filename: str) -> Optional[str]:
        """
        从文件名中提取番号

        Args:
            filename: 文件名

        Returns:
            Optional[str]: 提取的番号，未找到返回 None
        """
        if not filename:
            return None

        # 使用增强的水印移除器清理文件名
        cleaned, watermark = EnhancedWatermarkRemover.clean_filename(filename)

        # 如果清理后是网站编号，返回 None
        if EnhancedWatermarkRemover.is_site_id(cleaned):
            return None

        # 如果清理后已经是有效番号，直接返回
        if EnhancedWatermarkRemover.is_valid_adult_number(cleaned):
            return cleaned

        # 否则尝试从清理后的文本中提取番号
        name = cleaned.upper().strip()

        # 尝试匹配各种番号格式
        for pattern in cls.NUMBER_PATTERNS:
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

    @classmethod
    def normalize(cls, number: str) -> str:
        """
        标准化番号格式

        Args:
            number: 原始番号

        Returns:
            str: 标准化后的番号
        """
        if not number:
            return ""

        # 转大写并清理空格
        number = number.upper().strip()

        # 替换全角字符
        number = number.replace('－', '-').replace('＿', '_')

        return number

    @classmethod
    def validate(cls, number: str) -> bool:
        """
        验证番号格式

        Args:
            number: 待验证的番号

        Returns:
            bool: True 表示格式有效
        """
        if not number:
            return False

        # 标准化后验证
        normalized = cls.normalize(number)

        # 检查基本格式：字母-数字 或 字母-数字-字母
        basic_pattern = r'^[A-Z0-9\-]+$'
        if not re.match(basic_pattern, normalized):
            return False

        # 检查是否至少包含一个字母和一个数字
        has_letter = bool(re.search(r'[A-Z]', normalized))
        has_digit = bool(re.search(r'\d', normalized))

        return has_letter and has_digit

    @classmethod
    def is_jav_format(cls, number: str) -> bool:
        """
        判断是否为 JAV 番号格式

        Args:
            number: 待判断的番号

        Returns:
            bool: True 表示是 JAV 格式
        """
        if not number:
            return False

        normalized = cls.normalize(number)

        # JAV 番号格式模式
        jav_patterns = [
            r'^[A-Z]{2,10}-\d{2,5}$',  # 标准格式: SSIS-001
            r'^[A-Z]{2,10}-\d{2,5}-[A-Z]{0,4}$',  # 带后缀: ABC-123-UC
            r'^FC2(-PPV)?-\d{5,7}$',  # FC2 格式
            r'^HEYZO-\d{4}$',  # HEYZO 格式
            r'^\d{6}-\d{3}$',  # 纯数字格式
        ]

        upper_number = normalized.upper()
        for pattern in jav_patterns:
            if re.match(pattern, upper_number):
                return True

        return False

    @classmethod
    def extract_batch(cls, filenames: list) -> dict:
        """
        批量提取番号

        Args:
            filenames: 文件名列表

        Returns:
            dict: {filename: number} 映射字典
        """
        results = {}

        for filename in filenames:
            number = cls.extract(filename)
            if number:
                results[filename] = number

        return results
