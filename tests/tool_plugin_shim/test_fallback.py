"""
回退管理器测试
"""

import pytest

from src.tool_plugin_shim.core import (
    ToolError,
    ToolErrorCode,
)
from src.tool_plugin_shim.fallback import (
    FallbackHandler,
    DefaultValueFallback,
    MockDataFallback,
    CachedResultFallback,
    RetryFallback,
    CompositeFallback,
    FallbackManager,
    FallbackStrategy,
)


class TestDefaultValueFallback:
    """测试默认值回退处理器"""

    def test_default_value_fallback(self):
        """测试返回默认值"""
        handler = DefaultValueFallback(default_value=42)

        result = handler.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert result == 42

    def test_default_value_with_different_types(self):
        """测试不同类型的默认值"""
        # 字符串
        handler = DefaultValueFallback(default_value="default")
        assert handler.handle("test", None) == "default"

        # 字典
        handler = DefaultValueFallback(default_value={"key": "value"})
        assert handler.handle("test", None) == {"key": "value"}

        # 列表
        handler = DefaultValueFallback(default_value=[1, 2, 3])
        assert handler.handle("test", None) == [1, 2, 3]

        # None
        handler = DefaultValueFallback(default_value=None)
        assert handler.handle("test", None) is None


class TestMockDataFallback:
    """测试模拟数据回退处理器"""

    def test_mock_data_fallback(self):
        """测试返回模拟数据"""
        def mock_getter(tool_name):
            return f"mock_data_for_{tool_name}"

        handler = MockDataFallback(mock_getter)

        result = handler.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert result == "mock_data_for_test_tool"

    def test_mock_data_with_different_tools(self):
        """测试不同工具的模拟数据"""
        def mock_getter(tool_name):
            mock_data = {
                "tool_a": {"data": "A"},
                "tool_b": {"data": "B"},
            }
            return mock_data.get(tool_name, {})

        handler = MockDataFallback(mock_getter)

        result_a = handler.handle("tool_a", None)
        result_b = handler.handle("tool_b", None)
        result_c = handler.handle("tool_c", None)

        assert result_a == {"data": "A"}
        assert result_b == {"data": "B"}
        assert result_c == {}


class TestCachedResultFallback:
    """测试缓存结果回退处理器"""

    def test_cache_hit(self):
        """测试缓存命中"""
        handler = CachedResultFallback()

        # 缓存一个结果
        handler.cache_result("test_tool", (1, 2), {"x": 3}, {"result": "cached"})

        result = handler.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ), 1, 2, x=3)

        assert result == {"result": "cached"}

    def test_cache_miss(self):
        """测试缓存未命中"""
        handler = CachedResultFallback()

        with pytest.raises(ToolError):
            handler.handle("test_tool", ToolError(
                ToolErrorCode.TIMEOUT,
                "Timeout",
                tool_name="test_tool"
            ))

    def test_cache_with_custom_cache(self):
        """测试使用自定义缓存"""
        custom_cache = {"test_tool": "cached_value"}
        handler = CachedResultFallback(cache=custom_cache)

        result = handler.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert result == "cached_value"

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        handler = CachedResultFallback()

        # 相同参数应该生成相同的键
        key1 = handler._make_cache_key("test", (1, 2), {"x": 3})
        key2 = handler._make_cache_key("test", (1, 2), {"x": 3})

        assert key1 == key2

        # 不同参数应该生成不同的键
        key3 = handler._make_cache_key("test", (1, 2), {"x": 4})

        assert key1 != key3


