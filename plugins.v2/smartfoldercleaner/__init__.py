import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any, Set

from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import NotificationType


class SmartFolderCleaner(_PluginBase):
    """
    智能文件夹清理插件
    根据自定义规则删除"无有效文件"的文件夹
    """

    # ==================================================================
    # 插件元信息
    # ==================================================================
    plugin_name = "SmartFolderCleaner"
    plugin_desc = "遍历指定目录，删除符合自定义'空文件夹'定义的目录（无有效文件的目录）"
    plugin_version = "2.1"
    plugin_author = "MUBEY"
    plugin_icon = "delete.png"
    plugin_config_prefix = "smartfoldercleaner_"

    # ==================================================================
    # JSON 配置文件路径
    # ==================================================================
    CONFIG_FILE = Path("/config/plugins/smartfoldercleaner_config.json")

    # ==================================================================
    # 常量定义
    # ==================================================================

    # 文件类型扩展名常量
    DEFAULT_VIDEO_EXTENSIONS = [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".ts", ".mts", ".m2ts", ".rmvb", ".rm", ".3gp", ".3g2", ".asf",
        ".divx", ".xvid", ".vob", ".qt", ".yuv", ".f4v", ".ogv", ".dv",
        ".mxm", ".mpeg", ".mpg", ".mpe"
    ]

    DEFAULT_IMAGE_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
        ".svg", ".ico", ".psd", ".raw", ".cr2", ".nef", ".arw", ".dng",
        ".heic", ".heif", ".avif", ".jxl", ".jp2", ".j2k", ".exr", ".pnm",
        ".pbm", ".pgm", ".ppm", ".sr"
    ]

    DEFAULT_AUDIO_EXTENSIONS = [
        ".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".ape",
        ".opus", ".alac", ".ac3", ".dts", ".dtshd", ".truehd", ".aiff",
        ".aif", ".aifc", ".amr", ".au", ".ra", ".m4p", ".m4b", ".m4r",
        ".mp2", ".mp1", ".mpc", ".oma", ".tak", ".tta", ".wv", ".gsm", ".caf"
    ]

    DEFAULT_OTHER_EXTENSIONS = [
        ".txt", ".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt", ".smi",
        ".sup", ".rt", ".xml"
    ]

    # 排除文件扩展名（临时文件、下载中文件）
    DEFAULT_EXCLUDE_EXTENSIONS = [
        ".part",".!qB", ".aria2", ".qB",".download", 
        ".Thumbs.db", ".td", ".lnk", ".sync",".transmission", ".mt",".bt",".strm"
    ]

    # 默认排除的文件夹名称
    DEFAULT_EXCLUDED_FOLDERS = [
        "sample", "samples", "__macosx", "@eadir",
        ".ds_store", "thumbs.db", "recycle"
    ]

    # 大小单位转换常量
    SIZE_MULTIPLIERS = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4
    }

    # 系统保护路径（正则表达式模式）
    SYSTEM_PATH_PATTERNS = [
        r'^/system(/|$)',
        r'^/bin(/|$)',
        r'^/sbin(/|$)',
        r'^/usr/bin(/|$)',
        r'^/usr/sbin(/|$)',
        r'^/etc(/|$)',
        r'^/var(/|$)',
        r'^/proc(/|$)',
        r'^/dev(/|$)',
        r'^/sys(/|$)',
        r'^/boot(/|$)',
        r'^/lib(/|$)',
        r'^/lib64(/|$)',
        r'^/root(/|$)',
        r'^/home/[^/]+/\.(.+$)',  # 用户隐藏目录
    ]

    # Windows系统路径
    WINDOWS_SYSTEM_PATHS = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\System Volume Information",
        "C:\\Recovery",
    ]

    # ==================================================================
    # 私有属性
    # ==================================================================
    _enabled = False
    _cron = None
    _onlyonce = False
    _paths = []
    _dry_run = False
    _mode = "type_and_size"
    _size_unit = "MB"

    # 文件类型配置（使用Set提升查找效率）
    _video_enabled = False
    _video_extensions: Set[str] = set()
    _video_min_size = 0
    _video_min_size_unit = "MB"

    _image_enabled = False
    _image_extensions: Set[str] = set()
    _image_min_size = 0
    _image_min_size_unit = "MB"

    _audio_enabled = False
    _audio_extensions: Set[str] = set()
    _audio_min_size = 0
    _audio_min_size_unit = "MB"

    _other_enabled = False
    _other_extensions: Set[str] = set()
    _other_min_size = 0
    _other_min_size_unit = "MB"

    # 模式2: 仅按大小判定
    _global_min_size = 0
    _global_min_size_unit = "MB"

    # 排除配置
    _exclude_extensions: Set[str] = set()
    _excluded_folders: Set[str] = set()
    _protect_keywords: Set[str] = set()  # 保护关键字（文件名匹配时不删除）

    # 通用配置
    _notify = True
    _delete_invalid_files = False  # 是否删除无效文件

    # 编译后的正则表达式缓存
    _compiled_regex_cache: List[re.Pattern] = []

    # ==================================================================
    # JSON 配置文件管理
    # ==================================================================

    def _load_config_from_file(self) -> Dict[str, Any]:
        """
        从 JSON 文件加载配置
        """
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"从配置文件加载配置: {self.CONFIG_FILE}")
                return config
            else:
                logger.info(f"配置文件不存在，使用默认配置: {self.CONFIG_FILE}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()

    def _save_config_to_file(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到 JSON 文件
        """
        try:
            # 确保目录存在
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存到文件: {self.CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        """
        return {
            "enabled": False,
            "onlyonce": False,
            "cron": "0 2 * * *",
            "notify": True,
            "dry_run": False,
            "delete_invalid_files": False,
            "paths": "",
            "size_unit": "MB",
            "size_only_mode": False,
            "video_enabled": True,
            "video_extensions": ",".join(self.DEFAULT_VIDEO_EXTENSIONS),
            "video_min_size": 10,
            "image_enabled": True,
            "image_extensions": ",".join(self.DEFAULT_IMAGE_EXTENSIONS),
            "image_min_size": 1,
            "audio_enabled": True,
            "audio_extensions": ",".join(self.DEFAULT_AUDIO_EXTENSIONS),
            "audio_min_size": 1,
            "exclude_extensions": ",".join(self.DEFAULT_EXCLUDE_EXTENSIONS),
            "excluded_folders": ",".join(self.DEFAULT_EXCLUDED_FOLDERS),
            "protect_keywords": "",
            "global_min_size": 10
        }

    # ==================================================================
    # 插件初始化
    # ==================================================================
    def init_plugin(self, config: dict = None):
        """
        插件初始化
        """
        # 停止已有服务
        self.stop_service()

        if config:
            # 基础配置
            self._enabled = config.get("enabled", False)
            self._cron = config.get("cron")
            self._onlyonce = config.get("onlyonce", False)
            # 处理 paths 配置，可能是列表或字符串
            paths_config = config.get("paths")
            if isinstance(paths_config, list):
                self._paths = "\n".join(paths_config) if paths_config else ""
            else:
                self._paths = paths_config if paths_config else ""
            self._dry_run = config.get("dry_run", False)
            self._delete_invalid_files = config.get("delete_invalid_files", False)
            self._notify = config.get("notify") if config.get("notify") is not None else True

            # 统一单位选择器
            self._size_unit = config.get("size_unit", "MB")

            # 判定模式
            self._mode = "size_only" if config.get("size_only_mode") else "type_and_size"

            # 按类型+大小判定（size_only_mode=False）
            if self._mode == "type_and_size":
                self._video_enabled = config.get("video_enabled", True)
                video_ext_input = config.get("video_extensions", "").strip()
                self._video_extensions = set(self._parse_extensions(
                    video_ext_input,
                    self.DEFAULT_VIDEO_EXTENSIONS
                ))
                self._video_min_size = float(config.get("video_min_size", 10))
                self._video_min_size_unit = self._size_unit  # 直接使用统一单位

                self._image_enabled = config.get("image_enabled", True)
                image_ext_input = config.get("image_extensions", "").strip()
                self._image_extensions = set(self._parse_extensions(
                    image_ext_input,
                    self.DEFAULT_IMAGE_EXTENSIONS
                ))
                self._image_min_size = float(config.get("image_min_size", 1))
                self._image_min_size_unit = self._size_unit  # 直接使用统一单位

                self._audio_enabled = config.get("audio_enabled", True)
                audio_ext_input = config.get("audio_extensions", "").strip()
                self._audio_extensions = set(self._parse_extensions(
                    audio_ext_input,
                    self.DEFAULT_AUDIO_EXTENSIONS
                ))
                self._audio_min_size = float(config.get("audio_min_size", 1))
                self._audio_min_size_unit = self._size_unit  # 直接使用统一单位

            # 模式2: 仅按大小判定
            elif self._mode == "size_only":
                self._global_min_size = float(config.get("global_min_size", 10))
                self._global_min_size_unit = self._size_unit  # 直接使用统一单位

            # 排除文件格式（正在下载、临时文件等，始终启用）
            exclude_ext_input = config.get("exclude_extensions", "").strip()
            self._exclude_extensions = set(self._parse_extensions(
                exclude_ext_input,
                self.DEFAULT_EXCLUDE_EXTENSIONS
            ))

            # 保护关键字（文件名匹配时不删除）
            protect_keywords_input = config.get("protect_keywords", "").strip()
            self._protect_keywords = set(
                keyword.lower() for keyword in
                protect_keywords_input.split(",") if keyword.strip()
            )

            # 排除的文件夹名称
            exclude_folder_input = config.get("excluded_folders", "").strip()
            self._excluded_folders = set(
                name.lower() for name in
                (exclude_folder_input if exclude_folder_input else ",".join(self.DEFAULT_EXCLUDED_FOLDERS)).split(",")
                if name.strip()
            )

            # 配置验证
            self._validate_config()

            # 编译正则表达式缓存
            self._compiled_regex_cache = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.SYSTEM_PATH_PATTERNS
            ]

            # 输出配置信息（用于调试）
            logger.info(f"智能文件夹清理插件初始化完成:")
            logger.info(f"  - 模式: {self._mode}")
            logger.info(f"  - 监控目录: {self._paths if self._paths else '(未配置)'}")
            logger.info(f"  - 试运行: {self._dry_run}")
            if self._mode == "type_and_size":
                logger.info(f"  - 视频启用: {self._video_enabled}, 大小阈值: {self._video_min_size}{self._video_min_size_unit}")
                logger.info(f"  - 图片启用: {self._image_enabled}, 大小阈值: {self._image_min_size}{self._image_min_size_unit}")
                logger.info(f"  - 音频启用: {self._audio_enabled}, 大小阈值: {self._audio_min_size}{self._audio_min_size_unit}")
            else:
                logger.info(f"  - 全局大小阈值: {self._global_min_size}{self._global_min_size_unit}")
            logger.info(f"  - 排除扩展名: {len(self._exclude_extensions)}种")
            logger.info(f"  - 排除文件夹: {len(self._excluded_folders)}个")

            # 持久化配置
            self._update_config()

            # 立即运行一次（移到 if config: 块内部）
            if self._onlyonce:
                logger.info("智能文件夹清理服务启动，立即运行一次")
                # 先保存配置（onlyonce=False）
                self._onlyonce = False
                self._update_config()
                try:
                    deleted_count, deleted_files_count = self._scan_and_delete()
                    if self._notify and (deleted_count > 0 or deleted_files_count > 0):
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title="智能文件夹清理",
                            text=f"立即运行完成，共删除 {deleted_count} 个空文件夹" +
                                 (f"，{deleted_files_count} 个无效文件" if deleted_files_count > 0 else "")
                        )
                    logger.info(f"智能文件夹清理立即运行完成，共删除 {deleted_count} 个文件夹")
                except Exception as e:
                    logger.error(f"智能文件夹清理立即运行失败: {str(e)}")

    def _is_default_extensions(self, extensions: Set[str], defaults: List[str]) -> bool:
        """
        检查扩展名集合是否与默认值完全匹配

        :param extensions: 当前扩展名集合
        :param defaults: 默认扩展名列表
        :return: 如果完全匹配返回True
        """
        return extensions == set(defaults)

    def _update_config(self):
        """
        更新配置到持久化存储
        """
        # 检查扩展名是否为默认值，如果是则保存为空字符串
        video_ext = "" if self._is_default_extensions(self._video_extensions, self.DEFAULT_VIDEO_EXTENSIONS) else ",".join(sorted(self._video_extensions))
        image_ext = "" if self._is_default_extensions(self._image_extensions, self.DEFAULT_IMAGE_EXTENSIONS) else ",".join(sorted(self._image_extensions))
        audio_ext = "" if self._is_default_extensions(self._audio_extensions, self.DEFAULT_AUDIO_EXTENSIONS) else ",".join(sorted(self._audio_extensions))
        exclude_ext = "" if self._is_default_extensions(self._exclude_extensions, self.DEFAULT_EXCLUDE_EXTENSIONS) else ",".join(sorted(self._exclude_extensions))
        exclude_folder = "" if self._excluded_folders == set(f.lower() for f in self.DEFAULT_EXCLUDED_FOLDERS) else ",".join(sorted(self._excluded_folders))
        protect_keywords = ",".join(sorted(self._protect_keywords)) if self._protect_keywords else ""

        self.update_config({
            "enabled": self._enabled,
            "onlyonce": self._onlyonce,
            "cron": self._cron,
            "notify": self._notify,
            "dry_run": self._dry_run,
            "delete_invalid_files": self._delete_invalid_files,
            "paths": self._paths,
            "size_unit": self._size_unit,
            "size_only_mode": (self._mode == "size_only"),
            "video_enabled": self._video_enabled,
            "video_extensions": video_ext,
            "video_min_size": self._video_min_size,
            "image_enabled": self._image_enabled,
            "image_extensions": image_ext,
            "image_min_size": self._image_min_size,
            "audio_enabled": self._audio_enabled,
            "audio_extensions": audio_ext,
            "audio_min_size": self._audio_min_size,
            "exclude_extensions": exclude_ext,
            "excluded_folders": exclude_folder,
            "protect_keywords": protect_keywords,
            "global_min_size": self._global_min_size
        })

    def _validate_config(self):
        """
        验证配置的合理性
        """
        # 验证路径配置
        if not self._paths or not self._paths.strip():
            logger.warning("未配置目标目录，插件将不会执行任何操作")

        # 验证 type_and_size 模式
        if self._mode == "type_and_size":
            # 检查是否至少启用了一种文件类型
            if not any([
                self._video_enabled,
                self._image_enabled,
                self._audio_enabled
            ]):
                logger.warning("未启用任何文件类型，所有文件夹都将被视为空文件夹")

        # 验证路径安全性
        if self._paths:
            for path in self._paths.split("\n"):
                path = path.strip()
                if path and self._is_system_path(Path(path)):
                    logger.warning(f"检测到系统路径配置: {path}，为安全起见将跳过该路径")

    def _is_system_path(self, path: Path) -> bool:
        """
        检查路径是否为系统路径
        """
        path_str = str(path)

        # Windows系统路径检查
        if os.name == 'nt':
            for sys_path in self.WINDOWS_SYSTEM_PATHS:
                if path_str.lower().startswith(sys_path.lower()):
                    return True

        # Unix/Linux系统路径检查（使用预编译正则）
        for pattern in self._compiled_regex_cache:
            if pattern.match(path_str):
                return True

        return False

    def stop_service(self):
        """
        停止服务
        """
        pass

    # ==================================================================
    # 配置表单
    # ==================================================================
    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    # 基础设置
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 4, 'md': 3},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '启用插件',
                                            'model': 'enabled'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 4, 'md': 3},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '立即运行一次',
                                            'model': 'onlyonce'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 4, 'md': 3},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '发送通知',
                                            'model': 'notify'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 12, 'md': 3},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '定时周期',
                                            'model': 'cron',
                                            'placeholder': '0 2 * * *',
                                            'hint': 'cron表达式，默认每天凌晨2点'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 监控目录
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'label': '监控目录',
                                            'model': 'paths',
                                            'placeholder': '/path/to/folder1\n/path/to/folder2',
                                            'rows': 2,
                                            'hint': '每行一个目录路径'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 试运行模式
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '试运行模式（不实际删除，仅记录日志）',
                                            'model': 'dry_run',
                                            'color': 'warning'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '删除无效文件（删除不满足条件的文件）',
                                            'model': 'delete_invalid_files',
                                            'color': 'error',
                                            'hint': '开启后会删除不符合条件的文件（如太小的文件、未启用类型的文件）'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 判定模式选择
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '仅按大小判定（忽略文件类型）',
                                            'model': 'size_only_mode',
                                            'hint': '开启后只看文件大小，不区分类型'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'label': '统一单位',
                                            'model': 'size_unit',
                                            'items': [
                                                {'title': 'MB', 'value': 'MB'},
                                                {'title': 'GB', 'value': 'GB'},
                                                {'title': 'KB', 'value': 'KB'}
                                            ],
                                            'hint': '应用到所有文件类型'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 文件类型配置（分组布局 - 响应式）
                    {
                        'component': 'VRow',
                        'content': [
                            # 视频配置
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 6, 'md': 4, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '视频文件',
                                            'model': 'video_enabled'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '扩展名（补充）',
                                            'model': 'video_extensions',
                                            'placeholder': '留空使用内置格式，或输入自定义扩展名',
                                            'hint': '内置 .mp4, .mkv, .avi, .mov, .wmv, .flv 等30+种',
                                            'class': 'mt-4'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '最小大小',
                                            'type': 'number',
                                            'model': 'video_min_size',
                                            'suffix': 'MB',
                                            'class': 'mt-4'
                                        }
                                    }
                                ]
                            },
                            # 图片配置
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 6, 'md': 4, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '图片文件',
                                            'model': 'image_enabled'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '扩展名（补充）',
                                            'model': 'image_extensions',
                                            'placeholder': '留空使用内置格式，或输入自定义扩展名',
                                            'hint': '内置 .jpg, .png, .gif, .bmp, .webp 等25+种',
                                            'class': 'mt-4'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '最小大小',
                                            'type': 'number',
                                            'model': 'image_min_size',
                                            'suffix': 'MB',
                                            'class': 'mt-4'
                                        }
                                    }
                                ]
                            },
                            # 音频配置
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 6, 'md': 4, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'label': '音频文件',
                                            'model': 'audio_enabled'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '扩展名（补充）',
                                            'model': 'audio_extensions',
                                            'placeholder': '留空使用内置格式，或输入自定义扩展名',
                                            'hint': '内置 .mp3, .flac, .wav, .aac, .ogg 等20+种',
                                            'class': 'mt-4'
                                        }
                                    },
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '最小大小',
                                            'type': 'number',
                                            'model': 'audio_min_size',
                                            'suffix': 'MB',
                                            'class': 'mt-4'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 全局大小阈值（仅大小模式）
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'label': '全局最小文件大小（仅大小模式）',
                                            'type': 'number',
                                            'model': 'global_min_size',
                                            'suffix': 'MB',
                                            'hint': '启用"仅按大小判定"后生效'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 排除配置（响应式布局 + 增加间距）
                    {
                        'component': 'VRow',
                        'props': {'class': 'mt-4'},
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 6, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'label': '排除文件扩展名（补充）',
                                            'model': 'exclude_extensions',
                                            'placeholder': '留空使用内置列表，或输入自定义扩展名（逗号或换行分隔）',
                                            'rows': 2,
                                            'hint': '内置：.part, .torrent, .aria2, .td,.strm, .download 等20+种临时文件格式\n使用 "-.xxx" 从内置列表中移除（如：-.strm）'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'sm': 6, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'label': '排除文件夹名称（补充）',
                                            'model': 'excluded_folders',
                                            'placeholder': '留空使用内置列表，或输入自定义文件夹名（逗号或换行分隔）',
                                            'rows': 2,
                                            'hint': '内置：sample, samples, __macosx, @eadir 等常见示例文件夹'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'class': 'pa-3'},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'label': '保护关键字（文件名匹配时不删除）',
                                            'model': 'protect_keywords',
                                            'placeholder': '输入关键字，逗号或换行分隔',
                                            'rows': 2,
                                            'hint': '文件名包含这些关键字的文件不会被删除（如：trailer, sample, bonus）'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": "0 2 * * *",
            "notify": True,
            "dry_run": False,
            "paths": "",
            "size_unit": "MB",
            "size_only_mode": False,
            "video_enabled": True,
            "video_extensions": "",
            "video_min_size": 10,
            "image_enabled": True,
            "image_extensions": "",
            "image_min_size": 1,
            "audio_enabled": True,
            "audio_extensions": "",
            "audio_min_size": 1,
            "exclude_extensions": "",
            "excluded_folders": "",
            "protect_keywords": "",
            "global_min_size": 10
        }

    def get_page(self) -> List[dict]:
        """获取插件数据页面"""
        pass

    def get_state(self) -> bool:
        """获取插件状态"""
        return self._enabled if self._enabled else False

    def get_service(self) -> List[Dict[str, Any]]:
        """注册定时服务"""
        if not self._enabled or not self._cron:
            return []
        return [{
            "id": "SmartFolderCleaner",
            "name": "智能文件夹清理",
            "trigger": "cron",
            "func": self.clean_folders,
            "kwargs": {"cron": self._cron}
        }]

    def get_api(self) -> List[Dict[str, Any]]:
        """注册API接口"""
        return [{
            "path": "/smart_folder_cleaner/clean",
            "endpoint": self.clean_folders,
            "methods": ["POST"],
            "summary": "立即清理文件夹",
            "description": "扫描并删除符合条件的空文件夹"
        }]

    # ==================================================================
    # 公开方法
    # ==================================================================
    def clean_folders(self):
        """清理文件夹（定时任务调用）"""
        if not self._enabled:
            logger.info("智能文件夹清理插件未启用，跳过执行")
            return

        if not self._paths or not self._paths.strip():
            logger.warning("未配置目标目录，跳过执行")
            return

        logger.info("开始执行智能文件夹清理任务...")

        try:
            deleted_count, deleted_files_count = self._scan_and_delete()

            # 构建消息
            if self._dry_run:
                parts = []
                parts.append(f"试运行完成")
                if deleted_files_count > 0:
                    parts.append(f"将删除 {deleted_files_count} 个无效文件")
                if deleted_count > 0:
                    parts.append(f"将删除 {deleted_count} 个空文件夹")
                message = "，".join(parts)
            else:
                parts = []
                if deleted_files_count > 0:
                    parts.append(f"已删除 {deleted_files_count} 个无效文件")
                if deleted_count > 0:
                    parts.append(f"已删除 {deleted_count} 个空文件夹")
                message = "，".join(parts) if parts else "未删除任何文件或文件夹"

            if self._notify and (deleted_count > 0 or deleted_files_count > 0):
                self.post_message(
                    mtype=NotificationType.Plugin,
                    title="智能文件夹清理完成" if not self._dry_run else "智能文件夹清理试运行",
                    text=message
                )

            logger.info(f"智能文件夹清理任务完成，{message}")

        except Exception as e:
            logger.error(f"智能文件夹清理任务执行失败: {str(e)}")

    # ==================================================================
    # 私有方法
    # ==================================================================
    def _parse_extensions(self, extensions_str: str, default_extensions: List[str] = None) -> List[str]:
        """
        解析扩展名字符串为列表
        支持两种模式：
        1. 普通模式：直接添加扩展名（如 .mp4, .mkv）
        2. 排除模式：使用 - 前缀从默认列表中移除（如 -.strm）

        参数：
            extensions_str: 扩展名字符串（逗号分隔）
            default_extensions: 默认扩展名列表（用于排除模式）

        返回：
            最终的扩展名列表
        """
        extensions = set()
        remove_extensions = set()

        # 如果没有提供默认列表，使用空集合
        if default_extensions is None:
            default_extensions = []

        # 先添加所有默认扩展名
        extensions.update(default_extensions)

        # 解析输入的扩展名
        for ext in extensions_str.split(","):
            ext = ext.strip().lower()
            if not ext:
                continue

            # 检查是否为排除模式（以 - 开头）
            if ext.startswith("-"):
                # 排除模式：从列表中移除
                remove_ext = ext[1:].strip()  # 移除 - 符号
                if not remove_ext.startswith("."):
                    remove_ext = "." + remove_ext
                remove_extensions.add(remove_ext)
            else:
                # 普通模式：添加到列表
                if not ext.startswith("."):
                    ext = "." + ext
                extensions.add(ext)

        # 从最终列表中移除要排除的扩展名
        extensions -= remove_extensions

        return sorted(list(extensions))

    def _parse_size_to_bytes(self, size: float, unit: str) -> int:
        """
        将带单位的大小转换为字节数
        """
        multiplier = self.SIZE_MULTIPLIERS.get(unit, 1024 ** 2)  # 默认MB
        return int(size * multiplier)

    def _scan_and_delete(self) -> Tuple[int, int]:
        """
        扫描并删除空文件夹和无效文件
        返回 (删除的文件夹数量, 删除的文件数量)
        """
        deleted_count = 0
        deleted_files_total = 0
        paths = [p.strip() for p in self._paths.split("\n") if p.strip()]

        for path_str in paths:
            path = Path(path_str)

            # 路径安全检查
            if not path.exists():
                logger.warning(f"路径不存在: {path}")
                continue

            if not path.is_dir():
                logger.warning(f"路径不是目录: {path}")
                continue

            if self._is_system_path(path):
                logger.warning(f"跳过系统路径: {path}")
                continue

            logger.info(f"开始扫描目录: {path}")

            # 如果启用删除无效文件，先删除无效文件
            if self._delete_invalid_files:
                logger.info("删除无效文件功能已启用，开始扫描无效文件...")
                deleted_files_count = self._delete_invalid_files_in_path(path)
                deleted_files_total += deleted_files_count
                if deleted_files_count > 0:
                    logger.info(f"已删除 {deleted_files_count} 个无效文件")

            # 查找空文件夹
            empty_folders = self._find_empty_folders(path)

            # 删除空文件夹
            for folder in empty_folders:
                try:
                    if self._dry_run:
                        # 试运行模式：检查文件夹是否真的为空（可以被删除）
                        try:
                            # 尝试检查文件夹是否真的空
                            contents = list(folder.iterdir())
                            if contents:
                                # 文件夹不为空，无法删除
                                logger.debug(f"[试运行] 跳过非空文件夹: {folder} (包含 {len(contents)} 项)")
                            else:
                                # 文件夹为空，可以删除
                                logger.info(f"[试运行] 将删除文件夹: {folder}")
                                deleted_count += 1
                        except Exception as check_err:
                            logger.warning(f"[试运行] 检查文件夹失败 {folder}: {check_err}")
                    else:
                        # 实际删除模式
                        folder.rmdir()
                        logger.info(f"已删除文件夹: {folder}")
                        deleted_count += 1
                except OSError as e:
                    # 文件夹不为空（rmdir() 失败）
                    if "Directory not empty" in str(e) or "not empty" in str(e).lower():
                        logger.debug(f"文件夹不为空，跳过: {folder}")
                    else:
                        logger.error(f"删除文件夹失败 {folder}: {str(e)}")
                except Exception as e:
                    logger.error(f"删除文件夹失败 {folder}: {str(e)}")

        return deleted_count, deleted_files_total

    def _delete_invalid_files_in_path(self, root_path: Path) -> int:
        """
        删除路径中的所有无效文件
        无效文件定义：
        1. 太小的文件（不满足最小大小要求）
        2. 未启用类型的文件（如只启用视频时，音频文件被视为无效）

        注意：
        - 排除扩展名的文件不会被删除（如 .part, .torrent）
        - 排除文件夹内的文件不会被处理
        - 保护关键字匹配的文件不会被删除
        - 有效文件不会被删除

        返回删除的文件数量
        """
        deleted_count = 0

        # 递归遍历所有文件
        for file_path in root_path.rglob("*"):
            if not file_path.is_file():
                continue

            # 跳过排除文件夹内的文件
            parent_folder = file_path.parent
            if self._is_excluded_folder(parent_folder):
                continue

            # 检查文件名是否匹配保护关键字
            if self._protect_keywords:
                file_name_lower = file_path.name.lower()
                if any(keyword in file_name_lower for keyword in self._protect_keywords):
                    logger.debug(f"文件名匹配保护关键字，跳过: {file_path}")
                    continue

            # 检查文件扩展名
            ext = file_path.suffix.lower()

            # 排除扩展名的文件不删除
            if ext in self._exclude_extensions:
                continue

            # 检查文件是否为有效文件
            is_valid = self._is_valid_file(file_path)

            if is_valid:
                # 有效文件不删除
                continue

            # 无效文件，准备删除
            try:
                if self._dry_run:
                    # 试运行模式：只记录，不删除
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    logger.info(f"[试运行] 将删除无效文件: {file_path} ({file_size_mb:.2f} MB, {ext})")
                    deleted_count += 1
                else:
                    # 实际删除
                    file_path.unlink()
                    file_size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
                    logger.info(f"已删除无效文件: {file_path} ({file_size_mb:.2f} MB, {ext})")
                    deleted_count += 1
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {str(e)}")

        return deleted_count

    def _find_empty_folders(self, root_path: Path) -> List[Path]:
        """
        递归查找所有空文件夹
        从最深层开始检查，确保父目录在子目录删除后能被正确识别为空

        注意：排除的文件夹名称会被完全跳过，不进行任何遍历
        """
        empty_folders = []

        # 从最深到最浅排序
        all_dirs = sorted(root_path.rglob("*"), key=lambda p: (len(p.parts), str(p)), reverse=True)

        for current_path in all_dirs:
            if not current_path.is_dir():
                continue

            # 跳过根目录本身
            if current_path == root_path:
                continue

            # 跳过排除的文件夹（完全跳过，不遍历内部）
            if self._is_excluded_folder(current_path):
                logger.info(f"⏭️  跳过排除的文件夹: {current_path}")
                continue

            # 检查是否为空文件夹（无有效文件）
            if self._is_empty_folder(current_path):
                empty_folders.append(current_path)
                logger.info(f"发现空文件夹: {current_path}")

        return empty_folders

    def _is_empty_folder(self, folder_path: Path) -> bool:
        """
        判断文件夹是否为"空"（无有效文件）
        递归检查所有子文件夹中的文件

        判定逻辑：
        1. 只要包含排除扩展名的文件 → 绝对不能删除
        2. 只检查启用的文件类型
        3. 有任何有效文件 → 不能删除
        4. 只有没有任何文件（包括排除文件）且无子文件夹 → 才能删除
        """
        try:
            logger.info(f"🔍 检查文件夹: {folder_path}")

            # 统计文件
            total_valid_files = 0
            ignored_files = 0  # 排除扩展名的文件
            other_files = 0  # 未启用类型的文件
            has_excluded_files = False  # 是否包含排除文件

            # 递归检查所有文件
            for item in folder_path.rglob("*"):
                if not item.is_file():
                    continue

                ext = item.suffix.lower()

                # 首先检查是否为排除的文件扩展名（下载中、临时文件等）
                if ext in self._exclude_extensions:
                    ignored_files += 1
                    has_excluded_files = True
                    logger.info(f"  ⛔ 发现排除文件: {item.relative_to(folder_path)} ({ext})")
                    # 只要有一个排除文件，就绝对不能删除
                    # 但继续遍历以记录完整信息

                # 根据模式检查文件类型
                if self._mode == "type_and_size":
                    # 按类型+大小判定模式
                    is_valid = False

                    # 检查视频文件
                    if self._video_enabled and ext in self._video_extensions:
                        min_size_bytes = self._parse_size_to_bytes(
                            self._video_min_size,
                            self._video_min_size_unit
                        )
                        if item.stat().st_size >= min_size_bytes:
                            is_valid = True

                    # 检查图片文件
                    elif self._image_enabled and ext in self._image_extensions:
                        min_size_bytes = self._parse_size_to_bytes(
                            self._image_min_size,
                            self._image_min_size_unit
                        )
                        if item.stat().st_size >= min_size_bytes:
                            is_valid = True

                    # 检查音频文件
                    elif self._audio_enabled and ext in self._audio_extensions:
                        min_size_bytes = self._parse_size_to_bytes(
                            self._audio_min_size,
                            self._audio_min_size_unit
                        )
                        if item.stat().st_size >= min_size_bytes:
                            is_valid = True

                    # 未启用的类型或不符合条件
                    if not is_valid:
                        # 排除文件已经在上面统计过，这里不再重复统计
                        if ext not in self._exclude_extensions:
                            other_files += 1
                            logger.debug(f"  ○ 其他文件: {item.relative_to(folder_path)} ({ext}, {item.stat().st_size}字节)")
                    else:
                        total_valid_files += 1
                        logger.info(f"  ✓ 有效文件: {item.relative_to(folder_path)} ({ext}, {item.stat().st_size}字节)")

                elif self._mode == "size_only":
                    # 仅按大小判定模式
                    min_size_bytes = self._parse_size_to_bytes(
                        self._global_min_size,
                        self._global_min_size_unit
                    )
                    if item.stat().st_size >= min_size_bytes:
                        # 排除文件已经在上面统计过，这里不再重复统计
                        if ext not in self._exclude_extensions:
                            total_valid_files += 1
                            logger.info(f"  ✓ 有效文件: {item.relative_to(folder_path)} ({item.stat().st_size}字节)")
                    else:
                        # 排除文件已经在上面统计过，这里不再重复统计
                        if ext not in self._exclude_extensions:
                            other_files += 1
                            logger.debug(f"  ○ 小文件: {item.relative_to(folder_path)} ({item.stat().st_size}字节)")

            # 统计直接子文件夹数量
            subfolder_count = sum(1 for item in folder_path.iterdir() if item.is_dir())

            # 判定结果
            if has_excluded_files:
                # 包含排除文件 → 绝对不能删除
                logger.info(f"  ⛔ 文件夹 {folder_path.name}/ 包含排除扩展名文件，不能删除")
                logger.info(f"     - 忽略文件: {ignored_files} 个")
                if total_valid_files > 0:
                    logger.info(f"     - 有效文件: {total_valid_files} 个")
                if other_files > 0:
                    logger.info(f"     - 其他文件: {other_files} 个")
                if subfolder_count > 0:
                    logger.info(f"     - 子文件夹: {subfolder_count} 个")
                return False  # 绝对不删除

            if total_valid_files > 0:
                # 有有效文件，不是空文件夹
                logger.info(f"  ✅ 文件夹非空: 包含 {total_valid_files} 个有效文件")
                return False

            # 没有排除文件，也没有有效文件
            if subfolder_count > 0:
                # 有子文件夹，但不能删除（因为包含非空子文件夹）
                logger.info(f"  ⚠️  文件夹 {folder_path.name}/ 情况:")
                logger.info(f"     - 子文件夹: {subfolder_count} 个")
                if other_files > 0:
                    logger.info(f"     - 未启用类型文件: {other_files} 个")
                logger.info(f"  ❌ 不删除（包含子文件夹）")
                return False  # 不删除
            elif other_files > 0:
                # 只有未启用类型的文件（如只启用视频时只有图片）
                logger.info(f"  ⚠️  文件夹 {folder_path.name}/ 情况:")
                logger.info(f"     - 未启用类型文件: {other_files} 个")
                logger.info(f"  ✅ 可以删除（无有效文件，只有无用文件）")
                return True  # 可以删除
            else:
                # 完全空文件夹
                logger.info(f"  📭 文件夹 {folder_path.name}/ 为完全空目录")
                return True  # 可以删除

        except PermissionError:
            logger.warning(f"❌ 无权限访问: {folder_path}")
            return False  # 无权限，保守处理，不删除
        except Exception as e:
            logger.error(f"❌ 检查文件夹时出错 {folder_path}: {str(e)}")
            return False

    def _is_valid_file(self, file_path: Path) -> bool:
        """
        检查文件是否为有效文件
        根据模式使用不同的判定逻辑
        """
        try:
            ext = file_path.suffix.lower()

            # 首先检查是否为排除的文件格式（正在下载、临时文件等，始终检查）
            if ext in self._exclude_extensions:
                logger.info(f"文件 {file_path.name} 在排除扩展名列表中: {ext}")
                return False

            size_bytes = file_path.stat().st_size

            # 模式2: 仅按大小判定
            if self._mode == "size_only":
                min_size_bytes = self._parse_size_to_bytes(
                    self._global_min_size,
                    self._global_min_size_unit
                )
                is_valid = size_bytes >= min_size_bytes
                logger.info(f"文件 {file_path.name}: 大小={size_bytes}字节, 阈值={min_size_bytes}字节, 有效={is_valid}")
                return is_valid

            # 模式1: 按类型+大小判定
            elif self._mode == "type_and_size":
                # 检查视频类
                if self._video_enabled and ext in self._video_extensions:
                    min_size_bytes = self._parse_size_to_bytes(
                        self._video_min_size,
                        self._video_min_size_unit
                    )
                    if size_bytes >= min_size_bytes:
                        logger.info(f"文件 {file_path.name}: 有效视频文件 ({ext}, {size_bytes}字节 >= {min_size_bytes}字节)")
                        return True
                    else:
                        logger.info(f"文件 {file_path.name}: 视频文件但大小不足 ({ext}, {size_bytes}字节 < {min_size_bytes}字节)")
                        return False

                # 检查图片类
                if self._image_enabled and ext in self._image_extensions:
                    min_size_bytes = self._parse_size_to_bytes(
                        self._image_min_size,
                        self._image_min_size_unit
                    )
                    if size_bytes >= min_size_bytes:
                        logger.info(f"文件 {file_path.name}: 有效图片文件 ({ext}, {size_bytes}字节 >= {min_size_bytes}字节)")
                        return True
                    else:
                        logger.info(f"文件 {file_path.name}: 图片文件但大小不足 ({ext}, {size_bytes}字节 < {min_size_bytes}字节)")
                        return False

                # 检查音频类
                if self._audio_enabled and ext in self._audio_extensions:
                    min_size_bytes = self._parse_size_to_bytes(
                        self._audio_min_size,
                        self._audio_min_size_unit
                    )
                    if size_bytes >= min_size_bytes:
                        logger.info(f"文件 {file_path.name}: 有效音频文件 ({ext}, {size_bytes}字节 >= {min_size_bytes}字节)")
                        return True
                    else:
                        logger.info(f"文件 {file_path.name}: 音频文件但大小不足 ({ext}, {size_bytes}字节 < {min_size_bytes}字节)")
                        return False

                # 文件类型不匹配，视为无效文件
                logger.info(f"文件 {file_path.name}: 扩展名 '{ext}' 不在已启用的文件类型中（视频:{self._video_enabled}, 图片:{self._image_enabled}, 音频:{self._audio_enabled}）")
                return False

        except Exception as e:
            logger.error(f"检查文件时出错 {file_path}: {str(e)}")
            return False

    def _is_excluded_folder(self, folder_path: Path) -> bool:
        """
        检查文件夹是否应被排除
        检查路径中的任何部分是否匹配排除列表
        """
        path_parts = folder_path.parts
        for part in path_parts:
            if part.lower() in self._excluded_folders:
                return True
        return False
