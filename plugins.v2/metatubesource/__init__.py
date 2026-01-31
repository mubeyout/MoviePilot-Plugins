"""
Metatube 媒体识别插件
通过 Metatube API 识别番号媒体信息
"""
import re
from collections import deque
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional, List, Tuple

from app.chain import ChainBase
from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.plugins import _PluginBase
from app.log import logger
from app.schemas.types import MediaType

from .metatube_api import MetatubeApiClient
from .theporndb_api import ThePornDBApiClient
from .schema import (
    MetatubeMovie, MetatubeMovieDetail, LogEntry,
    ThePornDBScene, ThePornDBSceneDetail
)


class MetatubeSource(_PluginBase):
    # 插件名称
    plugin_name = "Metatube源"
    # 插件描述
    plugin_desc = "通过Metatube API识别番号媒体信息。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/Metatube.png"
    # 插件版本
    plugin_version = "1.1.0"
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

    # 关键字配置文件路径
    KEYWORDS_FILE_PATH = "keywords.json"  # 插件根目录下的 JSON 文件

    # 内置关键字库（按分类组织）
    # 日系关键词（包含番号前缀、制作商、发行商等）
    BUILT_IN_JAPANESE_KEYWORDS = [
        # === S1 NO.1 STYLE ===
        "SSIS", "SONE", "MIDV", "SSIS-", "SONE-", "MIDV-",

        # === IDEAPOCKET ===
        "IPX", "IPX-",

        # === Moodyz ===
        "MIAA", "MIDE", "MEYD", "JUL", "JUL-",
        "MIAD", "MIDD", "MIAE",

        # === Madonna ===
        "JUQ", "JUQ-", "JUL", "JUL-", "VENX",

        # === Premium ===
        "CAWD", "CAWD-",

        # === Alice JAPAN ===
        "ADN", "DLDSS", "DLD",

        # === kawaii* ===
        "KTRA", "KMHR", "KAWD",

        # === E-BODY ===
        "EBOD", "EBOD-",

        # === OPPAI ===
        "PPPE", "PPPD", "OPPAI",

        # === Wanz Factory ===
        "WANZ", "WAAA",

        # === SOD Create ===
        "STAR", "STARS", "SDMT", "SDDE", "SOE", "SDNM", "SDAB",

        # === KMP ===
        "OKAX", "OPUD",

        # === WAAP ===
        "SW",

        # === ROCK ===
        "KAWD",

        # === FC2 ===
        "FC2", "FC2-", "FC2PPV", "FC2-PPV", "PPV",

        # === HEYZO ===
        "HEYZO", "HEYZO-",

        # === Caribbean ===
        "CARIB", "CARIBPR", "CARIB-",
        "062", "063", "082", "083",
        "Caribbeancom", "Caribbeancompr",

        # === 1PonDo ===
        "1PONDO", "010115", "010",

        # === PacoPacomaMama ===
        "PACOPACOMAMA", "PACO",

        # === H0930 ===
        "H0930",

        # === H4610 ===
        "H4610",

        # === C0930 ===
        "C0930",

        # === Sky High Ent ===
        "SKY", "SKY-", "Sora",

        # === Red Hot ===
        "RED", "RED-",

        # === Tokyo Hot ===
        "Tokyo-Hot", "TOKYO-HOT",
        "n", "k",  # n1234, k1234 格式

        # === JAV通用 ===
        "JAV", "JavHD", "Javbus", "JAVHub",
        "AVOP", "AVOPEN",

        # === 其他常见制作商 ===
        "DOCP", "DOM",
        "HMN", "HOMA",
        "URE", "URE-",
        "MIMK", "MIMK-",
        "ABW", "ABP",

        # === 中文名称 ===
        "一本道", "加勒比", "红番区",
        "10musume", "Pcolle", "Gcolle", "Skyhigh", "Redhot",

        # === 其他番号前缀 ===
        "BF", "CWP", "SW", "KV", "MXGS", "BKSP", "SUPA"
    ]

    # 欧美系关键词（包含成人网站、工作室等）
    BUILT_IN_WESTERN_KEYWORDS = [
        # === Brazzers Network ===
        "BRAZZERS", "BRAZZERS-",
        "MomXXX", "MomXxx",
        "BigTitsAtWork", "BigWetButts",
        "BrazzersEx", "BabyGotBoobs",

        # === Naughty America ===
        "NAUGHTY", "NAUGHTY-",
        "NaughtyAmerica", "MyFriendsHotMom",
        "MySistersHotFriend", "NaughtyBookworms",
        "Housewife1on1", "MyWifesHotFriend",
        "MyFirstSexTeacher", "NaughtyOffice",

        # === Reality Kings ===
        "REALITYKINGS", "RealityKings",
        "RK", "RK-",
        "MoneyTalks", "8thStreetLatinas",
        "EuroSexParties", "GirlsGonePink",
        "LoveHomePorn", "MonsterCurves",
        "TopShelfPussy", "WildOnCam",

        # === Mofos ===
        "MOFOS", "MOFOS-",
        "Mofos", "CanSheTakeIt",
        "DontBreakMe", "EFrkt",
        "GirlsOfDesire", "IKnowThatGirl",
        "LetsTryAnal", "MofosBSC",
        "PervsOnPatrol", "PublicAgent",
        "ShesAFreak", "StrandedTeens",

        # === TeamSkeet ===
        "TeamSkeet", "TEAMSKEET",
        "ExxxtraSmall", "TeensLoveBlackCocks",
        "POVLife", "RubATeen",
        "She'sNew", "TeenCurves",
        "TheRealWorkout", "TittyAttack",
        "TukTukPatrol",

        # === Vixen Media ===
        "BLACKED", "BLACKEDRAW",
        "TUSHY", "TUSHYRAW",
        "VIXEN", "VIXEN-",
        "Deeper", "Slayed",

        # === BangBros ===
        "BangBros", "BANG",
        "BangBrosClips", "AssParade",
        "BallHoneys", "BigMouthfuls",
        "BigTitCreamPie", "BlowJobFridays",
        "BangBus", "BangPOV",
        "CanHeScore", "Chongas",
        "DirtyWorldTour", "FacialFest",
        "FuckTeamFive", "GloryHoleLoads",
        "LatinaRampage", "LivingWithAnna",
        "MilfHunter", "MilfLessons",
        "MomIsHorny", "MonstersOfCock",
        "PartyOfThree", "Parejas",
        "PowerMunch", "PrincessCum",
        "Remaster", "SlutLoad",
        "StreetBlowjobs", "TugJobs",

        # === Digital Playground ===
        "DigitalPlayground", "DP",
        "BlackedDigital", "Digital",
        "DPFanatics", "DPLingerie",

        # === Evil Angel ===
        "EvilAngel", "EvilAngel-",
        "Evil", "Angel",

        # === Jules Jordan ===
        "JulesJordan", "Jules",
        "JulesJordanVideo",

        # === Reality King ===
        "RealityKing",

        # === New Sensations ===
        "NewSensations",

        # === Pure Taboo ===
        "PureTaboo", "Pure-",

        # === XEmpire ===
        "XEmpire", "XEmpire-",
        "DarkX", "EroticaX",
        "LesbianX", "HardX",

        # === Girlfriend Films ===
        "GirlfriendFilms",
        "GirlfriendsFilms",

        # === Fakedriv ===
        "Fakehub", "FakeHub-",
        "FakeTaxi", "FakeAgent",
        "FemaleAgent", "PublicAgent",
        "FakeHospital", "FakeCop",

        # === Passion HD ===
        "PassionHD", "Passion-",
        "POVD", "Tiny4K",
        "Cum4K", "Lubed",

        # === 21Sextury ===
        "21Sextury", "21Sextury-",
        "21Naturals", "21FootArt",
        "21Erotica", "AnalTeenAngels",

        # === Dorcel ===
        "Dorcel", "MarcDorcel",
        "DorcelClub",

        # === Private ===
        "Private", "Private-",
        "PrivateClassics",

        # === Legal Porno ===
        "LegalPorno", "LegalPorno-",
        "Gonzo", "AnalOnly",

        # === Others ===
        "Pornhub", "Pornhub-",
        "Xvideos", "Xvideos-",
        "VOYEURHIT", "VICAT",
        "XEV", "Missa",
        "PervMom", "SisLovesMe",
        "Badoink", "Babes",
        "DorcelVision", "DorcelClub",
        "MofosNetwork", "BrazzersNetwork",
        "NaughtyAmericaNetwork", "RealityKingsNetwork"
    ]

    # 中文系关键词（包含传媒、制作商等）
    BUILT_IN_CHINESE_KEYWORDS = [
        # === 麻豆传媒 ===
        "MD", "MD-", "MDCN",
        "麻豆", "麻豆傳媒", "MADOU",

        # === 精东传媒 ===
        "MX", "MX-",
        "精东", "精東傳媒", "JD传媒",

        # === 天美传媒 ===
        "TM", "TM-",
        "天美", "天美傳媒",

        # === 蜜桃传媒 ===
        "PMC", "PMC-",
        "蜜桃", "蜜桃傳媒",

        # === 91制片 ===
        "AV", "AV-",
        "91制片", "九一制片",

        # === 台湾传媒 ===
        "TW", "TW-",
        "台湾", "台灣傳媒",

        # === 其他 ===
        "JK", "JK-",
        "HT", "HT-",
        "MDX", "MDX-",
        "约炮", "网红", "探花",
        "大尺寸", "小宝寻花",
        "传媒", "傳媒",
        "MDTV"
    ]

    # 其他关键词（通用特征）
    BUILT_IN_OTHER_KEYWORDS = [
        # === 画质 ===
        "高清", "超清", "蓝光", "HDRip",
        "HD", "FHD", "QHD",

        # === 编码类型 ===
        "无码", "有码", "薄码", "破解",
        "无修", "有修", "修复版",

        # === 字幕 ===
        "中文字幕", "中日字幕", "中英字幕",
        "字幕", "内嵌字幕", "外挂字幕",

        # === 音轨 ===
        "原声", "原版音轨", "日语原声",
        "国语", "粤语", "台配",

        # === 版本 ===
        "完整版", "无删减版", "导演剪辑版",
        "流出", "泄露", "流出版",
        "典藏版", "珍藏版", "合集",

        # === 其他特征 ===
        "独家", "首发", "最新",
        "成人", "AV", "JAV",
        "成人视频", "成人电影"
    ]

    # 内置排除关键字（匹配后直接跳过分类）
    BUILT_IN_EXCLUDE_KEYWORDS = [
        # === 画质标记 ===
        "4K", "UHD", "HDR", "HDR10", "HDR10+", "DOLBY", "DOLBY-VISION",
        "FHD", "HD", "SD", "LD", "ED",

        # === 分辨率 ===
        "2160P", "1440P", "1080P", "720P", "480P", "360P", "240P",
        "3840X2160", "1920X1080", "1280X720",
        "X264", "X265", "H264", "H265",

        # === 帧率 ===
        "60FPS", "120FPS", "240FPS", "30FPS", "24FPS",
        "60FPS", "59.94FPS", "29.97FPS",

        # === 视频编码 ===
        "H.265", "H.264", "HEVC", "XVID", "DIVX",
        "X264", "X265", "VC-1", "VP9", "VP8", "AV1", "AVC",
        "MPEG-2", "MPEG-4", "MPEG4", "MPEG2",
        "WMV", "RMVB", "RM", "FLV",

        # === 音频编码 ===
        "AC3", "DTS", "DTS-HD", "DTS-HDMA", "AAC", "FLAC",
        "MP3", "OPUS", "OGG", "WAV", "MKA",
        "TRUEHD", "DOLBY-ATMOS", "ATMOS",
        "EAC3", "DDP", "DD",

        # === 视频格式 ===
        "REMUX", "WEB-DL", "WEBRIP", "WEB-DL", "WEB",
        "BLURAY", "BDRIP", "BRRIP", "BD", "DVD",
        "DVDRIP", "HDDVD", "HDTV", "PDTV",
        "SATRIP", "TVRIP", "CAM", "TS", "TC",
        "TELESYNC", "TELECINE",

        # === 文件格式 ===
        "MKV", "MP4", "AVI", "WMV", "FLV",
        "MOV", "M4V", "TS", "M2TS",
        "ISO", "IMG", "DVD5", "DVD9",

        # === 制式 ===
        "NTSC", "PAL", "SECAM", "SECA",

        # === 分片标记 ===
        "CD1", "CD2", "CD3", "DISC1", "DISC2", "DISC3",
        "PART1", "PART2", "PART3",
        "PT1", "PT2", "PT3",

        # === 来源标记 ===
        "NETFLIX", "DISNEY+", "HULU", "AMZN",
        "HBO", "HBO-MAX", "PARAMOUNT+",
        "APPLE-TV", "APPLE+",
        "PRIME", "AMAZON",
        "CRUNCHYROLL", "FUNIMATION",

        # === 发布组 ===
        "RARBG", "YTS", "YIFY", "FGT",
        "RARBG", "1337X", "NYAA", "SUKEBEI",

        # === 语言标记 ===
        "DUAL", "MULTI", "MULTISUBS",
        "ENGLISH", "JAPANESE", "CHINESE",
        "EN", "JP", "CN", "ZH",
        "ENG", "JPN", "CHN", "ZHO",

        # === 版本标记 ===
        "DIRECTORS-CUT", "EXTENDED", "UNCUT",
        "UNCENSORED", "UNRATED",
        "REMASTERED", "REPACK", "PROPER",
        "LIMITED", "INTERNAL", "NUKED",

        # === 技术参数 ===
        "10BIT", "8BIT", "HI10P", "HI8P",
        "HYBRID", "COMPRESS", "RE-ENCODE",

        # === 其他常见标记 ===
        "SAMPLE", "PROOF", "NFO", "SFV",
        "SUBS", "SUBPACK", "SUBBED",
        "DUBBED", "DUAL-AUDIO",
        "COMPLETE", "FULL", "COMPLETE-SEASON",
        "SEASON", "S01", "S02", "S03",
        "EPISODE", "E01", "E02", "E03",

        # === 硬件相关 ===
        "OLED", "LED", "LCD", "PLASMA",
        "HDRIP", "SDR", "BT2020", "BT709",

        # === 压缩标记 ===
        "COMPRESSED", "ENCODED", "RE-ENC",
        "CRRIP", "DVDR", "R5",

        # === 质量标记 ===
        "HQ", "LQ", "PDTV", "DSR",
        "HDTVRIP", "HDTV",
        "SATRIP", "TVRIP",

        # === 分辨率简写 ===
        "4K60", "1080P60", "720P60",
        "4K60FPS", "1080P60FPS", "720P60FPS"
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

    # 识别失败控制
    _failed_download_control: bool = True  # 识别失败后是否执行下载（新配置项）

    # 通用配置
    _show_failure_detail: bool = True  # 识别失败提示开关

    # ThePornDB 配置
    _theporndb_enabled: bool = False  # 是否启用 ThePornDB
    _theporndb_api_token: str = ""  # ThePornDB API Token

    # 私有属性
    _metatube_client: MetatubeApiClient = None
    _theporndb_client: ThePornDBApiClient = None  # ThePornDB 客户端
    _original_method: Optional[Callable] = None
    _original_async_method: Optional[Callable[..., Coroutine[Any, Any, Optional[MediaInfo]]]] = None
    _log_entries: deque = None

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        plugin_instance: MetatubeSource = self

        def patched_recognize_media(chain_self, meta: MetaBase = None,
                                    mtype: Optional[MediaType] = None,
                                    tmdbid: Optional[int] = None,
                                    doubanid: Optional[str] = None,
                                    bangumiid: Optional[int] = None,
                                    episode_group: Optional[str] = None,
                                    cache: bool = True):
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
                result = plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                          episode_group, cache)
                if result:
                    return result

                # 3. 系统识别也失败，最后由 metatube 兜底处理
                logger.info(f"系统识别失败，通过插件 {MetatubeSource.plugin_name} 兜底执行：recognize_media ...")
                return plugin_instance.recognize_media(meta, mtype)

            # 插件未启用，直接调用原始方法
            return plugin_instance._original_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                    episode_group, cache)

        async def patched_async_recognize_media(chain_self, meta: MetaBase = None,
                                                mtype: Optional[MediaType] = None,
                                                tmdbid: Optional[int] = None,
                                                doubanid: Optional[str] = None,
                                                bangumiid: Optional[int] = None,
                                                episode_group: Optional[str] = None,
                                                cache: bool = True):
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
                result = await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                      episode_group, cache)
                if result:
                    return result

                # 3. 系统识别也失败，最后由 metatube 兜底处理
                logger.info(f"系统异步识别失败，通过插件 {MetatubeSource.plugin_name} 兜底执行：async_recognize_media ...")
                return await plugin_instance.async_recognize_media(meta, mtype)

            # 插件未启用，直接调用原始方法
            return await plugin_instance._original_async_method(chain_self, meta, mtype, tmdbid, doubanid, bangumiid,
                                                                episode_group, cache)

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
            self._keyword_failed_download = bool(config.get("keyword_failed_download") if config.get("keyword_failed_download") is not None else True)
            self._show_failure_detail = bool(config.get("show_failure_detail") if config.get("show_failure_detail") is not None else True)
            self._clear_logs_flag = bool(config.get("clear_logs_flag") or False)
            # 命名规则配置
            self._naming_template = config.get("naming_template") or "number_actor_studio"
            self._custom_naming_template = config.get("custom_naming_template") or ""
            self._max_actors = int(config.get("max_actors") or 2)
            # ThePornDB 配置
            self._theporndb_enabled = bool(config.get("theporndb_enabled") or False)
            self._theporndb_api_token = config.get("theporndb_api_token") or ""
            # 新增配置项
            self._exclude_keywords = config.get("exclude_keywords") or ""
            self._keywords_file_path = "keywords.json"  # 固定路径，不再提供配置
            self._failed_download_control = bool(config.get("failed_download_download") if config.get("failed_download_control") is not None else True)
            # 兼容旧配置项
            if config.get("keyword_failed_download") is not None:
                self._failed_download_control = bool(config.get("keyword_failed_download"))

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

        # 验证配置有效性
        self._validate_config()

        # 加载关键字文件（如果存在）
        self._load_keywords_from_file()

        if self._enabled:
            # 关键字触发模式：系统识别失败后接管，只处理包含关键字的内容
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
            }
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

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "strict_match",
                                            "label": "严格匹配",
                                            "hint": "区分大小写和全半角"
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
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
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "failed_download_control",
                                            "label": "失败自动下载",
                                            "hint": "识别失败时归类为'成人'并自动下载"
                                        }
                                    }
                                ]
                            }
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
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
                                "props": {"cols": 12, "md": 3},
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
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "timeout",
                                            "label": "超时时间",
                                            "type": "number",
                                            "placeholder": "30",
                                            "suffix": "秒",
                                            "hint": "API请求超时（1-60秒）"
                                        }
                                    }
                                ]
                            }
                        ],
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
                                            "hint": "Metatube服务地址，如：http://192.168.1.100:8080"
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
                                            "placeholder": "从 https://theporndb.net 获取API Token",
                                            "hint": "登录 ThePornDB 后在设置页面获取 Metadata API Token"
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
                                        "text": "命名规则配置"
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
                                            "hint": "选择文件重命名格式"
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
                                            "hint": "最多显示几位演员"
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
                                            "hint": "变量: {number} {actor} {studio} {label} {year} {series} {title}"
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
                                        "text": "自定义关键词配置（按分类管理）"
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
                                            "label": "日系关键词",
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
                                            "label": "欧美系关键词",
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
                                            "label": "中文系关键词",
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
                                            "label": "其他关键词",
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
                                            "label": "排除关键词",
                                            "placeholder": "4K, UHD, HDR, FHD, HD, 2160P, 1080P, 720P, 60FPS, H.265, H.264, HEVC, XVID, WEB-DL, REMUX, BLURAY...",
                                            "rows": 3,
                                            "hint": "匹配后直接跳过分类的关键词（画质标记、分辨率、编码格式等），逗号分隔。内置42个排除关键字：4K/UHD/HDR/FHD/HD/SD/2160P/1080P/720P/480P/360P/60FPS/120FPS/240FPS/H.265/H.264/HEVC/XVID/X264/X265/VC-1/VP9/AV1/AC3/DTS/AAC/FLAC/REMUX/WEB-DL/WEBRIP/BLURAY/NTSC/PAL/SECA/CD1/CD2/DISC1/DISC2"
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
                                                        "text": "• 关键字触发：标题包含指定关键字时使用 Metatube 识别，系统识别失败后自动接管"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 欧美系专用：启用 ThePornDB 后，匹配欧美系关键字的内容将使用 ThePornDB 识别"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 二级分类：自动识别内容类型并归类为「成人/日系」、「成人/欧美系」、「成人/中文系」、「成人/其他」"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 优先级：日系 > 欧美系 > 中文系 > 其他（匹配到第一个即停止）"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 排除关键字：配置排除关键字后，匹配到的内容将跳过分类"
                                                    },
                                                    {
                                                        "component": "p",
                                                        "text": "• 关键字文件：支持从 keywords.json 文件加载关键字配置（文件位于插件根目录）"
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
            "theporndb_api_token": ""
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
                status_color = "success" if log.status == "success" else "error"
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

    def stop_service(self):
        """退出插件"""
        if (getattr(ChainBase.recognize_media, "_patched_by", object()) == id(self) and
                self._original_method):
            ChainBase.recognize_media = self._original_method
        if (getattr(ChainBase.async_recognize_media, "_patched_by", object()) == id(self) and
                self._original_async_method):
            ChainBase.async_recognize_media = self._original_async_method

    def get_module(self) -> Dict[str, Any]:
        """获取插件模块声明"""
        # 已移除劫持模式，返回空
        return {}

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
        """从 JSON 文件加载关键字配置"""
        try:
            import json
            from pathlib import Path

            # 支持相对路径和绝对路径
            if not Path(self._keywords_file_path).is_absolute():
                # 相对于插件根目录
                plugin_dir = Path(__file__).parent
                keywords_file = plugin_dir / self._keywords_file_path
            else:
                keywords_file = Path(self._keywords_file_path)

            if not keywords_file.exists():
                logger.debug(f"Metatube: 关键字配置文件不存在: {keywords_file}，使用内置关键字")
                return

            # 读取 JSON 文件
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords_config = json.load(f)

                # 加载各分类关键字
                if 'japanese' in keywords_config and isinstance(keywords_config['japanese'], list):
                    self._custom_japanese_keywords = ','.join(keywords_config['japanese'])
                if 'western' in keywords_config and isinstance(keywords_config['western'], list):
                    self._custom_western_keywords = ','.join(keywords_config['western'])
                if 'chinese' in keywords_config and isinstance(keywords_config['chinese'], list):
                    self._custom_chinese_keywords = ','.join(keywords_config['chinese'])
                if 'other' in keywords_config and isinstance(keywords_config['other'], list):
                    self._custom_other_keywords = ','.join(keywords_config['other'])
                if 'exclude' in keywords_config and isinstance(keywords_config['exclude'], list):
                    self._exclude_keywords = ','.join(keywords_config['exclude'])

                logger.info(f"Metatube: 已从 {keywords_file} 加载关键字配置")

        except json.JSONDecodeError as e:
            logger.error(f"Metatube: 关键字配置文件 JSON 格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"Metatube: 加载关键字配置文件失败: {str(e)}")

    def _build_category(self, subcategory: str) -> str:
        """构建分类字符串"""
        return f"{self.CATEGORY_PREFIX}/{subcategory}"

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
            "theporndb_api_token": self._theporndb_api_token
        })

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

    def _get_all_keywords(self) -> List[str]:
        """获取所有关键字（内置 + 自定义）"""
        keywords = []

        # 添加所有分类的内置关键字
        keywords.extend(self.BUILT_IN_JAPANESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_WESTERN_KEYWORDS)
        keywords.extend(self.BUILT_IN_CHINESE_KEYWORDS)
        keywords.extend(self.BUILT_IN_OTHER_KEYWORDS)

        # 添加自定义关键字
        if self._custom_japanese_keywords:
            custom_list = [kw.strip() for kw in self._custom_japanese_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_western_keywords:
            custom_list = [kw.strip() for kw in self._custom_western_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_chinese_keywords:
            custom_list = [kw.strip() for kw in self._custom_chinese_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)
        if self._custom_other_keywords:
            custom_list = [kw.strip() for kw in self._custom_other_keywords.split(',') if kw.strip()]
            keywords.extend(custom_list)

        # 去重并返回
        return list(set(keywords))

    def _get_exclude_keywords(self) -> List[str]:
        """获取排除关键字列表（内置 + 自定义）"""
        exclude_keywords = []

        # 添加内置排除关键字
        exclude_keywords.extend(self.BUILT_IN_EXCLUDE_KEYWORDS)

        # 添加自定义排除关键字
        if self._exclude_keywords:
            custom_list = [kw.strip() for kw in self._exclude_keywords.split(',') if kw.strip()]
            exclude_keywords.extend(custom_list)

        # 标准化（非严格模式转大写）
        if not self._strict_match:
            exclude_keywords = [kw.upper() for kw in exclude_keywords]

        # 去重并返回
        return list(set(exclude_keywords))

    def _detect_category_type(self, title: str) -> str:
        """
        检测标题匹配的关键字类型，返回二级分类名称

        :param title: 标题文本
        :return: 二级分类名称：日系/欧美系/中文系/其他
        """
        if not title:
            return self.SUBCATEGORY_OTHER

        # 检查排除关键字
        exclude_keywords = self._get_exclude_keywords()
        if exclude_keywords:
            search_title = title.upper() if not self._strict_match else title
            for exclude_kw in exclude_keywords:
                if exclude_kw in search_title:
                    logger.debug(f"Metatube: 匹配到排除关键字 '{exclude_kw}'，跳过分类: {title}")
                    return self.SUBCATEGORY_OTHER

        # 标准化标题
        search_title = title
        if not self._strict_match:
            search_title = title.upper()
            search_title = search_title.replace('－', '-').replace('＿', '_')

        # 按优先级检测：日系 > 欧美系 > 中文系 > 其他
        categories = [
            (self.SUBCATEGORY_JAPANESE, self.BUILT_IN_JAPANESE_KEYWORDS, self._custom_japanese_keywords),
            (self.SUBCATEGORY_WESTERN, self.BUILT_IN_WESTERN_KEYWORDS, self._custom_western_keywords),
            (self.SUBCATEGORY_CHINESE, self.BUILT_IN_CHINESE_KEYWORDS, self._custom_chinese_keywords),
            (self.SUBCATEGORY_OTHER, self.BUILT_IN_OTHER_KEYWORDS, self._custom_other_keywords),
        ]

        for category_name, built_in_keywords, custom_keywords in categories:
            # 检查内置关键字
            for keyword in built_in_keywords:
                search_keyword = keyword.upper() if not self._strict_match else keyword
                if search_keyword in search_title:
                    logger.debug(f"Metatube: 匹配到{category_name}关键字 '{keyword}' 在标题 '{title}' 中")
                    return category_name

            # 检查自定义关键字
            if custom_keywords:
                custom_list = [kw.strip() for kw in custom_keywords.split(',') if kw.strip()]
                for keyword in custom_list:
                    search_keyword = keyword.upper() if not self._strict_match else keyword
                    if search_keyword in search_title:
                        logger.debug(f"Metatube: 匹配到{category_name}自定义关键字 '{keyword}' 在标题 '{title}' 中")
                        return category_name

        return self.SUBCATEGORY_OTHER

    def _match_keywords(self, meta: MetaBase) -> bool:
        """
        检查元数据是否匹配关键字

        :param meta: 元数据对象
        :return: 是否匹配
        """
        if not meta:
            return False

        # 获取所有关键字
        keywords = self._get_all_keywords()
        if not keywords:
            return False

        # 获取排除关键字
        exclude_keywords = self._get_exclude_keywords()

        # 获取标题（优先级：原始名称 > 中文名 > 英文名）
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or ""
        if not title:
            return False

        # 标准化标题
        if not self._strict_match:
            # 非严格模式：转大写，统一全半角
            title = title.upper()
            title = title.replace('－', '-').replace('＿', '_')
            keywords = [kw.upper() for kw in keywords]
            exclude_keywords = [kw.upper() for kw in exclude_keywords]

        # 先检查排除关键字
        for exclude_kw in exclude_keywords:
            if exclude_kw in title:
                logger.debug(f"Metatube: 匹配到排除关键字 '{exclude_kw}'，跳过: {title}")
                return False

        # 检查是否包含任意关键字
        for keyword in keywords:
            if keyword in title:
                logger.info(f"Metatube: 匹配到关键字 '{keyword}' 在标题 '{title}' 中")
                return True

        return False

    def _extract_number_from_meta(self, meta: MetaBase) -> Optional[str]:
        """从元数据中提取番号"""
        if not meta:
            return None

        # 优先从原始名称提取
        name = meta.org_string or meta.name or ""
        number = MetatubeApiClient.extract_number(name)
        if number:
            return number

        # 尝试从中文名提取
        if meta.cn_name:
            number = MetatubeApiClient.extract_number(meta.cn_name)
            if number:
                return number

        # 尝试从英文名提取
        if meta.en_name:
            number = MetatubeApiClient.extract_number(meta.en_name)
            if number:
                return number

        return None

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

        # 检测二级分类
        title = movie.title or movie.number or ""
        subcategory = self._detect_category_type(title)
        category = self._build_category(subcategory)

        # 设置分类（使用二级分类）
        mediainfo.set_category(category)
        logger.info(f"Metatube: 分类设置为 '{category}' (基于标题: {title})")

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

    def recognize_media(self, meta: MetaBase = None,
                        mtype: MediaType = None,
                        **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息

        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None

        if not meta:
            return None

        # 提取番号
        number = self._extract_number_from_meta(meta)
        if not number:
            logger.debug(f"Metatube: 无法从 '{meta.name}' 中提取番号")
            return None

        logger.info(f"Metatube: 正在识别番号 {number} ...")

        # 获取标题用于判断分类
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or number

        # 欧美系内容优先使用 ThePornDB
        if self._should_use_theporndb(title):
            logger.info(f"Metatube: 检测到欧美系内容，转交 ThePornDB 处理")
            result = self._recognize_with_theporndb(title)
            if result:
                return result
            # ThePornDB 识别失败，不再回退到 Metatube，直接按欧美系处理
            logger.info(f"Metatube: ThePornDB 识别失败，欧美系内容不回退 Metatube")
            if self._failed_download_control:
                category = self._build_category(self.SUBCATEGORY_WESTERN)
                logger.info(f"Metatube: 欧美系内容识别失败，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'theporndb'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "ThePornDB识别失败但已归类为欧美系", category=category)
                return mediainfo
            else:
                self._add_log(number, "", "failed", "ThePornDB识别失败，未启用失败自动下载", category=self._build_category(self.SUBCATEGORY_WESTERN))
                return None

        try:
            # 搜索
            results = self._metatube_client.search(number, fallback=True)
            if not results:
                # 识别失败处理
                failure_msg = "未找到匹配结果" if self._show_failure_detail else "识别失败"
                self._add_log(number, "", "failed", failure_msg, category="")
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")

                # 识别失败直接归类为"成人/其他"并返回
                if self._keyword_failed_download:
                    # 检测分类
                    subcategory = self._detect_category_type(number)
                    category = f"成人/{subcategory}"
                    logger.info(f"Metatube: 关键字触发模式识别失败，归类为'{category}'分类")
                    mediainfo = MediaInfo()
                    mediainfo.source = 'metatube'
                    mediainfo.type = MediaType.MOVIE
                    mediainfo.title = number
                    mediainfo.original_title = number
                    mediainfo.imdb_id = number
                    mediainfo.set_category(category)
                    self._add_log(number, f"{category} ({number})", "success", "识别失败但已归类为" + subcategory, category=category)
                    return mediainfo

                return None

            # 取第一个结果
            movie = results[0]

            # 尝试获取详情(可选)
            detail = None
            if movie.provider and movie.id:
                try:
                    detail = self._metatube_client.get_detail(movie.provider, movie.id)
                except Exception as e:
                    logger.debug(f"Metatube: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(movie, detail)

            # 获取分类信息
            title_for_category = movie.title or movie.number or ""
            subcategory = self._detect_category_type(title_for_category)
            category = f"成人/{subcategory}"

            self._add_log(number, mediainfo.title, "success",
                          f"来源: {movie.provider}", category=category)
            logger.info(f"Metatube: 识别成功 - {number} -> {mediainfo.title}")

            return mediainfo

        except Exception as e:
            # 异常处理
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            self._add_log(number, "", "failed", failure_msg, category="")
            logger.error(f"Metatube: 识别异常 - {str(e)}")

            # 识别异常处理：关键字触发模式下归类为"成人/其他"
            if self._failed_download_control:
                # 检测分类
                subcategory = self._detect_category_type(number)
                category = self._build_category(subcategory)
                logger.info(f"Metatube: 关键字触发模式识别异常，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'metatube'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "识别异常但已归类为" + subcategory, category=category)
                return mediainfo

            return None

    async def async_recognize_media(self, meta: MetaBase = None,
                                    mtype: MediaType = None,
                                    **kwargs) -> Optional[MediaInfo]:
        """
        异步识别媒体信息

        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        if not self._enabled:
            return None

        if not meta:
            return None

        # 提取番号
        number = self._extract_number_from_meta(meta)
        if not number:
            logger.debug(f"Metatube: 无法从 '{meta.name}' 中提取番号")
            return None

        logger.info(f"Metatube: 正在异步识别番号 {number} ...")

        # 获取标题用于判断分类
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or number

        # 欧美系内容优先使用 ThePornDB
        if self._should_use_theporndb(title):
            logger.info(f"Metatube: 检测到欧美系内容，转交 ThePornDB 处理")
            result = await self._async_recognize_with_theporndb(title)
            if result:
                return result
            # ThePornDB 识别失败，不再回退到 Metatube，直接按欧美系处理
            logger.info(f"Metatube: ThePornDB 识别失败，欧美系内容不回退 Metatube")
            if self._failed_download_control:
                category = self._build_category(self.SUBCATEGORY_WESTERN)
                logger.info(f"Metatube: 欧美系内容识别失败，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'theporndb'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "ThePornDB识别失败但已归类为欧美系", category=category)
                return mediainfo
            else:
                self._add_log(number, "", "failed", "ThePornDB识别失败，未启用失败自动下载", category=self._build_category(self.SUBCATEGORY_WESTERN))
                return None

        try:
            # 异步搜索
            results = await self._metatube_client.async_search(number, fallback=True)
            if not results:
                # 识别失败处理
                failure_msg = "未找到匹配结果" if self._show_failure_detail else "识别失败"
                self._add_log(number, "", "failed", failure_msg, category="")
                logger.warning(f"Metatube: 番号 {number} 未找到匹配结果")

                # 识别失败直接归类为"成人/其他"并返回
                if self._keyword_failed_download:
                    # 检测分类
                    subcategory = self._detect_category_type(number)
                    category = f"成人/{subcategory}"
                    logger.info(f"Metatube: 关键字触发模式识别失败，归类为'{category}'分类")
                    mediainfo = MediaInfo()
                    mediainfo.source = 'metatube'
                    mediainfo.type = MediaType.MOVIE
                    mediainfo.title = number
                    mediainfo.original_title = number
                    mediainfo.imdb_id = number
                    mediainfo.set_category(category)
                    self._add_log(number, f"{category} ({number})", "success", "识别失败但已归类为" + subcategory, category=category)
                    return mediainfo

                return None

            # 取第一个结果
            movie = results[0]

            # 尝试获取详情(可选)
            detail = None
            if movie.provider and movie.id:
                try:
                    detail = await self._metatube_client.async_get_detail(movie.provider, movie.id)
                except Exception as e:
                    logger.debug(f"Metatube: 获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(movie, detail)

            # 获取分类信息
            title_for_category = movie.title or movie.number or ""
            subcategory = self._detect_category_type(title_for_category)
            category = f"成人/{subcategory}"

            self._add_log(number, mediainfo.title, "success",
                          f"来源: {movie.provider}", category=category)
            logger.info(f"Metatube: 识别成功 - {number} -> {mediainfo.title}")

            return mediainfo

        except Exception as e:
            # 异常处理
            failure_msg = str(e) if self._show_failure_detail else "识别异常"
            self._add_log(number, "", "failed", failure_msg, category="")
            logger.error(f"Metatube: 异步识别异常 - {str(e)}")

            # 异常处理：关键字触发模式下归类为"成人/其他"
            if self._keyword_failed_download:
                # 检测分类
                subcategory = self._detect_category_type(number)
                category = f"成人/{subcategory}"
                logger.info(f"Metatube: 关键字触发模式识别异常，归类为'{category}'分类")
                mediainfo = MediaInfo()
                mediainfo.source = 'metatube'
                mediainfo.type = MediaType.MOVIE
                mediainfo.title = number
                mediainfo.original_title = number
                mediainfo.imdb_id = number
                mediainfo.set_category(category)
                self._add_log(number, f"{category} ({number})", "success", "识别异常但已归类为" + subcategory, category=category)
                return mediainfo

            return None
