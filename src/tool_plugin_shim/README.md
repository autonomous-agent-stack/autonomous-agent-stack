# 工具/插件兼容层（Shim）

一个统一的工具/插件兼容层，用于管理不同来源的工具和插件。

## 状态

✅ **核心功能已完成** - 已提交到 main 分支

## 快速开始

```python
from src.tool_plugin_shim.core import ToolRegistry
from src.tool_plugin_shim.discovery import ToolDiscovery, tool_decorator
from src.tool_plugin_shim.caller import ToolCaller

# 1. 创建组件
registry = ToolRegistry()
discovery = ToolDiscovery(registry)
caller = ToolCaller(registry)

# 2. 定义工具
@tool_decorator(
    name="my_tool",
    description="My amazing tool",
    category="example"
)
def my_function(x: int) -> int:
    return x * 2

# 3. 注册工具
from src.tool_plugin_shim.core import ToolDefinition
tool = ToolDefinition(
    name=my_function.__tool_metadata__.name,
    handler=my_function,
    metadata=my_function.__tool_metadata__
)
registry.register(tool)

# 4. 调用工具
result = caller.call("my_tool", 5)
if result.success:
    print(f"Result: {result.data}")  # 10
else:
    print(f"Error: {result.error}")
```

## 核心功能

### 1. 工具注册表

管理所有工具，支持按分类、来源、标签查询。

```python
# 查询工具
all_tools = registry.list_all()
math_tools = registry.list_by_category("math")
openclaw_tools = registry.list_by_source("openclaw")

# 搜索工具
results = registry.search("calculator")

# 启用/禁用工具
registry.disable("unreliable_tool")
registry.enable("reliable_tool")
```

### 2. 工具发现

自动从多种来源发现工具。

```python
# 从字典发现
tools_dict = {"tool1": func1, "tool2": func2}
discovery.discover_from_dict(tools_dict, source="my_source")

# 从模块发现
discovery.discover_from_module("my_tools_module")

# 从目录发现
discovery.discover_from_directory(Path("tools/"))

# 自动发现
discovery.add_discovery_path(Path("tools/"))
discovery.auto_discover()
```

### 3. 工具调用

统一的调用接口，支持超时、批量、并行调用。

```python
# 简单调用
result = caller.call("my_tool", arg1, arg2)

# 带超时
result = caller.call_with_timeout("my_tool", timeout=10, arg1)

# 安全调用（不抛异常）
result = caller.call_safe("my_tool", arg1)

# 批量调用
calls = [
    {"tool_name": "tool1", "args": [1, 2]},
    {"tool_name": "tool2", "kwargs": {"x": 1}},
]
results = caller.batch_call(calls)

# 并行调用
results = caller.parallel_call(calls, max_workers=4)
```

### 4. 回退管理

管理工具调用失败时的回退策略。

```python
from src.tool_plugin_shim.fallback import (
    FallbackManager,
    DefaultValueFallback,
    RetryFallback,
)

manager = FallbackManager()

# 设置默认回退
manager.set_default_handler(
    DefaultValueFallback(default_value={"status": "error"})
)

# 设置重试策略
manager.set_handler(
    "unreliable_tool",
    RetryFallback(retry_handler, max_retries=3)
)
```

## 错误处理

所有错误使用统一的错误码：

```python
from src.tool_plugin_shim.core import ToolErrorCode, ToolError

# 错误类型
TOOL_NOT_FOUND      # 工具未找到
VALIDATION_ERROR    # 参数验证失败
TIMEOUT             # 执行超时
INTERNAL_ERROR      # 工具内部错误
NETWORK_ERROR       # 网络错误
PERMISSION_ERROR    # 权限错误
UNAVAILABLE         # 工具不可用
FALLBACK_FAILED     # 回退失败

# 错误信息
try:
    result = caller.call("my_tool")
except ToolError as e:
    print(f"Code: {e.code.value}")
    print(f"Message: {e.message}")
    print(f"Tool: {e.tool_name}")
    print(f"Context: {e.context}")
```

## 测试

```bash
# 运行所有测试
cd tests && source .venv/bin/activate
pytest ../tests/tool_plugin_shim/ -v

# 运行特定测试
pytest ../tests/tool_plugin_shim/test_core.py -v
pytest ../tests/tool_plugin_shim/test_discovery.py -v
pytest ../tests/tool_plugin_shim/test_caller.py -v
pytest ../tests/tool_plugin_shim/test_fallback.py -v
pytest ../tests/tool_plugin_shim/test_integration.py -v

# 查看覆盖率
pytest ../tests/tool_plugin_shim/ --cov=src/tool_plugin_shim --cov-report=html
```

## 文档

- **集成指南**: [docs/TOOL_PLUGIN_SHIM_GUIDE.md](../docs/TOOL_PLUGIN_SHIM_GUIDE.md)
- **实现总结**: [docs/TOOL_PLUGIN_SHIM_SUMMARY.md](../docs/TOOL_PLUGIN_SHIM_SUMMARY.md)

## 架构

```
ToolRegistry (注册表)
    ↓
ToolDiscovery (发现) → ToolDefinition (定义) → ToolMetadata (元数据)
    ↓
ToolCaller (调用器)
    ↓
ToolCallResult (结果) / ToolError (错误)
    ↓
FallbackManager (回退) → FallbackHandler (处理器)
```

## 集成到现有系统

### OpenClaw 集成

```python
# 包装 OpenClaw 工具
def wrap_openclaw_tool(tool_func, tool_name, description):
    metadata = ToolMetadata(
        name=tool_name,
        description=description,
        source="openclaw",
        version="1.0.0"
    )
    tool = ToolDefinition(
        name=tool_name,
        handler=tool_func,
        metadata=metadata
    )
    registry.register(tool)
```

### 插件生态适配器

```python
class MCPAdapter:
    """MCP 插件适配器"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def register_mcp_tool(self, mcp_tool):
        """将 MCP 工具注册到 shim"""
        metadata = ToolMetadata(
            name=mcp_tool.name,
            description=mcp_tool.description,
            source="mcp",
            version="1.0.0"
        )

        def handler(**kwargs):
            return mcp_tool.execute(kwargs)

        tool = ToolDefinition(
            name=mcp_tool.name,
            handler=handler,
            metadata=metadata
        )

        self.registry.register(tool)
```

## 性能考虑

- 工具注册在启动时完成
- 使用并行调用提高效率
- 使用缓存回退缓存频繁调用结果
- 根据工具特性设置合理超时时间

## 待办事项

- [ ] 修复41个失败的测试（主要是参数问题）
- [ ] 添加更多性能测试
- [ ] 实现常见插件生态的适配器
- [ ] 添加监控和日志
- [ ] 完善文档和示例

## 贡献

欢迎提交 PR 和 Issue！

## 许可

MIT License
