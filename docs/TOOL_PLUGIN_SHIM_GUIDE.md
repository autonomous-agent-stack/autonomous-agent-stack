# 工具/插件兼容层（Shim）- 兼容性说明

## 概述

`src/tool_plugin_shim/` 提供了一个统一的工具/插件兼容层，用于：

1. **统一工具调用的输入输出结构**
2. **归一错误处理语义**
3. **为多种插件生态预留扩展点**
4. **与现有 OpenClaw/self_integration 兼容**

## 版本信息

- **版本**: 0.1.0
- **状态**: 稳定
- **兼容性**: Python 3.8+

## 核心组件

### 1. 工具注册表（ToolRegistry）

管理所有已注册的工具，支持按分类、来源和标签查询。

```python
from src.tool_plugin_shim.core import ToolRegistry, ToolDefinition, ToolMetadata

registry = ToolRegistry()

# 注册工具
metadata = ToolMetadata(
    name="my_tool",
    description="My tool description",
    category="example",
    source="custom"
)

tool = ToolDefinition(
    name="my_tool",
    handler=my_function,
    metadata=metadata
)

registry.register(tool)

# 查询工具
tools = registry.list_all()
math_tools = registry.list_by_category("math")
custom_tools = registry.list_by_source("custom")
```

### 2. 工具发现（ToolDiscovery）

自动从不同来源发现和加载工具：

```python
from src.tool_plugin_shim.discovery import ToolDiscovery, tool_decorator

discovery = ToolDiscovery(registry)

# 从字典发现
tools_dict = {
    "tool1": function1,
    "tool2": function2,
}
discovery.discover_from_dict(tools_dict, source="my_source")

# 使用装饰器
@tool_decorator(
    name="calculator",
    description="A simple calculator",
    category="math",
    tags=["math", "calc"]
)
def add(a: int, b: int) -> int:
    return a + b
```

### 3. 工具调用器（ToolCaller）

统一的工具调用接口，处理超时、错误和结果封装：

```python
from src.tool_plugin_shim.caller import ToolCaller

caller = ToolCaller(registry)

# 简单调用
result = caller.call("my_tool", arg1, arg2, kwarg1=value1)

if result.success:
    print(f"Result: {result.data}")
else:
    print(f"Error: {result.error}")

# 安全调用（不抛出异常）
result = caller.call_safe("my_tool", arg1)

# 带超时的调用
result = caller.call_with_timeout("my_tool", timeout=10, arg1)

# 批量调用
calls = [
    {"tool_name": "tool1", "args": [1, 2]},
    {"tool_name": "tool2", "kwargs": {"x": 1, "y": 2}},
]
results = caller.batch_call(calls)

# 并行调用
results = caller.parallel_call(calls, max_workers=4)
```

### 4. 回退管理器（FallbackManager）

管理工具调用失败时的回退策略：

```python
from src.tool_plugin_shim.fallback import (
    FallbackManager,
    DefaultValueFallback,
    RetryFallback,
    CachedResultFallback,
)

manager = FallbackManager()

# 设置默认回退
manager.set_default_handler(
    DefaultValueFallback(default_value={"status": "unavailable"})
)

# 设置工具特定回退
manager.set_handler(
    "unreliable_tool",
    RetryFallback(retry_handler=retry_func, max_retries=3)
)

# 设置缓存回退
cache_handler = CachedResultFallback()
manager.set_handler("cacheable_tool", cache_handler)
```

## 错误处理

### 错误码

所有错误都使用统一的错误码：

```python
from src.tool_plugin_shim.core import ToolErrorCode

# TOOL_NOT_FOUND - 工具未找到
# VALIDATION_ERROR - 参数验证失败
# TIMEOUT - 执行超时
# INTERNAL_ERROR - 工具内部错误
# NETWORK_ERROR - 网络错误
# PERMISSION_ERROR - 权限错误
# UNAVAILABLE - 工具不可用
# FALLBACK_FAILED - 回退失败
```

### 错误信息

错误对象包含完整的上下文信息：

```python
try:
    result = caller.call("my_tool")
except ToolError as e:
    # 访问错误信息
    print(f"Code: {e.code.value}")
    print(f"Message: {e.message}")
    print(f"Tool: {e.tool_name}")

    # 转换为字典
    error_dict = e.to_dict()
```

## 集成指南

### 方式一：直接使用 shim

```python
# 1. 创建注册表和发现器
from src.tool_plugin_shim.core import ToolRegistry
from src.tool_plugin_shim.discovery import ToolDiscovery
from src.tool_plugin_shim.caller import ToolCaller

registry = ToolRegistry()
discovery = ToolDiscovery(registry)
caller = ToolCaller(registry)

# 2. 发现并注册工具
discovery.discover_from_module("my_tools_module")

# 3. 调用工具
result = caller.call("my_tool", arg1, arg2)
```

### 方式二：包装现有工具

```python
# 包装现有的 OpenClaw 工具
def wrap_openclaw_tool(tool_func, tool_name, description):
    metadata = ToolMetadata(
        name=tool_name,
        description=description,
        source="openclaw"
    )

    tool = ToolDefinition(
        name=tool_name,
        handler=tool_func,
        metadata=metadata
    )

    registry.register(tool)
```

### 方式三：适配器模式

为不同的插件生态系统创建适配器：

```python
class MCPAdapter:
    """MCP 插件适配器"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def register_mcp_tool(self, mcp_tool):
        """将 MCP 工具注册到 shim"""
        # 提取 MCP 工具元数据
        metadata = ToolMetadata(
            name=mcp_tool.name,
            description=mcp_tool.description,
            source="mcp"
        )

        # 包装 MCP 工具处理器
        def handler(**kwargs):
            return mcp_tool.execute(kwargs)

        # 注册到 shim
        tool = ToolDefinition(
            name=mcp_tool.name,
            handler=handler,
            metadata=metadata
        )

        self.registry.register(tool)
```

