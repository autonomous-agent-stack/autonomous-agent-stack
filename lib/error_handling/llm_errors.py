"""
LLM（大语言模型）相关错误

涵盖 API 调用、响应处理、内容过滤等场景的错误类型。
"""

from typing import Any, Dict, Optional

from .base import BaseError, ErrorSeverity, RecoveryStrategy, RetryConfig


class APIKeyError(BaseError):
    """
    API 密钥错误

    当 API 密钥无效、缺失或过期时抛出。

    严重程度：CRITICAL
    恢复策略：MANUAL（需要更新 API 密钥）
    重试：不重试
    """

    message_template = "API 密钥错误：{provider} - {reason}"
    severity = ErrorSeverity.CRITICAL
    recovery_strategy = RecoveryStrategy.MANUAL
    retry_config = None
    error_code = "LLM_API_KEY_ERROR"

    def __init__(
        self,
        provider: str,
        reason: str = "密钥无效或已过期",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["provider"] = provider
        details["reason"] = reason

        super().__init__(details=details, context=context)


class RateLimitError(BaseError):
    """
    API 速率限制错误

    当请求超过 API 提供商的速率限制时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（等待后重试）
    重试：指数退避
    """

    message_template = "API 速率限制：{provider} - {message}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(
        max_attempts=5, initial_delay=5.0, max_delay=300.0, backoff_factor=2.0
    )
    error_code = "LLM_RATE_LIMIT_ERROR"

    def __init__(
        self,
        provider: str,
        message: str = "请求过于频繁，请稍后重试",
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["provider"] = provider
        details["message"] = message
        if retry_after is not None:
            details["retry_after"] = retry_after
            # 如果 API 返回了具体的重试时间，调整重试配置
            self.retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=max(1.0, retry_after),
                max_delay=max(10.0, retry_after * 2),
                backoff_factor=1.5,
            )

        super().__init__(details=details, context=context)


class TokenLimitError(BaseError):
    """
    Token 限制错误

    当输入或输出的 token 数量超过限制时抛出。

    严重程度：MEDIUM
    恢复策略：FALLBACK（截断或拆分）
    重试：不重试
    """

    message_template = "Token 限制：模型 {model} - {input_tokens} 输入 tokens 超过限制 {max_tokens}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.FALLBACK
    retry_config = None
    error_code = "LLM_TOKEN_LIMIT_ERROR"

    def __init__(
        self,
        model: str,
        input_tokens: int,
        max_tokens: int,
        output_tokens: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["model"] = model
        details["input_tokens"] = input_tokens
        details["max_tokens"] = max_tokens
        if output_tokens is not None:
            details["output_tokens"] = output_tokens

        super().__init__(details=details, context=context)


class ContextWindowError(BaseError):
    """
    上下文窗口错误

    当对话历史或文档内容超过模型的上下文窗口时抛出。

    严重程度：HIGH
    恢复策略：FALLBACK（压缩或分批）
    重试：不重试
    """

    message_template = "上下文窗口超限：模型 {model} - 当前 {current_tokens} tokens 超过窗口大小 {window_size} tokens"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.FALLBACK
    retry_config = None
    error_code = "LLM_CONTEXT_WINDOW_ERROR"

    def __init__(
        self,
        model: str,
        current_tokens: int,
        window_size: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["model"] = model
        details["current_tokens"] = current_tokens
        details["window_size"] = window_size

        super().__init__(details=details, context=context)


class ModelNotAvailableError(BaseError):
    """
    模型不可用错误

    当请求的模型不存在、已下线或服务不可用时抛出。

    严重程度：HIGH
    恢复策略：FALLBACK（使用备用模型）
    重试：不重试
    """

    message_template = "模型不可用：{model} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.FALLBACK
    retry_config = None
    error_code = "LLM_MODEL_NOT_AVAILABLE_ERROR"

    def __init__(
        self,
        model: str,
        reason: str = "模型不存在或服务不可用",
        alternative_models: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["model"] = model
        details["reason"] = reason
        if alternative_models:
            details["alternative_models"] = alternative_models

        super().__init__(details=details, context=context)


class ResponseParsingError(BaseError):
    """
    响应解析错误

    当无法解析 LLM 返回的响应时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（重新请求或使用备用解析器）
    重试：少量重试
    """

    message_template = "响应解析失败：{parser} - {reason}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0, backoff_factor=2.0)
    error_code = "LLM_RESPONSE_PARSING_ERROR"

    def __init__(
        self,
        parser: str,
        reason: str = "响应格式不符合预期",
        raw_response: Optional[str] = None,
        expected_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["parser"] = parser
        details["reason"] = reason
        if raw_response is not None:
            details["raw_response"] = raw_response[:500]  # 只保留前 500 字符
        if expected_format is not None:
            details["expected_format"] = expected_format

        super().__init__(details=details, context=context)


class TimeoutError(BaseError):
    """
    请求超时错误

    当 LLM API 请求超时时抛出。

    严重程度：MEDIUM
    恢复策略：RETRY（延长超时后重试）
    重试：少量重试，递增延迟
    """

    message_template = "请求超时：{endpoint} - 超时时间 {timeout}s"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(
        max_attempts=3, initial_delay=2.0, max_delay=30.0, backoff_factor=2.0
    )
    error_code = "LLM_TIMEOUT_ERROR"

    def __init__(
        self,
        endpoint: str,
        timeout: float,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["endpoint"] = endpoint
        details["timeout"] = timeout

        super().__init__(details=details, context=context)


class ContentFilterError(BaseError):
    """
    内容过滤错误

    当 LLM 返回的内容被安全过滤器拦截时抛出。

    严重程度：LOW
    恢复策略：RETRY（修改提示词后重试）或 SKIP
    重试：少量重试
    """

    message_template = "内容被过滤：{filter_type} - {reason}"
    severity = ErrorSeverity.LOW
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0, backoff_factor=2.0)
    error_code = "LLM_CONTENT_FILTER_ERROR"

    def __init__(
        self,
        filter_type: str,
        reason: str = "内容违反安全策略",
        blocked_content: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["filter_type"] = filter_type
        details["reason"] = reason
        if blocked_content is not None:
            details["blocked_content"] = blocked_content[:200]  # 只保留前 200 字符

        super().__init__(details=details, context=context)
