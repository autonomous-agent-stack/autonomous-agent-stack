"""
工具/插件兼容层（Shim）

统一工具调用的输入输出结构，归一错误语义，为多插件生态预留扩展点。

主要功能：
- 工具发现与注册
- 统一调用接口
- 错误回退机制
- 版本信息管理
"""

from .core import ToolRegistry, ToolCallResult, ToolError, ToolErrorCode
from .discovery import ToolDiscovery
from .caller import ToolCaller
from .fallback import FallbackManager

__version__ = "0.1.0"
__all__ = [
    "ToolRegistry",
    "ToolCallResult",
    "ToolError",
    "ToolErrorCode",
    "ToolDiscovery",
    "ToolCaller",
    "FallbackManager",
]
