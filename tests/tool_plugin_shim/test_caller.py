"""
工具调用测试
"""

import time
import pytest

from src.tool_plugin_shim.core import (
    ToolRegistry,
    ToolDefinition,
    ToolMetadata,
    ToolError,
    ToolErrorCode,
    ToolCallResult,
)
from src.tool_plugin_shim.caller import ToolCaller


class TestToolCaller:
    """测试工具调用器"""

    def test_caller_creation(self):
        """测试调用器创建"""
        registry = ToolRegistry()
        caller = ToolCaller(registry)
        assert caller.registry is registry

    def test_call_simple_tool(self):
        """测试调用简单工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="add",
            description="Add two numbers",
            version="1.0.0"
        )

        def add(a: int, b: int) -> int:
            return a + b

        tool = ToolDefinition(
            name="add",
            handler=add,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call("add", 2, 3)

        assert result.success is True
        assert result.data == 5
        assert result.tool_name == "add"
        assert result.duration_ms > 0
        assert result.error is None

    def test_call_with_positional_args(self):
        """测试带位置参数的调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="concat",
            description="Concatenate strings",
            version="1.0.0"
        )

        def concat(a: str, b: str, c: str) -> str:
            return a + b + c

        tool = ToolDefinition(
            name="concat",
            handler=concat,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call("concat", "a", "b", "c")

        assert result.success is True
        assert result.data == "abc"

    def test_call_with_keyword_args(self):
        """测试带关键字参数的调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="greet",
            description="Greet someone",
            version="1.0.0"
        )

        def greet(name: str, title: str = "Mr.") -> str:
            return f"Hello, {title} {name}"

        tool = ToolDefinition(
            name="greet",
            handler=greet,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)

        # 使用关键字参数
        result = caller.call("greet", name="Smith", title="Dr.")
        assert result.success is True
        assert result.data == "Hello, Dr. Smith"

        # 使用默认参数
        result = caller.call("greet", name="Doe")
        assert result.success is True
        assert result.data == "Hello, Mr. Doe"

    def test_call_nonexistent_tool(self):
        """测试调用不存在的工具"""
        registry = ToolRegistry()
        caller = ToolCaller(registry)

        with pytest.raises(ToolError) as exc_info:
            caller.call("nonexistent")

        assert exc_info.value.code == ToolErrorCode.TOOL_NOT_FOUND

    def test_call_disabled_tool(self):
        """测试调用已禁用的工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="disabled_tool", description="Tool", version="1.0.0")

        def disabled_tool():
            return "should not run"

        tool = ToolDefinition(
            name="disabled_tool",
            handler=disabled_tool,
            metadata=metadata,
            enabled=False
        )
        registry.register(tool)

        caller = ToolCaller(registry)

        with pytest.raises(ToolError) as exc_info:
            caller.call("disabled_tool")

        assert exc_info.value.code == ToolErrorCode.UNAVAILABLE

    def test_call_safe_success(self):
        """测试安全调用成功情况"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="safe_add", description="Tool", version="1.0.0")

        def safe_add(a: int, b: int) -> int:
            return a + b

        tool = ToolDefinition(
            name="safe_add",
            handler=safe_add,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call_safe("safe_add", 10, 20)

        assert result.success is True
        assert result.data == 30
        assert result.error is None

    def test_call_safe_failure(self):
        """测试安全调用失败情况"""
        registry = ToolRegistry()
        caller = ToolCaller(registry)

        result = caller.call_safe("nonexistent")

        assert result.success is False
        assert result.error is not None
        assert result.error.code == ToolErrorCode.TOOL_NOT_FOUND

    def test_call_with_timeout_success(self):
        """测试带超时的成功调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="quick", timeout_seconds=5)

        def quick(x):
            return x * 2

        tool = ToolDefinition(
            name="quick",
            handler=quick,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call_with_timeout("quick", 5, timeout=1)

        assert result.success is True
        assert result.data == 10

    def test_call_with_timeout_failure(self):
        """测试带超时的失败调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="slow", timeout_seconds=1)

        def slow():
            time.sleep(2)
            return "done"

        tool = ToolDefinition(
            name="slow",
            handler=slow,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call_with_timeout("slow", timeout=1)

        assert result.success is False
        assert result.error is not None
        assert result.error.code == ToolErrorCode.TIMEOUT

    def test_tool_exception_handling(self):
        """测试工具异常处理"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="failing_tool", description="Tool", version="1.0.0")

        def failing_tool():
            raise ValueError("Tool error")

        tool = ToolDefinition(
            name="failing_tool",
            handler=failing_tool,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call("failing_tool")

        assert result.success is False
        assert result.error is not None
        assert result.error.code == ToolErrorCode.VALIDATION_ERROR
        assert result.error.original_error is not None

    def test_permission_error_handling(self):
        """测试权限错误处理"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="perm_tool", description="Tool", version="1.0.0")

        def perm_tool():
            raise PermissionError("Access denied")

        tool = ToolDefinition(
            name="perm_tool",
            handler=perm_tool,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call("perm_tool")

        assert result.success is False
        assert result.error is not None
        assert result.error.code == ToolErrorCode.PERMISSION_ERROR

    def test_batch_call(self):
        """测试批量调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="multiply", description="Tool", version="1.0.0")

        def multiply(x, y):
            return x * y

        tool = ToolDefinition(
            name="multiply",
            handler=multiply,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)

        calls = [
            {"tool_name": "multiply", "args": [2, 3]},
            {"tool_name": "multiply", "kwargs": {"x": 4, "y": 5}},
            {"tool_name": "multiply", "args": [6], "kwargs": {"y": 7}},
        ]

        results = caller.batch_call(calls)

        assert len(results) == 3
        assert results[0].success is True
        assert results[0].data == 6
        assert results[1].success is True
        assert results[1].data == 20
        assert results[2].success is True
        assert results[2].data == 42

    def test_batch_call_with_failure(self):
        """测试批量调用（包含失败）"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="good", description="Tool", version="1.0.0")
        metadata_fail = ToolMetadata(name="bad", description="Tool", version="1.0.0")

        def good():
            return "success"

        def bad():
            raise ValueError("failure")

        good_tool = ToolDefinition(
            name="good",
            handler=good,
            metadata=metadata
        )
        bad_tool = ToolDefinition(
            name="bad",
            handler=bad,
            metadata=metadata_fail
        )
        registry.register(good_tool)
        registry.register(bad_tool)

        caller = ToolCaller(registry)

        calls = [
            {"tool_name": "good"},
            {"tool_name": "bad"},
        ]

        with pytest.raises(ToolError):
            caller.batch_call(calls)

    def test_parallel_call(self):
        """测试并行调用"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="slow_task", description="Tool", version="1.0.0")

        def slow_task(delay):
            time.sleep(delay)
            return delay

        tool = ToolDefinition(
            name="slow_task",
            handler=slow_task,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)

        calls = [
            {"tool_name": "slow_task", "args": [0.1]},
            {"tool_name": "slow_task", "args": [0.2]},
            {"tool_name": "slow_task", "args": [0.1]},
        ]

        start_time = time.time()
        results = caller.parallel_call(calls, max_workers=3)
        duration = time.time() - start_time

        # 并行执行应该比顺序执行快
        assert duration < 0.4  # 顺序需要 0.4s，并行应该更快

        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].data == 0.1
        assert results[1].data == 0.2
        assert results[2].data == 0.1

    def test_parallel_call_with_error(self):
        """测试并行调用（包含错误）"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="task", description="Tool", version="1.0.0")

        def task(value):
            if value < 0:
                raise ValueError("Negative value")
            return value

        tool = ToolDefinition(
            name="task",
            handler=task,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)

        calls = [
            {"tool_name": "task", "args": [1]},
            {"tool_name": "task", "args": [-1]},  # 会失败
            {"tool_name": "task", "args": [2]},
        ]

        results = caller.parallel_call(calls, max_workers=3)

        assert len(results) == 3
        assert results[0].success is True
        assert results[0].data == 1
        assert results[1].success is False
        assert results[1].error is not None
        assert results[2].success is True
        assert results[2].data == 2

    def test_result_to_dict(self):
        """测试结果转字典"""
        registry = ToolRegistry()

        metadata = ToolMetadata(name="test", description="Tool", version="1.0.0")

        def test_func():
            return {"key": "value"}

        tool = ToolDefinition(
            name="test",
            handler=test_func,
            metadata=metadata
        )
        registry.register(tool)

        caller = ToolCaller(registry)
        result = caller.call("test")

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["tool_name"] == "test"
        assert result_dict["duration_ms"] > 0
        assert result_dict["error"] is None
