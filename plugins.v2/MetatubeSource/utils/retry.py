# Category: 工具函数
"""
请求重试装饰器
为 API 调用提供自动重试机制
"""
import time
from functools import wraps
from typing import Callable, Optional
from app.log import logger


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    请求重试装饰器

    Args:
        max_retries: 最大重试次数，默认 3 次
        delay: 初始重试延迟（秒），默认 1 秒
        backoff: 退避系数，每次重试延迟时间乘以此系数，默认 2
        exceptions: 需要重试的异常类型元组，默认所有异常
        on_retry: 重试回调函数，接收参数 (attempt, delay, exception)

    Returns:
        装饰器函数

    Examples:
        >>> @retry_on_failure(max_retries=3, delay=1.0)
        >>> def api_call():
        >>>     # 可能失败的 API 调用
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            last_exception = None

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    retries += 1

                    if retries >= max_retries:
                        logger.error(
                            f"{func.__name__} 重试 {max_retries} 次后仍失败: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 失败，{current_delay:.1f}秒后重试 "
                        f"({retries}/{max_retries}): {str(e)}"
                    )

                    # 调用重试回调
                    if on_retry:
                        try:
                            on_retry(retries, current_delay, e)
                        except Exception as callback_error:
                            logger.error(f"重试回调执行失败: {str(callback_error)}")

                    # 等待后重试
                    time.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里，但为了类型安全
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_on_failure_async(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    异步请求重试装饰器

    Args:
        max_retries: 最大重试次数，默认 3 次
        delay: 初始重试延迟（秒），默认 1 秒
        backoff: 退避系数，每次重试延迟时间乘以此系数，默认 2
        exceptions: 需要重试的异常类型元组，默认所有异常
        on_retry: 重试回调函数，接收参数 (attempt, delay, exception)

    Returns:
        异步装饰器函数

    Examples:
        >>> @retry_on_failure_async(max_retries=3)
        >>> async def async_api_call():
        >>>     # 可能失败的异步 API 调用
        >>>     pass
    """
    import asyncio

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            last_exception = None

            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    retries += 1

                    if retries >= max_retries:
                        logger.error(
                            f"{func.__name__} 异步重试 {max_retries} 次后仍失败: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 异步调用失败，{current_delay:.1f}秒后重试 "
                        f"({retries}/{max_retries}): {str(e)}"
                    )

                    # 调用重试回调
                    if on_retry:
                        try:
                            on_retry(retries, current_delay, e)
                        except Exception as callback_error:
                            logger.error(f"重试回调执行失败: {str(callback_error)}")

                    # 异步等待后重试
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里，但为了类型安全
            if last_exception:
                raise last_exception

        return async_wrapper
    return decorator
