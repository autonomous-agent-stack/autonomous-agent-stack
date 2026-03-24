"""
错误处理库 - AI 系统的完整错误管理解决方案

这个库提供了全面的错误处理机制，包括：
- LLM 相关错误（API 调用、响应解析、内容过滤等）
- RAG 相关错误（文档解析、向量化、检索、存储等）
- Agent 相关错误（任务规划、工具调用、自我反思等）

每个错误类都包含：
- 错误消息模板
- 恢复策略
- 日志记录
- 重试逻辑配置
"""

from .base import BaseError, ErrorSeverity, RecoveryStrategy
from .llm_errors import (
    APIKeyError,
    RateLimitError,
    TokenLimitError,
    ContextWindowError,
    ModelNotAvailableError,
    ResponseParsingError,
    TimeoutError as LLMTimeoutError,
    ContentFilterError,
)
from .rag_errors import (
    DocumentParsingError,
    VectorizationError,
    RetrievalError,
    StorageError,
    QueryError,
    CacheError,
)
from .agent_errors import (
    TaskPlanningError,
    ToolCallError,
    SelfReflectionError,
    MemoryError as AgentMemoryError,
    CollaborationError,
    TimeoutError as AgentTimeoutError,
)

__all__ = [
    # 基础类
    "BaseError",
    "ErrorSeverity",
    "RecoveryStrategy",
    # LLM 错误
    "APIKeyError",
    "RateLimitError",
    "TokenLimitError",
    "ContextWindowError",
    "ModelNotAvailableError",
    "ResponseParsingError",
    "LLMTimeoutError",
    "ContentFilterError",
    # RAG 错误
    "DocumentParsingError",
    "VectorizationError",
    "RetrievalError",
    "StorageError",
    "QueryError",
    "CacheError",
    # Agent 错误
    "TaskPlanningError",
    "ToolCallError",
    "SelfReflectionError",
    "AgentMemoryError",
    "CollaborationError",
    "AgentTimeoutError",
]

__version__ = "1.0.0"
