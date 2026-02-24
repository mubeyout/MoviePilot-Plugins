# Category: 核心模块
"""
Metatube 核心识别器
"""
import re
from typing import Optional, List, Dict, Any
from collections import deque
from datetime import datetime
from ..models.base import (
    MediaInfo, RecognitionResult, RecognitionContext,
    RecognitionStatus, LogEntry, LogConfig
)
from ..config.settings import MetatubeConfig
from ..api import (
    MetatubeApiClient, ThePornDBApiClient, ByteMuseApiClient
)

class MediaRecognizer:
    """媒体识别器"""

    def __init__(self, config: MetatubeConfig):
        self.config = config
        self._metatube_client = MetatubeApiClient(
            base_url=config.api_url,
            timeout=config.timeout
        )
        self._theporndb_client = ThePornDBApiClient(
            api_token=config.theporndb.api_token,
            timeout=config.timeout
        )
        self._bytemuse_client = ByteMuseApiClient(
            base_url=config.bytemuse.url,
            username=config.bytemuse.username,
            password=config.bytemuse.password,
            api_token=config.bytemuse.api_token,
            timeout=config.timeout
        )
        self._log_entries = deque(maxlen=config.max_logs)

    def _extract_number_from_meta(self, meta: Any, detected_category: str) -> Optional[str]:
        """从元数据中提取番号"""
        if not meta:
            return None

        # 获取可能的标题字段
        title = meta.org_string or meta.cn_name or meta.en_name or meta.name or ""
        if not title:
            return None

        # 清理标题
        title = title.upper().strip()
        title = re.sub(r'\[.*?\]', ' ', title)
        title = re.sub(r'\(.*?\)', ' ', title)
        title = re.sub(r'[@＠].*', '', title)

        # 尝试匹配各种番号格式
        number_patterns = [
            # FC2 系列
            r'(FC2)[-_]?(PPV)?[-_]?(\d{5,7})',
            # HEYZO 系列
            r'(HEYZO)[-_]?(\d{4})',
            # Tokyo Hot 系列
            r'([nNK]|K|KD)[-_]?(\d{4,5})',
            # 主流标准格式
            r'([A-Z]{2,10})[-_]?(\d{2,5})',
            # 素人/单体系列
            r'(10MUSUME|10MU)[-_]?(\d{2,4})',
            r'(PACO|PACOPACO)[-_]?(\d{3,5})',
            r'(XXX[-_]?AV|AV)[-_]?(\d{5})',
            # 网站系列
            r'(CARIB|CARIBPR|CARIBBEANCOM)[-_]?(\d{6})[-_]?(\d{3})',
            r'(\d{6})[_-](\d{3})',
            r'(S2M|SKY|SKYHIGH)[-_]?(\d{3,4})',
            r'(RED|REDHOT)[-_]?(\d{3})',
            # 数字编号系列
            r'(H\d{4})[-_]?(\d{3})',
            r'(C\d{4})[-_]?(\d{3})',
            r'(\d{6})[-_](\d{3})',
            # 特殊厂商
            r'(KIN8|TENGOKU|ENG)[-_]?(\d{3,5})',
            r'(GOLD)[-_]?(\d{3,4})',
            r'(CWP)[-_]?(\d{3,5})',
            r'(ABP|ABW|BKSP)[-_]?(\d{3,4})',
            r'(SSIS|STARS|SSND|SNIS)[-_]?(\d{3,4})',
            r'(IPX|IPZ|IPZZ|MIAE|MIRD)[-_]?(\d{3,4})',
            r'(EBOD|EBODY)[-_]?(\d{3,4})',
            r'(WANZ|WAAA)[-_]?(\d{3,4})',
            # VR系列
            r'(VR|3DVR|VRVR)[-_]?(\d{3,5})',
            # 欧美系列
            r'(RK)[-_]?(\d{4,5})',
            r'(XEMPIRE|DARKX|EROTICAX|HARDX|LESBIANX)[-_]?(\d{3,5})',
            r'(21SEXTURY|21NATURALS|21FOOTART|21EROTICA)[-_]?(\d{3,5})',
            # 中文系列
            r'(MDTV|MDX|MD|JD)[-_]?(\d{3,4})',
            # 复合格式
            r'([A-Z]{2,6})[-_]?(\d{3,5})[-_]?([A-Z]{0,4})',
            r'(\d{5,6})[-_](\d{3})',
        ]

        for pattern in number_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return f"{groups[0]}-{groups[1]}".upper()
                elif len(groups) == 3:
                    if groups[0] == 'FC2':
                        if groups[1]:
                            return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                        else:
                            return f"{groups[0]}-{groups[2]}".upper()
                    elif groups[0] in ['CARIB', 'CARIBPR', 'CARIBBEANCOM']:
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                    elif groups[1] is None or groups[1] == '':
                        return f"{groups[0]}-{groups[2]}".upper()
                    else:
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()

        return None

    def _recognize_with_bytemuse(self, number: str) -> RecognitionResult:
        """使用 ByteMuse 识别媒体"""
        if not self.config.bytemuse.enabled:
            return RecognitionResult(RecognitionStatus.FAIL, None, "ByteMuse 未启用")

        try:
            logger = self._get_logger()
            logger.info(f"使用 ByteMuse 识别番号: {number}")

            result = self._bytemuse_client.search(number)
            if not result:
                logger.warning(f"ByteMuse 识别失败: {number}")
                return RecognitionResult(RecognitionStatus.FAIL, None, "ByteMuse 识别失败")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(result[0])
            logger.info(f"ByteMuse 识别成功: {number} -> {mediainfo.title}")

            return RecognitionResult(RecognitionStatus.SUCCESS, mediainfo, None, "bytemuse")

        except Exception as e:
            error_msg = f"ByteMuse 识别异常: {str(e)}"
            logger = self._get_logger()
            logger.error(error_msg)
            return RecognitionResult(RecognitionStatus.FAIL, None, error_msg, "bytemuse")

    def _recognize_with_theporndb_jav(self, number: str) -> RecognitionResult:
        """使用 ThePornDB JAV API 识别媒体"""
        if not self.config.theporndb.enabled or not self.config.theporndb.api_token:
            return RecognitionResult(RecognitionStatus.FAIL, None, "ThePornDB JAV 未配置")

        try:
            logger = self._get_logger()
            logger.info(f"使用 ThePornDB JAV 识别 JAV 番号: {number}")

            result = self._theporndb_client.search_jav(number)
            if not result:
                logger.warning(f"ThePornDB JAV 识别失败: {number}")
                return RecognitionResult(RecognitionStatus.FAIL, None, "ThePornDB JAV 识别失败")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(result[0])
            logger.info(f"ThePornDB JAV 识别成功: {number} -> {mediainfo.title}")

            return RecognitionResult(RecognitionStatus.SUCCESS, mediainfo, None, "theporndb_jav")

        except Exception as e:
            error_msg = f"ThePornDB JAV 识别异常: {str(e)}"
            logger = self._get_logger()
            logger.error(error_msg)
            return RecognitionResult(RecognitionStatus.FAIL, None, error_msg, "theporndb_jav")

    def _recognize_with_metatube(self, number: str) -> RecognitionResult:
        """使用 Metatube API 识别媒体"""
        try:
            logger = self._get_logger()
            logger.info(f"使用 Metatube API 识别番号: {number}")

            results = self._metatube_client.search(number, fallback=True)
            if not results:
                logger.warning(f"Metatube API 未找到匹配结果: {number}")
                return RecognitionResult(RecognitionStatus.FAIL, None, "Metatube API 未找到匹配结果")

            # 取第一个结果
            movie = results[0]

            # 尝试获取详情
            detail = None
            if movie.provider and movie.id:
                try:
                    detail = self._metatube_client.get_detail(movie.provider, movie.id)
                except Exception as e:
                    logger.debug(f"获取详情失败: {str(e)}")

            # 转换为 MediaInfo
            mediainfo = self._convert_to_mediainfo(movie, detail)
            logger.info(f"Metatube API 识别成功: {number} -> {mediainfo.title}")

            return RecognitionResult(RecognitionStatus.SUCCESS, mediainfo, None, "metatube")

        except Exception as e:
            error_msg = f"Metatube API 识别异常: {str(e)}"
            logger = self._get_logger()
            logger.error(error_msg)
            return RecognitionResult(RecognitionStatus.FAIL, None, error_msg, "metatube")

    def _convert_to_mediainfo(self, movie: Any, detail: Any = None) -> MediaInfo:
        """将 API 结果转换为 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = "metatubesource"
        mediainfo.type = MediaType.MOVIE
        mediainfo.title = movie.title or ""
        mediainfo.original_title = movie.title or ""
        mediainfo.imdb_id = movie.external_id or ""
        mediainfo.year = movie.year
        mediainfo.description = movie.description or ""

        # 添加演员
        if hasattr(movie, 'actors') and movie.actors:
            for actor in movie.actors:
                mediainfo.add_actor(actor.name if hasattr(actor, 'name') else actor)

        # 添加片商
        if hasattr(movie, 'studios') and movie.studios:
            for studio in movie.studios:
                mediainfo.add_studio(studio.name if hasattr(studio, 'name') else studio)

        # 添加标签
        if hasattr(movie, 'tags') and movie.tags:
            mediainfo.tags = [tag.name if hasattr(tag, 'name') else tag for tag in movie.tags]

        # 添加详情信息
        if detail:
            if hasattr(detail, 'poster') and detail.poster:
                mediainfo.poster = detail.poster
            if hasattr(detail, 'backdrop') and detail.backdrop:
                mediainfo.backdrop = detail.backdrop

        return mediainfo

    def _get_logger(self):
        """获取日志记录器"""
        # 这里应该返回实际的 logger，简化处理
        return type('Logger', (), {'info': print, 'warning': print, 'error': print, 'debug': print})()

    def _add_log(self, message: str, level: str = "info", source: str = "metatubesource"):
        """添加日志条目"""
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            source=source
        )
        self._log_entries.append(log_entry)
        if LogConfig.should_log(message):
            print(f"[{level.upper()}] {message}")

    def recognize(self, context: RecognitionContext) -> RecognitionResult:
        """识别媒体"""
        logger = self._get_logger()
        logger.info(f"开始识别: {context.title}")

        # 检查是否应该处理
        if not self._should_process(context):
            logger.info(f"跳过识别: {context.title}")
            return RecognitionResult(RecognitionStatus.FAIL, None, "不匹配成人内容")

        # 提取番号
        number = self._extract_number_from_meta(context.meta, context.detected_category)
        if not number:
            error_msg = f"无法从 '{context.title}' 中提取番号"
            logger.warning(error_msg)
            self._add_log(error_msg, "warning")
            return RecognitionResult(RecognitionStatus.FAIL, None, error_msg)

        logger.info(f"正在识别番号: {number} (分类: {context.detected_category})")

        # 1. 首先尝试 ByteMuse（如果启用）
        if self.config.bytemuse.enabled:
            result = self._recognize_with_bytemuse(number)
            if result.is_success:
                return result
            logger.info(f"ByteMuse 识别失败，尝试备用识别源")

        # 2. 尝试 ThePornDB JAV（如果是 JAV 格式且已启用）
        is_jav = self._is_jav_number(number)
        if is_jav and self.config.theporndb.enabled and self.config.theporndb.api_token:
            result = self._recognize_with_theporndb_jav(number)
            if result.is_success:
                return result
            logger.info(f"ThePornDB JAV 识别失败，继续尝试备用识别源")

        # 3. 使用 Metatube API 作为最后的选择
        result = self._recognize_with_metatube(number)
        return result

    def _should_process(self, context: RecognitionContext) -> bool:
        """判断是否应该处理"""
        return self.config.recognition.failed_download_control or self.keyword_matcher.is_adult_content(context.title)

    def _is_jav_number(self, number: str) -> bool:
        """判断是否为 JAV 格式番号"""
        # 简单的 JAV 番号格式判断
        jav_patterns = [
            r'^[A-Z]{2,4}-\d{3,5}$',  # 标准格式: SSIS-001
            r'^\d{5,6}-\d{3}$',      # 数字格式: 123456-123
        ]
        for pattern in jav_patterns:
            if re.match(pattern, number):
                return True
        return False

    def get_logs(self) -> List[LogEntry]:
        """获取日志条目"""
        return list(self._log_entries)

    def clear_logs(self):
        """清空日志"""
        self._log_entries.clear()
        self._add_log("识别日志已清空", "info")