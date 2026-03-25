"""
工具注册表测试
"""

import pytest

from src.tool_plugin_shim.core import (
    ToolRegistry,
    ToolDefinition,
    ToolMetadata,
    ToolError,
    ToolErrorCode,
)


class TestToolMetadata:
    """测试工具元数据"""

    def test_create_metadata(self):
        """测试创建元数据"""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            version="1.0.0",
            category="test",
            timeout_seconds=30,
            requires_network=False,
            tags=["test", "demo"],
            source="test"
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.version == "1.0.0"
        assert metadata.category == "test"
        assert metadata.timeout_seconds == 30
        assert not metadata.requires_network
        assert metadata.tags == ["test", "demo"]
        assert metadata.source == "test"


class TestToolDefinition:
    """测试工具定义"""

    def test_create_definition(self):
        """测试创建工具定义"""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool"
        )

        def handler(x):
            return x * 2

        definition = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        assert definition.name == "test_tool"
        assert definition.handler == handler
        assert definition.metadata == metadata
        assert definition.enabled is True


class TestToolRegistry:
    """测试工具注册表"""

    def test_registry_creation(self):
        """测试注册表创建"""
        registry = ToolRegistry()
        assert len(registry) == 0

    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            category="test",
            source="test"
        )

        def handler(x):
            return x * 2

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)
        assert len(registry) == 1
        assert "test_tool" in registry

    def test_register_duplicate_tool(self):
        """测试注册重复工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool"
        )

        def handler(x):
            return x * 2

        tool1 = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        tool2 = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_unregister_tool(self):
        """测试注销工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            category="test",
            source="test"
        )

        def handler(x):
            return x * 2

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)
        assert len(registry) == 1

        registry.unregister("test_tool")
        assert len(registry) == 0
        assert "test_tool" not in registry

    def test_unregister_nonexistent_tool(self):
        """测试注销不存在的工具"""
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    def test_get_tool(self):
        """测试获取工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool"
        )

        def handler(x):
            return x * 2

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)
        retrieved = registry.get("test_tool")

        assert retrieved is not None
        assert retrieved.name == "test_tool"
        assert retrieved.handler == handler

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        registry = ToolRegistry()
        retrieved = registry.get("nonexistent")
        assert retrieved is None

    def test_list_all_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()

        for i in range(3):
            metadata = ToolMetadata(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test",
                source="test"
            )

            def handler(x, i=i):
                return x * i

            tool = ToolDefinition(
                name=f"tool_{i}",
                handler=handler,
                metadata=metadata
            )

            registry.register(tool)

        tools = registry.list_all()
        assert len(tools) == 3
        assert "tool_0" in tools
        assert "tool_1" in tools
        assert "tool_2" in tools

    def test_list_by_category(self):
        """测试按分类列出工具"""
        registry = ToolRegistry()

        for cat in ["test", "demo"]:
            for i in range(2):
                metadata = ToolMetadata(
                    name=f"{cat}_tool_{i}",
                    description=f"{cat} tool {i}",
                    category=cat,
                    source="test"
                )

                def handler(x):
                    return x

                tool = ToolDefinition(
                    name=f"{cat}_tool_{i}",
                    handler=handler,
                    metadata=metadata
                )

                registry.register(tool)

        test_tools = registry.list_by_category("test")
        assert len(test_tools) == 2
        assert "test_tool_0" in test_tools
        assert "test_tool_1" in test_tools

        demo_tools = registry.list_by_category("demo")
        assert len(demo_tools) == 2

    def test_list_by_source(self):
        """测试按来源列出工具"""
        registry = ToolRegistry()

        for src in ["openclaw", "mcp"]:
            for i in range(2):
                metadata = ToolMetadata(
                    name=f"{src}_tool_{i}",
                    description=f"{src} tool {i}",
                    source=src
                )

                def handler(x):
                    return x

                tool = ToolDefinition(
                    name=f"{src}_tool_{i}",
                    handler=handler,
                    metadata=metadata
                )

                registry.register(tool)

        openclaw_tools = registry.list_by_source("openclaw")
        assert len(openclaw_tools) == 2

        mcp_tools = registry.list_by_source("mcp")
        assert len(mcp_tools) == 2

    def test_list_enabled(self):
        """测试列出已启用的工具"""
        registry = ToolRegistry()

        for i in range(4):
            metadata = ToolMetadata(
                name=f"tool_{i}",
                description=f"Tool {i}",
                source="test"
            )

            def handler(x):
                return x

            tool = ToolDefinition(
                name=f"tool_{i}",
                handler=handler,
                metadata=metadata,
                enabled=(i % 2 == 0)
            )

            registry.register(tool)

        enabled_tools = registry.list_enabled()
        assert len(enabled_tools) == 2
        assert "tool_0" in enabled_tools
        assert "tool_2" in enabled_tools

    def test_enable_disable_tool(self):
        """测试启用和禁用工具"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            source="test"
        )

        def handler(x):
            return x

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata,
            enabled=True
        )

        registry.register(tool)

        assert len(registry.list_enabled()) == 1

        registry.disable("test_tool")
        assert len(registry.list_enabled()) == 0

        registry.enable("test_tool")
        assert len(registry.list_enabled()) == 1

    def test_get_categories(self):
        """测试获取所有分类"""
        registry = ToolRegistry()

        for cat in ["test", "demo", "example"]:
            metadata = ToolMetadata(
                name=f"{cat}_tool",
                description=f"{cat} tool",
                category=cat,
                source="test"
            )

            def handler(x):
                return x

            tool = ToolDefinition(
                name=f"{cat}_tool",
                handler=handler,
                metadata=metadata
            )

            registry.register(tool)

        categories = registry.get_categories()
        assert len(categories) == 3
        assert "test" in categories
        assert "demo" in categories
        assert "example" in categories

    def test_get_sources(self):
        """测试获取所有来源"""
        registry = ToolRegistry()

        for src in ["openclaw", "mcp", "langchain"]:
            metadata = ToolMetadata(
                name=f"{src}_tool",
                description=f"{src} tool",
                source=src
            )

            def handler(x):
                return x

            tool = ToolDefinition(
                name=f"{src}_tool",
                handler=handler,
                metadata=metadata
            )

            registry.register(tool)

        sources = registry.get_sources()
        assert len(sources) == 3
        assert "openclaw" in sources
        assert "mcp" in sources
        assert "langchain" in sources

    def test_search_by_name(self):
        """测试按名称搜索"""
        registry = ToolRegistry()

        for name in ["calculator", "calculator_plus", "calculator_pro"]:
            metadata = ToolMetadata(
                name=name,
                description=f"{name} tool",
                source="test"
            )

            def handler(x):
                return x

            tool = ToolDefinition(
                name=name,
                handler=handler,
                metadata=metadata
            )

            registry.register(tool)

        results = registry.search("calculator")
        assert len(results) == 3

        results = registry.search("plus")
        assert len(results) == 1
        assert "calculator_plus" in results

    def test_search_by_description(self):
        """测试按描述搜索"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="math_tool",
            description="A tool for mathematical operations",
            source="test"
        )

        def handler(x):
            return x

        tool = ToolDefinition(
            name="math_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)

        results = registry.search("mathematical")
        assert len(results) == 1
        assert "math_tool" in results

    def test_search_by_tags(self):
        """测试按标签搜索"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="data_tool",
            description="A data processing tool",
            tags=["data", "processing", "analytics"],
            source="test"
        )

        def handler(x):
            return x

        tool = ToolDefinition(
            name="data_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)

        results = registry.search("analytics")
        assert len(results) == 1
        assert "data_tool" in results

    def test_get_metadata(self):
        """测试获取工具元数据"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            version="1.0.0",
            source="test"
        )

        def handler(x):
            return x

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)

        retrieved_metadata = registry.get_metadata("test_tool")
        assert retrieved_metadata is not None
        assert retrieved_metadata.name == "test_tool"
        assert retrieved_metadata.version == "1.0.0"

    def test_contains_operator(self):
        """测试 in 操作符"""
        registry = ToolRegistry()

        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            source="test"
        )

        def handler(x):
            return x

        tool = ToolDefinition(
            name="test_tool",
            handler=handler,
            metadata=metadata
        )

        registry.register(tool)

        assert "test_tool" in registry
        assert "nonexistent" not in registry


class TestToolError:
    """测试工具错误"""

    def test_create_error(self):
        """测试创建错误"""
        error = ToolError(
            ToolErrorCode.TIMEOUT,
            "Tool timed out",
            tool_name="test_tool"
        )

        assert error.code == ToolErrorCode.TIMEOUT
        assert error.message == "Tool timed out"
        assert error.tool_name == "test_tool"

    def test_error_with_original_exception(self):
        """测试带原始异常的错误"""
        original_error = ValueError("Invalid input")
        error = ToolError(
            ToolErrorCode.VALIDATION_ERROR,
            "Validation failed",
            original_error=original_error,
            tool_name="test_tool"
        )

        assert error.original_error == original_error
        assert error.code == ToolErrorCode.VALIDATION_ERROR

    def test_error_to_dict(self):
        """测试错误转字典"""
        original_error = ValueError("Test error")
        error = ToolError(
            ToolErrorCode.INTERNAL_ERROR,
            "Internal error",
            original_error=original_error,
            tool_name="test_tool",
            context={"retry_count": 3}
        )

        error_dict = error.to_dict()

        assert error_dict["code"] == "INTERNAL_ERROR"
        assert error_dict["message"] == "Internal error"
        assert error_dict["tool_name"] == "test_tool"
        assert error_dict["error_type"] == "ValueError"
        assert error_dict["error_message"] == "Test error"
        assert error_dict["context"]["retry_count"] == 3

    def test_error_str_representation(self):
        """测试错误字符串表示"""
        error = ToolError(
            ToolErrorCode.TIMEOUT,
            "Tool timed out",
            tool_name="test_tool"
        )

        error_str = str(error)
        assert "test_tool" in error_str
        assert "TIMEOUT" in error_str
        assert "Tool timed out" in error_str
