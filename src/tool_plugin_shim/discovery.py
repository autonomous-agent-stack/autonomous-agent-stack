"""
工具发现模块

自动发现和加载不同来源的工具。
"""

import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, Callable

from .core import ToolRegistry, ToolDefinition, ToolMetadata, ToolError, ToolErrorCode


logger = logging.getLogger(__name__)


class ToolDiscovery:
    """工具发现器

    支持从多个来源自动发现工具：
    - Python 模块
    - 函数注解
    - 配置文件
    - 插件目录
    """

    def __init__(self, registry: ToolRegistry):
        """初始化工具发现器

        Args:
            registry: 工具注册表
        """
        self.registry = registry
        self.discovery_paths: List[Path] = []
        self.loaded_modules: Dict[str, Any] = {}

    def add_discovery_path(self, path: Path, recursive: bool = True) -> None:
        """添加工具发现路径

        Args:
            path: 路径
            recursive: 是否递归搜索
        """
        if not path.exists():
            logger.warning(f"Discovery path does not exist: {path}")
            return

        if recursive and path.is_dir():
            # 添加目录及其子目录
            for item in path.rglob("*.py"):
                if item.name != "__init__.py":
                    self.discovery_paths.append(item)
        else:
            self.discovery_paths.append(path)

        logger.info(f"Added discovery path: {path}")

    def discover_from_module(self, module_name: str, source: str = "module") -> int:
        """从 Python 模块发现工具

        Args:
            module_name: 模块名（支持点号路径）
            source: 来源标识

        Returns:
            发现并注册的工具数量
        """
        count = 0

        try:
            module = importlib.import_module(module_name)
            self.loaded_modules[module_name] = module

            # 遍历模块成员
            for name, obj in inspect.getmembers(module):
                if self._is_tool_function(obj):
                    # 尝试从注解或文档字符串提取元数据
                    metadata = self._extract_metadata(obj, name, source)

                    tool = ToolDefinition(
                        name=metadata.name,
                        handler=obj,
                        metadata=metadata,
                        source=source
                    )

                    self.registry.register(tool)
                    count += 1
                    logger.info(f"Discovered tool: {metadata.name} from {module_name}")

        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            raise ToolError(
                ToolErrorCode.INTERNAL_ERROR,
                f"Failed to import module: {module_name}",
                original_error=e
            )

        return count

    def discover_from_file(self, file_path: Path, source: str = "file") -> int:
        """从 Python 文件发现工具

        Args:
            file_path: 文件路径
            source: 来源标识

        Returns:
            发现并注册的工具数量
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 0

        # 将文件路径转换为模块路径
        module_path = file_path.parent
        module_name = file_path.stem

        if str(module_path) not in sys.path:
            sys.path.insert(0, str(module_path))

        return self.discover_from_module(module_name, source)

    def discover_from_directory(
        self,
        directory: Path,
        source: str = "directory",
        pattern: str = "*.py"
    ) -> int:
        """从目录发现工具

        Args:
            directory: 目录路径
            source: 来源标识
            pattern: 文件匹配模式

        Returns:
            发现并注册的工具数量
        """
        count = 0

        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 0

        for file_path in directory.glob(pattern):
            if file_path.name == "__init__.py":
                continue

            try:
                count += self.discover_from_file(file_path, source)
            except Exception as e:
                logger.warning(f"Failed to discover tools from {file_path}: {e}")

        return count

    def discover_from_dict(
        self,
        tools_dict: Dict[str, Callable],
        source: str = "dict"
    ) -> int:
        """从字典发现工具

        Args:
            tools_dict: 工具字典 {name: handler}
            source: 来源标识

        Returns:
            发现并注册的工具数量
        """
        count = 0

        for name, handler in tools_dict.items():
            if self._is_tool_function(handler):
                metadata = self._extract_metadata(handler, name, source)

                tool = ToolDefinition(
                    name=metadata.name,
                    handler=handler,
                    metadata=metadata
                )

                self.registry.register(tool)
                count += 1
                logger.info(f"Discovered tool: {metadata.name} from dict")

        return count

    def auto_discover(self) -> int:
        """自动发现所有路径中的工具

        Returns:
            发现并注册的工具总数
        """
        total = 0

        for path in self.discovery_paths:
            if path.is_file():
                total += self.discover_from_file(path, "auto")
            elif path.is_dir():
                total += self.discover_from_directory(path, "auto")

        logger.info(f"Auto-discovered {total} tools from {len(self.discovery_paths)} paths")
        return total

    def _is_tool_function(self, obj: Any) -> bool:
        """检查是否为工具函数"""
        return (
            inspect.isfunction(obj) or
            inspect.ismethod(obj) or
            (inspect.isclass(obj) and hasattr(obj, '__call__'))
        )

    def _extract_metadata(
        self,
        func: Callable,
        default_name: str,
        default_source: str
    ) -> ToolMetadata:
        """从函数提取元数据

        Args:
            func: 函数对象
            default_name: 默认名称
            default_source: 默认来源

        Returns:
            工具元数据
        """
        # 尝试从注解提取
        if hasattr(func, '__annotations__') and 'tool_metadata' in func.__annotations__:
            return func.__annotations__['tool_metadata']

        # 从文档字符串提取
        doc = inspect.getdoc(func) or ""

        # 简单解析第一行作为描述
        lines = doc.strip().split('\n')
        description = lines[0] if lines else f"Tool from {default_source}"

        # 尝试解析更多元数据（如果文档中有 YAML 风格的元数据）
        category = None
        timeout = 30
        requires_network = False
        tags = []

        # 检查是否有注解标记
        if hasattr(func, '__tool_category__'):
            category = func.__tool_category__
        if hasattr(func, '__tool_timeout__'):
            timeout = func.__tool_timeout__
        if hasattr(func, '__tool_requires_network__'):
            requires_network = func.__tool_requires_network__
        if hasattr(func, '__tool_tags__'):
            tags = func.__tool_tags__

        # 提取参数信息
        sig = inspect.signature(func)
        parameters = {}
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None,
            }
            parameters[param_name] = param_info

        return ToolMetadata(
            name=default_name,
            description=description,
            version="1.0.0",
            category=category,
            parameters=parameters,
            timeout_seconds=timeout,
            requires_network=requires_network,
            tags=tags,
            source=default_source
        )


def tool_decorator(
    name: str,
    description: str,
    category: Optional[str] = None,
    timeout_seconds: int = 30,
    requires_network: bool = False,
    tags: Optional[List[str]] = None,
    version: str = "1.0.0",
    author: Optional[str] = None,
    source: str = "decorator"
):
    """工具装饰器

    用于将普通函数标记为工具，并附加元数据。

    Args:
        name: 工具名称
        description: 工具描述
        category: 分类
        timeout_seconds: 超时时间（秒）
        requires_network: 是否需要网络
        tags: 标签列表
        version: 版本
        author: 作者
        source: 来源标识

    Example:
        ```python
        @tool_decorator(
            name="my_tool",
            description="A simple tool",
            category="example",
            tags=["demo"]
        )
        def my_function(x: int, y: int) -> int:
            return x + y
        ```
    """
    def decorator(func):
        # 创建元数据
        metadata = ToolMetadata(
            name=name,
            description=description,
            version=version,
            author=author,
            category=category,
            timeout_seconds=timeout_seconds,
            requires_network=requires_network,
            tags=tags or [],
            source=source
        )

        # 将元数据附加到函数
        func.__tool_metadata__ = metadata

        # 也可以作为注解
        if not hasattr(func, '__annotations__'):
            func.__annotations__ = {}
        func.__annotations__['tool_metadata'] = metadata

        return func

    return decorator
