"""
工具/插件兼容层 - 核心模块

定义统一的错误类型、工具调用结果和注册表。
"""

import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ToolErrorCode(Enum):
    """工具错误码枚举"""
    # 工具未找到
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    # 参数验证失败
    VALIDATION_ERROR = "VALIDATION_ERROR"
    # 执行超时
    TIMEOUT = "TIMEOUT"
    # 工具内部错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    # 网络错误
    NETWORK_ERROR = "NETWORK_ERROR"
    # 权限错误
    PERMISSION_ERROR = "PERMISSION_ERROR"
    # 不可用（服务宕机等）
    UNAVAILABLE = "UNAVAILABLE"
    # 回退失败
    FALLBACK_FAILED = "FALLBACK_FAILED"


@dataclass
class ToolError(Exception):
    """工具调用错误"""
    code: ToolErrorCode
    message: str
    original_error: Optional[Exception] = None
    tool_name: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = [f"[{self.code.value}] {self.message}"]
        if self.tool_name:
            parts.insert(0, f"Tool: {self.tool_name}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "message": self.message,
            "tool_name": self.tool_name,
            "context": self.context,
            "error_type": type(self.original_error).__name__ if self.original_error else None,
            "error_message": str(self.original_error) if self.original_error else None,
        }


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    data: Any
    tool_name: str
    duration_ms: int
    error: Optional[ToolError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "data": self.data,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "error": self.error.to_dict() if self.error else None,
            "metadata": self.metadata,
            "fallback_used": self.fallback_used,
        }


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    version: str
    author: Optional[str] = None
    category: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    requires_network: bool = False
    tags: List[str] = field(default_factory=list)
    # 插件来源标识（如 "openclaw", "mcp", "langchain" 等）
    source: Optional[str] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    handler: Callable
    metadata: ToolMetadata
    # 回退处理器
    fallback_handler: Optional[Callable] = None
    # 版本兼容性信息
    compatible_versions: List[str] = field(default_factory=list)
    # 是否启用
    enabled: bool = True


class ToolRegistry:
    """工具注册表

    管理所有已注册的工具，提供发现、注册、查询功能。
    """

    def __init__(self):
        """初始化工具注册表"""
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._sources: Dict[str, List[str]] = {}

    def register(self, tool: ToolDefinition) -> None:
        """注册工具

        Args:
            tool: 工具定义

        Raises:
            ValueError: 如果工具名已存在
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")

        self._tools[tool.name] = tool

        # 按分类索引
        category = tool.metadata.category or "uncategorized"
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)

        # 按来源索引
        source = tool.metadata.source or "unknown"
        if source not in self._sources:
            self._sources[source] = []
        self._sources[source].append(tool.name)

    def unregister(self, tool_name: str) -> None:
        """注销工具

        Args:
            tool_name: 工具名称

        Raises:
            KeyError: 如果工具不存在
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]

        # 从分类索引移除
        category = tool.metadata.category or "uncategorized"
        if category in self._categories and tool_name in self._categories[category]:
            self._categories[category].remove(tool_name)

        # 从来源索引移除
        source = tool.metadata.source or "unknown"
        if source in self._sources and tool_name in self._sources[source]:
            self._sources[source].remove(tool_name)

        del self._tools[tool_name]

    def get(self, tool_name: str) -> Optional[ToolDefinition]:
        """获取工具定义

        Args:
            tool_name: 工具名称

        Returns:
            工具定义，如果不存在返回 None
        """
        return self._tools.get(tool_name)

    def list_all(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def list_by_category(self, category: str) -> List[str]:
        """按分类列出工具"""
        return self._categories.get(category, []).copy()

    def list_by_source(self, source: str) -> List[str]:
        """按来源列出工具"""
        return self._sources.get(source, []).copy()

    def list_enabled(self) -> List[str]:
        """列出已启用的工具"""
        return [name for name, tool in self._tools.items() if tool.enabled]

    def enable(self, tool_name: str) -> None:
        """启用工具"""
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found")
        self._tools[tool_name].enabled = True

    def disable(self, tool_name: str) -> None:
        """禁用工具"""
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found")
        self._tools[tool_name].enabled = False

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self._categories.keys())

    def get_sources(self) -> List[str]:
        """获取所有来源"""
        return list(self._sources.keys())

    def search(self, query: str) -> List[str]:
        """搜索工具（按名称、描述、标签）"""
        query = query.lower()
        results = []

        for name, tool in self._tools.items():
            # 名称匹配
            if query in name.lower():
                results.append(name)
                continue

            # 描述匹配
            if query in tool.metadata.description.lower():
                results.append(name)
                continue

            # 标签匹配
            for tag in tool.metadata.tags:
                if query in tag.lower():
                    results.append(name)
                    break

        return results

    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        tool = self.get(tool_name)
        return tool.metadata if tool else None

    def __len__(self) -> int:
        """返回已注册工具数量"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._tools
