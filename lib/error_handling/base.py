"""
基础错误类定义

提供所有错误类的核心功能，包括：
- 错误严重程度
- 恢复策略
- 日志记录
- 重试配置
"""

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class ErrorSeverity(Enum):
    """错误严重程度分类"""

    LOW = "low"  # 低严重性错误，可以自动恢复
    MEDIUM = "medium"  # 中等严重性错误，需要人工干预或特殊处理
    HIGH = "high"  # 高严重性错误，可能导致功能失败
    CRITICAL = "critical"  # 致命错误，需要立即处理


class RecoveryStrategy(Enum):
    """错误恢复策略"""

    RETRY = "retry"  # 重试操作
    FALLBACK = "fallback"  # 使用备用方案
    SKIP = "skip"  # 跳过当前操作
    ABORT = "abort"  # 终止操作
    MANUAL = "manual"  # 需要人工介入


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大重试次数（不包括首次尝试）
            initial_delay: 初始延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子，每次重试延迟乘以该因子
            jitter: 是否添加随机抖动避免惊群效应
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        计算第 n 次重试的延迟时间

        Args:
            attempt: 重试次数（从 1 开始）

        Returns:
            延迟时间（秒）
        """
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class BaseError(Exception, ABC):
    """
    所有错误类的基类

    提供统一的错误处理接口，包括：
    - 结构化错误信息
    - 错误上下文
    - 恢复建议
    - 重试配置
    """

    # 默认错误消息模板
    message_template: str = "An error occurred: {details}"

    # 默认错误严重程度
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    # 默认恢复策略
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY

    # 默认重试配置（None 表示不重试）
    retry_config: Optional[RetryConfig] = None

    # 错误代码（用于日志和监控）
    error_code: str = "BASE_ERROR"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        初始化错误实例

        Args:
            message: 自定义错误消息（如果提供则忽略模板）
            details: 错误详细信息
            context: 错误发生时的上下文信息
            cause: 原始异常（异常链）
        """
        self.details = details or {}
        self.context = context or {}
        self.cause = cause
        self.timestamp = time.time()
        self._logger = logging.getLogger(self.__class__.__name__)

        # 构建错误消息
        if message:
            self.message = message
        else:
            self.message = self.message_template.format(**self.details)

        # 调用父类初始化
        super().__init__(self.message)

        # 自动记录日志
        self._log_error()

    def _log_error(self):
        """记录错误日志"""
        log_level = self._get_log_level()

        log_data = {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "recovery_strategy": self.recovery_strategy.value,
            "timestamp": self.timestamp,
        }

        if self.details:
            log_data["details"] = self.details

        if self.context:
            log_data["context"] = self.context

        if self.cause:
            log_data["cause"] = str(self.cause)

        self._logger.log(log_level, log_data, exc_info=self.cause)

    def _get_log_level(self) -> int:
        """根据严重程度确定日志级别"""
        severity_map = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        return severity_map.get(self.severity, logging.ERROR)

    def get_recovery_suggestion(self) -> str:
        """
        获取恢复建议

        Returns:
            恢复建议的文本描述
        """
        strategy_map = {
            RecoveryStrategy.RETRY: "重试操作",
            RecoveryStrategy.FALLBACK: "使用备用方案",
            RecoveryStrategy.SKIP: "跳过当前操作",
            RecoveryStrategy.ABORT: "终止操作",
            RecoveryStrategy.MANUAL: "需要人工介入",
        }
        suggestion = strategy_map.get(self.recovery_strategy, "未知策略")

        if self.retry_config:
            suggestion += f"（最多重试 {self.retry_config.max_attempts} 次）"

        return suggestion

    def to_dict(self) -> Dict[str, Any]:
        """
        将错误转换为字典格式

        Returns:
            包含错误所有信息的字典
        """
        return {
            "error_code": self.error_code,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "recovery_strategy": self.recovery_strategy.value,
            "recovery_suggestion": self.get_recovery_suggestion(),
            "details": self.details,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def retry(
        func: Callable[..., T],
        error_classes: Optional[type] = None,
        config: Optional[RetryConfig] = None,
    ) -> T:
        """
        带重试机制执行函数

        Args:
            func: 要执行的函数
            error_classes: 需要重试的错误类型（默认为 BaseError 及其子类）
            config: 重试配置

        Returns:
            函数执行结果

        Raises:
            最后一次异常（如果所有重试都失败）
        """
        if error_classes is None:
            error_classes = BaseError

        if config is None:
            config = RetryConfig()

        last_exception = None

        for attempt in range(config.max_attempts + 1):
            try:
                return func()
            except Exception as e:
                if not isinstance(e, error_classes):
                    raise

                last_exception = e

                if attempt < config.max_attempts:
                    delay = config.get_delay(attempt + 1)
                    time.sleep(delay)

        # 所有重试都失败，抛出最后一次异常
        if last_exception:
            raise last_exception

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"
