"""
重试策略辅助工具

提供便捷的重试装饰器和工具函数。
"""

import functools
import logging
import time
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from .base import BaseError, RetryConfig

T = TypeVar("T")

logger = logging.getLogger(__name__)


def retry_on_exception(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    重试装饰器

    Args:
        max_attempts: 最大重试次数（不包括首次尝试）
        initial_delay: 初始延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
        jitter: 是否添加随机抖动
        exceptions: 需要捕获和重试的异常类型
        on_retry: 每次重试前的回调函数（参数：重试次数，异常对象）

    Returns:
        装饰器函数

    Example:
        @retry_on_exception(max_attempts=3, exceptions=(RateLimitError, TimeoutError))
        def call_llm_api(prompt: str) -> str:
            # API 调用逻辑
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
            )

            last_exception = None

            for attempt in range(config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt + 1)

                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败：{e}，"
                            f"{delay:.2f} 秒后重试"
                        )

                        if on_retry:
                            on_retry(attempt + 1, e)

                        time.sleep(delay)

            # 所有重试都失败，抛出最后一次异常
            if last_exception:
                raise last_exception

            # 理论上不会执行到这里
            raise RuntimeError("重试逻辑异常")

        return wrapper

    return decorator


class Retryable:
    """
    可重试操作的上下文管理器

    用于需要手动控制重试逻辑的场景。

    Example:
        with Retryable(max_attempts=3) as retry:
            for attempt in retry.attempts():
                try:
                    result = risky_operation()
                    retry.success(result)
                    break
                except Exception as e:
                    retry.record_failure(e)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            jitter=jitter,
        )
        self.failures: List[Exception] = []
        self._succeeded = False
        self._result: Any = None

    def attempts(self):
        """
        生成重试迭代器

        Yields:
            当前尝试次数（从 1 开始）
        """
        for attempt in range(1, self.config.max_attempts + 2):
            yield attempt

            # 如果已经成功，退出迭代
            if self._succeeded:
                break

            # 如果还有剩余重试次数，等待后继续
            if attempt <= self.config.max_attempts:
                delay = self.config.get_delay(attempt)
                time.sleep(delay)

    def record_failure(self, exception: Exception):
        """记录一次失败"""
        self.failures.append(exception)
        logger.warning(f"记录失败：{exception}（已失败 {len(self.failures)} 次）")

    def success(self, result: Any):
        """标记操作成功"""
        self._succeeded = True
        self._result = result

    @property
    def succeeded(self) -> bool:
        """是否成功"""
        return self._succeeded

    @property
    def result(self) -> Any:
        """获取结果（仅在成功后有效）"""
        if not self._succeeded:
            raise RuntimeError("操作尚未成功，无法获取结果")
        return self._result

    @property
    def last_failure(self) -> Optional[Exception]:
        """获取最后一次失败"""
        return self.failures[-1] if self.failures else None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self._succeeded:
            self.record_failure(exc_val)
        return True  # 抑制异常


def exponential_backoff(
    base_delay: float,
    max_delay: float,
    attempts: int,
    jitter: bool = True,
) -> float:
    """
    计算指数退避延迟时间

    Args:
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        attempts: 重试次数
        jitter: 是否添加随机抖动

    Returns:
        延迟时间（秒）
    """
    delay = base_delay * (2 ** (attempts - 1))
    delay = min(delay, max_delay)

    if jitter:
        import random

        delay = delay * (0.5 + random.random() * 0.5)

    return delay


def should_retry(exception: Exception, max_attempts: int, current_attempt: int) -> bool:
    """
    判断是否应该重试

    Args:
        exception: 捕获的异常
        max_attempts: 最大重试次数
        current_attempt: 当前尝试次数

    Returns:
        是否应该重试
    """
    # 检查是否达到最大重试次数
    if current_attempt >= max_attempts:
        return False

    # 检查异常类型是否支持重试
    if isinstance(exception, BaseError):
        return exception.retry_config is not None

    # 对于普通异常，默认可以重试
    return True
