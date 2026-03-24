"""
Agent 相关错误

涵盖任务规划、工具调用、自我反思、协作等场景的错误类型。
"""

from typing import Any, Dict, List, Optional

from .base import BaseError, ErrorSeverity, RecoveryStrategy, RetryConfig


class TaskPlanningError(BaseError):
    """
    任务规划错误

    当 Agent 无法正确规划任务或生成执行计划时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新规划）或 MANUAL（人工干预）
    重试：少量重试
    """

    message_template = "任务规划失败：{agent_name} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=2.0, max_delay=20.0, backoff_factor=2.0)
    error_code = "AGENT_TASK_PLANNING_ERROR"

    def __init__(
        self,
        agent_name: str,
        reason: str = "无法生成有效的任务计划",
        task_description: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["agent_name"] = agent_name
        details["reason"] = reason
        if task_description:
            details["task_description"] = task_description[:300]
        if available_tools:
            details["available_tools"] = available_tools

        super().__init__(details=details, context=context)


class ToolCallError(BaseError):
    """
    工具调用错误

    当 Agent 调用工具失败时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（重新调用）或 FALLBACK（使用备用工具）
    重试：根据工具类型决定
    """

    message_template = "工具调用失败：{tool_name} - {reason}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    error_code = "AGENT_TOOL_CALL_ERROR"

    def __init__(
        self,
        tool_name: str,
        reason: str = "工具执行失败",
        tool_args: Optional[Dict[str, Any]] = None,
        tool_output: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["tool_name"] = tool_name
        details["reason"] = reason
        if tool_args:
            details["tool_args"] = str(tool_args)[:300]
        if tool_output:
            details["tool_output"] = tool_output[:500]

        super().__init__(details=details, context=context)


class SelfReflectionError(BaseError):
    """
    自我反思错误

    当 Agent 无法正确进行自我反思或评估执行结果时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（重新反思）或 ABORT
    重试：少量重试
    """

    message_template = "自我反思失败：{agent_name} - {reason}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0, backoff_factor=2.0)
    error_code = "AGENT_SELF_REFLECTION_ERROR"

    def __init__(
        self,
        agent_name: str,
        reason: str = "无法正确评估执行结果",
        action_history: Optional[List[str]] = None,
        outcome: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["agent_name"] = agent_name
        details["reason"] = reason
        if action_history:
            details["action_history"] = action_history[-5:]  # 只保留最近 5 个动作
        if outcome:
            details["outcome"] = outcome[:300]

        super().__init__(details=details, context=context)


class MemoryError(BaseError):
    """
    记忆错误

    当 Agent 无法读写记忆（包括短期记忆、长期记忆、工作记忆）时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新操作）或 SKIP（忽略记忆）
    重试：少量重试
    """

    message_template = "记忆操作失败：{memory_type} - {operation} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    error_code = "AGENT_MEMORY_ERROR"

    def __init__(
        self,
        memory_type: str,
        operation: str,
        reason: str = "无法访问记忆",
        memory_key: Optional[str] = None,
        memory_size: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["memory_type"] = memory_type
        details["operation"] = operation
        details["reason"] = reason
        if memory_key:
            details["memory_key"] = memory_key
        if memory_size is not None:
            details["memory_size"] = memory_size

        super().__init__(details=details, context=context)


class CollaborationError(BaseError):
    """
    协作错误

    当多个 Agent 之间的协作失败时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新协作）或 MANUAL（人工协调）
    重试：少量重试
    """

    message_template = "协作失败：{agent_1} 与 {agent_2} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=2.0, max_delay=20.0, backoff_factor=2.0)
    error_code = "AGENT_COLLABORATION_ERROR"

    def __init__(
        self,
        agent_1: str,
        agent_2: str,
        reason: str = "无法协调完成任务",
        protocol: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["agent_1"] = agent_1
        details["agent_2"] = agent_2
        details["reason"] = reason
        if protocol:
            details["protocol"] = protocol
        if message:
            details["message"] = message[:500]

        super().__init__(details=details, context=context)


class TimeoutError(BaseError):
    """
    Agent 超时错误

    当 Agent 执行任务超时时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（延长时间后重试）或 ABORT
    重试：不重试（超时通常需要人工介入）
    """

    message_template = "Agent 超时：{agent_name} - 执行时间 {elapsed}s 超过限制 {timeout}s"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.ABORT
    retry_config = None
    error_code = "AGENT_TIMEOUT_ERROR"

    def __init__(
        self,
        agent_name: str,
        elapsed: float,
        timeout: float,
        task_description: Optional[str] = None,
        current_step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["agent_name"] = agent_name
        details["elapsed"] = elapsed
        details["timeout"] = timeout
        if task_description:
            details["task_description"] = task_description[:300]
        if current_step:
            details["current_step"] = current_step

        super().__init__(details=details, context=context)
