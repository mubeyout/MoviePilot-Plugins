# Category: 插件入口
"""
Metatube 媒体识别插件
通过 Metatube API 识别番号媒体信息
"""
import re
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, Optional, List, Tuple
import threading

from app.chain import ChainBase
from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.plugins import _PluginBase
from app.log import logger
from app.schemas.types import MediaType
from app.core.event import eventmanager, Event
from app.schemas.types import ChainEventType
from app.schemas import DiscoverMediaSource, DiscoverSourceEventData
from app.core.config import settings

from .metatube_api import MetatubeApiClient
from .theporndb_api import ThePornDBApiClient
from .bytemuse_api import ByteMuseApiClient
from .javbus_api import JavBusApiClient
from .schema import (
    MetatubeMovie, MetatubeMovieDetail, LogEntry,
    ThePornDBScene, ThePornDBSceneDetail,
    ThePornDBJAVDetail, ThePornDBJAVScene,
    ByteMuseMovie, ByteMuseSearchResponse,
    JavBusMovie, JavBusMovieDetail, JavBusEntity, JavBusSample
)



class _RateLimiter:
    """Lightweight thread-safe rate limiter"""
    def __init__(self, interval: float = 0.5):
        self._interval = interval
        self._last_time = None
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            now = datetime.now()
            if self._last_time is None or (now - self._last_time).total_seconds() >= self._interval:
                self._last_time = now
                return True
            return False

    def get_wait_time(self) -> float:
        with self._lock:
            if self._last_time is None:
                return 0.0
            elapsed = (datetime.now() - self._last_time).total_seconds()
            return max(0.0, self._interval - elapsed)

