# Category: 核心模块
"""
Metatube 关键字匹配器
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ..models.base import KeywordMatchResult, LogConfig

class KeywordMatcher:
    """关键字匹配器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "keywords" / "builtin.json"
        self.builtin_keywords = self._load_builtin_keywords()
        self.custom_keywords = {}
        self.exclude_keywords = []
        self.strict_match = False

    def _load_builtin_keywords(self) -> Dict[str, List[str]]:
        """加载内置关键字"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'japanese': data.get('japanese', []),
                    'western': data.get('western', []),
                    'chinese': data.get('chinese', []),
                    'other': data.get('other', []),
                    'exclude': data.get('exclude', [])
                }
        except Exception as e:
            if LogConfig.should_log(f"加载内置关键字失败: {str(e)}"):
                print(f"警告: 加载内置关键字失败: {str(e)}")
            return {
                'japanese': [], 'western': [], 'chinese': [], 'other': [], 'exclude': []
            }

    def set_custom_keywords(self, keywords: Dict[str, List[str]]):
        """设置自定义关键字"""
        self.custom_keywords = keywords

    def set_exclude_keywords(self, exclude: List[str]):
        """设置排除关键字"""
        self.exclude_keywords = exclude

    def set_strict_match(self, strict: bool):
        """设置严格匹配模式"""
        self.strict_match = strict

    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        if not self.strict_match:
            text = text.upper()
        return text.strip()

    def _check_exclude_keywords(self, text: str) -> bool:
        """检查是否匹配排除关键字"""
        search_text = self._normalize_text(text)
        for exclude_kw in self.exclude_keywords:
            if exclude_kw in search_text:
                return True
        return False

    def _match_category_keywords(self, text: str, category: str) -> Tuple[bool, List[str]]:
        """匹配指定分类的关键字"""
        keywords = []

        # 获取对应分类的关键字
        if category == "日系":
            keywords = self.builtin_keywords['japanese'] + self.custom_keywords.get('japanese', [])
        elif category == "欧美系":
            keywords = self.builtin_keywords['western'] + self.custom_keywords.get('western', [])
        elif category == "中文系":
            keywords = self.builtin_keywords['chinese'] + self.custom_keywords.get('chinese', [])
        else:  # 其他
            keywords = self.builtin_keywords['other'] + self.custom_keywords.get('other', [])

        # 检查匹配
        matched = []
        search_text = self._normalize_text(text)

        for kw in keywords:
            if kw in search_text:
                matched.append(kw)

        return len(matched) > 0, matched

    def detect_category(self, text: str) -> KeywordMatchResult:
        """检测内容分类"""
        if not text:
            return KeywordMatchResult("其他", [], 0.0)

        # 首先检查排除关键字
        if self._check_exclude_keywords(text):
            return KeywordMatchResult("其他", [], 0.0)

        # 检查各个分类 - 调整优先级，中文系优先
        categories = ["中文系", "日系", "欧美系", "其他"]
        best_match = "其他"
        best_matched = []
        max_confidence = 0.0

        for category in categories:
            matched, keywords = self._match_category_keywords(text, category)
            if matched:
                # 计算置信度
                confidence = len(keywords) / max(1, len(text.split()))

                # 中文系使用更低的阈值（因为中文关键字更具体）
                threshold = 0.03 if category == "中文系" else 0.08

                if confidence > max_confidence and confidence >= threshold:
                    max_confidence = confidence
                    best_match = category
                    best_matched = keywords

        return KeywordMatchResult(best_match, best_matched, max_confidence)

    def is_adult_content(self, text: str) -> bool:
        """判断是否为成人内容"""
        result = self.detect_category(text)
        return result.is_adult_content

    def get_matched_keywords(self, text: str, category: str) -> List[str]:
        """获取匹配的关键字"""
        _, matched = self._match_category_keywords(text, category)
        return matched

    def get_confidence_score(self, text: str, category: str) -> float:
        """获取匹配置信度"""
        _, matched = self._match_category_keywords(text, category)
        return len(matched) / max(1, len(text.split()))

    def update_builtin_keywords(self, new_keywords: Dict[str, List[str]]):
        """更新内置关键字"""
        self.builtin_keywords = new_keywords
        # 保存到文件
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_keywords, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if LogConfig.should_log(f"保存关键字配置失败: {str(e)}"):
                print(f"警告: 保存关键字配置失败: {str(e)}")