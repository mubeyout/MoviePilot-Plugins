# Category: 核心模块
"""
Metatube 内容分类器
"""
from typing import Dict, List, Optional
from .keyword_matcher import KeywordMatcher
from ..models.base import KeywordMatchResult, RecognitionContext

class ContentClassifier:
    """内容分类器"""

    def __init__(self, keyword_matcher: KeywordMatcher):
        self.keyword_matcher = keyword_matcher
        self.category_mapping = {
            "日系": "成人/日系",
            "欧美系": "成人/欧美系",
            "中文系": "成人/中文系",
            "其他": "成人/其他"
        }

    def classify(self, context: RecognitionContext) -> KeywordMatchResult:
        """分类内容"""
        return self.keyword_matcher.detect_category(context.title)

    def get_category(self, context: RecognitionContext) -> str:
        """获取分类"""
        result = self.classify(context)
        return self.category_mapping.get(result.detected_category, "成人/其他")

    def should_process(self, context: RecognitionContext) -> bool:
        """判断是否应该处理"""
        result = self.classify(context)
        return result.is_adult_content

    def get_confidence(self, context: RecognitionContext) -> float:
        """获取分类置信度"""
        result = self.classify(context)
        return result.confidence

    def get_matched_keywords(self, context: RecognitionContext) -> List[str]:
        """获取匹配的关键字"""
        result = self.classify(context)
        return result.matched_keywords

    def handle_chinese_content(self, context: RecognitionContext) -> bool:
        """处理中文系内容"""
        result = self.classify(context)
        return result.detected_category == "中文系"

    def handle_western_content(self, context: RecognitionContext) -> bool:
        """处理欧美系内容"""
        result = self.classify(context)
        return result.detected_category == "欧美系"

    def handle_japanese_content(self, context: RecognitionContext) -> bool:
        """处理日系内容"""
        result = self.classify(context)
        return result.detected_category == "日系"

    def get_adult_category(self, context: RecognitionContext) -> str:
        """获取成人分类"""
        result = self.classify(context)
        return self.category_mapping.get(result.detected_category, "成人/其他")

    def is_adult_content(self, context: RecognitionContext) -> bool:
        """判断是否为成人内容"""
        result = self.classify(context)
        return result.is_adult_content

    def should_skip_by_keywords(self, context: RecognitionContext) -> bool:
        """判断是否应该跳过（匹配排除关键字）"""
        result = self.classify(context)
        return not result.is_adult_content