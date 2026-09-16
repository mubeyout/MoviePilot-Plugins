# Category: 工具函数
"""
线程安全的频率限制器
"""
import threading
from datetime import datetime, timedelta
from typing import Optional
from app.log import logger


class RateLimiter:
    """线程安全的请求频率限制器"""

    def __init__(self, interval: float = 0.5):
        """
        初始化频率限制器

        Args:
            interval: 最小请求间隔时间（秒），默认 0.5 秒
        """
        self._interval = interval
        self._last_time: Optional[datetime] = None
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """
        尝试获取请求许可

        Returns:
            bool: True 表示可以发起请求，False 表示被限流
        """
        with self._lock:
            now = datetime.now()

            # 首次请求或已超过间隔时间
            if self._last_time is None or \
               (now - self._last_time).total_seconds() >= self._interval:
                self._last_time = now
                return True

            # 请求过于频繁
            logger.debug(
                f"请求过于频繁，需等待 {self._interval - (now - self._last_time).total_seconds():.2f} 秒"
            )
            return False

    def get_wait_time(self) -> float:
        """
        获取需要等待的时间（秒）

        Returns:
            float: 需要等待的秒数，0 表示可以立即请求
        """
        with self._lock:
            if self._last_time is None:
                return 0.0

            elapsed = (datetime.now() - self._last_time).total_seconds()
            wait_time = max(0.0, self._interval - elapsed)
            return wait_time

    def reset(self):
        """重置频率限制器"""
        with self._lock:
            self._last_time = None


class LogBuffer:
    """线程安全的日志缓冲区"""

    def __init__(self, max_size: int = 500):
        """
        初始化日志缓冲区

        Args:
            max_size: 最大缓存条数，默认 500
        """
        from collections import deque
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._max_size = max_size

    def append(self, log_entry: dict):
        """
        添加日志条目

        Args:
            log_entry: 日志条目字典
        """
        with self._lock:
            self._buffer.append(log_entry)

    def get_recent(self, count: int = 100) -> list:
        """
        获取最近的日志条目

        Args:
            count: 获取条数，默认 100

        Returns:
            list: 日志条目列表
        """
        with self._lock:
            buffer_list = list(self._buffer)
            return buffer_list[-count:] if count < len(buffer_list) else buffer_list

    def clear(self):
        """清空日志缓冲区"""
        with self._lock:
            self._buffer.clear()

    def size(self) -> int:
        """
        获取当前缓冲区大小

        Returns:
            int: 当前日志条数
        """
        with self._lock:
            return len(self._buffer)

    def get_all(self) -> list:
        """
        获取所有日志条目

        Returns:
            list: 所有日志条目列表
        """
        with self._lock:
            return list(self._buffer)