class MetatubeSource(_PluginBase):
    # 插件名称
    plugin_name = "Metatube源"
    # 插件描述
    plugin_desc = "通过Metatube API识别番号媒体信息。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/Metatube.png"
    # 插件版本
    plugin_version = "2.0.0"
    # 插件作者
    plugin_author = "MUBEY"
    # 作者主页
    author_url = "https://github.com/mubeyout"
    # 插件配置项ID前缀
    plugin_config_prefix = "metatubesource_"
    # 加载顺序
    plugin_order = 23
    # 可使用的用户级别
    auth_level = 1

    # ==================== 分类常量 ====================
    CATEGORY_PREFIX = "成人"
    SUBCATEGORY_JAPANESE = "日系"
    SUBCATEGORY_WESTERN = "欧美系"
    SUBCATEGORY_CHINESE = "中文系"
    SUBCATEGORY_OTHER = "其他"
    SUBCATEGORY_SKIP = "__SKIP__"  # 特殊标记：应该跳过识别

    # 关键字配置文件路径
    KEYWORDS_FILE_PATH = "keywords.json"  # 插件根目录下的 JSON 文件

    # 内置核心关键字库（按分类组织）- 优先级：2（低于UI自定义，高于keywords.json文件）
    # 日系核心关键词（主流番号前缀、知名片商）
    BUILT_IN_JAPANESE_KEYWORDS = [
        # === 主流番号前缀 ===
        "SSIS", "IPX", "MIAA", "JUL", "CAWD",
        "FC2", "FC2PPV", "HEYZO", "CARIB",
        "STAR", "STARS", "EBOD", "WANZ",

        # === 知名片商标识 ===
        "S1", "Moodyz", "IdeaPocket", "Madonna", "Premium",
        "Alice JAPAN", "kawaii", "E-BODY", "OPPAI",
        "Wanz Factory", "SOD", "Prestige",

        # === JAV通用 ===
        "JAV", "JavHD", "Javbus", "DMM", "FANZA",

        # === 中文标识 ===
        "一本道", "加勒比", "东京热", "Caribbean",
        "Tokyo Hot", "Sky High", "Red Hot",

        # === 民营网站 ===
        "10musume", "Pacopacomama", "1Pondo",
        "Heyzo", "Caribbeancom",
    ]

    # 欧美系核心关键词（主流成人网站、工作室）
    BUILT_IN_WESTERN_KEYWORDS = [
        # === 主流网站 ===
        "BRAZZERS", "BRAZZERS-",
        "NaughtyAmerica", "NAUGHTY",
        "RealityKings", "RK",
        "Mofos", "MOFOS",

        # === Vixen Media ===
        "BLACKED", "BLACKEDRAW",
        "TUSHY", "TUSHYRAW",
        "VIXEN", "VIXEN-",
        "Deeper", "Slayed",

        # === BangBros ===
        "BangBros", "BANG",

        # === 其他知名工作室 ===
        "DigitalPlayground", "DP",
        "EvilAngel", "EvilAngel-",
        "JulesJordan", "Jules",
        "PureTaboo", "Pure-",

        # === 主流网站 ===
        "Pornhub", "Pornhub-",
        "Xvideos", "Xvideos-",
    ]

    # 中文系核心关键词（主流传媒品牌）
    # 优化: 移除过于宽泛的关键字，提高识别精度（v1.1.1）
    BUILT_IN_CHINESE_KEYWORDS = [
        # === 主流传媒品牌（高优先级，强特征） ===
        "MD", "MD-", "MDCN", "麻豆", "麻豆傳媒", "MADOU",
        "MX", "MX-", "精东", "精東傳媒",
        "TM", "TM-", "天美", "天美傳媒",
        "PMC", "PMC-", "蜜桃", "蜜桃傳媒",
        "91制片", "九一制片",
        "TW", "TW-", "台湾", "台灣傳媒",

        # === 探花系列（特定成人内容） ===
        "约炮", "探花", "小宝寻花", "李寻花", "沈先生",
        # 移除 "网红" - 过于宽泛，普通网红视频很多

        # === 成人内容标识（强特征） ===
        "传媒", "傳媒", "自拍", "偷拍", "露脸",
        "成人", "色情", "黄色", "情色",
        "做爱", "性交", "口交", "肛交",
        # 移除 "国产" - 过于宽泛

        # === 体型特征（保留，强特征） ===
        "巨乳", "大胸", "爆乳", "翘臀",
        "丝袜", "美腿", "黑丝", "裸体", "全裸",

        # === 职业/身份（优化 - 移除通用词） ===
        "空姐", "护士", "女仆",  # 保留特定角色
        "少妇", "人妻", "熟女",  # 保留成人特定
        # 移除 "老师", "学生", "模特", "主播" - 过于宽泛

        # === 视频特征 ===
        "无码", "有码", "内射", "颜射",
        "中文字幕",

        # === 新增：组合特征（更精确的成人内容标识） ===
        "福利视频", "大秀", "私拍", "流出",
        "门事件", "艳照", "不雅视频",
    ]

    # 其他核心关键词（通用特征）
    # 优化: 移除单字关键字(屄,逼,屌,操,干)和画质/字幕等通用词汇
    BUILT_IN_OTHER_KEYWORDS = [
        # === 编码类型 ===
        "破解", "无修",

        # === 成人标识 ===
        "AV", "成人视频", "A片",

        # === 版本特征 (移除可能误判的"完整版") ===
        "无删减版", "流出", "泄露",
    ]

    # 内置排除关键字（匹配后直接跳过分类）
    BUILT_IN_EXCLUDE_KEYWORDS = [
        # === 画质标记 ===
        "UHD", "HDR", "HDR10", "HDR10+", "DOLBY", "DOLBY-VISION", "HDR-10",
        "FHD", "HD", "SD", "LD", "ED",

        # === 分辨率 ===
        "3840X2160", "1920X1080", "1280X720",
        "X264", "X265", "H264", "H265",

        # === 帧率 ===
        "60FPS", "120FPS", "240FPS", "30FPS", "24FPS",
        "60FPS", "59.94FPS", "29.97FPS",

        # === 音频编码 ===
        "AC3", "DTS", "DTS-HD", "DTS-HDMA", "AAC", "FLAC",
        "MP3", "OPUS", "OGG", "WAV", "MKA",
        "TRUEHD", "DOLBY-ATMOS", "ATMOS",
        "EAC3", "DDP", "DD",
        "LPCM", "PCM",

        # === 视频格式 ===
        "REMUX", "WEB-DL", "WEBRIP", "WEB", "WEB-DL",
        "BLURAY", "BLU-RAY", "BDRIP", "BRRIP", "BD", "DVD",
        "DVDRIP", "HDDVD", "HDTV", "PDTV", "TVRIP",
        "SATRIP", "CAM", "TS", "TC",
        "TELESYNC", "TELECINE",

        # === 制式 ===
        "NTSC", "PAL", "SECAM", "SECA",

        # === 来源标记 ===
        "NETFLIX", "DISNEY+", "HULU", "AMZN", "AMAZON",
        "HBO", "HBO-MAX", "PARAMOUNT+",
        "APPLE-TV", "APPLE+",
        "PRIME", "CRUNCHYROLL", "FUNIMATION",
        "BILIBILI", "YOUTUBE", "IQIYI", "TENCENT",
        "YOUKU", "MANGO", "TV", "VLC", "MM",
        "KYTICE", "MONUMENT", "FULLBRUTALITY", "FRDS",
        "MTEAM", "MT", "CWAHD", "LAZERS", "LWRTD",
        "PROPER", "REPACK", "INTERNAL", "LIMITED",

        # === 语言标记 ===
        "DUAL", "MULTI", "MULTISUBS",
        "ENGLISH", "JAPANESE", "CHINESE", "CANTONESE", "MANDARIN",
        "EN", "JP", "CN", "ZH", "ZH-CN", "ZH-TW",
        "ENG", "JPN", "CHN", "ZHO",
        "GBR", "USA", "JPN", "CHN", "HKG", "KOR", "TWN",

        # === 版本标记 ===
        "DIRECTORS-CUT", "EXTENDED", "UNCUT",
        "UNCENSORED", "UNRATED",
        "PROPER", "REPACK", "LIMITED", "INTERNAL",
        "REMASTERED", "RESTORED", "THEATRICAL", "EXTENDED",
        "SPECIAL", "COLLECTOR", "ULTIMATE", "DELUXE",

        # === 发行标记 ===
        "COMPLETE", "SEASON", "EPISODE", "EP", "S",
        "SCENE", "COMPILATION", "ANTHOLOGY",
        "BOXSET", "COLLECTION", "SERIES", "SAGA",

        # === 常见影视类型 ===

        # === 中文剧集/电影常见词 === "OVA", "OAD",

        # === 常见动漫/剧集标题 ===

        # === 中文常见标识 ===
        "国语", "粤语", "中字", "中英", "双语",
        "简体", "繁体", "字幕", "内嵌", "外挂",
        "合集", "收藏", "珍藏", "纪念",

        # === 英文常见标识 ===
        "AKA", "ALSO", "KNOWN", "AS", "COMPLETE",
        "PART", "PART1", "PART2", "PART3",
        "VOL", "VOL1", "VOL2", "VOLUME",
        "EDITION", "VERSION", "RELEASE",

        # === 地区标识 ===
        "USA", "UK", "GBR", "JPN", "CHN", "HKG", "KOR", "TWN",
        "EUR", "ASIA", "WORLD", "GLOBAL", "INTERNATIONAL",

        # === 发行组标识 ===
        "FGT", "FYQ", "EZTV", "RARBG", "YIFY", "YTS",
        "SPARKS", "FLUX", "GT", "QTS", "SMURF",

        # === 特殊格式 ===
        "3D", "2D", "VR", "MINIMAL", "NO-FRILLS",
        "HYBRID", "RE-ENCODE", "RE-MUX", "REPACK",

        # === 其他技术标记 ===
        "HYBRID", "COMPRESS", "CRRIP", "DVDR",
        "R5", "READNFO", "NFO", "SFV", "MD5",
        "SAMPLE", "PROOF", "SUBS", "SUBPACK",
        "DUBBED", "SUBBED", "SYNCED", "FIXED",

        # === 编码器标识 ===
        "XVID", "DIVX", "RMVB", "WMV", "AVI",
        "MKV", "MP4", "MOV", "FLV", "TS", "M2TS",

        # === 其他 ===
        "RELEASE", "BLURAYDISC", "DISC", "DISC1", "DISC2",
        "CD1", "CD2", "DVD1", "DVD2", "DVD5", "DVD9",
        "PAL", "NTSC", "SECAM",

        # === 档案组/发布组 ===
        "CHD", "CHDTV", "CHDBITS", "HDChina", "TTG",
        "HDSky", "MTeam", "CMCT", "FRDS", "ADWeb",
        "UBWEB", "HDKWeb", "MONUMENT", "KYTiCE",

        # === 文件质量标记 ===
        "HQ", "LQ", "HIGH", "LOW", "BEST",
        "GOOD", "BAD", "PROPER", "NUKE",

        # ==================== 新增：非成人内容排除标识 ====================
        # === 音乐演唱会标识 ===

        # === 短剧/网剧标识 ===

        # === 综艺/访谈标识 ===

        # === 歌曲/专辑标识 === "MV",

        # === 视频创作者标识 ===

        # === 体育/游戏标识 ===
    ]

    # ==================== 命名模板预设 ====================
    # 支持变量: {number} {actor} {studio} {label} {year} {title} {series}
    NAMING_TEMPLATES = {
        "number_actor_studio": "{number} {actor} [{studio}]",          # SSIS-001 三上悠亚 [S1]
        "number_actor": "{number} {actor}",                            # SSIS-001 三上悠亚
        "number_studio_actor": "{number} [{studio}] {actor}",          # SSIS-001 [S1] 三上悠亚
        "number_only": "{number}",                                     # SSIS-001
        "number_year": "{number} ({year})",                            # SSIS-001 (2024)
        "number_actor_year": "{number} {actor} ({year})",              # SSIS-001 三上悠亚 (2024)
        "full": "{number} {actor} [{studio}] ({year})",                # SSIS-001 三上悠亚 [S1] (2024)
        "custom": ""  # 用户自定义模板
    }

    # 模板显示名称（用于UI）
    NAMING_TEMPLATE_LABELS = {
        "number_actor_studio": "番号 演员 [片商]",
        "number_actor": "番号 演员",
        "number_studio_actor": "番号 [片商] 演员",
        "number_only": "仅番号",
        "number_year": "番号 (年份)",
        "number_actor_year": "番号 演员 (年份)",
        "full": "完整格式",
        "custom": "自定义模板"
    }

    # 插件配置
    _enabled: bool = False
    _api_url: str = "http://127.0.0.1:8080"
    _timeout: int = 30  # 默认超时30秒，metatube搜索可能需要较长时间
    _max_logs: int = 100
    _clear_logs_flag: bool = False  # 清空日志开关

    # 命名规则配置
    _naming_template: str = "number_actor_year"  # 默认模板调整为 number_actor_year
    _custom_naming_template: str = ""  # 自定义模板
    _max_actors: int = 2  # 最多显示演员数

    # 关键字相关配置（分类管理）
    _custom_japanese_keywords: str = ""  # 自定义日系关键字
    _custom_western_keywords: str = ""  # 自定义欧美系关键字
    _custom_chinese_keywords: str = ""  # 自定义中文系关键字
    _custom_other_keywords: str = ""  # 自定义其他关键字
    _exclude_keywords: str = ""  # 排除关键字（逗号分隔）
    _keywords_file_path: str = "keywords.json"  # 关键字文件路径（固定，不提供UI配置）
    _strict_match: bool = False  # 是否严格匹配

    _failed_download_control: bool = True  # 识别失败后是否执行下载

    # 通用配置
    _show_failure_detail: bool = True  # 识别失败提示开关

    # ThePornDB 配置
    _theporndb_enabled: bool = False  # 是否启用 ThePornDB
    _theporndb_api_token: str = ""  # ThePornDB API Token

    # ByteMuse 配置
    _bytemuse_enabled: bool = False  # 是否启用 ByteMuse
    _bytemuse_url: str = "http://127.0.0.1:3750"  # ByteMuse API 地址
    _bytemuse_username: str = ""  # ByteMuse 登录用户名
    _bytemuse_password: str = ""  # ByteMuse 登录密码

    # JavBus 配置
    _javbus_enabled: bool = False  # 是否启用 JavBus
    _javbus_api_url: str = "http://10.0.0.1:8922"  # javbus-api 地址

    # JAV 配置
    _jav_number_auto_match: bool = True  # JAV番号自动匹配

    # 搜索数据源配置
    _search_enabled: bool = False  # 是否启用搜索数据源功能

    # 私有属性
    _metatube_client: MetatubeApiClient = None
    _theporndb_client: ThePornDBApiClient = None  # ThePornDB 客户端
    _bytemuse_client: ByteMuseApiClient = None  # ByteMuse 客户端
    _javbus_client: JavBusApiClient = None  # JavBus 客户端
    _original_method: Optional[Callable] = None
    _original_async_method: Optional[Callable[..., Coroutine[Any, Any, Optional[MediaInfo]]]] = None
    _log_entries: deque = None

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        # 初始化线程安全的频率限制器
        self._rate_limiter = _RateLimiter(interval=0.5)

        # 识别去重缓存：避免短时间内重复识别同一项目
        # {标题key: (结果状态, 时间戳)}
        self._recognize_cache: Dict[str, Tuple[str, float]] = {}
        self._recognize_cache_ttl = 3600  # 缓存有效期 1 小时（秒）

        plugin_instance: MetatubeSource = self

        def patched_recognize_media(chain_self, meta: MetaBase = None,
                                    mtype: Optional[MediaType] = None,
                                    tmdbid: Optional[int] = None,
                                    doubanid: Optional[str] = None,
                                    bangumiid: Optional[int] = None,
                                    episode_group: Optional[str] = None,
                                    cache: bool = True,
                                    **kwargs):
            """
            劫持系统媒体识别方法（关键字优先模式）

            优先级：
            1. 匹配 metatube 关键词 → 直接由 metatube 处理
            2. 不匹配关键词 → 交由系统 IMDB 识别
            3. 系统识别失败 → 最后由 metatube 兜底处理
            """
            if not plugin_instance._original_method:
                return None

            if plugin_instance._enabled:
                # 1. 优先检查是否匹配 metatube 关键词
                if plugin_instance._match_keywords(meta):
                    logger.info(f"通过插件 {MetatubeSource.plugin_name} 关键词匹配，优先执行：recognize_media ...")
                    result = plugin_instance.recognize_media(meta, mtype)
                    if result:
                        return result
                    # metatube 识别失败，不再回退系统识别（因为已匹配关键词，应由 metatube 全权处理）
                    logger.debug(f"Metatube 识别失败，关键词匹配内容不回退系统识别")
                    return None

                # 2. 不匹配关键词，交由系统 IMDB 识别
                _filtered_kwargs = {k: v for k, v in kwargs.items()
                                   if k in ("share_meta",)}
                result = plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                          episode_group, cache, **_filtered_kwargs)
                if result:
                    return result

                # 3. 系统识别也失败，最后由 metatube 兜底处理
                logger.info(f"系统识别失败，通过插件 {MetatubeSource.plugin_name} 兜底执行：recognize_media ...")
                return plugin_instance.recognize_media(meta, mtype)

            # 插件未启用，直接调用原始方法
            _filtered_kwargs = {k: v for k, v in kwargs.items()
                               if k in ("share_meta",)}
            return plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                    episode_group, cache, **_filtered_kwargs)

        async def patched_async_recognize_media(chain_self, meta: MetaBase = None,
                                                mtype: Optional[MediaType] = None,
                                                tmdbid: Optional[int] = None,
                                                doubanid: Optional[str] = None,
                                                bangumiid: Optional[int] = None,
                                                episode_group: Optional[str] = None,
                                                cache: bool = True,
                                                **kwargs):
            """
            异步劫持系统媒体识别方法（关键字优先模式）

            优先级：
            1. 匹配 metatube 关键词 → 直接由 metatube 处理
            2. 不匹配关键词 → 交由系统 IMDB 识别
            3. 系统识别失败 → 最后由 metatube 兜底处理
            """
            if not plugin_instance._original_async_method:
                return None

            if plugin_instance._enabled:
                # 1. 优先检查是否匹配 metatube 关键词
                if plugin_instance._match_keywords(meta):
                    logger.info(f"通过插件 {MetatubeSource.plugin_name} 关键词匹配，优先执行：async_recognize_media ...")
                    result = await plugin_instance.async_recognize_media(meta, mtype)
                    if result:
                        return result
                    # metatube 识别失败，不再回退系统识别（因为已匹配关键词，应由 metatube 全权处理）
                    logger.debug(f"Metatube 异步识别失败，关键词匹配内容不回退系统识别")
                    return None

                # 2. 不匹配关键词，交由系统 IMDB 识别
                _filtered_kwargs = {k: v for k, v in kwargs.items()
                                   if k in ("share_meta",)}
                result = await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                      episode_group, cache, **_filtered_kwargs)
                if result:
                    return result

                # 3. 系统识别也失败，最后由 metatube 兜底处理
                logger.info(f"系统异步识别失败，通过插件 {MetatubeSource.plugin_name} 兜底执行：async_recognize_media ...")
                return await plugin_instance.async_recognize_media(meta, mtype)

            # 插件未启用，直接调用原始方法
            _filtered_kwargs = {k: v for k, v in kwargs.items()
                               if k in ("share_meta",)}
            return await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                episode_group, cache, **_filtered_kwargs)

        # 给 patch 函数加唯一标记
        setattr(patched_recognize_media, '_patched_by', id(self))
        setattr(patched_async_recognize_media, '_patched_by', id(self))

        # 保存原始方法
        if not getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self):
            self._original_method = getattr(ChainBase, "recognize_media", None)
        if not getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self):
            self._original_async_method = getattr(ChainBase, "async_recognize_media", None)

        # 初始化日志队列
        if self._log_entries is None:
            self._log_entries = deque(maxlen=self._max_logs)

        if config:
            self._enabled = bool(config.get("enabled"))
            self._api_url = config.get("api_url") or "http://127.0.0.1:8080"
            self._timeout = int(config.get("timeout") or 30)
            self._max_logs = int(config.get("max_logs") or 100)
            self._custom_japanese_keywords = config.get("custom_japanese_keywords") or ""
            self._custom_western_keywords = config.get("custom_western_keywords") or ""
            self._custom_chinese_keywords = config.get("custom_chinese_keywords") or ""
            self._custom_other_keywords = config.get("custom_other_keywords") or ""
            self._strict_match = bool(config.get("strict_match") or False)
            # 识别失败控制（兼容旧配置名 keyword_failed_download）
            failed_download_config = config.get("failed_download_control")
            if failed_download_config is None:
                failed_download_config = config.get("keyword_failed_download", True)
            self._failed_download_control = bool(failed_download_config)
            self._show_failure_detail = bool(config.get("show_failure_detail") if config.get("show_failure_detail") is not None else True)
            self._clear_logs_flag = bool(config.get("clear_logs_flag") or False)
            # 命名规则配置
            self._naming_template = config.get("naming_template") or "number_actor_studio"
            self._custom_naming_template = config.get("custom_naming_template") or ""
            self._max_actors = int(config.get("max_actors") or 2)
            # ThePornDB 配置
            self._theporndb_enabled = bool(config.get("theporndb_enabled") or False)
            self._theporndb_api_token = config.get("theporndb_api_token") or ""
            # ByteMuse 配置
            self._bytemuse_enabled = bool(config.get("bytemuse_enabled") or False)
            self._bytemuse_url = config.get("bytemuse_url") or "http://127.0.0.1:3750"
            self._bytemuse_username = config.get("bytemuse_username") or ""
            self._bytemuse_password = config.get("bytemuse_password") or ""
            # JavBus 配置
            self._javbus_enabled = bool(config.get("javbus_enabled") or False)
            self._javbus_api_url = config.get("javbus_api_url") or "http://10.0.0.1:8922"
            # JAV 配置
            self._jav_number_auto_match = bool(config.get("jav_number_auto_match") or True)
            # 搜索数据源配置
            self._search_enabled = bool(config.get("search_enabled") or False)
            # 小文件配置
            self._skip_small_files = bool(config.get("skip_small_files") or False)
            self._small_file_threshold = int(config.get("small_file_threshold") or 100)
            # 新增配置项
            self._exclude_keywords = config.get("exclude_keywords") or ""
            self._keywords_file_path = "keywords.json"  # 固定路径，不再提供配置

            # 更新日志队列大小
            if self._log_entries and self._log_entries.maxlen != self._max_logs:
                old_logs = list(self._log_entries)
                self._log_entries = deque(old_logs[-self._max_logs:], maxlen=self._max_logs)

            # 检查是否需要清空日志（配置开关触发）
            if self._clear_logs_flag:
                if self._log_entries:
                    self._log_entries.clear()
                logger.info("Metatube: 识别日志已清空")
                self._clear_logs_flag = False

            self._update_config()

        # 初始化API客户端
        self._metatube_client = MetatubeApiClient(
            base_url=self._api_url,
            timeout=self._timeout
        )

        # 初始化 ThePornDB 客户端
        self._theporndb_client = ThePornDBApiClient(
            api_token=self._theporndb_api_token,
            timeout=self._timeout
        )

        # 初始化 ByteMuse 客户端（使用账号密码认证）
        self._bytemuse_client = ByteMuseApiClient(
            base_url=self._bytemuse_url,
            username=self._bytemuse_username,
            password=self._bytemuse_password,
            timeout=self._timeout
        )

        # 初始化 JavBus 客户端
        self._javbus_client = JavBusApiClient(
            base_url=self._javbus_api_url,
            timeout=self._timeout
        )

        # 验证配置有效性
        self._validate_config()

        # 加载关键字文件（如果存在）
        self._load_keywords_from_file()


        # Precompile keyword regex patterns for performance
        self._precompiled_keywords = self._build_precompiled_keywords()

        if self._enabled:
            # 关键字优先模式：匹配关键词直接由 metatube 处理，不匹配则系统识别
            if not (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self)):
                ChainBase.recognize_media = patched_recognize_media
            if not (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self)):
                ChainBase.async_recognize_media = patched_async_recognize_media
        else:
            self.stop_service()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取插件API"""
        return [
            {
                "path": "/logs",
                "endpoint": self.get_logs,
                "methods": ["GET"],
                "summary": "获取识别日志",
                "description": "获取 Metatube 识别日志",
            },
            {
                "path": "/clear_logs",
                "endpoint": self.clear_logs,
                "methods": ["POST"],
                "summary": "清空识别日志",
                "description": "清空 Metatube 识别日志",
            },
            {
                "path": "/test_connection",
                "endpoint": self.test_connection,
                "methods": ["GET"],
                "summary": "测试API连接",
                "description": "测试 Metatube API 连接状态",
            },
            {
                "path": "/search",
                "endpoint": self.media_search,
                "methods": ["GET"],
                "summary": "搜索番号",
                "description": "通过 Metatube API 搜索番号（探索数据源）",
            },
            {
                "path": "/search_detail",
                "endpoint": self.search_detail,
                "methods": ["GET"],
                "summary": "搜索番号详情",
                "description": "根据 provider 和 id 获取番号详情",
            },
        ]

    def get_logs(self) -> List[Dict[str, Any]]:
        """获取识别日志"""
        if self._log_entries:
            return [log.model_dump() for log in list(self._log_entries)]
        return []

    def clear_logs(self) -> Dict[str, Any]:
        """清空识别日志"""
        if self._log_entries:
            self._log_entries.clear()
        logger.info("Metatube: 识别日志已清空")
        return {"success": True, "message": "日志已清空"}

    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        if self._metatube_client and self._metatube_client.test_connection():
            return {"success": True, "message": "连接成功"}
        return {"success": False, "message": "连接失败"}

    def media_search(self, title: str = "", page: int = 1, count: int = 20) -> List[MediaInfo]:
        """
        搜索番号（探索数据源API）

        :param title: 搜索关键词
        :param page: 页码
        :param count: 每页数量
        :return: 媒体信息列表
        """
        if not self._enabled or not self._search_enabled:
            return []

        if not title:
            return []

        # 过滤太短的搜索词（减少无效请求）
        if len(title.strip()) < 2:
            logger.debug(f"Metatube: 搜索关键词过短，跳过搜索: '{title}'")
            return []

        # 搜索频率限制（避免前端自动完成造成的大量请求）
        if not self._rate_limiter.acquire():
            wait_time = self._rate_limiter.get_wait_time()
            logger.debug(f"Metatube: 搜索频率过高，跳过搜索: '{title}' (需等待 {wait_time:.2f}s)")
            return []

        try:
            results = self._metatube_client.search(title)
            if not results:
                return []

            # 计算分页
            start_idx = (page - 1) * count
            end_idx = start_idx + count
            paged_results = results[start_idx:end_idx]

            # 转换为 MediaInfo 并去重
            media_list = []
            seen_ids = set()  # 用于去重
            for movie in paged_results:
                media = self._convert_metatube_search_to_mediainfo(movie)
                if media:
                    # 使用 media_id 去重
                    media_id = media.media_id or ""
                    if media_id and media_id in seen_ids:
                        logger.debug(f"Metatube 跳过重复结果: {media_id}")
                        continue
                    if media_id:
                        seen_ids.add(media_id)
                    media_list.append(media)

            logger.info(f"Metatube 搜索成功: {title}, 返回 {len(media_list)} 条结果")
            return media_list

        except Exception as e:
            logger.error(f"Metatube 搜索失败: {str(e)}")
            return []

    def search_detail(self, provider: str = "", movie_id: str = "") -> Optional[MediaInfo]:
        """
        获取番号详情（探索数据源API）

        :param provider: 数据来源
        :param movie_id: 电影ID
        :return: 媒体信息
        """
        if not self._enabled or not self._search_enabled:
            return None

        if not provider or not movie_id:
            return None

        try:
            detail = self._metatube_client.get_detail(provider, movie_id)
            if not detail:
                return None

            # 转换为 MediaInfo（使用详情数据）
            return self._convert_metatube_detail_to_mediainfo(detail)

        except Exception as e:
            logger.error(f"Metatube 获取详情失败: {str(e)}")
            return None

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
        return [
            {
                "component": "VForm",
                "content": [
                    # ==================== 功能开关 ====================
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2 mt-4"},
                                        "text": "⚙️ 功能开关"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                            "hint": "开启后将自动识别番号媒体"
                                        },
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "strict_match",
                                            "label": "严格匹配",
                                            "hint": "区分大小写和全半角"
                                        },
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "show_failure_detail",
                                            "label": "显示失败详情",
                                            "hint": "在日志中显示详细失败原因"
                                        },
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "failed_download_control",
                                            "label": "失败自动下载",
                                            "hint": "识别失败时归类并自动下载"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "jav_number_auto_match",
                                            "label": "JAV番号自动匹配",
                                            "hint": "自动检测JAV番号格式"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "search_enabled",
                                            "label": "搜索数据源",
                                            "hint": "在探索页面提供搜索功能"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "theporndb_enabled",
                                            "label": "启用ThePornDB",
                                            "hint": "欧美系内容使用ThePornDB识别"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "bytemuse_enabled",
                                            "label": "启用ByteMuse",
                                            "hint": "启用ByteMuse作为主要识别源"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "javbus_enabled",
                                            "label": "启用JavBus",
                                            "hint": "通过javbus-api识别番号媒体信息"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "clear_logs_flag",
                                            "label": "清空识别记录",
                                            "hint": "保存后清空所有识别日志记录"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # ==================== 基础设置 ====================
                    {
                        "component": "VDivider",
                        "props": {"class": "my-4"}
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2"},
                                        "text": "🔧 基础设置"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "api_url",
                                            "label": "Metatube API地址",
                                            "placeholder": "http://127.0.0.1:8080",
                                            "hint": "Metatube服务地址",
                                            "prepend-icon": "mdi-server"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "theporndb_api_token",
                                            "label": "ThePornDB API Token",
                                            "placeholder": "从 https://theporndb.net 获取",
                                            "hint": "登录后在设置页面获取 Metadata API Token",
                                            "prepend-icon": "mdi-key"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "bytemuse_url",
                                            "label": "ByteMuse API地址",
                                            "placeholder": "http://127.0.0.1:3750",
                                            "hint": "ByteMuse服务地址",
                                            "prepend-icon": "mdi-server-network"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "bytemuse_username",
                                            "label": "ByteMuse 用户名",
                                            "placeholder": "请输入用户名",
                                            "hint": "ByteMuse登录用户名",
                                            "prepend-icon": "mdi-account"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "bytemuse_password",
                                            "label": "ByteMuse 密码",
                                            "placeholder": "请输入密码",
                                            "hint": "ByteMuse登录密码",
                                            "type": "password",
                                            "prepend-icon": "mdi-lock"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "javbus_api_url",
                                            "label": "JavBus API地址",
                                            "placeholder": "http://10.0.0.1:8922",
                                            "hint": "javbus-api服务地址（ovnrain/javbus-api）",
                                            "prepend-icon": "mdi-server-network"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "timeout",
                                            "label": "API超时时间",
                                            "type": "number",
                                            "placeholder": "30",
                                            "suffix": "秒",
                                            "hint": "API请求超时时间（1-60秒）",
                                            "prepend-icon": "mdi-clock-outline"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "max_logs",
                                            "label": "日志记录数",
                                            "type": "number",
                                            "placeholder": "100",
                                            "hint": "最多保留的识别日志条数",
                                            "prepend-icon": "mdi-format-list-bulleted"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # ==================== 文件过滤设置 ====================
                    {
                        "component": "VDivider",
                        "props": {"class": "my-4"}
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2"},
                                        "text": "📁 文件过滤设置"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "skip_small_files",
                                            "label": "跳过小文件",
                                            "hint": "跳过小于指定大小的文件识别"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "small_file_threshold",
                                            "label": "小文件阈值",
                                            "placeholder": "100",
                                            "suffix": "MB",
                                            "hint": "小于此大小的文件将被跳过",
                                            "type": "number",
                                            "prepend-icon": "mdi-file-outline"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": []
                            }
                        ]
                    },
                    # ==================== 命名规则配置 ====================
                    {
                        "component": "VDivider",
                        "props": {"class": "my-4"}
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2"},
                                        "text": "📝 命名规则配置"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "naming_template",
                                            "label": "命名模板",
                                            "items": [
                                                {"title": "番号 演员 [片商]", "value": "number_actor_studio"},
                                                {"title": "番号 演员", "value": "number_actor"},
                                                {"title": "番号 [片商] 演员", "value": "number_studio_actor"},
                                                {"title": "仅番号", "value": "number_only"},
                                                {"title": "番号 (年份)", "value": "number_year"},
                                                {"title": "番号 演员 (年份)", "value": "number_actor_year"},
                                                {"title": "完整格式", "value": "full"},
                                                {"title": "自定义模板", "value": "custom"}
                                            ],
                                            "hint": "选择文件重命名格式",
                                            "prepend-icon": "mdi-rename-box"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 2},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "max_actors",
                                            "label": "演员数量",
                                            "type": "number",
                                            "placeholder": "2",
                                            "hint": "最多显示几位演员",
                                            "prepend-icon": "mdi-account-multiple"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "custom_naming_template",
                                            "label": "自定义模板",
                                            "placeholder": "{number} {actor} [{studio}] ({year})",
                                            "hint": "变量: {number} {actor} {studio} {label} {year} {series} {title}",
                                            "prepend-icon": "mdi-code-braces"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-h6 mb-2"},
                                        "text": "🔑 关键词配置（按分类管理）"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_japanese_keywords",
                                            "label": "🇯🇵 日系关键词",
                                            "placeholder": "SSIS, FC2, HEYZO...",
                                            "rows": 2,
                                            "hint": "日系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_western_keywords",
                                            "label": "🇺🇸 欧美系关键词",
                                            "placeholder": "BRAZZERS, BLACKED, TUSHY...",
                                            "rows": 2,
                                            "hint": "欧美系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_chinese_keywords",
                                            "label": "🇨🇳 中文系关键词",
                                            "placeholder": "MD, 约炮, 探花...",
                                            "rows": 2,
                                            "hint": "中文系内容识别关键词，逗号分隔"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "custom_other_keywords",
                                            "label": "📦 其他关键词",
                                            "placeholder": "高清, 无码, 有码...",
                                            "rows": 2,
                                            "hint": "其他通用特征关键词，逗号分隔"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "exclude_keywords",
                                            "label": "🚫 排除关键词（匹配后直接跳过）",
                                            "placeholder": "4K, UHD, HDR, FHD, HD, 2160P, 1080P, 720P, 60FPS, H.265, H.264, HEVC, XVID, WEB-DL, REMUX, BLURAY...",
                                            "rows": 3,
                                            "hint": "匹配后直接跳过分类的关键词（画质标记、分辨率、编码格式等），逗号分隔。内置排除关键字已包含常见画质和技术标记"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "title": "使用说明"
                                        },
                                        "content": [
                                            {
                                                "component": "div",
                                                "content": [
                                                    {
                                                        "component": "p",
                                                        "text": "• 工作模式：关键字优先模式，匹配关键字直接使用 Metatube 识别，不匹配则系统识别"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 欧美系专用：启用 ThePornDB 后，匹配欧美系关键字的内容将使用 ThePornDB 识别"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 自动分类：Metatube 识别成功固定为「成人/日系」；识别失败根据关键字匹配归类，未匹配则归类为「成人/其他」"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 排除关键字：配置排除关键字后，匹配到的内容将跳过分类"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 关键字优先级：自定义(UI) > 内置 > keywords.json文件"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 失败控制：识别失败时可选择自动归类并下载，或终止流程"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "api_url": "http://127.0.0.1:8080",
            "timeout": 30,
            "max_logs": 100,
            "custom_japanese_keywords": "",
            "custom_western_keywords": "",
            "custom_chinese_keywords": "",
            "custom_other_keywords": "",
            "exclude_keywords": "",
            "strict_match": False,
            "failed_download_control": True,
            "keyword_failed_download": True,  # 兼容旧配置
            "show_failure_detail": True,
            "clear_logs_flag": False,
            "naming_template": "number_actor_year",
            "custom_naming_template": "",
            "max_actors": 2,
            "theporndb_enabled": False,
            "theporndb_api_token": "",
            "bytemuse_enabled": False,
            "bytemuse_url": "http://127.0.0.1:3750",
            "javbus_enabled": False,
            "javbus_api_url": "http://10.0.0.1:8922",
            "jav_number_auto_match": True
        }

    def get_page(self) -> List[dict]:
        """插件详情页面 - 日志查看"""
        # 获取当前日志
        logs_data = self.get_logs()

        return [
            {
                "component": "VCard",
                "props": {"class": "mb-4"},
                "content": [
                    {
                        "component": "VCardTitle",
                        "text": "识别记录"
                    },
                    {
                        "component": "VCardText",
                        "content": [
                            {
                                "component": "VTable",
                                "props": {
                                    "hover": True,
                                    "density": "compact"
                                },
                                "content": [
                                    {
                                        "component": "thead",
                                        "content": [
                                            {
                                                "component": "tr",
                                                "content": [
                                                    {"component": "th", "text": "时间"},
                                                    {"component": "th", "text": "关键词"},
                                                    {"component": "th", "text": "结果"},
                                                    {"component": "th", "text": "分类"},
                                                    {"component": "th", "text": "状态"},
                                                    {"component": "th", "text": "详情"}
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "tbody",
                                        "content": self._build_log_rows()
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def _build_log_rows(self) -> List[dict]:
        """构建日志表格行"""
        rows = []
        if self._log_entries:
            for log in reversed(list(self._log_entries)):
                # 状态颜色：success=绿色, fallback=橙色, failed=红色
                if log.status == "success":
                    status_color = "success"
                elif log.status == "fallback":
                    status_color = "warning"
                else:
                    status_color = "error"

                # 分类颜色
                category_color = "primary"
                if "日系" in log.category:
                    category_color = "pink"
                elif "欧美" in log.category:
                    category_color = "blue"
                elif "中文" in log.category:
                    category_color = "orange"
                rows.append({
                    "component": "tr",
                    "content": [
                        {"component": "td", "text": log.timestamp},
                        {"component": "td", "text": log.keyword},
                        {"component": "td", "text": log.result[:30] + "..." if len(log.result) > 30 else log.result},
                        {
                            "component": "td",
                            "content": [
                                {
                                    "component": "VChip",
                                    "props": {"color": category_color, "size": "x-small", "variant": "tonal"},
                                    "text": log.category or "-"
                                }
                            ]
                        },
                        {
                            "component": "td",
                            "content": [
                                {
                                    "component": "VChip",
                                    "props": {"color": status_color, "size": "x-small"},
                                    "text": log.status
                                }
                            ]
                        },
                        {"component": "td", "text": log.message[:50] + "..." if len(log.message) > 50 else log.message}
                    ]
                })
        if not rows:
            rows.append({
                "component": "tr",
                "content": [
                    {
                        "component": "td",
                        "props": {"colspan": 5, "class": "text-center text-disabled"},
                        "text": "暂无识别日志"
                    }
                ]
            })
        return rows

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        注册搜索探索源事件
        """
        if not self._search_enabled:
            return

        event_data: DiscoverSourceEventData = event.event_data

        # 检查是否已经注册过此探索源（避免重复注册）
        if event_data.extra_sources:
            for source in event_data.extra_sources:
                # 避免重复注册相同 mediaid_prefix
                if source.mediaid_prefix == "metatube_search":
                    logger.debug("Metatube 搜索探索源已存在，跳过注册")
                    return

        search_source = DiscoverMediaSource(
            name="Metatube 搜索",
            mediaid_prefix="metatube_search",
            api_path=f"plugin/MetatubeSource/search?apikey={settings.API_TOKEN}",
            filter_params={
                "title": "",
                "page": 1,
                "count": 20,
            },
            filter_ui=[
                {
                    "component": "VTextField",
                    "props": {
                        "model": "title",
                        "label": "番号",
                        "placeholder": "请输入番号，如 SSIS-001",
                        "variant": "outlined",
                        "density": "compact",
                        "clearable": True,
                        "hide-details": True,
                    }
                },
            ],
        )

        if not event_data.extra_sources:
            event_data.extra_sources = [search_source]
        else:
            event_data.extra_sources.append(search_source)

        logger.info("Metatube 搜索探索源已注册")

    def stop_service(self):
        """退出插件"""
        if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                self._original_method):
            ChainBase.recognize_media = self._original_method
        if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                self._original_async_method):
            ChainBase.async_recognize_media = self._original_async_method


    def get_module(self) -> Dict[str, Any]:
        """
        获取插件模块声明，用于劫持系统模块实现

        通过模块系统注册识别方法，确保插件能正确拦截识别流程
        """
        if self._enabled:
            return {
                'recognize_media': self._module_recognize_media,
                'async_recognize_media': self._module_async_recognize_media
            }
        return {}

    def _module_recognize_media(self, meta: MetaBase = None,
                                 mtype: Optional[MediaType] = None,
                                 tmdbid: Optional[int] = None,
                                 doubanid: Optional[str] = None,
                                 bangumiid: Optional[int] = None,
                                 episode_group: Optional[str] = None,
                                 cache: bool = True) -> Optional[MediaInfo]:
        """
        模块劫持识别方法（关键字优先模式）

        优先级：
        1. 匹配 metatube 关键词 → 直接由 metatube 处理（忽略外部ID，避免成人内容被误识别）
        2. 不匹配关键词 + 有外部ID → 返回 None，交由系统处理
        3. 不匹配关键词 + 无外部ID → 由 metatube 尝试处理，失败则返回 None 让系统继续
        """
        if not self._enabled:
            return None

        # 1. 优先检查是否匹配 metatube 关键词（关键词匹配优先于外部ID检查）
        # 原因：成人内容通常没有正确的TMDB/豆瓣/Bangumi ID，即使有也可能是误匹配
        if self._match_keywords(meta):
            logger.info(f"通过插件 {MetatubeSource.plugin_name} 模块劫持，关键词匹配，执行：recognize_media ...")
            if tmdbid or doubanid or bangumiid:
                logger.debug(f"Metatube: 关键词匹配，忽略外部ID (tmdbid={tmdbid}, doubanid={doubanid}, bangumiid={bangumiid})")
            result = self.recognize_media(meta, mtype)
            if result:
                return result
            # metatube 识别失败，关键词匹配内容不回退系统识别
            logger.debug(f"Metatube 模块识别失败，关键词匹配内容不回退系统识别")
            return None

        # 2. 不匹配关键词，如果有外部 ID，交由系统处理
        if tmdbid or doubanid or bangumiid:
            return None

        # 3. 不匹配关键词且无外部ID，由 metatube 尝试处理
        # 原因：可能是未被关键词覆盖的成人内容，尝试用 metatube 识别
        logger.info(f"通过插件 {MetatubeSource.plugin_name} 模块劫持，无外部ID，尝试 metatube 识别 ...")
        result = self.recognize_media(meta, mtype)
        if result:
            return result
        # metatube 识别失败，返回 None 让系统继续处理
        logger.debug(f"Metatube 无外部ID识别失败，交由系统继续处理")
        return None

    async def _module_async_recognize_media(self, meta: MetaBase = None,
                                             mtype: Optional[MediaType] = None,
                                             tmdbid: Optional[int] = None,
                                             doubanid: Optional[str] = None,
                                             bangumiid: Optional[int] = None,
                                             episode_group: Optional[str] = None,
                                             cache: bool = True) -> Optional[MediaInfo]:
        """
        异步模块劫持识别方法（关键字优先模式）

        优先级：
        1. 匹配 metatube 关键词 → 直接由 metatube 处理（忽略外部ID，避免成人内容被误识别）
        2. 不匹配关键词 + 有外部ID → 返回 None，交由系统处理
        3. 不匹配关键词 + 无外部ID → 由 metatube 尝试处理，失败则返回 None 让系统继续
        """
        if not self._enabled:
            return None

        # 1. 优先检查是否匹配 metatube 关键词（关键词匹配优先于外部ID检查）
        # 原因：成人内容通常没有正确的TMDB/豆瓣/Bangumi ID，即使有也可能是误匹配
        if self._match_keywords(meta):
            logger.info(f"通过插件 {MetatubeSource.plugin_name} 模块劫持，关键词匹配，执行：async_recognize_media ...")
            if tmdbid or doubanid or bangumiid:
                logger.debug(f"Metatube: 关键词匹配，忽略外部ID (tmdbid={tmdbid}, doubanid={doubanid}, bangumiid={bangumiid})")
            result = await self.async_recognize_media(meta, mtype)
            if result:
                return result
            # metatube 识别失败，关键词匹配内容不回退系统识别
            logger.debug(f"Metatube 异步模块识别失败，关键词匹配内容不回退系统识别")
            return None

        # 2. 不匹配关键词，如果有外部 ID，交由系统处理
        if tmdbid or doubanid or bangumiid:
            return None

        # 3. 不匹配关键词且无外部ID，由 metatube 尝试处理
        # 原因：可能是未被关键词覆盖的成人内容，尝试用 metatube 识别
        logger.info(f"通过插件 {MetatubeSource.plugin_name} 模块劫持，无外部ID，尝试 metatube 异步识别 ...")
        result = await self.async_recognize_media(meta, mtype)
        if result:
            return result
        # metatube 识别失败，返回 None 让系统继续处理
        logger.debug(f"Metatube 无外部ID异步识别失败，交由系统继续处理")
        return None

    def _validate_config(self) -> bool:
        """验证配置有效性"""
        validated = True

        # 验证超时时间
        if self._timeout < 1 or self._timeout > 300:
            logger.warning(f"Metatube: timeout 超出范围(1-300): {self._timeout}，已自动调整为30秒")
            self._timeout = 30
            validated = False

        # 验证最大演员数
        if self._max_actors < 1:
            logger.warning(f"Metatube: max_actors 必须大于0: {self._max_actors}，已自动调整为1")
            self._max_actors = 1
            validated = False

        # 验证 API URL 格式
        if self._api_url and not self._api_url.startswith(('http://', 'https://')):
            logger.error(f"Metatube: API URL 格式错误: {self._api_url}，已使用默认值")
            self._api_url = "http://127.0.0.1:8080"
            validated = False

        # 验证 ThePornDB Token
        if self._theporndb_enabled and not self._theporndb_api_token:
            logger.warning("Metatube: ThePornDB 已启用但未配置 API Token")

        return validated

    def _load_keywords_from_file(self):
        """从 keywords.json 文件加载扩展关键字（最低优先级）"""
        try:
            import json
            from pathlib import Path

            # 支持相对路径和绝对路径
            keywords_file = Path(self._keywords_file_path)
            if not keywords_file.is_absolute():
                # 相对于插件根目录
                plugin_dir = Path(__file__).parent
                keywords_file = plugin_dir / self._keywords_file_path

            # 检查文件是否存在
            if not keywords_file.exists():
                logger.debug(f"Metatube: 关键字配置文件不存在: {keywords_file}，仅使用内置核心关键字")
                self._file_keywords = {}
                self._file_keywords_loaded = False
                return

            # 读取 JSON 文件
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords_config = json.load(f)

            # 解析各分类扩展关键字（最低优先级）
            self._file_keywords = {}
            if isinstance(keywords_config, dict) and "categories" in keywords_config:
                categories = keywords_config["categories"]
                if isinstance(categories, dict):
                    for category_key, category_data in categories.items():
                        # 支持两种格式:
                        # 1. 直接数组格式: {"japanese": [...]}
                        # 2. 嵌套格式: {"japanese": {"keywords": [...], "name": "..."}}
                        if isinstance(category_data, list):
                            # 直接数组格式
                            self._file_keywords[category_key] = category_data
                            logger.info(f"Metatube: 从文件加载 {len(category_data)} 个「{category_key}」扩展关键字（最低优先级）")
                        elif isinstance(category_data, dict) and "keywords" in category_data:
                            # 嵌套格式
                            self._file_keywords[category_key] = category_data["keywords"]
                            logger.info(f"Metatube: 从文件加载 {len(category_data['keywords'])} 个「{category_data.get('name', category_key)}」扩展关键字（最低优先级）")

            self._file_keywords_loaded = True
            logger.info(f"Metatube: ✓ 从 {keywords_file.name} 加载扩展关键字成功（最低优先级）")

        except json.JSONDecodeError as e:
            logger.error(f"Metatube: 关键字配置文件 JSON 格式错误: {str(e)}")
            self._file_keywords = {}
            self._file_keywords_loaded = False
        except FileNotFoundError:
            logger.debug(f"Metatube: 关键字配置文件不存在: {self._keywords_file_path}，仅使用内置核心关键字")
            self._file_keywords = {}
            self._file_keywords_loaded = False
        except Exception as e:
            logger.error(f"Metatube: 加载关键字配置文件失败: {str(e)}")
            self._file_keywords = {}
            self._file_keywords_loaded = False


    def _build_precompiled_keywords(self) -> dict:
        """
        Precompile all keyword regex patterns for fast matching.
        Returns dict mapping keyword -> compiled regex or None (for substring match).
        """
        compiled = {}
        all_kw_lists = [
            (self.BUILT_IN_JAPANESE_KEYWORDS, 'japanese'),
            (self.BUILT_IN_WESTERN_KEYWORDS, 'western'),
            (self.BUILT_IN_CHINESE_KEYWORDS, 'chinese'),
            (self.BUILT_IN_OTHER_KEYWORDS, 'other'),
        ]
        # Add file keywords
        if self._file_keywords:
            for cat_key, cat_list in self._file_keywords.items():
                filtered = self._filter_keywords(cat_list) if isinstance(cat_list, list) else []
                all_kw_lists.append((filtered, cat_key))
        
        for keywords, _ in all_kw_lists:
            for kw in keywords:
                kw_upper = kw.upper() if not self._strict_match else kw
                if len(kw_upper) <= 3:
                    try:
                        compiled[kw_upper] = re.compile(r'\b' + re.escape(kw_upper) + r'\b')
                    except re.error:
                        compiled[kw_upper] = None
                else:
                    compiled[kw_upper] = None  # None = use substring match

        # Also add custom keywords
        for custom_str in [self._custom_japanese_keywords, self._custom_western_keywords,
                           self._custom_chinese_keywords, self._custom_other_keywords]:
            if custom_str:
                for kw in custom_str.split(','):
                    kw = kw.strip().upper() if not self._strict_match else kw.strip()
                    if not kw:
                        continue
                    if len(kw) <= 3:
                        try:
                            compiled[kw] = re.compile(r'\b' + re.escape(kw) + r'\b')
                        except re.error:
                            compiled[kw] = None
                    else:
                        compiled[kw] = None

        # Precompile exclude keywords
        self._precompiled_exclude = []
        for kw in self.BUILT_IN_EXCLUDE_KEYWORDS:
            if len(kw) > 2:
                kw_upper = kw.upper() if not self._strict_match else kw
                self._precompiled_exclude.append(kw_upper)
        if self._exclude_keywords:
            for kw in self._exclude_keywords.split(','):
                kw = kw.strip()
                if len(kw) > 2:
                    kw_upper = kw.upper() if not self._strict_match else kw
                    self._precompiled_exclude.append(kw_upper)

        logger.debug(f"Metatube: Precompiled {len(compiled)} keyword patterns, {len(self._precompiled_exclude)} exclude patterns")
        return compiled

    def _build_category(self, subcategory: str) -> str:
        """构建分类字符串"""
        return f"{self.CATEGORY_PREFIX}/{subcategory}"

    def _get_file_size_mb(self, meta: MetaBase, kwargs: dict) -> Optional[float]:
        """
        获取文件大小（MB）

        :param meta: 元数据对象
        :param kwargs: 额外参数，可能包含文件路径
        :return: 文件大小（MB），如果无法获取则返回 None
        """
        try:
            # 尝试从 kwargs 中获取文件路径
            file_path = kwargs.get('path') or kwargs.get('file_path') or kwargs.get('filepath')

            if file_path:
                # 从文件路径获取大小
                from pathlib import Path
                path = Path(file_path)
                if path.exists() and path.is_file():
                    size_bytes = path.stat().st_size
                    size_mb = size_bytes / (1024 * 1024)  # 转换为 MB
                    return size_mb

            # 尝试从 meta 对象获取文件大小（如果有）
            if hasattr(meta, 'size') and meta.size:
                size_mb = meta.size / (1024 * 1024)
                return size_mb

            return None
        except Exception as e:
            logger.debug(f"Metatube: 获取文件大小失败 - {str(e)}")
            return None

    def _update_config(self):
        """更新配置"""
        self.update_config({
            "enabled": self._enabled,
            "api_url": self._api_url,
            "timeout": self._timeout,
            "max_logs": self._max_logs,
            "custom_japanese_keywords": self._custom_japanese_keywords,
            "custom_western_keywords": self._custom_western_keywords,
            "custom_chinese_keywords": self._custom_chinese_keywords,
            "custom_other_keywords": self._custom_other_keywords,
            "exclude_keywords": self._exclude_keywords,
            "strict_match": self._strict_match,
            "failed_download_control": self._failed_download_control,
            "keyword_failed_download": self._failed_download_control,  # 兼容旧配置名
            "show_failure_detail": self._show_failure_detail,
            "clear_logs_flag": self._clear_logs_flag,
            "naming_template": self._naming_template,
            "custom_naming_template": self._custom_naming_template,
            "max_actors": self._max_actors,
            "theporndb_enabled": self._theporndb_enabled,
            "theporndb_api_token": self._theporndb_api_token,
            "bytemuse_enabled": self._bytemuse_enabled,
            "bytemuse_url": self._bytemuse_url,
            "bytemuse_username": self._bytemuse_username,
            "bytemuse_password": self._bytemuse_password,
            "javbus_enabled": self._javbus_enabled,
            "javbus_api_url": self._javbus_api_url,
            "jav_number_auto_match": self._jav_number_auto_match,
            "search_enabled": self._search_enabled,
            "skip_small_files": self._skip_small_files,
            "small_file_threshold": self._small_file_threshold
        })

    @staticmethod
    def _filter_keywords(keywords: List[str]) -> List[str]:
        """
        过滤关键字列表，排除注释行和空行

        :param keywords: 原始关键字列表
        :return: 过滤后的关键字列表
        """
        filtered = []
        for kw in keywords:
            # 跳过注释行（以 #== 开头）
            if isinstance(kw, str) and kw.strip().startswith('#=='):
                continue
            # 跳过空行
            if not kw or not kw.strip():
                continue
            filtered.append(kw)
        return filtered

    def _match_keyword_in_text(self, keyword: str, search_text: str) -> bool:
        """
        安全的关键字匹配，对超短关键字（≤3字符）使用预编译词边界匹配
        """
        # Check precompiled cache first
        compiled = getattr(self, '_precompiled_keywords', None)
        if compiled and keyword in compiled:
            pattern = compiled[keyword]
            if pattern is not None:
                return pattern.search(search_text) is not None
            else:
                return keyword in search_text

        # Fallback for non-precompiled (shouldn't happen normally)
        kw_len = len(keyword)
        if kw_len <= 3:
            try:
                return re.search(r'\b' + re.escape(keyword) + r'\b', search_text) is not None
            except re.error:
                return keyword in search_text
        else:
            return keyword in search_text

    def _add_log(self, keyword: str, result: str, status: str, message: str, category: str = ""):
        """添加日志条目"""
        if self._log_entries is None:
            self._log_entries = deque(maxlen=self._max_logs)
        log_entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level="INFO" if status == "success" else "WARNING",
            keyword=keyword,
            result=result,
            category=category,
            status=status,
            message=message
        )
        self._log_entries.append(log_entry)

    def _handle_recognition_failure(self, number: str, title: str, failure_reason: str = "识别失败") -> Optional[MediaInfo]:
        """
        统一的识别失败处理方法

        :param number: 番号
        :param title: 原始标题（用于分类检测）
        :param failure_reason: 失败原因
        :return: 处理后的 MediaInfo 或 None
        """
        # 使用原始标题进行分类检测（修复：原异常流程错误使用 number）
        subcategory = self._detect_category_type(title)

        # 如果没有匹配到任何成人内容关键字，直接返回 None 让系统使用 IMDB/TMDB 识别
        # 这防止了普通电视剧/动画被错误归类为"成人/其他"
        if subcategory == self.SUBCATEGORY_OTHER:
            logger.info(f"Metatube: {failure_reason}，未匹配成人内容关键字，交由系统处理: {title}")
            return None

        # 未启用失败自动下载，直接返回 None
        if not self._failed_download_control:
            self._add_log(number, "", "failed", f"{failure_reason}，未启用失败自动下载", category="")
            return None

        category = self._build_category(subcategory)

        # 构建日志消息
        if subcategory == self.SUBCATEGORY_OTHER:
            log_msg = f"{failure_reason}，未匹配关键字，归类为成人/其他"
        else:
            log_msg = f"{failure_reason}，匹配{subcategory}关键字，归类为成人/{subcategory}"

        # 使用 "fallback" 状态表示识别失败但归类成功（修复：原代码先记录 failed 又记录 success）
        self._add_log(number, f"{category} ({number})", "fallback", log_msg, category=category)
        logger.info(f"Metatube: {log_msg} (番号: {number})")

        # 创建基础 MediaInfo，包含必要的字段以支持下载流程
        mediainfo = MediaInfo()
        mediainfo.source = 'metatube'
        mediainfo.type = MediaType.MOVIE
        mediainfo.title = number
        mediainfo.original_title = title or number  # 保留原始标题用于模糊搜索
        mediainfo.imdb_id = number  # 使用番号作为 IMDB ID
        mediainfo.tmdb_id = None
        mediainfo.tvdb_id = None
        mediainfo.douban_id = None
        mediainfo.bangumi_id = None
        mediainfo.year = None
        mediainfo.set_category(category)

        logger.debug(f"Metatube: 创建失败处理的 MediaInfo - title={mediainfo.title}, original_title={mediainfo.original_title}, category={category}")

        return mediainfo

    def _get_all_keywords(self) -> List[str]:
        """获取所有关键字（优先级: 自定义 > 内置核心 > keywords.json文件）"""
        keywords = []

        # 优先级 3: 添加从文件加载的扩展关键字（最低优先级）
        if self._file_keywords_loaded and self._file_keywords:
            for category_keywords in self._file_keywords.values():
                if isinstance(category_keywords, list):
                    # 过滤掉注释行
                    filtered_keywords = self._filter_keywords(category_keywords)
                    keywords.extend(filtered_keywords)

        # 优先级 2: 添加所有分类的内置核心关键字（中等优先级）
        keywords.extend(self.BUILT_IN_JAPANESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_WESTERN_KEYWORDS)
        keywords.extend(self.BUILT_IN_CHINESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_OTHER_KEYWORDS)

        # 优先级 1: 添加自定义关键字（最高优先级，会覆盖其他）
        custom_keywords = []
        if self._custom_japanese_keywords:
            custom_list = [kw.strip() for kw in self._custom_japanese_keywords.split(',') if kw.strip()]
            custom_keywords.extend(custom_list)
        if self._custom_western_keywords:
            custom_list = [kw.strip() for kw in self._custom_western_keywords.split(',') if kw.strip()]
            custom_keywords.extend(custom_list)
        if self._custom_chinese_keywords:
            custom_list = [kw.strip() for kw in self._custom_chinese_keywords.split(',') if kw.strip()]
            custom_keywords.extend(custom_list)
        if self._custom_other_keywords:
            custom_list = [kw.strip() for kw in self._custom_other_keywords.split(',') if kw.strip()]
            custom_keywords.extend(custom_list)

        # 合并所有关键字（去重）
        all_keywords = list(set(keywords + custom_keywords))

        return all_keywords

    def _get_exclude_keywords(self) -> List[str]:
        """获取排除关键字列表（内置 + 自定义），过滤短关键字避免误匹配"""
        exclude_keywords = []

        # 添加内置排除关键字（过滤单字母和双字母关键字）
        for kw in self.BUILT_IN_EXCLUDE_KEYWORDS:
            if len(kw) > 2:  # 仅保留长度 > 2 的关键字，避免误匹配 JAV 番号
                exclude_keywords.append(kw)

        # 添加自定义排除关键字（同样过滤短关键字）
        if self._exclude_keywords:
            custom_list = [kw.strip() for kw in self._exclude_keywords.split(',') if kw.strip()]
            custom_list = [kw for kw in custom_list if len(kw) > 2]  # 过滤短关键字
            exclude_keywords.extend(custom_list)

        # 标准化（非严格模式转大写）
        if not self._strict_match:
            exclude_keywords = [kw.upper() for kw in exclude_keywords]

        # 去重并返回
        return list(set(exclude_keywords))

    def _detect_category_type(self, title: str) -> str:
        """
        检测标题匹配的关键字类型，返回二级分类名称（优先级: 自定义 > 内置核心 > keywords.json文件）

        :param title: 标题文本
        :return: 二级分类名称：日系/欧美系/中文系/其他/__SKIP__（跳过识别）
        """
        if not title:
            return self.SUBCATEGORY_OTHER

        # === 内容类型预检 ===
        should_skip, skip_reason = self._should_skip_by_content_type(title)
        if should_skip:
            logger.debug(f"Metatube: 检测到{skip_reason}，跳过分类: {title}")
            return self.SUBCATEGORY_SKIP
        # === 内容类型预检结束 ===

        # 检查排除关键字
        exclude_keywords = self._get_exclude_keywords()
        if exclude_keywords:
            search_title = title.upper() if not self._strict_match else title
            for exclude_kw in exclude_keywords:
                if exclude_kw in search_title:
                    logger.debug(f"Metatube: 匹配到排除关键字 '{exclude_kw}'，跳过识别: {title}")
                    return self.SUBCATEGORY_SKIP  # 返回特殊标记，表示应该跳过

        # 标准化标题
        search_title = title
        if not self._strict_match:
            search_title = title.upper()
            search_title = search_title.replace('－', '-').replace('＿', '_')

        # 构建完整的分类关键字列表（按三级优先级）
        categories = [
            {
                "name": self.SUBCATEGORY_JAPANESE,
                "built_in": self.BUILT_IN_JAPANESE_KEYWORDS,
                "custom": self._custom_japanese_keywords,
                "file": self._file_keywords.get("japanese", []) if self._file_keywords else []
            },
            {
                "name": self.SUBCATEGORY_WESTERN,
                "built_in": self.BUILT_IN_WESTERN_KEYWORDS,
                "custom": self._custom_western_keywords,
                "file": self._file_keywords.get("western", []) if self._file_keywords else []
            },
            {
                "name": self.SUBCATEGORY_CHINESE,
                "built_in": self.BUILT_IN_CHINESE_KEYWORDS,
                "custom": self._custom_chinese_keywords,
                "file": self._file_keywords.get("chinese", []) if self._file_keywords else []
            },
            {
                "name": self.SUBCATEGORY_OTHER,
                "built_in": self.BUILT_IN_OTHER_KEYWORDS,
                "custom": self._custom_other_keywords,
                "file": self._file_keywords.get("other", []) if self._file_keywords else []
            },
        ]

        for category in categories:
            category_name = category["name"]

            # 优先级 1: 检查自定义关键字（最高优先级）
            if category["custom"]:
                custom_list = [kw.strip() for kw in category["custom"].split(',') if kw.strip()]
                for keyword in custom_list:
                    search_keyword = keyword.upper() if not self._strict_match else keyword
                    if self._match_keyword_in_text(search_keyword, search_title):
                        logger.debug(f"Metatube: 匹配到【自定义关键字】'{keyword}' → {category_name} (标题: {title})")
                        return category_name

            # 优先级 2: 检查内置核心关键字（中等优先级）
            for keyword in category["built_in"]:
                search_keyword = keyword.upper() if not self._strict_match else keyword
                if self._match_keyword_in_text(search_keyword, search_title):
                    logger.debug(f"Metatube: 匹配到【内置核心关键字】'{keyword}' → {category_name} (标题: {title})")
                    return category_name

            # 优先级 3: 检查 keywords.json 文件扩展关键字（最低优先级）
            if category["file"]:
                file_keywords = self._filter_keywords(category["file"])
                if isinstance(file_keywords, list):
                    for keyword in file_keywords:
                        search_keyword = keyword.upper() if not self._strict_match else keyword
                        if self._match_keyword_in_text(search_keyword, search_title):
                            logger.debug(f"Metatube: 匹配到【扩展关键字】'{keyword}' → {category_name} (标题: {title})")
                            return category_name

        return self.SUBCATEGORY_OTHER

    def _detect_content_type(self, title: str) -> str:
        """
        检测内容类型，优先于关键字匹配

        :param title: 标题文本
        :return: 内容类型: music/drama/variety/unknown
        """
        if not title:
            return "unknown"

        title_upper = title.upper()

        # 1. 音乐/演唱会检测
        music_indicators = [
            # 演唱会标识
            r'.*\bLIVE.*CONCERT\b.*',
            r'.*\bONEMAN.*LIVE\b.*',
            r'.*\bTOUR.*\d{4}\b.*',  # TOUR 2024
            r'.*\bFESTIVAL\b.*',

            # 音乐会相关中文
            r'.*演唱会.*',
            r'.*音乐会.*',
            r'.*现场表演.*',
            r'.*现场版.*',

            # 歌曲格式
            r'.*\bMV\b.*',
            r'.*\bMUSIC\s+VIDEO\b.*',
            r'.*\[.*?\]\s*LIVE\s*$',  # [歌名] LIVE

            # 艺术家 - 演唱模式
            r'.+演唱.*歌曲.*',
            r'.+\s+-\s+.+\s+\(\d{4}\)$',  # 艺术家 - 歌名 (年份)
        ]

        for pattern in music_indicators:
            if re.search(pattern, title_upper) or re.search(pattern, title):
                return "music"

        # 2. 短剧/网剧检测（支持全角括号）
        drama_indicators = [
            # SKIT 标识（最常见）— 不再要求在末尾，允许后面有标签
            r'-\s*SKIT\b',
            r'\bSKIT\b',

            # 集数格式（同时支持半角和全角括号）
            r'[（(]\d+\s*[集话部][）)]',
            r'第\s*\d+\s*[集话部]',
            r'\s+EP\d+\s*$',
            r'\s+E\d+\s*$',

            # 短剧标识
            r'.*短剧.*',
            r'.*网剧.*',
            r'.*小剧场.*',
            r'.*微电影.*',

            # 剧集特征
            r'.*续集.*',
            r'.*第.*季.*',
        ]

        for pattern in drama_indicators:
            if re.search(pattern, title):
                return "drama"

        # 3. 综艺/访谈检测
        if any(x in title_upper for x in ['VARIETY', 'TALK SHOW', 'TALKSHOW']):
            return "variety"
        if any(x in title for x in ['综艺', '访谈', '脱口秀']):
            return "variety"

        return "unknown"

    def _should_skip_by_content_type(self, title: str) -> tuple:
        """
        根据内容类型判断是否应该跳过识别

        :param title: 标题文本
        :return: (是否跳过, 跳过原因)
        """
        content_type = self._detect_content_type(title)

        if content_type == "music":
            return True, "音乐内容"
        if content_type == "drama":
            return True, "短剧/网剧"
        if content_type == "variety":
            return True, "综艺节目"

        return False, ""

    def _match_keywords(self, meta: MetaBase) -> bool:
        """
        检查元数据是否匹配关键字（优先级: 自定义 > 内置核心 > keywords.json文件）

        :param meta: 元数据对象
        :return: 是否匹配
        """
        if not meta:
            return False

        # 获取标题（优先级：原始名称 > 中文名 > 英文名）
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or ""
        if not title:
            return False

        # === 内容类型预检 ===
        should_skip, skip_reason = self._should_skip_by_content_type(title)
        if should_skip:
            logger.debug(f"Metatube: 检测到{skip_reason}，跳过关键字匹配: {title}")
            return False
        # === 内容类型预检结束 ===

        # 标准化标题
        if not self._strict_match:
            # 非严格模式：转大写，统一全半角
            title = title.upper()
            title = title.replace('－', '-').replace('＿', '_')

        # 获取排除关键字
        exclude_keywords = self._get_exclude_keywords()

        # 标准化排除关键字
        if not self._strict_match:
            exclude_keywords = [kw.upper() for kw in exclude_keywords]

        # 先检查排除关键字
        for exclude_kw in exclude_keywords:
            if exclude_kw in title:
                logger.debug(f"Metatube: 匹配到排除关键字 '{exclude_kw}'，跳过: {title}")
                return False

        # 按三级优先级检查关键字匹配（优先级从高到低）
        # 优先级 1: 自定义关键字（UI配置）- 最高优先级
        custom_keywords_list = []
        if self._custom_japanese_keywords:
            custom_list = [kw.strip() for kw in self._custom_japanese_keywords.split(',') if kw.strip()]
            custom_keywords_list.extend(custom_list)
        if self._custom_western_keywords:
            custom_list = [kw.strip() for kw in self._custom_western_keywords.split(',') if kw.strip()]
            custom_keywords_list.extend(custom_list)
        if self._custom_chinese_keywords:
            custom_list = [kw.strip() for kw in self._custom_chinese_keywords.split(',') if kw.strip()]
            custom_keywords_list.extend(custom_list)
        if self._custom_other_keywords:
            custom_list = [kw.strip() for kw in self._custom_other_keywords.split(',') if kw.strip()]
            custom_keywords_list.extend(custom_list)

        # 标准化自定义关键字
        if not self._strict_match:
            custom_keywords_list = [kw.upper() for kw in custom_keywords_list]

        # 检查自定义关键字
        for keyword in custom_keywords_list:
            if self._match_keyword_in_text(keyword, title):
                logger.info(f"Metatube: 匹配到【自定义关键字】'{keyword}' 在标题 '{title}' 中")
                return True

        # 优先级 2: 内置核心关键字 - 中等优先级
        built_in_keywords = []
        built_in_keywords.extend(self.BUILT_IN_JAPANESE_KEYWORDS)
        built_in_keywords.extend(self.BUILT_IN_WESTERN_KEYWORDS)
        built_in_keywords.extend(self.BUILT_IN_CHINESE_KEYWORDS)
        built_in_keywords.extend(self.BUILT_IN_OTHER_KEYWORDS)

        # 标准化内置关键字
        if not self._strict_match:
            built_in_keywords = [kw.upper() for kw in built_in_keywords]

        # 检查内置核心关键字
        for keyword in built_in_keywords:
            if self._match_keyword_in_text(keyword, title):
                logger.info(f"Metatube: 匹配到【内置核心关键字】'{keyword}' 在标题 '{title}' 中")
                return True

        # 优先级 3: keywords.json 文件扩展关键字 - 最低优先级
        if self._file_keywords_loaded and self._file_keywords:
            for category_keywords in self._file_keywords.values():
                if isinstance(category_keywords, list):
                    # 过滤掉注释行
                    file_keywords = self._filter_keywords(category_keywords)
                    # 标准化文件关键字
                    file_keywords_list = file_keywords if self._strict_match else [kw.upper() for kw in file_keywords]
                    for keyword in file_keywords_list:
                        if self._match_keyword_in_text(keyword, title):
                            logger.info(f"Metatube: 匹配到【扩展关键字】'{keyword}' 在标题 '{title}' 中")
                            return True

        return False

    def _extract_number_from_meta(self, meta: MetaBase, category: str = None) -> Optional[str]:
        """
        从元数据中提取番号

        :param meta: 元数据对象
        :param category: 内容分类（日系/欧美系/中文系/其他），用于选择不同的提取规则
        :return: 提取的番号
        """
        if not meta:
            return None

        # 优先从原始名称提取
        name = meta.org_string or meta.name or ""

        # 根据分类选择不同的提取方法
        if category == self.SUBCATEGORY_WESTERN:
            # 欧美系：使用欧美系专用提取规则
            number = self._extract_western_number(name)
        elif category == self.SUBCATEGORY_CHINESE:
            # 中文系：使用中文系专用提取规则
            number = self._extract_chinese_number(name)
        elif category == self.SUBCATEGORY_JAPANESE:
            # 日系：使用标准日系提取规则
            number = self._extract_japanese_number(name)
        else:
            # 其他/未知：使用通用提取规则
            number = MetatubeApiClient.extract_number(name)

        if number:
            return number

        # 尝试从中文名提取
        if meta.cn_name:
            if category == self.SUBCATEGORY_CHINESE:
                number = self._extract_chinese_number(meta.cn_name)
            else:
                number = MetatubeApiClient.extract_number(meta.cn_name)
            if number:
                return number

        # 尝试从英文名提取
        if meta.en_name:
            if category == self.SUBCATEGORY_WESTERN:
                number = self._extract_western_number(meta.en_name)
            else:
                number = MetatubeApiClient.extract_number(meta.en_name)
            if number:
                return number

        return None

    def _extract_japanese_number(self, filename: str) -> Optional[str]:
        """
        日系番号提取（标准JAV格式）

        支持格式:
        - 标准格式: SSIS-001, IPX-123, ABC-123
        - FC2格式: FC2-PPV-1234567
        - HEYZO格式: HEYZO-1234
        - 1Pondo/Carib格式: 123456-123
        """
        if not filename:
            return None

        # 使用标准提取方法
        return MetatubeApiClient.extract_number(filename)

    def _extract_western_number(self, filename: str) -> Optional[str]:
        """
        欧美系番号提取

        支持格式:
        - 网站名称: Brazzers, Blacked, Tushy, Vixen 等
        - 场景ID: scene-12345, video-12345
        - 日期格式: 2024-01-15-title
        - 通用格式: studio-title-performer
        """
        if not filename:
            return None

        import re
        name = filename.strip()

        # 欧美系特殊模式
        western_patterns = [
            # 场景ID格式: scene-12345, video-12345
            r'(scene|video|clip)[-_]?(\d{4,6})',
            # 日期格式: 2024-01-15 或 20240115
            r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})',
            # 网站专用格式
            r'(brazzers|blacked|tushy|vixen|deeper|slayed)[-_.](.+)',
            # 通用格式: 保留原始名称作为标识
            r'([a-z0-9]+[-_.][a-z0-9]+[-_.][a-z0-9]+)',
        ]

        for pattern in western_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                # 根据匹配结果构建番号
                groups = match.groups()
                if len(groups) >= 2:
                    return f"{groups[0].upper()}-{groups[1]}"
                elif len(groups) == 1:
                    return groups[0].upper()

        # 回退到通用提取
        return MetatubeApiClient.extract_number(filename)

    def _extract_chinese_number(self, filename: str) -> Optional[str]:
        """
        中文系番号提取

        支持格式:
        - 麻豆系列: MD-0001, MDX-0001, MDTV-0001
        - 精东系列: JD-001, JDX-001
        - 天美系列: TM-001, TMX-001
        - 蜜桃系列: PMC-001, PMCX-001
        - 91系列: 91CM-001
        - 探花/网红: 保留原始标题
        """
        if not filename:
            return None

        import re
        name = filename.upper().strip()

        # 中文系特殊模式
        chinese_patterns = [
            # 麻豆系列
            r'(MD|MDX|MDTV|MADOU)[-_]?(\d{3,5})',
            # 精东系列
            r'(JD|JDX|JINGDONG)[-_]?(\d{3,4})',
            # 天美系列
            r'(TM|TMX|TIANMEI)[-_]?(\d{3,4})',
            # 蜜桃系列
            r'(PMC|PMCX|PEACH)[-_]?(\d{3,4})',
            # 91系列
            r'(91CM|91)[-_]?(\d{3,4})',
            # 台湾系列
            r'(TW|TWX)[-_]?(\d{3,4})',
            # 通用国产格式
            r'([A-Z]{2,4})[-_]?(\d{3,5})',
        ]

        for pattern in chinese_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    prefix = groups[0].upper()
                    number = groups[1]
                    return f"{prefix}-{number}"

        # 回退到通用提取
        return MetatubeApiClient.extract_number(filename)

    def _build_optimized_title(self, number: str, actors: List[str] = None,
                                 studio: str = "", label: str = "", year: str = "",
                                 series: str = "", original_title: str = "") -> str:
        """
        基于模板构建优化的标题

        支持变量: {number} {actor} {studio} {label} {year} {title} {series}
        示例模板: "{number} {actor} [{studio}]" -> "SSIS-001 三上悠亚 [S1]"

        :param number: 番号（必须）
        :param actors: 演员列表
        :param studio: 制作商/片商
        :param label: 发行商
        :param year: 年份
        :param series: 系列
        :param original_title: 原始标题
        :return: 优化后的标题
        """
        # 获取模板
        template_key = self._naming_template or "number_actor_studio"
        if template_key == "custom" and self._custom_naming_template:
            template = self._custom_naming_template
        else:
            template = self.NAMING_TEMPLATES.get(template_key, self.NAMING_TEMPLATES["number_actor_studio"])

        # 准备变量值
        number_str = (number or "").upper().strip()

        # 处理演员列表
        actor_str = ""
        if actors and len(actors) > 0:
            valid_actors = [a.strip() for a in actors if a and a.strip()]
            if valid_actors:
                max_actors = self._max_actors or 2
                if len(valid_actors) <= max_actors:
                    actor_str = ", ".join(valid_actors)
                else:
                    actor_str = ", ".join(valid_actors[:max_actors]) + "…"

        # 片商：优先 studio，其次 label
        studio_str = (studio or "").strip() or (label or "").strip()
        label_str = (label or "").strip()
        year_str = (year or "").strip()
        series_str = (series or "").strip()
        title_str = (original_title or "").strip()

        # 替换模板变量
        result = template
        result = result.replace("{number}", number_str)
        result = result.replace("{actor}", actor_str)
        result = result.replace("{studio}", studio_str)
        result = result.replace("{label}", label_str)
        result = result.replace("{year}", year_str)
        result = result.replace("{series}", series_str)
        result = result.replace("{title}", title_str)

        # 清理空括号和多余空格
        result = re.sub(r'\[\s*\]', '', result)  # 移除空的 []
        result = re.sub(r'\(\s*\)', '', result)  # 移除空的 ()
        result = re.sub(r'\s+', ' ', result)     # 合并多余空格
        result = result.strip()

        # 兜底
        if not result:
            return number_str or title_str or "Unknown"

        return result

    def _convert_bytemuse_to_mediainfo(self, movie: ByteMuseMovie) -> MediaInfo:
        """将 ByteMuse 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'bytemuse'
        mediainfo.type = MediaType.MOVIE  # 番号内容通常作为电影处理

        # 解析年份
        year = ""
        if movie.release_date:
            try:
                date_str = movie.release_date.split('T')[0]
                year = date_str[:4]
            except Exception:
                pass

        # 处理演员列表：优先使用 actors，其次使用 casts (逗号分隔字符串)
        actors = []
        if movie.actors:
            actors = [actor.name for actor in movie.actors]
        elif movie.casts:
            # casts 是逗号分隔的字符串
            actors = [name.strip() for name in movie.casts.split(',') if name.strip()]

        # 处理制作商/发行商
        studio = movie.studio or movie.publisher or ""
        label = movie.label or movie.producer or ""

        # 构建优化标题（基于模板）
        optimized_title = self._build_optimized_title(
            number=movie.code,
            actors=actors,
            studio=studio,
            label=label,
            year=year,
            series=movie.series or "",
            original_title=movie.title
        )

        # 基础信息
        mediainfo.title = optimized_title
        mediainfo.original_title = movie.code

        # 解析发布日期获取年份
        if movie.release_date:
            try:
                date_str = movie.release_date.split('T')[0]
                mediainfo.year = date_str[:4]
                mediainfo.release_date = date_str
            except Exception:
                pass

        # 使用番号作为标识
        mediainfo.imdb_id = movie.code

        # 封面和海报
        if movie.cover_url:  # cover_url 别名为 banner (横幅/封面)
            mediainfo.poster_path = movie.cover_url
        if movie.poster_url:  # poster_url 别名为 poster (海报)
            mediainfo.poster_path = movie.poster_url
        if movie.preview_url:
            mediainfo.backdrop_path = movie.preview_url
        if movie.thumb_url:
            mediainfo.thumb_path = movie.thumb_url

        # 评分
        if movie.score:
            mediainfo.vote_average = round(float(movie.score), 1)

        # 演员
        if actors:
            mediainfo.actor = [{"name": name} for name in actors]

        # 概要
        if movie.summary:
            mediainfo.overview = movie.summary

        # 导演
        if movie.director:
            mediainfo.director = [{"name": movie.director}]

        # 类型标签 (genres 可能是字符串，需要分割)
        if movie.genres:
            if isinstance(movie.genres, str):
                genre_list = [g.strip() for g in movie.genres.split(',') if g.strip()]
            elif isinstance(movie.genres, list):
                genre_list = movie.genres
            else:
                genre_list = []
            mediainfo.genres = [{"id": g, "name": g} for g in genre_list]

        # 时长
        if movie.runtime:
            mediainfo.runtime = movie.runtime
        elif movie.duration:
            mediainfo.runtime = movie.duration // 60  # 转换为分钟

        # 制作商信息
        if studio:
            mediainfo.studio = studio
        if label:
            if hasattr(mediainfo, 'label'):
                mediainfo.label = label

        # 预览图 (still_photo 是逗号分隔的URL列表)
        if movie.still_photo:
            image_urls = [url.strip() for url in movie.still_photo.split(',') if url.strip()]
            if image_urls and hasattr(mediainfo, 'images'):
                mediainfo.images = image_urls

        return mediainfo

    def _convert_to_mediainfo(self, movie: MetatubeMovie, detail: Optional[MetatubeMovieDetail] = None) -> MediaInfo:
        """将 Metatube 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'metatube'
        mediainfo.type = MediaType.MOVIE  # 番号内容通常作为电影处理

        # 获取详情中的额外信息
        studio = detail.studio if detail else ""
        label = detail.label if detail else ""
        series = detail.series if detail else ""

        # 解析年份
        year = ""
        if movie.release_date:
            try:
                date_str = movie.release_date.split('T')[0]
                year = date_str[:4]
            except Exception:
                pass

        # 构建优化标题（基于模板）
        optimized_title = self._build_optimized_title(
            number=movie.number,
            actors=movie.actors,
            studio=studio,
            label=label,
            year=year,
            series=series,
            original_title=movie.title
        )

        # 基础信息
        mediainfo.title = optimized_title
        mediainfo.original_title = movie.number

        # 解析发布日期获取年份
        if movie.release_date:
            try:
                # 处理 ISO 格式日期: 2025-09-05T00:00:00Z
                date_str = movie.release_date.split('T')[0]
                mediainfo.year = date_str[:4]
                mediainfo.release_date = date_str
            except Exception:
                pass

        # 使用番号作为标识
        mediainfo.imdb_id = movie.number

        # 封面和海报
        if movie.cover_url:
            mediainfo.poster_path = movie.cover_url
        if movie.thumb_url:
            mediainfo.backdrop_path = movie.thumb_url

        # 评分
        if movie.score:
            mediainfo.vote_average = round(float(movie.score), 1)

        # 演员
        if movie.actors:
            mediainfo.actor = [{"name": actor} for actor in movie.actors]

        # 如果有详情，补充更多信息
        if detail:
            if detail.summary:
                mediainfo.overview = detail.summary
            if detail.director:
                mediainfo.director = [{"name": detail.director}]
            if detail.genres:
                mediainfo.genres = [{"id": g, "name": g} for g in detail.genres]
            if detail.runtime:
                mediainfo.runtime = detail.runtime
            if detail.poster_url:
                mediainfo.poster_path = detail.poster_url
            if detail.images:
                mediainfo.backdrop_path = detail.images[0] if detail.images else mediainfo.backdrop_path

        # 识别成功，固定分类为"日系"
        subcategory = self.SUBCATEGORY_JAPANESE
        category = self._build_category(subcategory)

        # 设置分类（识别成功固定为日系）
        mediainfo.set_category(category)
        logger.info(f"Metatube: 识别成功，分类设置为 '{category}'")

        return mediainfo

    def _convert_theporndb_to_mediainfo(self, scene: ThePornDBScene,
                                        detail: Optional[ThePornDBSceneDetail] = None) -> MediaInfo:
        """将 ThePornDB 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'theporndb'
        mediainfo.type = MediaType.MOVIE  # 作为电影处理

        # 基础信息
        mediainfo.title = scene.title
        mediainfo.original_title = scene.title

        # 解析日期获取年份
        if scene.date:
            try:
                date_str = scene.date.split('T')[0] if 'T' in scene.date else scene.date
                mediainfo.year = date_str[:4]
                mediainfo.release_date = date_str
            except Exception:
                pass

        # 使用 UUID 作为标识
        mediainfo.imdb_id = scene.uuid

        # 海报
        if scene.poster:
            mediainfo.poster_path = scene.poster

        # 如果有详情，补充更多信息
        if detail:
            if detail.description:
                mediainfo.overview = detail.description
            if detail.tags:
                mediainfo.genres = [{"id": tag.name, "name": tag.name} for tag in detail.tags]
            if detail.duration:
                mediainfo.runtime = detail.duration // 60  # 秒转分钟
            if detail.posters and detail.posters.large:
                mediainfo.poster_path = detail.posters.large
            if detail.background and detail.background.large:
                mediainfo.backdrop_path = detail.background.large
            if detail.performers:
                mediainfo.actors = [{"name": p.name} for p in detail.performers]

        # 欧美系分类
        category = "成人/欧美系"
        mediainfo.set_category(category)
        logger.info(f"ThePornDB: 分类设置为 '{category}' (标题: {scene.title})")

        return mediainfo

    def _convert_metatube_search_to_mediainfo(self, movie: MetatubeMovie) -> Optional[MediaInfo]:
        """
        将 MetatubeMovie 搜索结果转换为 MediaInfo（用于探索数据源）

        :param movie: MetatubeMovie 对象
        :return: MediaInfo 对象
        """
        if not movie:
            return None

        # 构建标题 - 显示番号和标题
        title = movie.title or ""
        if movie.number and movie.number not in title:
            title = f"{movie.number} {title}".strip()
        elif not title:
            title = movie.number or ""

        # 从 release_date 提取年份
        year = None
        if movie.release_date:
            try:
                year = movie.release_date[:4]
            except Exception:
                pass

        # 使用 number 作为主要 media_id（number 比 id 更可靠）
        media_id = movie.number or movie.id or ""

        # 使用属性赋值方式创建 MediaInfo
        mediainfo = MediaInfo()
        mediainfo.source = 'metatube_search'
        mediainfo.type = MediaType.MOVIE
        mediainfo.title = title
        mediainfo.original_title = movie.number or ""
        mediainfo.imdb_id = movie.number or ""
        mediainfo.poster_path = movie.cover_url or movie.thumb_url or ""
        mediainfo.vote_average = float(movie.score) if movie.score else None
        mediainfo.year = year
        mediainfo.overview = ""
        mediainfo.studio = movie.provider or ""
        # 设置 media_id 属性用于去重
        mediainfo.media_id = movie.number or movie.id or ""
        return mediainfo

    def _convert_metatube_detail_to_mediainfo(self, detail: MetatubeMovieDetail) -> Optional[MediaInfo]:
        """
        将 MetatubeMovieDetail 详情转换为 MediaInfo（用于探索数据源）

        :param detail: MetatubeMovieDetail 对象
        :return: MediaInfo 对象
        """
        if not detail:
            return None

        # 构建标题
        title = detail.title or ""
        if detail.number and detail.number not in title:
            title = f"{detail.number} {title}".strip()
        elif not title:
            title = detail.number or ""

        # 从 release_date 提取年份
        year = None
        if detail.release_date:
            try:
                year = detail.release_date[:4]
            except Exception:
                pass

        # 处理演员信息
        actors = []
        if detail.actors:
            actors = [actor for actor in detail.actors if actor][:self._max_actors]

        # 使用 number 作为主要 media_id
        media_id = detail.number or detail.id or ""

        # 使用属性赋值方式创建 MediaInfo
        mediainfo = MediaInfo()
        mediainfo.source = 'metatube_search'
        mediainfo.type = MediaType.MOVIE
        mediainfo.title = title
        mediainfo.original_title = detail.number or ""
        mediainfo.imdb_id = detail.number or ""
        mediainfo.poster_path = detail.cover_url or detail.thumb_url or ""
        mediainfo.vote_average = float(detail.score) if detail.score else None
        mediainfo.year = year
        mediainfo.overview = detail.summary or ""
        mediainfo.studio = detail.studio or ""
        mediainfo.actors = actors
        # 设置 media_id 属性用于去重
        mediainfo.media_id = detail.number or detail.id or ""
        return mediainfo

    def _should_use_theporndb(self, title: str) -> bool:
        """
        判断是否应该使用 ThePornDB 进行识别

        :param title: 标题
        :return: 是否使用 ThePornDB
        """
        if not self._theporndb_enabled or not self._theporndb_api_token:
            return False

        # 检测分类类型
        category_type = self._detect_category_type(title)
        return category_type == "欧美系"

    def _recognize_with_bytemuse(self, title: str) -> Optional[MediaInfo]:
        """
        使用 ByteMuse 识别媒体（主要识别源）

        :param title: 搜索标题/番号
        :return: 识别结果
        """
        logger.info(f"ByteMuse: 正在识别 '{title}' ...")

        try:
            # 搜索
            results = self._bytemuse_client.search(title)
            if not results:
                logger.debug(f"ByteMuse: '{title}' 未找到匹配结果")
                return None

            # 取第一个结果
            movie = results[0]

            # 转换为 MediaInfo
            mediainfo = self._convert_bytemuse_to_mediainfo(movie)

            # 根据内容判断分类
            category = self._detect_category_type(title)
            if category == self.SUBCATEGORY_OTHER:
                category = self.SUBCATEGORY_JAPANESE  # 默认为日系

            full_category = self._build_category(category)
            mediainfo.set_category(full_category)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                         f"ByteMuse: {movie.provider}", category=full_category)
            logger.info(f"ByteMuse: 识别成功 - {title} -> {mediainfo.title} (分类: {full_category})")

            return mediainfo

        except Exception as e:
            logger.error(f"ByteMuse: 识别异常 - {str(e)}")
            return None

    def _convert_javbus_to_mediainfo(self, detail: JavBusMovieDetail) -> MediaInfo:
        """将 JavBus 详情结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'javbus'
        mediainfo.type = MediaType.MOVIE

        # 解析年份
        year = ""
        if detail.date:
            try:
                year = detail.date[:4]
            except Exception:
                pass

        # 处理演员列表
        actors = []
        if detail.stars:
            actors = [star.name for star in detail.stars if star.name]

        # 制作商/发行商
        studio = detail.producer.name if detail.producer else ""
        label = detail.publisher.name if detail.publisher else ""
        series = detail.series.name if detail.series else ""

        # 构建优化标题
        optimized_title = self._build_optimized_title(
            number=detail.id,
            actors=actors,
            studio=studio,
            label=label,
            year=year,
            series=series,
            original_title=detail.title
        )

        # 基础信息
        mediainfo.title = optimized_title
        mediainfo.original_title = detail.id

        # 年份和日期
        if detail.date:
            mediainfo.year = year
            mediainfo.release_date = detail.date

        # 番号作为标识
        mediainfo.imdb_id = detail.id

        # 封面和海报
        if detail.img:
            mediainfo.poster_path = detail.img
            mediainfo.backdrop_path = detail.img

        # 演员
        if actors:
            mediainfo.actor = [{"name": name} for name in actors]

        # 概要
        if detail.info:
            mediainfo.overview = detail.info

        # 导演
        if detail.director and detail.director.name:
            mediainfo.director = [{"name": detail.director.name}]

        # 类型标签
        if detail.genres:
            mediainfo.genres = [{"id": g.id, "name": g.name} for g in detail.genres if g.name]

        # 时长
        if detail.videoLength:
            mediainfo.runtime = detail.videoLength

        # 制作商信息
        if studio:
            mediainfo.studio = studio

        # 预览图 (samples)
        if detail.samples:
            image_urls = [s.src for s in detail.samples if s.src]
            if image_urls and hasattr(mediainfo, 'images'):
                mediainfo.images = image_urls

        return mediainfo

    def _recognize_with_javbus(self, title: str) -> Optional[MediaInfo]:
        """
        使用 JavBus API 识别媒体

        :param title: 搜索标题/番号
        :return: 识别结果
        """
        logger.info(f"JavBus: 正在识别 '{title}' ...")

        try:
            # 搜索并获取详情
            detail = self._javbus_client.search_with_detail(title)
            if not detail:
                logger.debug(f"JavBus: '{title}' 未找到匹配结果")
                return None

            # 转换为 MediaInfo
            mediainfo = self._convert_javbus_to_mediainfo(detail)

            # 固定分类为日系
            category = self._build_category(self.SUBCATEGORY_JAPANESE)
            mediainfo.set_category(category)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                         "来源: JavBus", category=category)
            logger.info(f"JavBus: 识别成功 - {title} -> {mediainfo.title} (分类: {category})")

            return mediainfo

        except Exception as e:
            logger.error(f"JavBus: 识别异常 - {str(e)}")
            return None

    async def _async_recognize_with_javbus(self, title: str) -> Optional[MediaInfo]:
        """
        异步使用 JavBus API 识别媒体

        :param title: 搜索标题/番号
        :return: 识别结果
        """
        logger.info(f"JavBus: 正在异步识别 '{title}' ...")

        try:
            # 异步搜索并获取详情
            detail = await self._javbus_client.async_search_with_detail(title)
            if not detail:
                logger.debug(f"JavBus: '{title}' 未找到匹配结果")
                return None

            # 转换为 MediaInfo
            mediainfo = self._convert_javbus_to_mediainfo(detail)

            # 固定分类为日系
            category = self._build_category(self.SUBCATEGORY_JAPANESE)
            mediainfo.set_category(category)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                         "来源: JavBus", category=category)
            logger.info(f"JavBus: 异步识别成功 - {title} -> {mediainfo.title} (分类: {category})")

            return mediainfo

        except Exception as e:
            logger.error(f"JavBus: 异步识别异常 - {str(e)}")
            return None

    def _recognize_with_theporndb(self, title: str) -> Optional[MediaInfo]:
        """
        使用 ThePornDB 识别媒体

        :param title: 搜索标题
        :return: 识别结果
        """
        logger.info(f"ThePornDB: 正在识别 '{title}' ...")

        try:
            # 搜索
            results = self._theporndb_client.search_scenes(title)
            if not results:
                logger.warning(f"ThePornDB: '{title}' 未找到匹配结果")
                return None

            # 取第一个结果
            scene = results[0]

            # 尝试获取详情
            detail = None
            if scene.uuid:
                try:
                    detail = self._theporndb_client.get_scene_detail(scene.uuid)
                except Exception as e:
                    logger.debug(f"ThePornDB: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_theporndb_to_mediainfo(scene, detail)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                          "来源: ThePornDB", category=self._build_category(self.SUBCATEGORY_WESTERN))
            logger.info(f"ThePornDB: 识别成功 - {title} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            logger.error(f"ThePornDB: 识别异常 - {str(e)}")
            return None

    async def _async_recognize_with_bytemuse(self, title: str) -> Optional[MediaInfo]:
        """
        异步使用 ByteMuse 识别媒体（主要识别源）

        :param title: 搜索标题/番号
        :return: 识别结果
        """
        logger.info(f"ByteMuse: 正在异步识别 '{title}' ...")

        try:
            # 异步搜索
            results = await self._bytemuse_client.async_search(title)
            if not results:
                logger.debug(f"ByteMuse: '{title}' 未找到匹配结果")
                return None

            # 取第一个结果
            movie = results[0]

            # 转换为 MediaInfo
            mediainfo = self._convert_bytemuse_to_mediainfo(movie)

            # 根据内容判断分类
            category = self._detect_category_type(title)
            if category == self.SUBCATEGORY_OTHER:
                category = self.SUBCATEGORY_JAPANESE  # 默认为日系

            full_category = self._build_category(category)
            mediainfo.set_category(full_category)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                         f"ByteMuse: {movie.provider}", category=full_category)
            logger.info(f"ByteMuse: 异步识别成功 - {title} -> {mediainfo.title} (分类: {full_category})")

            return mediainfo

        except Exception as e:
            logger.error(f"ByteMuse: 异步识别异常 - {str(e)}")
            return None

    async def _async_recognize_with_theporndb(self, title: str) -> Optional[MediaInfo]:
        """
        异步使用 ThePornDB 识别媒体

        :param title: 搜索标题
        :return: 识别结果
        """
        logger.info(f"ThePornDB: 正在异步识别 '{title}' ...")

        try:
            # 异步搜索
            results = await self._theporndb_client.async_search_scenes(title)
            if not results:
                logger.warning(f"ThePornDB: '{title}' 未找到匹配结果")
                return None

            # 取第一个结果
            scene = results[0]

            # 尝试获取详情
            detail = None
            if scene.uuid:
                try:
                    detail = await self._theporndb_client.async_get_scene_detail(scene.uuid)
                except Exception as e:
                    logger.debug(f"ThePornDB: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_theporndb_to_mediainfo(scene, detail)

            self._add_log(title, f"{mediainfo.title} ({mediainfo.year})", "success",
                          "来源: ThePornDB", category=self._build_category(self.SUBCATEGORY_WESTERN))
            logger.info(f"ThePornDB: 识别成功 - {title} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            logger.error(f"ThePornDB: 异步识别异常 - {str(e)}")
            return None

    # Precompiled JAV number patterns (compiled once at class load)
    _JAV_NUMBER_PATTERNS = [
        re.compile(r'^(?:FC2-PPV-\d{7,8}|HEYZO-\d{4}|[A-Z]{2,6}-\d{3,5}|\d{6}[-_]\d{3})$', re.IGNORECASE),
    ]

    def _is_jav_number(self, number: str) -> bool:
        """检测是否为 JAV 番号格式（使用预编译正则）"""
        if not number:
            return False
        return any(p.match(number) for p in self._JAV_NUMBER_PATTERNS)

    def _convert_theporndb_jav_to_mediainfo(self, jav_detail: ThePornDBJAVDetail) -> MediaInfo:
        """将 ThePornDB JAV 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = 'theporndb-jav'
        mediainfo.type = MediaType.MOVIE

        # 构建优化标题（基于模板）
        actors = []
        if jav_detail.performers:
            actors = [p.name for p in jav_detail.performers]

        studio = jav_detail.site.name if jav_detail.site else ""
        year = ""
        if jav_detail.date:
            try:
                year = jav_detail.date[:4]
            except Exception:
                pass

        optimized_title = self._build_optimized_title(
            number=jav_detail.external_id,
            actors=actors,
            studio=studio,
            label="",
            year=year,
            series="",
            original_title=jav_detail.title
        )

        # 基础信息
        mediainfo.title = optimized_title
        mediainfo.original_title = jav_detail.external_id

        # 解析日期获取年份
        if jav_detail.date:
            try:
                date_str = jav_detail.date.split('T')[0] if 'T' in jav_detail.date else jav_detail.date
                mediainfo.year = date_str[:4]
                mediainfo.release_date = date_str
            except Exception:
                pass

        # 使用番号作为标识
        mediainfo.imdb_id = jav_detail.external_id

        # 海报
        if jav_detail.posters and jav_detail.posters.full:
            mediainfo.poster_path = jav_detail.posters.full
        elif jav_detail.poster:
            mediainfo.poster_path = jav_detail.poster

        # 背景
        if jav_detail.background and jav_detail.background.full:
            mediainfo.backdrop_path = jav_detail.background.full

        # 时长
        if jav_detail.duration:
            mediainfo.runtime = jav_detail.duration // 60  # 秒转分钟

        # 演员
        if jav_detail.performers:
            mediainfo.actor = [{"name": p.name} for p in jav_detail.performers]

        # 标签
        if jav_detail.tags:
            mediainfo.genres = [{"id": str(t.id), "name": t.name} for t in jav_detail.tags]

        # 日系分类
        category = self._build_category(self.SUBCATEGORY_JAPANESE)
        mediainfo.set_category(category)
        logger.info(f"ThePornDB JAV: 分类设置为 '{category}' (番号: {jav_detail.external_id})")

        return mediainfo

    def _recognize_with_theporndb_jav(self, number: str) -> Optional[MediaInfo]:
        """
        使用 ThePornDB JAV API 识别媒体

        使用两步法：先网页搜索获取 UUID，再 API 获取详情

        :param number: 番号
        :return: 识别结果
        """
        logger.info(f"ThePornDB JAV: 正在识别 '{number}' ...")

        try:
            # 使用两步法：先搜索获取 UUID，再获取详情
            details = self._theporndb_client.search_jav_to_detail(number)
            if not details:
                logger.debug(f"ThePornDB JAV: '{number}' 未找到匹配结果")
                return None

            # 取第一个结果
            detail = details[0]

            # 转换为 MediaInfo
            mediainfo = self._convert_theporndb_jav_to_mediainfo(detail)

            self._add_log(number, f"{mediainfo.title} ({mediainfo.year})", "success",
                         "来源: ThePornDB JAV", category=self._build_category(self.SUBCATEGORY_JAPANESE))
            logger.info(f"ThePornDB JAV: 识别成功 - {number} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            logger.error(f"ThePornDB JAV: 识别异常 - {str(e)}")
            return None

    async def _async_recognize_with_theporndb_jav(self, number: str) -> Optional[MediaInfo]:
        """
        异步使用 ThePornDB JAV API 识别媒体

        使用两步法：先网页搜索获取 UUID，再 API 获取详情

        :param number: 番号
        :return: 识别结果
        """
        logger.info(f"ThePornDB JAV: 正在异步识别 '{number}' ...")

        try:
            # 使用两步法：先搜索获取 UUID，再获取详情
            details = await self._theporndb_client.async_search_jav_to_detail(number)
            if not details:
                logger.debug(f"ThePornDB JAV: '{number}' 未找到匹配结果")
                return None

            # 取第一个结果
            detail = details[0]

            # 转换为 MediaInfo
            mediainfo = self._convert_theporndb_jav_to_mediainfo(detail)

            self._add_log(number, f"{mediainfo.title} ({mediainfo.year})", "success",
                         "来源: ThePornDB JAV", category=self._build_category(self.SUBCATEGORY_JAPANESE))
            logger.info(f"ThePornDB JAV: 异步识别成功 - {number} -> {mediainfo.title} ({mediainfo.year})")

            return mediainfo

        except Exception as e:
            logger.error(f"ThePornDB JAV: 异步识别异常 - {str(e)}")
            return None

    def _check_recognize_cache(self, title: str) -> Optional[str]:
        """
        检查识别去重缓存

        :param title: 标题
        :return: 缓存的状态字符串（skip/none/fallback+分类），None 表示未缓存
        """
        if not title:
            return None
        cache_key = title.strip()
        if cache_key in self._recognize_cache:
            status, ts = self._recognize_cache[cache_key]
            if (datetime.now().timestamp() - ts) < self._recognize_cache_ttl:
                logger.debug(f"Metatube: 命中识别缓存，跳过重复识别: {cache_key[:50]} (状态: {status})")
                return status
            else:
                del self._recognize_cache[cache_key]
        return None

    def _set_recognize_cache(self, title: str, status: str):
        """设置识别缓存"""
        if not title:
            return
        cache_key = title.strip()
        self._recognize_cache[cache_key] = (status, datetime.now().timestamp())
        # 清理过期缓存（每次写入时顺便清理，避免无限增长）
        now = datetime.now().timestamp()
        expired_keys = [k for k, (_, ts) in self._recognize_cache.items()
                       if (now - ts) >= self._recognize_cache_ttl]
        for k in expired_keys:
            del self._recognize_cache[k]


    def _recognize_pipeline(self, title: str, meta: MetaBase, mtype: Optional[MediaType],
                            is_async: bool = False) -> Optional[MediaInfo]:
        """
        Core recognition pipeline shared by sync and async paths.
        Returns (MediaInfo or None).
        """
        if not self._enabled or not meta:
            return None

        # Step 0: Check file size
        if self._skip_small_files:
            file_size_mb = self._get_file_size_mb(meta, {})
            if file_size_mb is not None and file_size_mb < self._small_file_threshold:
                logger.info(f"Metatube: 文件过小 ({file_size_mb:.1f}MB < {self._small_file_threshold}MB)，跳过: {meta.name}")
                return None

        # Step 1: Category detection
        detected_category = self._detect_category_type(title)

        # Step 2: Skip if excluded
        if detected_category == self.SUBCATEGORY_SKIP:
            self._set_recognize_cache(title, "skip")
            return None

        # Step 3: Extract number
        number = self._extract_number_from_meta(meta, detected_category)
        if not number:
            result = self._handle_recognition_failure(title or meta.name or "", title, "无法提取番号")
            self._set_recognize_cache(title, "none")
            return result

        logger.info(f"Metatube: 识别番号 {number} (分类: {detected_category}) ...")

        # Step 4: Recognition source chain
        # 4a. ByteMuse
        if self._bytemuse_enabled:
            result = self._call_recognize("bytemuse", number, title, is_async)
            if result:
                return result

        # 4b. JavBus
        if self._javbus_enabled:
            result = self._call_recognize("javbus", number, title, is_async)
            if result:
                return result

        # 4c. ThePornDB JAV (JAV format)
        is_jav = self._is_jav_number(number)
        if is_jav and self._theporndb_enabled and self._theporndb_api_token:
            result = self._call_recognize("theporndb_jav", number, title, is_async)
            if result:
                return result

        # 4d. ThePornDB (Western)
        if detected_category == self.SUBCATEGORY_WESTERN and self._theporndb_enabled and self._theporndb_api_token:
            result = self._call_recognize("theporndb", title, title, is_async)
            if result:
                return result
            # Western fallback: create category entry if auto-download enabled
            if self._failed_download_control:
                category = self._build_category(self.SUBCATEGORY_WESTERN)
                mediainfo = MediaInfo()
                mediainfo.source = 'theporndb'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "fallback", "ThePornDB识别失败，归类欧美系", category=category)
                return mediainfo
            self._add_log(number, "", "failed", "ThePornDB识别失败", category=self._build_category(self.SUBCATEGORY_WESTERN))
            return None

        # 4d. Metatube API
        return self._call_recognize("metatube", number, title, is_async,
                                    extra={"detected_category": detected_category})

    async def _recognize_pipeline_async(self, title: str, meta: MetaBase, mtype: Optional[MediaType]) -> Optional[MediaInfo]:
        """Async wrapper for the pipeline"""
        if not self._enabled or not meta:
            return None

        if self._skip_small_files:
            file_size_mb = self._get_file_size_mb(meta, {})
            if file_size_mb is not None and file_size_mb < self._small_file_threshold:
                return None

        detected_category = self._detect_category_type(title)
        if detected_category == self.SUBCATEGORY_SKIP:
            self._set_recognize_cache(title, "skip")
            return None

        number = self._extract_number_from_meta(meta, detected_category)
        if not number:
            result = self._handle_recognition_failure(title or meta.name or "", title, "无法提取番号")
            self._set_recognize_cache(title, "none")
            return result

        logger.info(f"Metatube: 异步识别番号 {number} (分类: {detected_category}) ...")

        if self._bytemuse_enabled:
            result = await self._call_recognize_async("bytemuse", number, title)
            if result:
                return result

        if self._javbus_enabled:
            result = await self._call_recognize_async("javbus", number, title)
            if result:
                return result

        is_jav = self._is_jav_number(number)
        if is_jav and self._theporndb_enabled and self._theporndb_api_token:
            result = await self._call_recognize_async("theporndb_jav", number, title)
            if result:
                return result

        if detected_category == self.SUBCATEGORY_WESTERN and self._theporndb_enabled and self._theporndb_api_token:
            result = await self._call_recognize_async("theporndb", title, title)
            if result:
                return result
            if self._failed_download_control:
                category = self._build_category(self.SUBCATEGORY_WESTERN)
                mediainfo = MediaInfo()
                mediainfo.source = 'theporndb'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "fallback", "ThePornDB识别失败，归类欧美系", category=category)
                return mediainfo
            return None

        return await self._call_recognize_async("metatube", number, title,
                                                  extra={"detected_category": detected_category})

    def _call_recognize(self, source: str, query: str, title: str, is_async: bool,
                        extra: dict = None) -> Optional[MediaInfo]:
        """Dispatch to the right recognition source (sync)"""
        try:
            if source == "bytemuse":
                return self._recognize_with_bytemuse(query)
            elif source == "javbus":
                return self._recognize_with_javbus(query)
            elif source == "theporndb_jav":
                return self._recognize_with_theporndb_jav(query)
            elif source == "theporndb":
                return self._recognize_with_theporndb(title)
            elif source == "metatube":
                return self._recognize_with_metatube(query, title, extra)
        except Exception as e:
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            logger.error(f"Metatube: {source} 识别异常 - {e}")
            return self._handle_recognition_failure(query, title, failure_msg)
        return None

    async def _call_recognize_async(self, source: str, query: str, title: str,
                                     extra: dict = None) -> Optional[MediaInfo]:
        """Dispatch to the right recognition source (async)"""
        try:
            if source == "bytemuse":
                return await self._async_recognize_with_bytemuse(query)
            elif source == "javbus":
                return await self._async_recognize_with_javbus(query)
            elif source == "theporndb_jav":
                return await self._async_recognize_with_theporndb_jav(query)
            elif source == "theporndb":
                return await self._async_recognize_with_theporndb(title)
            elif source == "metatube":
                return await self._recognize_with_metatube_async(query, title, extra)
        except Exception as e:
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            logger.error(f"Metatube: {source} 异步识别异常 - {e}")
            return self._handle_recognition_failure(query, title, failure_msg)
        return None

    def _recognize_with_metatube(self, number: str, title: str, extra: dict = None) -> Optional[MediaInfo]:
        """Metatube API recognition (sync)"""
        results = self._metatube_client.search(number, fallback=True)
        if not results:
            return self._handle_recognition_failure(number, title, "未找到匹配结果")

        movie = results[0]
        detail = None
        if movie.provider and movie.id:
            try:
                detail = self._metatube_client.get_detail(movie.provider, movie.id)
            except Exception:
                pass

        mediainfo = self._convert_to_mediainfo(movie, detail)
        category = self._build_category(self.SUBCATEGORY_JAPANESE)
        self._add_log(number, mediainfo.title, "success", f"来源: {movie.provider}", category=category)
        self._set_recognize_cache(title, "success")
        return mediainfo

    async def _recognize_with_metatube_async(self, number: str, title: str, extra: dict = None) -> Optional[MediaInfo]:
        """Metatube API recognition (async)"""
        results = await self._metatube_client.async_search(number, fallback=True)
        if not results:
            return self._handle_recognition_failure(number, title, "未找到匹配结果")

        movie = results[0]
        detail = None
        if movie.provider and movie.id:
            try:
                detail = await self._metatube_client.async_get_detail(movie.provider, movie.id)
            except Exception:
                pass

        mediainfo = self._convert_to_mediainfo(movie, detail)
        category = self._build_category(self.SUBCATEGORY_JAPANESE)
        self._add_log(number, mediainfo.title, "success", f"来源: {movie.provider}", category=category)
        self._set_recognize_cache(title, "success")
        return mediainfo

    def recognize_media(self, meta: MetaBase = None,
                        mtype: MediaType = None,
                        **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息（委托给统一 pipeline）
        """
        title = (meta.org_string or meta.cn_name or meta.en_name or meta.name or "") if meta else ""
        cached = self._check_recognize_cache(title)
        if cached == "skip":
            return None
        return self._recognize_pipeline(title, meta, mtype, is_async=False)

    async def async_recognize_media(self, meta: MetaBase = None,
                                    mtype: MediaType = None,
                                    **kwargs) -> Optional[MediaInfo]:
        """
        异步识别媒体信息（委托给统一 pipeline）
        """
        title = (meta.org_string or meta.cn_name or meta.en_name or meta.name or "") if meta else ""
        cached = self._check_recognize_cache(title)
        if cached == "skip":
            return None
        return await self._recognize_pipeline_async(title, meta, mtype)
