"""
工具发现测试
"""

import pytest
from pathlib import Path
import tempfile

from src.tool_plugin_shim.core import (
    ToolRegistry,
    ToolDefinition,
    ToolMetadata,
)
from src.tool_plugin_shim.discovery import (
    ToolDiscovery,
    tool_decorator,
)


class TestToolDiscovery:
    """测试工具发现器"""

    def test_discovery_creation(self):
        """测试发现器创建"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)
        assert discovery.registry is registry

    def test_discover_from_dict(self):
        """测试从字典发现工具"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        def add(a: int, b: int) -> int:
            return a + b

        def multiply(a: int, b: int) -> int:
            return a * b

        tools = {
            "add": add,
            "multiply": multiply,
        }

        count = discovery.discover_from_dict(tools, source="test")
        assert count == 2
        assert "add" in registry
        assert "multiply" in registry

    def test_discover_from_decorator(self):
        """测试从装饰器发现工具"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        @tool_decorator(
            name="calculator",
            description="A simple calculator",
            category="math",
            tags=["math", "calculator"]
        )
        def add(a: int, b: int) -> int:
            return a + b

        # 手动注册装饰后的函数
        metadata = add.__tool_metadata__
        tool = ToolDefinition(
            name=metadata.name,
            handler=add,
            metadata=metadata
        )
        registry.register(tool)

        assert "calculator" in registry
        retrieved = registry.get("calculator")
        assert retrieved.metadata.category == "math"
        assert "math" in retrieved.metadata.tags
        assert "calculator" in retrieved.metadata.tags

    def test_decorator_metadata(self):
        """测试装饰器元数据"""
        @tool_decorator(
            name="test_tool",
            description="A test tool",
            category="test",
            timeout_seconds=60,
            requires_network=True,
            tags=["test", "network"],
            version="2.0.0",
            author="test_author",
            source="decorator_test"
        )
        def test_function(x: int) -> int:
            return x * 2

        assert hasattr(test_function, "__tool_metadata__")
        metadata = test_function.__tool_metadata__

        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.category == "test"
        assert metadata.timeout_seconds == 60
        assert metadata.requires_network is True
        assert metadata.tags == ["test", "network"]
        assert metadata.version == "2.0.0"
        assert metadata.author == "test_author"
        assert metadata.source == "decorator_test"

    def test_extract_metadata_from_function(self):
        """测试从函数提取元数据"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        def calculate(a: int, b: int) -> int:
            """A simple calculator tool.

            This tool performs basic arithmetic operations.
            """
            return a + b

        metadata = discovery._extract_metadata(calculate, "calculate", "test")

        assert metadata.name == "calculate"
        assert "calculator tool" in metadata.description.lower()
        assert metadata.version == "1.0.0"
        assert "a" in metadata.parameters
        assert "b" in metadata.parameters

        # 检查参数类型
        assert metadata.parameters["a"]["type"] == "<class 'int'>"
        assert metadata.parameters["b"]["type"] == "<class 'int'>"
        assert metadata.parameters["a"]["required"] is True
        assert metadata.parameters["b"]["required"] is True

    def test_extract_metadata_with_custom_annotations(self):
        """测试提取带自定义注解的元数据"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        def custom_tool(x):
            return x

        # 添加自定义注解
        custom_tool.__tool_category__ = "custom"
        custom_tool.__tool_timeout__ = 120
        custom_tool.__tool_requires_network__ = True
        custom_tool.__tool_tags__ = ["custom", "test"]

        metadata = discovery._extract_metadata(custom_tool, "custom_tool", "test")

        assert metadata.category == "custom"
        assert metadata.timeout_seconds == 120
        assert metadata.requires_network is True
        assert "custom" in metadata.tags
        assert "test" in metadata.tags

    def test_is_tool_function(self):
        """测试是否为工具函数"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        def regular_function():
            pass

        class CallableClass:
            def __call__(self):
                pass

        class NonCallableClass:
            pass

        assert discovery._is_tool_function(regular_function) is True
        assert discovery._is_tool_function(CallableClass) is True
        assert discovery._is_tool_function(NonCallableClass) is False
        assert discovery._is_tool_function("not a function") is False

    def test_add_discovery_path(self):
        """测试添加发现路径"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建一个测试文件
            test_file = tmpdir_path / "test.py"
            test_file.write_text("x = 1\n")

            discovery.add_discovery_path(tmpdir_path, recursive=True)

            assert len(discovery.discovery_paths) > 0

    def test_discover_from_file(self):
        """测试从文件发现工具"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建一个包含工具的文件
            test_file = tmpdir_path / "tools.py"
            test_file.write_text('''
def tool_func(x):
    """A test tool function."""
    return x * 2
''')

            count = discovery.discover_from_file(test_file, source="file")
            assert count == 1
            assert "tool_func" in registry

    def test_discover_from_directory(self):
        """测试从目录发现工具"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建几个测试文件
            for i in range(3):
                test_file = tmpdir_path / f"tool_{i}.py"
                test_file.write_text(f'''
def tool_{i}_func(x):
    """Tool {i} function."""
    return x * {i}
''')

            count = discovery.discover_from_directory(tmpdir_path, source="directory")
            assert count == 3
            assert "tool_0_func" in registry
            assert "tool_1_func" in registry
            assert "tool_2_func" in registry

    def test_auto_discover(self):
        """测试自动发现"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建工具目录和文件
            tools_dir = tmpdir_path / "tools"
            tools_dir.mkdir()

            for i in range(2):
                test_file = tools_dir / f"tool_{i}.py"
                test_file.write_text(f'''
def auto_tool_{i}(x):
    """Auto discovered tool {i}."""
    return x * {i}
''')

            discovery.add_discovery_path(tools_dir, recursive=False)

            count = discovery.auto_discover()
            assert count == 2

    def test_discover_with_error_handling(self):
        """测试错误处理"""
        registry = ToolRegistry()
        discovery = ToolDiscovery(registry)

        # 尝试从不存在的模块导入
        count = discovery.discover_from_module("nonexistent_module")
        assert count == 0

        # 尝试从不存在的文件导入
        count = discovery.discover_from_file(Path("/nonexistent/file.py"))
        assert count == 0

        # 尝试从不存在的目录导入
        count = discovery.discover_from_directory(Path("/nonexistent/dir"))
        assert count == 0


class TestToolDecorator:
    """测试工具装饰器"""

    def test_decorator_preserves_function(self):
        """测试装饰器不破坏原始函数"""
        @tool_decorator(
            name="test",
            description="Test"
        )
        def test_func(x):
            return x * 2

        assert test_func(5) == 10

    def test_decorator_with_optional_params(self):
        """测试装饰器可选参数"""
        @tool_decorator(name="test", description="Test")
        def test_func():
            pass

        metadata = test_func.__tool_metadata__
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"  # 默认版本
        assert metadata.timeout_seconds == 30  # 默认超时

    def test_decorator_with_all_params(self):
        """测试装饰器完整参数"""
        @tool_decorator(
            name="full_tool",
            description="Full featured tool",
            category="full",
            timeout_seconds=120,
            requires_network=True,
            tags=["full", "featured"],
            version="3.0.0",
            author="author",
            source="test_source"
        )
        def full_tool():
            pass

        metadata = full_tool.__tool_metadata__
        assert metadata.name == "full_tool"
        assert metadata.category == "full"
        assert metadata.timeout_seconds == 120
        assert metadata.requires_network is True
        assert metadata.tags == ["full", "featured"]
        assert metadata.version == "3.0.0"
        assert metadata.author == "author"
        assert metadata.source == "test_source"
