"""
工具调用模块

统一的工具调用接口，包含超时控制、错误处理和结果封装。
"""

import concurrent.futures
import logging
import signal
import time
import traceback
from typing import Any, Dict, Optional, Callable

from .core import (
    ToolRegistry,
    ToolCallResult,
    ToolError,
    ToolErrorCode,
    ToolDefinition,
)


logger = logging.getLogger(__name__)


class ToolCaller:
    """工具调用器

    提供统一的工具调用接口，处理超时、错误和结果封装。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        default_timeout: int = 30,
        fallback_handler: Optional[Callable] = None
    ):
        """初始化工具调用器

        Args:
            registry: 工具注册表
            default_timeout: 默认超时时间（秒）
            fallback_handler: 默认回退处理器
        """
        self.registry = registry
        self.default_timeout = default_timeout
        self.fallback_handler = fallback_handler

    def call(
        self,
        tool_name: str,
        *args,
        **kwargs
    ) -> ToolCallResult:
        """调用工具

        Args:
            tool_name: 工具名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具调用结果

        Raises:
            ToolError: 如果工具不存在或调用失败
        """
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ToolError(
                ToolErrorCode.TOOL_NOT_FOUND,
                f"Tool '{tool_name}' not found in registry"
            )

        if not tool.enabled:
            raise ToolError(
                ToolErrorCode.UNAVAILABLE,
                f"Tool '{tool_name}' is disabled"
            )

        return self._execute_tool(tool, *args, **kwargs)

    def call_safe(
        self,
        tool_name: str,
        *args,
        **kwargs
    ) -> ToolCallResult:
        """安全调用工具（总是返回结果，不抛出异常）

        Args:
            tool_name: 工具名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具调用结果（即使失败也返回错误信息）
        """
        try:
            return self.call(tool_name, *args, **kwargs)
        except ToolError as e:
            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool_name,
                duration_ms=0,
                error=e,
                fallback_used=False
            )
        except Exception as e:
            # 捕获未预期的异常
            error = ToolError(
                ToolErrorCode.INTERNAL_ERROR,
                f"Unexpected error calling tool '{tool_name}': {str(e)}",
                original_error=e
            )
            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool_name,
                duration_ms=0,
                error=error,
                fallback_used=False
            )

    def call_with_timeout(
        self,
        tool_name: str,
        timeout: Optional[int] = None,
        *args,
        **kwargs
    ) -> ToolCallResult:
        """带超时控制的工具调用

        Args:
            tool_name: 工具名称
            timeout: 超时时间（秒），None 表示使用工具默认超时
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具调用结果
        """
        tool = self.registry.get(tool_name)

        if tool is None:
            raise ToolError(
                ToolErrorCode.TOOL_NOT_FOUND,
                f"Tool '{tool_name}' not found in registry"
            )

        # 确定实际超时时间
        actual_timeout = timeout or tool.metadata.timeout_seconds or self.default_timeout

        return self._execute_tool(tool, *args, **kwargs, timeout=actual_timeout)

    def _execute_tool(
        self,
        tool: ToolDefinition,
        *args,
        timeout: Optional[int] = None,
        **kwargs
    ) -> ToolCallResult:
        """执行工具

        Args:
            tool: 工具定义
            *args: 位置参数
            timeout: 超时时间
            **kwargs: 关键字参数

        Returns:
            工具调用结果
        """
        start_time = time.time()
        tool_timeout = timeout or tool.metadata.timeout_seconds or self.default_timeout

        try:
            # 使用线程池执行（避免阻塞主线程）
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(tool.handler, *args, **kwargs)

                try:
                    result = future.result(timeout=tool_timeout)
                    duration_ms = int((time.time() - start_time) * 1000)

                    return ToolCallResult(
                        success=True,
                        data=result,
                        tool_name=tool.name,
                        duration_ms=duration_ms,
                        metadata={
                            "timeout": tool_timeout,
                            "source": tool.metadata.source,
                        }
                    )

                except concurrent.futures.TimeoutError:
                    duration_ms = int((time.time() - start_time) * 1000)

                    error = ToolError(
                        ToolErrorCode.TIMEOUT,
                        f"Tool '{tool.name}' timed out after {tool_timeout}s",
                        tool_name=tool.name,
                        context={"timeout": tool_timeout}
                    )

                    logger.warning(f"Tool timeout: {tool.name} after {tool_timeout}s")

                    # 尝试使用回退处理器
                    if tool.fallback_handler or self.fallback_handler:
                        return self._try_fallback(
                            tool,
                            error,
                            *args,
                            **kwargs
                        )

                    return ToolCallResult(
                        success=False,
                        data=None,
                        tool_name=tool.name,
                        duration_ms=duration_ms,
                        error=error,
                        fallback_used=False
                    )

        except ToolError:
            # 重新抛出工具错误
            raise

        except PermissionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error = ToolError(
                ToolErrorCode.PERMISSION_ERROR,
                f"Permission denied for tool '{tool.name}': {str(e)}",
                tool_name=tool.name,
                original_error=e
            )

            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool.name,
                duration_ms=duration_ms,
                error=error,
                fallback_used=False
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # 检查是否为网络错误
            error_code = self._classify_error(e)

            error = ToolError(
                error_code,
                f"Tool '{tool.name}' failed: {str(e)}",
                tool_name=tool.name,
                original_error=e,
                context={"traceback": traceback.format_exc()}
            )

            logger.error(f"Tool execution failed: {tool.name}", exc_info=True)

            # 尝试使用回退处理器
            if tool.fallback_handler or self.fallback_handler:
                return self._try_fallback(tool, error, *args, **kwargs)

            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool.name,
                duration_ms=duration_ms,
                error=error,
                fallback_used=False
            )

    def _try_fallback(
        self,
        tool: ToolDefinition,
        original_error: ToolError,
        *args,
        **kwargs
    ) -> ToolCallResult:
        """尝试使用回退处理器

        Args:
            tool: 工具定义
            original_error: 原始错误
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具调用结果
        """
        start_time = time.time()

        # 优先使用工具级别的回退处理器
        fallback_handler = tool.fallback_handler or self.fallback_handler

        if fallback_handler is None:
            # 无回退处理器可用
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool.name,
                duration_ms=duration_ms,
                error=original_error,
                fallback_used=False
            )

        try:
            # 调用回退处理器
            result = fallback_handler(tool.name, original_error, *args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Fallback handler succeeded for tool: {tool.name}")

            return ToolCallResult(
                success=True,
                data=result,
                tool_name=tool.name,
                duration_ms=duration_ms,
                error=None,
                fallback_used=True,
                metadata={
                    "original_error": original_error.to_dict(),
                    "fallback_used": True
                }
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            fallback_error = ToolError(
                ToolErrorCode.FALLBACK_FAILED,
                f"Fallback handler failed for tool '{tool.name}': {str(e)}",
                tool_name=tool.name,
                original_error=e,
                context={
                    "original_error": original_error.to_dict()
                }
            )

            logger.error(f"Fallback handler failed: {tool.name}", exc_info=True)

            return ToolCallResult(
                success=False,
                data=None,
                tool_name=tool.name,
                duration_ms=duration_ms,
                error=fallback_error,
                fallback_used=False,
                metadata={
                    "original_error": original_error.to_dict()
                }
            )

    def _classify_error(self, error: Exception) -> ToolErrorCode:
        """分类错误类型

        Args:
            error: 异常对象

        Returns:
            错误码
        """
        # 网络相关错误
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ToolErrorCode.NETWORK_ERROR

        # 权限错误
        if isinstance(error, PermissionError):
            return ToolErrorCode.PERMISSION_ERROR

        # 验证错误
        if isinstance(error, (ValueError, TypeError, AttributeError)):
            return ToolErrorCode.VALIDATION_ERROR

        # 其他错误归为内部错误
        return ToolErrorCode.INTERNAL_ERROR

    def batch_call(
        self,
        calls: list[Dict[str, Any]]
    ) -> list[ToolCallResult]:
        """批量调用工具

        Args:
            calls: 调用列表，每个元素是一个字典，包含：
                - tool_name: 工具名称
                - args: 位置参数（可选）
                - kwargs: 关键字参数（可选）
                - timeout: 超时时间（可选）

        Returns:
            工具调用结果列表
        """
        results = []

        for call_spec in calls:
            tool_name = call_spec.get("tool_name")
            args = call_spec.get("args", [])
            kwargs = call_spec.get("kwargs", {})
            timeout = call_spec.get("timeout")

            if timeout is not None:
                result = self.call_with_timeout(tool_name, timeout, *args, **kwargs)
            else:
                result = self.call(tool_name, *args, **kwargs)

            results.append(result)

        return results

    def parallel_call(
        self,
        calls: list[Dict[str, Any]],
        max_workers: int = 4
    ) -> list[ToolCallResult]:
        """并行调用工具

        Args:
            calls: 调用列表（同 batch_call）
            max_workers: 最大并发数

        Returns:
            工具调用结果列表（顺序与输入一致）
        """
        def execute_call(call_spec):
            tool_name = call_spec.get("tool_name")
            args = call_spec.get("args", [])
            kwargs = call_spec.get("kwargs", {})
            timeout = call_spec.get("timeout")

            try:
                if timeout is not None:
                    result = self.call_with_timeout(tool_name, timeout, *args, **kwargs)
                else:
                    result = self.call(tool_name, *args, **kwargs)
                return (len(calls) - 1, result)  # 返回索引
            except Exception as e:
                error = ToolError(
                    ToolErrorCode.INTERNAL_ERROR,
                    f"Parallel call failed: {str(e)}",
                    original_error=e
                )
                return (len(calls) - 1, ToolCallResult(
                    success=False,
                    data=None,
                    tool_name=tool_name,
                    duration_ms=0,
                    error=error,
                    fallback_used=False
                ))

        results = [None] * len(calls)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(execute_call, call_spec) for call_spec in calls]

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                index, result = future.result()
                results[index] = result

        return results
