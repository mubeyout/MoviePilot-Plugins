# Category: 核心模块
"""
高效的关键字匹配器
使用预编译正则表达式优化性能
"""
import re
from typing import Dict, List, Tuple, Optional
from app.log import logger


class EfficientKeywordMatcher:
    """高效的关键字匹配器（使用预编译正则）"""

    def __init__(self):
        """初始化匹配器"""
        self._patterns: Dict[str, re.Pattern] = {}
        self._category_keywords: Dict[str, List[str]] = {}
        self._initialized = False

    def initialize(self, keywords_config: Dict[str, List[str]]):
        """
        初始化关键字匹配器

        Args:
            keywords_config: 关键字配置字典 {category: [keywords]}
        """
        self._category_keywords = keywords_config
        self._compile_patterns()
        self._initialized = True
        logger.info(f"高效关键字匹配器初始化完成，共 {len(keywords_config)} 个分类")

    def _compile_patterns(self):
        """为每个分类预编译正则表达式"""
        for category, keywords in self._category_keywords.items():
            if not keywords:
                continue

            # 转义特殊字符，用 | 连接（按长度降序排序，优先匹配长关键字）
            escaped_keywords = [re.escape(kw) for kw in keywords]
            escaped_keywords.sort(key=len, reverse=True)

            pattern = '|'.join(escaped_keywords)

            try:
                self._patterns[category] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"编译分类 '{category}' 的正则表达式失败: {str(e)}")

    def match(self, text: str) -> Dict[str, List[str]]:
        """
        一次性匹配所有分类的关键字

        Args:
            text: 待匹配的文本

        Returns:
            Dict[str, List[str]]: {category: [matched_keywords]}
        """
        if not self._initialized:
            logger.warning("关键字匹配器未初始化，返回空结果")
            return {}

        if not text:
            return {}

        matches = {}

        # 并行匹配所有分类
        for category, pattern in self._patterns.items():
            found = pattern.findall(text)
            if found:
                # 去重并保持顺序
                seen = set()
                unique_matches = []
                for item in found:
                    if item not in seen:
                        seen.add(item)
                        unique_matches.append(item)
                matches[category] = unique_matches

        return matches

    def get_best_match(self, text: str, priority_order: List[str] = None) -> Tuple[str, List[str]]:
        """
        获取最佳匹配分类

        Args:
            text: 待匹配的文本
            priority_order: 分类优先级列表，如 ['日系', '欧美系', '中文系']

        Returns:
            Tuple[str, List[str]]: (best_category, matched_keywords)
        """
        matches = self.match(text)

        if not matches:
            return "其他", []

        # 按优先级顺序查找
        if priority_order:
            for category in priority_order:
                if category in matches:
                    return category, matches[category]

        # 返回匹配关键字最多的分类
        best_category = max(matches.keys(), key=lambda k: len(matches[k]))
        return best_category, matches[best_category]

    def update_keywords(self, category: str, keywords: List[str]):
        """
        更新指定分类的关键字

        Args:
            category: 分类名称
            keywords: 新的关键字列表
        """
        self._category_keywords[category] = keywords

        # 重新编译该分类的正则
        if keywords:
            escaped = [re.escape(kw) for kw in keywords]
            escaped.sort(key=len, reverse=True)
            pattern = '|'.join(escaped)
            try:
                self._patterns[category] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"更新分类 '{category}' 的正则表达式失败: {str(e)}")
        elif category in self._patterns:
            del self._patterns[category]

    def reload_all(self, keywords_config: Dict[str, List[str]]):
        """
        重新加载所有关键字配置

        Args:
            keywords_config: 新的关键字配置
        """
        self._category_keywords = keywords_config
        self._patterns.clear()
        self._compile_patterns()
        logger.info("关键字匹配器配置已重新加载")


# 兼容层：保持与原 KeywordMatcher 相同的接口
class KeywordMatcher:
    """关键字匹配器（兼容层，使用高效实现）"""

    def __init__(self, config_path=None):
        """初始化（兼容旧接口）"""
        from pathlib import Path
        import json

        self.config_path = config_path or Path(__file__).parent / "keywords" / "builtin.json"
        self.builtin_keywords = self._load_builtin_keywords()

        # 使用高效匹配器
        self._matcher = EfficientKeywordMatcher()
        self._matcher.initialize(self.builtin_keywords)

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
            print(f"警告: 加载内置关键字失败: {str(e)}")
            return {
                'japanese': [], 'western': [], 'chinese': [], 'other': [], 'exclude': []
            }

    def set_custom_keywords(self, keywords: Dict[str, List[str]]):
        """设置自定义关键字"""
        self.custom_keywords = keywords

        # 合并关键字并重新初始化匹配器
        merged_keywords = {}
        for category in self.builtin_keywords.keys():
            builtin = self.builtin_keywords.get(category, [])
            custom = keywords.get(category, [])
            merged_keywords[category] = list(set(builtin + custom))

        self._matcher.reload_all(merged_keywords)

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

    def detect_category(self, text: str):
        """检测内容分类（返回兼容的结果对象）"""
        from ..models.base import KeywordMatchResult

        if not text:
            return KeywordMatchResult("其他", [], 0.0)

        # 首先检查排除关键字
        if self._check_exclude_keywords(text):
            return KeywordMatchResult("其他", [], 0.0)

        # 使用高效匹配器
        priority_order = ["日系", "欧美系", "中文系", "其他"]
        best_category, matched_keywords = self._matcher.get_best_match(text, priority_order)

        # 计算置信度
        confidence = len(matched_keywords) / max(1, len(text.split()))

        return KeywordMatchResult(best_category, matched_keywords, confidence)

    def is_adult_content(self, text: str) -> bool:
        """判断是否为成人内容"""
        result = self.detect_category(text)
        return result.is_adult_content

    def get_matched_keywords(self, text: str, category: str) -> List[str]:
        """获取匹配的关键字"""
        matches = self._matcher.match(text)
        return matches.get(category, [])

    def get_confidence_score(self, text: str, category: str) -> float:
        """获取匹配置信度"""
        matched = self.get_matched_keywords(text, category)
        return len(matched) / max(1, len(text.split()))