class TestRetryFallback:
    """测试重试回退处理器"""

    def test_retry_success(self):
        """测试重试成功"""
        attempt_count = [0]

        def retry_handler(x):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ConnectionError("Network error")
            return x * 2

        handler = RetryFallback(retry_handler, max_retries=3)

        result = handler.handle("test_tool", ToolError(
            ToolErrorCode.NETWORK_ERROR,
            "Network error",
            tool_name="test_tool"
        ), 5)

        assert result == 10
        assert attempt_count[0] == 3

    def test_retry_failure(self):
        """测试重试失败"""
        def retry_handler(x):
            raise ConnectionError("Always fails")

        handler = RetryFallback(retry_handler, max_retries=3)

        with pytest.raises(ToolError) as exc_info:
            handler.handle("test_tool", ToolError(
                ToolErrorCode.NETWORK_ERROR,
                "Network error",
                tool_name="test_tool"
            ))

        assert exc_info.value.code == ToolErrorCode.FALLBACK_FAILED

    def test_retry_with_non_retryable_error(self):
        """测试不可重试的错误"""
        def retry_handler(x):
            return x * 2

        handler = RetryFallback(
            retry_handler,
            max_retries=3,
            retryable_errors=[ToolErrorCode.TIMEOUT, ToolErrorCode.NETWORK_ERROR]
        )

        with pytest.raises(ToolError) as exc_info:
            handler.handle("test_tool", ToolError(
                ToolErrorCode.VALIDATION_ERROR,  # 不可重试
                "Validation error",
                tool_name="test_tool"
            ))

        assert exc_info.value.code == ToolErrorCode.FALLBACK_FAILED


