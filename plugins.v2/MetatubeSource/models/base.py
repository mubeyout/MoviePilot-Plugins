# Category: 数据模型
"""
Metatube 插件数据模型
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class MediaType(Enum):
    """媒体类型枚举"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    ADULT = "adult"

class RecognitionStatus(Enum):
    """识别状态枚举"""
    SUCCESS = "success"
    RETRY = "retry"
    FAIL = "fail"

@dataclass
class RecognitionResult:
    """识别结果"""
    status: RecognitionStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    source: Optional[str] = None

    @property
    def should_retry(self) -> bool:
        return self.status == RecognitionStatus.RETRY

    @property
    def is_success(self) -> bool:
        return self.status == RecognitionStatus.SUCCESS

@dataclass
class KeywordMatchResult:
    """关键字匹配结果"""
    detected_category: str
    matched_keywords: List[str]
    confidence: float

    @property
    def is_adult_content(self) -> bool:
        return self.detected_category != "其他"

@dataclass
class MediaInfo:
    """媒体信息"""
    source: str = ""
    type: MediaType = MediaType.MOVIE
    title: str = ""
    original_title: str = ""
    imdb_id: str = ""
    tmdb_id: Optional[int] = None
    douban_id: str = ""
    category: str = ""
    year: Optional[int] = None
    description: str = ""
    poster: str = ""
    backdrop: str = ""
    actors: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    studios: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def set_category(self, category: str):
        """设置分类"""
        self.category = category

    def add_actor(self, actor: str):
        """添加演员"""
        if actor and actor not in self.actors:
            self.actors.append(actor)

    def add_studio(self, studio: str):
        """添加片商"""
        if studio and studio not in self.studios:
            self.studios.append(studio)

@dataclass
class RecognitionContext:
    """识别上下文"""
    meta: Any
    title: str
    detected_category: str
    original_title: str
    config: Any

    def __post_init__(self):
        if not self.title:
            self.title = self.original_title

@dataclass
class APIRequest:
    """API请求信息"""
    method: str
    url: str
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    proxies: Optional[Dict[str, str]] = None

    @property
    def full_url(self) -> str:
        """完整URL"""
        from urllib.parse import urljoin
        return urljoin(self.url, f"?{self.query_string}") if self.params else self.url

    @property
    def query_string(self) -> str:
        """查询字符串"""
        return "&".join([f"{k}={v}" for k, v in self.params.items()])

@dataclass
class APIResponse:
    """API响应信息"""
    status_code: int
    data: Any
    request: APIRequest
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status_code == 200

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    message: str
    category: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'message': self.message,
            'category': self.category,
            'source': self.source,
        }

@dataclass
class NamingTemplate:
    """命名模板"""
    template: str
    label: str
    variables: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NamingTemplate':
        """从字典创建"""
        return cls(
            template=data['template'],
            label=data['label'],
            variables=data.get('variables', [])
        )

class LogConfig:
    """日志配置"""
    # 日志级别
    LEVEL = "INFO"

    # 关键日志（必须记录）
    CRITICAL_LOGS = [
        "识别成功",
        "识别失败",
        "API连接失败",
        "关键词匹配",
        "配置加载完成",
    ]

    # 调试日志（可选）
    DEBUG_LOGS = [
        "番号提取详情",
        "API请求参数",
        "数据转换详情",
        "关键字匹配过程",
    ]

    @classmethod
    def should_log(cls, message: str) -> bool:
        """判断是否应该记录"""
        if cls.LEVEL == "DEBUG":
            return True

        for critical in cls.CRITICAL_LOGS:
            if critical in message:
                return True

        return False