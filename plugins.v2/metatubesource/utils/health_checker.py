# Category: 工具函数
"""
API 健康检查机制
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
from app.log import logger


class HealthChecker:
    """API 健康检查器"""

    def __init__(self, check_interval: int = 60):
        """
        初始化健康检查器

        Args:
            check_interval: 健康检查间隔（秒），默认 60 秒
        """
        self._check_interval = check_interval
        self._api_status: Dict[str, dict] = {}
        self._last_check: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def register_api(self, api_name: str, health_check_func: Callable):
        """
        注册 API 健康检查函数

        Args:
            api_name: API 名称
            health_check_func: 健康检查函数，返回 True 表示健康，False 表示不健康
        """
        with self._lock:
            self._api_status[api_name] = {
                'healthy': True,
                'check_func': health_check_func,
                'last_check': None,
                'failure_count': 0
            }
            logger.info(f"已注册 API 健康检查: {api_name}")

    def is_healthy(self, api_name: str) -> bool:
        """
        检查 API 是否健康

        Args:
            api_name: API 名称

        Returns:
            bool: True 表示健康，False 表示不健康
        """
        with self._lock:
            if api_name not in self._api_status:
                # 未注册的 API 默认健康
                return True

            # 检查是否需要重新验证
            status = self._api_status[api_name]
            last_check = status.get('last_check')

            if last_check is None or \
               (datetime.now() - last_check).total_seconds() >= self._check_interval:
                # 需要重新检查
                self._perform_health_check(api_name)

            return status['healthy']

    def mark_unhealthy(self, api_name: str, reason: str = ""):
        """
        手动标记 API 为不健康

        Args:
            api_name: API 名称
            reason: 不健康原因
        """
        with self._lock:
            if api_name in self._api_status:
                self._api_status[api_name]['healthy'] = False
                self._api_status[api_name]['failure_count'] += 1
                logger.warning(
                    f"API {api_name} 标记为不健康: {reason} "
                    f"(失败次数: {self._api_status[api_name]['failure_count']})"
                )

    def mark_healthy(self, api_name: str):
        """
        手动标记 API 为健康

        Args:
            api_name: API 名称
        """
        with self._lock:
            if api_name in self._api_status:
                self._api_status[api_name]['healthy'] = True
                self._api_status[api_name]['failure_count'] = 0
                logger.info(f"API {api_name} 标记为健康")

    def _perform_health_check(self, api_name: str):
        """
        执行健康检查

        Args:
            api_name: API 名称
        """
        with self._lock:
            if api_name not in self._api_status:
                return

            status = self._api_status[api_name]
            check_func = status.get('check_func')

            if not check_func:
                return

            try:
                # 执行健康检查
                is_healthy = check_func()
                status['healthy'] = is_healthy
                status['last_check'] = datetime.now()

                if not is_healthy:
                    status['failure_count'] += 1
                    logger.warning(f"API {api_name} 健康检查失败")
                else:
                    if status['failure_count'] > 0:
                        logger.info(f"API {api_name} 健康检查恢复正常")
                    status['failure_count'] = 0

            except Exception as e:
                logger.error(f"API {api_name} 健康检查异常: {str(e)}")
                status['healthy'] = False
                status['failure_count'] += 1
                status['last_check'] = datetime.now()

    def get_status(self, api_name: str = None) -> Dict:
        """
        获取 API 状态

        Args:
            api_name: API 名称，为空则返回所有 API 状态

        Returns:
            Dict: API 状态信息
        """
        with self._lock:
            if api_name:
                return self._api_status.get(api_name, {}).copy()

            return {name: status.copy() for name, status in self._api_status.items()}

    def reset(self, api_name: str = None):
        """
        重置 API 状态

        Args:
            api_name: API 名称，为空则重置所有
        """
        with self._lock:
            if api_name:
                if api_name in self._api_status:
                    self._api_status[api_name]['healthy'] = True
                    self._api_status[api_name]['failure_count'] = 0
                    self._api_status[api_name]['last_check'] = None
            else:
                for status in self._api_status.values():
                    status['healthy'] = True
                    status['failure_count'] = 0
                    status['last_check'] = None

            logger.info(f"健康检查状态已重置: {api_name or '所有 API'}")
