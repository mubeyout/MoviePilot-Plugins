# Category: 工具函数
"""
配置文件热更新监控器
"""
import time
import threading
from pathlib import Path
from typing import Callable, Optional
from app.log import logger


class ConfigWatcher:
    """配置文件变更监控器"""

    def __init__(self, config_file: Path, callback: Callable, check_interval: float = 5.0):
        """
        初始化配置监控器

        Args:
            config_file: 要监控的配置文件路径
            callback: 配置变更时的回调函数
            check_interval: 检查间隔（秒），默认 5 秒
        """
        self._config_file = Path(config_file)
        self._callback = callback
        self._check_interval = check_interval
        self._last_mtime: Optional[float] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _get_mtime(self) -> Optional[float]:
        """获取文件修改时间"""
        try:
            return self._config_file.stat().st_mtime
        except Exception:
            return None

    def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                current_mtime = self._get_mtime()

                # 首次检查或文件被修改
                if current_mtime is not None and \
                   (self._last_mtime is None or current_mtime > self._last_mtime):
                    logger.info(f"检测到配置文件变更: {self._config_file.name}")

                    # 等待文件写入完成
                    time.sleep(0.5)

                    # 调用回调函数
                    try:
                        self._callback(str(self._config_file))
                        logger.info(f"配置文件 {self._config_file.name} 重新加载成功")
                    except Exception as e:
                        logger.error(f"配置回调执行失败: {str(e)}")

                    self._last_mtime = current_mtime

            except Exception as e:
                logger.error(f"配置监控检查异常: {str(e)}")

            # 等待下次检查
            time.sleep(self._check_interval)

    def start(self):
        """启动监控"""
        if self._running:
            logger.warning("配置监控器已在运行")
            return

        self._running = True
        self._last_mtime = self._get_mtime()

        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

        logger.info(f"配置监控器已启动: {self._config_file.name}")

    def stop(self):
        """停止监控"""
        if not self._running:
            return

        self._running = False

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info(f"配置监控器已停止: {self._config_file.name}")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