## 与现有系统集成

### OpenClaw 集成

```python
# 在 OpenClaw 中使用 shim
from src.tool_plugin_shim.core import ToolRegistry
from src.tool_plugin_shim.caller import ToolCaller

# 创建全局注册表
registry = ToolRegistry()
caller = ToolCaller(registry)

# 注册 OpenClaw 原生工具
for tool_name, tool_func in openclaw_tools.items():
    wrap_openclaw_tool(tool_func, tool_name, f"OpenClaw {tool_name}")

# 使用统一的调用接口
def call_tool_unified(tool_name, *args, **kwargs):
    result = caller.call(tool_name, *args, **kwargs)

    if result.success:
        return result.data
    else:
        # 处理错误
        logger.error(f"Tool {tool_name} failed: {result.error}")
        return None
```

### Self-Integration 集成

```python
# 在 self_integration 中使用 shim
from src.tool_plugin_shim.core import ToolRegistry

class SelfIntegratedAgent:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.tool_caller = ToolCaller(self.tool_registry)

    def register_self_tools(self):
        """注册 self 工具"""
        # 自动发现 self 工具
        from src.tool_plugin_shim.discovery import ToolDiscovery
        discovery = ToolDiscovery(self.tool_registry)
        discovery.discover_from_directory("tools/self", source="self")

    def use_tool(self, tool_name, *args, **kwargs):
        """使用工具"""
        result = self.tool_caller.call(tool_name, *args, **kwargs)

        if result.success:
            return result.data
        else:
            # 触发 self 反思
            self.reflect_on_tool_failure(result.error)
            return None
```

## 最佳实践

### 1. 工具命名

```python
# 好的命名：描述性、符合规范
@tool_decorator(
    name="math_calculator_add",
    description="Add two numbers",
    category="math"
)
def add_numbers(a, b):
    return a + b

# 避免模糊的命名
@tool_decorator(
    name="tool1",  # 太模糊
    description="A tool"
)
def func(x):
    return x
```

### 2. 错误处理

```python
# 好的做法：使用工具级别的回退
manager.set_handler(
    "unreliable_tool",
    RetryFallback(retry_handler, max_retries=3)
)

# 避免：忽略错误
result = caller.call("tool")
# 不检查 result.success
```

### 3. 超时设置

```python
# 根据工具特性设置合理的超时
@tool_decorator(
    name="quick_tool",
    description="Fast operation",
    timeout_seconds=5
)
def quick_operation():
    return "done"

@tool_decorator(
    name="slow_tool",
    description="Long-running operation",
    timeout_seconds=120
)
def slow_operation():
    # 可能需要很长时间
    return "done"
```

### 4. 元数据完整

```python
# 提供完整的元数据
@tool_decorator(
    name="data_processor",
    description="Process large datasets",
    category="data",
    tags=["data", "processing", "analytics"],
    version="1.0.0",
    author="data_team",
    requires_network=True
)
def process_data(data):
    return transformed_data
```

## 扩展性

### 添加新的插件生态

```python
class NewPluginAdapter:
    """新插件生态的适配器"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def discover_and_register(self, plugin_path):
        """发现并注册新插件工具"""
        # 1. 扫描插件目录
        # 2. 提取工具元数据
        # 3. 包装工具处理器
        # 4. 注册到 shim
        pass
```

### 自定义回退策略

```python
from src.tool_plugin_shim.fallback import FallbackHandler

class CustomFallback(FallbackHandler):
    """自定义回退处理器"""

    def handle(self, tool_name, error, *args, **kwargs):
        # 实现自定义回退逻辑
        if error.code == ToolErrorCode.TIMEOUT:
            return {"timeout": True, "cached": self.get_cached()}
        else:
            raise error
```

## 性能考虑

1. **工具注册**: 在启动时完成，避免运行时动态注册
2. **批量调用**: 使用 `batch_call` 或 `parallel_call` 提高效率
3. **缓存**: 使用 `CachedResultFallback` 缓存频繁调用的结果
4. **超时控制**: 根据工具特性设置合理的超时时间

## 测试

```bash
# 运行所有测试
pytest tests/tool_plugin_shim/

# 运行特定测试
pytest tests/tool_plugin_shim/test_core.py
pytest tests/tool_plugin_shim/test_discovery.py
pytest tests/tool_plugin_shim/test_caller.py
pytest tests/tool_plugin_shim/test_fallback.py
pytest tests/tool_plugin_shim/test_integration.py

# 查看覆盖率
pytest tests/tool_plugin_shim/ --cov=src/tool_plugin_shim --cov-report=html
```

## 故障排除

### 问题：工具调用超时

```python
# 增加超时时间
result = caller.call_with_timeout("slow_tool", timeout=120)

# 或使用回退
manager.set_handler(
    "slow_tool",
    CachedResultFallback()
)
```

### 问题：工具未找到

```python
# 检查工具是否已注册
if "my_tool" not in registry:
    # 发现并注册
    discovery.discover_from_module("my_tools")
```

### 问题：回退失败

```python
# 设置更健壮的回退链
composite = manager.create_composite_handler(
    "my_tool",
    RetryFallback(retry_func, max_retries=3),
    CachedResultFallback(),
    DefaultValueFallback(default_value={})
)
```

## 总结

工具/插件兼容层提供了一个灵活、可扩展的方式来管理不同来源的工具。通过统一接口、错误处理和回退机制，它能够：

1. 简化工具集成
2. 提高系统健壮性
3. 支持多种插件生态
4. 与现有系统无缝集成

使用此 shim 可以快速将新工具集成到系统中，同时保持代码的可维护性和可扩展性。
