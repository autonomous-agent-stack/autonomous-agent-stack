"""
回退管理模块

提供工具调用失败时的回退策略和处理器。
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .core import (
    ToolError,
    ToolErrorCode,
    ToolCallResult,
)


logger = logging.getLogger(__name__)


class FallbackStrategy:
    """回退策略枚举"""
    # 立即失败，不使用回退
    FAIL_FAST = "fail_fast"
    # 尝试一次回退
    RETRY_ONCE = "retry_once"
    # 重试多次
    RETRY_MULTIPLE = "retry_multiple"
    # 返回默认值
    DEFAULT_VALUE = "default_value"
    # 返回模拟数据
    MOCK_DATA = "mock_data"
    # 缓存的旧结果
    CACHED_RESULT = "cached_result"
    # 组合多个策略
    COMPOSITE = "composite"


class FallbackHandler:
    """回退处理器基类

    子类需要实现 handle 方法。
    """

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """处理回退

        Args:
            tool_name: 工具名称
            error: 原始错误
            *args: 原始位置参数
            **kwargs: 原始关键字参数

        Returns:
            回退结果

        Raises:
            ToolError: 如果回退失败
        """
        raise NotImplementedError


class DefaultValueFallback(FallbackHandler):
    """默认值回退处理器"""

    def __init__(self, default_value: Any):
        """初始化

        Args:
            default_value: 默认值
        """
        self.default_value = default_value

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """返回默认值"""
        logger.info(f"Using default value for tool: {tool_name}")
        return self.default_value


class MockDataFallback(FallbackHandler):
    """模拟数据回退处理器"""

    def __init__(self, mock_data_getter: Callable[[str], Any]):
        """初始化

        Args:
            mock_data_getter: 根据工具名称获取模拟数据的函数
        """
        self.mock_data_getter = mock_data_getter

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """返回模拟数据"""
        logger.info(f"Using mock data for tool: {tool_name}")
        return self.mock_data_getter(tool_name)


class CachedResultFallback(FallbackHandler):
    """缓存结果回退处理器"""

    def __init__(self, cache: Optional[Dict[str, Any]] = None):
        """初始化

        Args:
            cache: 缓存字典，如果为 None 则使用内部缓存
        """
        self.cache = cache or {}

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """返回缓存结果"""
        cache_key = self._make_cache_key(tool_name, args, kwargs)

        if cache_key in self.cache:
            logger.info(f"Using cached result for tool: {tool_name}")
            return self.cache[cache_key]

        # 缓存中没有，尝试使用原始参数生成缓存键
        logger.warning(f"No cached result for tool: {tool_name}, cache_key: {cache_key}")

        # 尝试返回任何缓存结果（如果只有一个）
        if self.cache:
            logger.info(f"Returning any cached result for tool: {tool_name}")
            return next(iter(self.cache.values()))

        raise ToolError(
            ToolErrorCode.FALLBACK_FAILED,
            f"No cached result available for tool: {tool_name}"
        )

    def cache_result(self, tool_name: str, args: tuple, kwargs: dict, result: Any) -> None:
        """缓存结果"""
        cache_key = self._make_cache_key(tool_name, args, kwargs)
        self.cache[cache_key] = result

    def _make_cache_key(self, tool_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        # 简单实现：使用工具名 + 参数的字符串表示
        # 生产环境应该使用更健壮的序列化方法
        import json

        try:
            args_str = json.dumps(args, default=str, sort_keys=True)
            kwargs_str = json.dumps(kwargs, default=str, sort_keys=True)
            return f"{tool_name}:{args_str}:{kwargs_str}"
        except Exception:
            # 如果序列化失败，使用简单哈希
            return f"{tool_name}:{hash(str(args) + str(kwargs))}"


class RetryFallback(FallbackHandler):
    """重试回退处理器"""

    def __init__(
        self,
        retry_handler: Callable,
        max_retries: int = 3,
        retryable_errors: Optional[List[ToolErrorCode]] = None
    ):
        """初始化

        Args:
            retry_handler: 重试处理器函数
            max_retries: 最大重试次数
            retryable_errors: 可重试的错误类型，None 表示全部可重试
        """
        self.retry_handler = retry_handler
        self.max_retries = max_retries
        self.retryable_errors = retryable_errors or [
            ToolErrorCode.TIMEOUT,
            ToolErrorCode.NETWORK_ERROR,
            ToolErrorCode.UNAVAILABLE,
        ]

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """重试调用"""
        if error.code not in self.retryable_errors:
            # 错误不可重试
            raise ToolError(
                ToolErrorCode.FALLBACK_FAILED,
                f"Error not retryable: {error.code.value}"
            )

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} for tool: {tool_name}")
                return self.retry_handler(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # 最后一次尝试也失败
                    raise ToolError(
                        ToolErrorCode.FALLBACK_FAILED,
                        f"Retry failed after {self.max_retries} attempts: {str(e)}",
                        original_error=e
                    )
                logger.warning(f"Retry {attempt + 1} failed for tool: {tool_name}: {str(e)}")


class CompositeFallback(FallbackHandler):
    """组合回退处理器

    按顺序尝试多个回退策略，直到成功或全部失败。
    """

    def __init__(self, handlers: List[FallbackHandler]):
        """初始化

        Args:
            handlers: 回退处理器列表
        """
        self.handlers = handlers

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """依次尝试所有回退处理器"""
        last_error = error

        for i, handler in enumerate(self.handlers):
            try:
                logger.info(f"Trying fallback handler {i + 1}/{len(self.handlers)} for tool: {tool_name}")
                return handler.handle(tool_name, last_error, *args, **kwargs)
            except Exception as e:
                last_error = e if isinstance(e, ToolError) else ToolError(
                    ToolErrorCode.FALLBACK_FAILED,
                    f"Fallback handler {i + 1} failed: {str(e)}",
                    original_error=e
                )
                logger.warning(f"Fallback handler {i + 1} failed for tool: {tool_name}: {str(e)}")

        # 所有回退处理器都失败
        raise ToolError(
            ToolErrorCode.FALLBACK_FAILED,
            f"All {len(self.handlers)} fallback handlers failed for tool: {tool_name}",
            original_error=last_error
        )


class FallbackManager:
    """回退管理器

    管理工具的回退策略和处理器。
    """

    def __init__(self):
        """初始化回退管理器"""
        self._strategies: Dict[str, FallbackStrategy] = {}
        self._handlers: Dict[str, FallbackHandler] = {}
        self._error_handlers: Dict[ToolErrorCode, FallbackHandler] = {}
        self._default_handler: Optional[FallbackHandler] = None

    def set_strategy(
        self,
        tool_name: str,
        strategy: FallbackStrategy
    ) -> None:
        """设置工具的回退策略

        Args:
            tool_name: 工具名称
            strategy: 回退策略
        """
        self._strategies[tool_name] = strategy
        logger.debug(f"Set fallback strategy for tool {tool_name}: {strategy.value}")

    def set_handler(
        self,
        tool_name: str,
        handler: FallbackHandler
    ) -> None:
        """设置工具的回退处理器

        Args:
            tool_name: 工具名称
            handler: 回退处理器
        """
        self._handlers[tool_name] = handler
        logger.debug(f"Set fallback handler for tool {tool_name}")

    def set_error_handler(
        self,
        error_code: ToolErrorCode,
        handler: FallbackHandler
    ) -> None:
        """设置错误类型的回退处理器

        Args:
            error_code: 错误码
            handler: 回退处理器
        """
        self._error_handlers[error_code] = handler
        logger.debug(f"Set error handler for {error_code.value}")

    def set_default_handler(self, handler: FallbackHandler) -> None:
        """设置默认回退处理器

        Args:
            handler: 回退处理器
        """
        self._default_handler = handler
        logger.debug("Set default fallback handler")

    def get_handler(
        self,
        tool_name: str,
        error: ToolError
    ) -> Optional[FallbackHandler]:
        """获取回退处理器

        Args:
            tool_name: 工具名称
            error: 错误对象

        Returns:
            回退处理器，如果没有合适的返回 None
        """
        # 优先使用工具特定的处理器
        if tool_name in self._handlers:
            return self._handlers[tool_name]

        # 其次使用错误类型的处理器
        if error.code in self._error_handlers:
            return self._error_handlers[error.code]

        # 最后使用默认处理器
        return self._default_handler

    def handle(
        self,
        tool_name: str,
        error: ToolError,
        *args,
        **kwargs
    ) -> Any:
        """执行回退

        Args:
            tool_name: 工具名称
            error: 错误对象
            *args: 原始位置参数
            **kwargs: 原始关键字参数

        Returns:
            回退结果

        Raises:
            ToolError: 如果回退失败
        """
        handler = self.get_handler(tool_name, error)

        if handler is None:
            # 没有可用的回退处理器
            raise ToolError(
                ToolErrorCode.FALLBACK_FAILED,
                f"No fallback handler available for tool: {tool_name}"
            )

        return handler.handle(tool_name, error, *args, **kwargs)

    def create_composite_handler(
        self,
        tool_name: str,
        *handlers: FallbackHandler
    ) -> CompositeFallback:
        """创建组合回退处理器

        Args:
            tool_name: 工具名称
            *handlers: 回退处理器列表

        Returns:
            组合回退处理器
        """
        composite = CompositeFallback(list(handlers))
        self.set_handler(tool_name, composite)
        return composite

    def clear_tool(self, tool_name: str) -> None:
        """清除工具的回退设置

        Args:
            tool_name: 工具名称
        """
        self._strategies.pop(tool_name, None)
        self._handlers.pop(tool_name, None)
        logger.debug(f"Cleared fallback settings for tool: {tool_name}")

    def clear_all(self) -> None:
        """清除所有回退设置"""
        self._strategies.clear()
        self._handlers.clear()
        self._error_handlers.clear()
        self._default_handler = None
        logger.debug("Cleared all fallback settings")
