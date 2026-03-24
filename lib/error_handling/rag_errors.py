"""
RAG（检索增强生成）相关错误

涵盖文档解析、向量化、检索、存储等场景的错误类型。
"""

from typing import Any, Dict, List, Optional

from .base import BaseError, ErrorSeverity, RecoveryStrategy, RetryConfig


class DocumentParsingError(BaseError):
    """
    文档解析错误

    当无法解析文档内容时抛出。

    严重程度：MEDIUM
    恢复策略：FALLBACK（使用备用解析器）
    重试：少量重试
    """

    message_template = "文档解析失败：{file_type} - {file_name} - {reason}"
    severity = ErrorSeverity.MEDIUM
    recovery_strategy = RecoveryStrategy.FALLBACK
    retry_config = RetryConfig(max_attempts=2, initial_delay=1.0, max_delay=5.0, backoff_factor=2.0)
    error_code = "RAG_DOCUMENT_PARSING_ERROR"

    def __init__(
        self,
        file_type: str,
        file_name: str,
        reason: str = "无法识别文档格式或内容损坏",
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["file_type"] = file_type
        details["file_name"] = file_name
        details["reason"] = reason
        if file_path:
            details["file_path"] = file_path

        super().__init__(details=details, context=context)


class VectorizationError(BaseError):
    """
    向量化错误

    当将文本转换为向量表示失败时抛出。

    严重程度：HIGH
    恢复策略：RETRY 或 FALLBACK（使用备用嵌入模型）
    重试：指数退避
    """

    message_template = "向量化失败：{embedding_model} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(
        max_attempts=3, initial_delay=2.0, max_delay=30.0, backoff_factor=2.0
    )
    error_code = "RAG_VECTORIZATION_ERROR"

    def __init__(
        self,
        embedding_model: str,
        reason: str = "无法生成向量表示",
        text_length: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["embedding_model"] = embedding_model
        details["reason"] = reason
        if text_length is not None:
            details["text_length"] = text_length

        super().__init__(details=details, context=context)


class RetrievalError(BaseError):
    """
    检索错误

    当从向量数据库检索文档失败时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新检索）
    重试：少量重试
    """

    message_template = "文档检索失败：{vector_store} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    error_code = "RAG_RETRIEVAL_ERROR"

    def __init__(
        self,
        vector_store: str,
        reason: str = "无法检索相关文档",
        query: Optional[str] = None,
        top_k: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["vector_store"] = vector_store
        details["reason"] = reason
        if query:
            details["query"] = query[:200]  # 只保留前 200 字符
        if top_k:
            details["top_k"] = top_k

        super().__init__(details=details, context=context)


class StorageError(BaseError):
    """
    存储错误

    当无法将文档或向量存储到数据库时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新存储）或 ABORT
    重试：少量重试
    """

    message_template = "存储失败：{storage_type} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    error_code = "RAG_STORAGE_ERROR"

    def __init__(
        self,
        storage_type: str,
        reason: str = "无法存储数据",
        document_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["storage_type"] = storage_type
        details["reason"] = reason
        if document_count is not None:
            details["document_count"] = document_count

        super().__init__(details=details, context=context)


class QueryError(BaseError):
    """
    查询错误

    当查询向量数据库失败时抛出。

    严重程度：HIGH
    恢复策略：RETRY（重新查询）
    重试：少量重试
    """

    message_template = "查询失败：{vector_store} - {reason}"
    severity = ErrorSeverity.HIGH
    recovery_strategy = RecoveryStrategy.RETRY
    retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    error_code = "RAG_QUERY_ERROR"

    def __init__(
        self,
        vector_store: str,
        reason: str = "无法执行查询",
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["vector_store"] = vector_store
        details["reason"] = reason
        if query:
            details["query"] = query[:200]

        super().__init__(details=details, context=context)


class CacheError(BaseError):
    """
    缓存错误

    当无法读写缓存时抛出。

    严重程度：LOW
    恢复策略：SKIP（跳过缓存，直接查询）
    重试：不重试
    """

    message_template = "缓存错误：{cache_type} - {reason}"
    severity = ErrorSeverity.LOW
    recovery_strategy = RecoveryStrategy.SKIP
    retry_config = None
    error_code = "RAG_CACHE_ERROR"

    def __init__(
        self,
        cache_type: str,
        reason: str = "无法读写缓存",
        cache_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["cache_type"] = cache_type
        details["reason"] = reason
        if cache_key:
            details["cache_key"] = cache_key

        super().__init__(details=details, context=context)
