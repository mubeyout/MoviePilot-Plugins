# Category: 工具
"""
Metatube 统一错误处理机制
"""
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass
from ..models.base import RecognitionResult, MediaInfo

class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network"
    API_ERROR = "api"
    PARSING_ERROR = "parsing"
    CONFIG_ERROR = "config"
    IDENTIFICATION_ERROR = "identification"
    UNKNOWN_ERROR = "unknown"

@dataclass
class PluginError:
    """插件错误"""
    error_type: ErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'error_type': self.error_type.value,
            'message': self.message,
            'details': self.details or {},
            'timestamp': self.timestamp,
            'source': self.source
        }

class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        self.errors: List[PluginError] = []
        self.error_counts: Dict[ErrorType, int] = {error_type: 0 for error_type in ErrorType}

    def handle_error(self, error_type: ErrorType, message: str, details: Optional[Dict[str, Any]] = None, source: str = "metatube") -> PluginError:
        """处理错误"""
        error = PluginError(error_type, message, details, source=source)
        self.errors.append(error)
        self.error_counts[error_type] += 1
        return error

    def get_recent_errors(self, count: int = 10) -> List[PluginError]:
        """获取最近错误"""
        return sorted(self.errors, key=lambda x: x.timestamp, reverse=True)[:count]

    def get_error_count(self, error_type: Optional[ErrorType] = None) -> int:
        """获取错误数量"""
        if error_type:
            return self.error_counts.get(error_type, 0)
        return len(self.errors)

    def clear_errors(self):
        """清空错误"""
        self.errors.clear()
        self.error_counts = {error_type: 0 for error_type in ErrorType}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_errors': len(self.errors),
            'error_counts': {k.value: v for k, v in self.error_counts.items()},
            'recent_errors': [error.to_dict() for error in self.get_recent_errors()]
        }

class ResultHandler:
    """结果处理器 - 统一处理识别结果"""

    @staticmethod
    def handle_success(result: Any, source: str = "metatube") -> RecognitionResult:
        """处理成功结果"""
        return RecognitionResult(
            status=RecognitionStatus.SUCCESS,
            data=result,
            source=source
        )

    @staticmethod
    def handle_retry(result: Any = None, message: str = "", source: str = "metatube") -> RecognitionResult:
        """处理需要重试的结果"""
        return RecognitionResult(
            status=RecognitionStatus.RETRY,
            data=result,
            error=message,
            source=source
        )

    @staticmethod
    def handle_failure(message: str, error_type: ErrorType = ErrorType.IDENTIFICATION_ERROR, source: str = "metatube") -> RecognitionResult:
        """处理失败结果"""
        return RecognitionResult(
            status=RecognitionStatus.FAIL,
            data=None,
            error=message,
            source=source
        )

    @staticmethod
    def fallback_to_category(title: str, category: str, source: str = "metatube") -> MediaInfo:
        """回退到分类结果"""
        mediainfo = MediaInfo()
        mediainfo.source = source
        mediainfo.type = MediaType.MOVIE
        mediainfo.title = title
        mediainfo.original_title = title
        mediainfo.imdb_id = title
        mediainfo.set_category(category)
        return mediainfo

    @staticmethod
    def should_retry(result: RecognitionResult) -> bool:
        """判断是否应该重试"""
        return result.status == RecognitionResult.Status.RETRY

    @staticmethod
    def is_success(result: RecognitionResult) -> bool:
        """判断是否成功"""
        return result.status == RecognitionResult.Status.SUCCESS

class RetryManager:
    """重试管理器"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.current_retries = 0

    def can_retry(self) -> bool:
        """判断是否可以重试"""
        return self.current_retries < self.max_retries

    def increment_retry(self):
        """增加重试次数"""
        self.current_retries += 1

    def reset(self):
        """重置重试计数器"""
        self.current_retries = 0

    def get_retry_delay(self) -> float:
        """获取重试延迟"""
        return self.retry_delay * (2 ** (self.current_retries - 1))  # 指数退避

class ErrorReporting:
    """错误报告"""

    @staticmethod
    def format_error(error: PluginError) -> str:
        """格式化错误信息"""
        details = f" 详情: {error.details}" if error.details else ""
        return f"[{error.timestamp}] [{error.error_type.value.upper()}] {error.message}{details}"

    @staticmethod
    def summarize_errors(errors: List[PluginError]) -> str:
        """总结错误信息"""
        if not errors:
            return "无错误"

        error_types = {}
        for error in errors:
            error_type = error.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1

        summary = "错误摘要:\n"
        for error_type, count in error_types.items():
            summary += f"- {error_type}: {count}次\n"

        return summary

# 全局错误处理器实例
global_error_handler = ErrorHandler()
global_retry_manager = RetryManager()