# Category: 配置
"""
Metatube 插件配置管理
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

@dataclass
class ThePornDBConfig:
    """ThePornDB API 配置"""
    enabled: bool = False
    api_token: str = ""
    timeout: int = 30
    proxies: Optional[Dict[str, str]] = None

@dataclass
class ByteMuseConfig:
    """ByteMuse API 配置"""
    enabled: bool = False
    url: str = "http://127.0.0.1:3750"
    username: str = ""
    password: str = ""
    timeout: int = 30
    proxies: Optional[Dict[str, str]] = None

@dataclass
class NamingConfig:
    """命名模板配置"""
    template: str = "number_actor_year"
    custom_template: str = ""
    max_actors: int = 2

@dataclass
class KeywordConfig:
    """关键字配置"""
    japanese: str = ""
    western: str = ""
    chinese: str = ""
    other: str = ""
    exclude: str = ""
    strict_match: bool = False

@dataclass
class RecognitionConfig:
    """识别配置"""
    failed_download_control: bool = True
    show_failure_detail: bool = True
    jav_number_auto_match: bool = True
    search_enabled: bool = False

@dataclass
class MetatubeConfig:
    """Metatube 插件主配置"""
    # 基础配置
    enabled: bool = False
    api_url: str = "http://127.0.0.1:8080"
    timeout: int = 30
    max_logs: int = 100

    # 命名配置
    naming: NamingConfig = field(default_factory=NamingConfig)

    # 关键字配置
    keywords: KeywordConfig = field(default_factory=KeywordConfig)

    # API 配置
    theporndb: ThePornDBConfig = field(default_factory=ThePornDBConfig)
    bytemuse: ByteMuseConfig = field(default_factory=ByteMuseConfig)

    # 识别配置
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)

    # 日志配置
    clear_logs_flag: bool = False

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MetatubeConfig':
        """从字典加载配置"""
        if not config_dict:
            return cls()

        # 基础配置
        base_config = {
            'enabled': config_dict.get('enabled', False),
            'api_url': config_dict.get('api_url', 'http://127.0.0.1:8080'),
            'timeout': int(config_dict.get('timeout', 30)),
            'max_logs': int(config_dict.get('max_logs', 100)),
            'clear_logs_flag': config_dict.get('clear_logs_flag', False),
        }

        # 命名配置
        naming_config = {
            'template': config_dict.get('naming_template', 'number_actor_year'),
            'custom_template': config_dict.get('custom_naming_template', ''),
            'max_actors': int(config_dict.get('max_actors', 2)),
        }

        # 关键字配置
        keyword_config = {
            'japanese': config_dict.get('custom_japanese_keywords', ''),
            'western': config_dict.get('custom_western_keywords', ''),
            'chinese': config_dict.get('custom_chinese_keywords', ''),
            'other': config_dict.get('custom_other_keywords', ''),
            'exclude': config_dict.get('exclude_keywords', ''),
            'strict_match': config_dict.get('strict_match', False),
        }

        # ThePornDB 配置
        theporndb_config = {
            'enabled': config_dict.get('theporndb_enabled', False),
            'api_token': config_dict.get('theporndb_api_token', ''),
            'timeout': int(config_dict.get('timeout', 30)),
        }

        # ByteMuse 配置
        bytemuse_config = {
            'enabled': config_dict.get('bytemuse_enabled', False),
            'url': config_dict.get('bytemuse_url', 'http://127.0.0.1:3750'),
            'username': config_dict.get('bytemuse_username', ''),
            'password': config_dict.get('bytemuse_password', ''),
            'timeout': int(config_dict.get('timeout', 30)),
        }

        # 识别配置
        recognition_config = {
            'failed_download_control': config_dict.get('failed_download_control', True),
            'show_failure_detail': config_dict.get('show_failure_detail', True),
            'jav_number_auto_match': config_dict.get('jav_number_auto_match', True),
            'search_enabled': config_dict.get('search_enabled', False),
        }

        return cls(
            **base_config,
            naming=NamingConfig(**naming_config),
            keywords=KeywordConfig(**keyword_config),
            theporndb=ThePornDBConfig(**theporndb_config),
            bytemuse=ByteMuseConfig(**bytemuse_config),
            recognition=RecognitionConfig(**recognition_config),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'enabled': self.enabled,
            'api_url': self.api_url,
            'timeout': self.timeout,
            'max_logs': self.max_logs,
            'clear_logs_flag': self.clear_logs_flag,
            'naming_template': self.naming.template,
            'custom_naming_template': self.naming.custom_template,
            'max_actors': self.naming.max_actors,
            'custom_japanese_keywords': self.keywords.japanese,
            'custom_western_keywords': self.keywords.western,
            'custom_chinese_keywords': self.keywords.chinese,
            'custom_other_keywords': self.keywords.other,
            'exclude_keywords': self.keywords.exclude,
            'strict_match': self.keywords.strict_match,
            'theporndb_enabled': self.theporndb.enabled,
            'theporndb_api_token': self.theporndb.api_token,
            'bytemuse_enabled': self.bytemuse.enabled,
            'bytemuse_url': self.bytemuse.url,
            'bytemuse_username': self.bytemuse.username,
            'bytemuse_password': self.bytemuse.password,
            'failed_download_control': self.recognition.failed_download_control,
            'show_failure_detail': self.recognition.show_failure_detail,
            'jav_number_auto_match': self.recognition.jav_number_auto_match,
            'search_enabled': self.recognition.search_enabled,
        }