class TestCompositeFallback:
    """测试组合回退处理器"""

    def test_composite_fallback_success(self):
        """测试组合回退成功"""
        handler1 = DefaultValueFallback(default_value=1)
        handler2 = DefaultValueFallback(default_value=2)

        # handler1 会失败（这里我们让它成功）
        # handler2 不会执行
        composite = CompositeFallback([handler1, handler2])

        # 由于所有 handler 都会成功，应该返回第一个的结果
        result = composite.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert result == 1

    def test_composite_fallback_with_failure(self):
        """测试组合回退（包含失败的处理器）"""
        class FailingHandler(FallbackHandler):
            def handle(self, tool_name, error, *args, **kwargs):
                raise ToolError(
                    ToolErrorCode.FALLBACK_FAILED,
                    "Handler failed"
                )

        handler1 = FailingHandler()
        handler2 = DefaultValueFallback(default_value=42)

        composite = CompositeFallback([handler1, handler2])

        result = composite.handle("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert result == 42

    def test_composite_fallback_all_fail(self):
        """测试所有组合处理器都失败"""
        class FailingHandler(FallbackHandler):
            def handle(self, tool_name, error, *args, **kwargs):
                raise ToolError(
                    ToolErrorCode.FALLBACK_FAILED,
                    "Handler failed"
                )

        handler1 = FailingHandler()
        handler2 = FailingHandler()

        composite = CompositeFallback([handler1, handler2])

        with pytest.raises(ToolError) as exc_info:
            composite.handle("test_tool", ToolError(
                ToolErrorCode.TIMEOUT,
                "Timeout",
                tool_name="test_tool"
            ))

        assert exc_info.value.code == ToolErrorCode.FALLBACK_FAILED


class TestFallbackManager:
    """测试回退管理器"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = FallbackManager()
        assert len(manager._strategies) == 0
        assert len(manager._handlers) == 0

    def test_set_and_get_strategy(self):
        """测试设置和获取策略"""
        manager = FallbackManager()

        manager.set_strategy("test_tool", FallbackStrategy.RETRY_ONCE)

        assert "test_tool" in manager._strategies
        assert manager._strategies["test_tool"] == FallbackStrategy.RETRY_ONCE

    def test_set_and_get_handler(self):
        """测试设置和获取处理器"""
        manager = FallbackManager()
        handler = DefaultValueFallback(default_value=42)

        manager.set_handler("test_tool", handler)

        assert "test_tool" in manager._handlers
        assert manager._handlers["test_tool"] is handler

    def test_set_error_handler(self):
        """测试设置错误处理器"""
        manager = FallbackManager()
        handler = DefaultValueFallback(default_value="error")

        manager.set_error_handler(ToolErrorCode.TIMEOUT, handler)

        assert ToolErrorCode.TIMEOUT in manager._error_handlers
        assert manager._error_handlers[ToolErrorCode.TIMEOUT] is handler

    def test_set_default_handler(self):
        """测试设置默认处理器"""
        manager = FallbackManager()
        handler = DefaultValueFallback(default_value="default")

        manager.set_default_handler(handler)

        assert manager._default_handler is handler

    def test_get_handler_priority(self):
        """测试处理器优先级"""
        manager = FallbackManager()

        tool_handler = DefaultValueFallback(default_value="tool")
        error_handler = DefaultValueFallback(default_value="error")
        default_handler = DefaultValueFallback(default_value="default")

        manager.set_handler("test_tool", tool_handler)
        manager.set_error_handler(ToolErrorCode.TIMEOUT, error_handler)
        manager.set_default_handler(default_handler)

        # 优先使用工具特定的处理器
        handler = manager.get_handler("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert handler is tool_handler

    def test_get_handler_fallback_to_error_handler(self):
        """测试回退到错误处理器"""
        manager = FallbackManager()

        error_handler = DefaultValueFallback(default_value="error")
        default_handler = DefaultValueFallback(default_value="default")

        manager.set_error_handler(ToolErrorCode.TIMEOUT, error_handler)
        manager.set_default_handler(default_handler)

        # 没有工具特定处理器，使用错误处理器
        handler = manager.get_handler("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert handler is error_handler

    def test_get_handler_fallback_to_default(self):
        """测试回退到默认处理器"""
        manager = FallbackManager()

        default_handler = DefaultValueFallback(default_value="default")

        manager.set_default_handler(default_handler)

        # 没有工具特定处理器和错误处理器，使用默认处理器
        handler = manager.get_handler("test_tool", ToolError(
            ToolErrorCode.TIMEOUT,
            "Timeout",
            tool_name="test_tool"
        ))

        assert handler is default_handler

    def test_handle_fallback(self):
        """测试执行回退"""
        manager = FallbackManager()
        handler = DefaultValueFallback(default_value=42)

        manager.set_handler("test_tool", handler)

        result = manager.handle(
            "test_tool",
            ToolError(
                ToolErrorCode.TIMEOUT,
                "Timeout",
                tool_name="test_tool"
            )
        )

        assert result == 42

    def test_handle_no_handler_available(self):
        """测试没有可用处理器的情况"""
        manager = FallbackManager()

        with pytest.raises(ToolError) as exc_info:
            manager.handle(
                "test_tool",
                ToolError(
                    ToolErrorCode.TIMEOUT,
                    "Timeout",
                    tool_name="test_tool"
                )
            )

        assert exc_info.value.code == ToolErrorCode.FALLBACK_FAILED

    def test_create_composite_handler(self):
        """测试创建组合处理器"""
        manager = FallbackManager()

        handler1 = DefaultValueFallback(default_value=1)
        handler2 = DefaultValueFallback(default_value=2)

        composite = manager.create_composite_handler("test_tool", handler1, handler2)

        assert isinstance(composite, CompositeFallback)
        assert len(composite.handlers) == 2

    def test_clear_tool(self):
        """测试清除工具设置"""
        manager = FallbackManager()

        manager.set_strategy("test_tool", FallbackStrategy.RETRY_ONCE)
        manager.set_handler("test_tool", DefaultValueFallback(default_value=42))

        assert "test_tool" in manager._strategies
        assert "test_tool" in manager._handlers

        manager.clear_tool("test_tool")

        assert "test_tool" not in manager._strategies
        assert "test_tool" not in manager._handlers

    def test_clear_all(self):
        """测试清除所有设置"""
        manager = FallbackManager()

        manager.set_strategy("test_tool", FallbackStrategy.RETRY_ONCE)
        manager.set_handler("test_tool", DefaultValueFallback(default_value=42))
        manager.set_error_handler(ToolErrorCode.TIMEOUT, DefaultValueFallback(default_value=1))
        manager.set_default_handler(DefaultValueFallback(default_value=2))

        manager.clear_all()

        assert len(manager._strategies) == 0
        assert len(manager._handlers) == 0
        assert len(manager._error_handlers) == 0
        assert manager._default_handler is None
