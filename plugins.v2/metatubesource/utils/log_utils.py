# Category: 工具
"""
Metatube 优化日志系统
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from ..models.base import LogConfig

class OptimizedLogger:
    """优化日志记录器"""

    def __init__(self, plugin_name: str, log_file: Optional[Path] = None):
        self.plugin_name = plugin_name
        self.log_file = log_file
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"metatube.{self.plugin_name}")
        logger.setLevel(logging.INFO)

        # 清除现有处理器
        logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 文件处理器（如果指定）
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger

    def _should_log(self, message: str) -> bool:
        """判断是否应该记录"""
        if LogConfig.LEVEL == "DEBUG":
            return True

        for critical in LogConfig.CRITICAL_LOGS:
            if critical in message:
                return True

        return False

    def info(self, message: str, **kwargs):
        """记录信息"""
        if self._should_log(message):
            self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告"""
        if self._should_log(message):
            self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录错误"""
        if self._should_log(message):
            self.logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        if self._should_log(message):
            self.logger.debug(message, **kwargs)

    def log_recognition_start(self, title: str, category: str):
        """记录识别开始"""
        self.info(f"开始识别: {title} (分类: {category})")

    def log_recognition_success(self, number: str, title: str, source: str):
        """记录识别成功"""
        self.info(f"{source} 识别成功: {number} -> {title}")

    def log_recognition_failure(self, number: str, reason: str, source: str):
        """记录识别失败"""
        self.warning(f"{source} 识别失败: {number} - {reason}")

    def log_api_request(self, method: str, url: str, params: Dict[str, Any] = None):
        """记录API请求"""
        params_str = f" params: {params}" if params else ""
        self.debug(f"API请求: {method} {url}{params_str}")

    def log_api_response(self, status_code: int, url: str, data: Any = None):
        """记录API响应"""
        data_str = f" 数据: {data}" if data else ""
        self.debug(f"API响应: {status_code} {url}{data_str}")

    def log_keyword_match(self, title: str, category: str, matched_keywords: List[str]):
        """记录关键字匹配"""
        if matched_keywords:
            self.info(f"关键字匹配: {title} -> {category} (匹配: {', '.join(matched_keywords)})")
        else:
            self.debug(f"关键字匹配: {title} -> {category} (无匹配)")

    def log_config_load(self, config_path: str):
        """记录配置加载"""
        self.info(f"加载配置: {config_path}")

    def log_config_save(self, config_path: str):
        """记录配置保存"""
        self.info(f"保存配置: {config_path}")

    def log_plugin_init(self, version: str):
        """记录插件初始化"""
        self.info(f"插件 {self.plugin_name} 初始化完成，版本 {version}")

    def log_plugin_shutdown(self):
        """记录插件关闭"""
        self.info(f"插件 {self.plugin_name} 正在关闭")

class LogFilter:
    """日志过滤器"""

    @staticmethod
    def filter_by_level(logs: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
        """按级别过滤日志"""
        return [log for log in logs if log.get('level', '').upper() == level.upper()]

    @staticmethod
    def filter_by_source(logs: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """按来源过滤日志"""
        return [log for log in logs if log.get('source', '') == source]

    @staticmethod
    def get_latest_logs(logs: List[Dict[str, Any]], count: int = 10) -> List[Dict[str, Any]]:
        """获取最新日志"""
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:count]

    @staticmethod
    def get_logs_by_category(logs: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        """按分类获取日志"""
        return [log for log in logs if category in log.get('message', '')]

class LogManager:
    """日志管理器"""

    def __init__(self, max_logs: int = 100):
        self.max_logs = max_logs
        self.logs = []

    def add_log(self, level: str, message: str, source: str = "metatube"):
        """添加日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'source': source
        }
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def get_logs(self) -> List[Dict[str, Any]]:
        """获取所有日志"""
        return self.logs.copy()

    def clear_logs(self):
        """清空日志"""
        self.logs.clear()

    def export_logs(self, file_path: str):
        """导出日志到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for log in self.logs:
                    f.write(f"{log['timestamp']} - {log['level']} - {log['message']}\n")
            return True
        except Exception as e:
            print(f"导出日志失败: {str(e)}")
            return False

# 全局日志管理器实例
global_log_manager = LogManager()