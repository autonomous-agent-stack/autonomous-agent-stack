# 错误处理指南

本文档提供了完整的错误处理库使用指南，帮助你在 AI 系统中正确使用错误处理机制。

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [错误类型](#错误类型)
4. [基础用法](#基础用法)
5. [高级特性](#高级特性)
6. [最佳实践](#最佳实践)
7. [示例代码](#示例代码)
8. [常见问题](#常见问题)

## 概述

本错误处理库专为 AI 系统设计，提供了全面的错误管理解决方案，涵盖三大类错误：

- **LLM 错误**：与大语言模型相关的错误（API 调用、响应解析、内容过滤等）
- **RAG 错误**：检索增强生成系统的错误（文档解析、向量化、检索、存储等）
- **Agent 错误**：AI Agent 的错误（任务规划、工具调用、自我反思、协作等）

### 核心特性

- ✅ 统一的错误接口
- ✅ 结构化错误信息
- ✅ 自动日志记录
- ✅ 内置重试机制
- ✅ 恢复策略配置
- ✅ 错误严重程度分级
- ✅ 详细的上下文信息

## 快速开始

### 安装

```bash
# 将错误处理库添加到你的项目
cp -r lib/error-handling /path/to/your/project/lib/
```

### 基础使用

```python
from lib.error_handling import APIKeyError, RateLimitError, BaseError

# 创建错误
error = APIKeyError(
    provider="OpenAI",
    reason="密钥已过期",
    context={"user_id": 123}
)

# 抛出和捕获
try:
    raise APIKeyError(provider="OpenAI", reason="密钥无效")
except APIKeyError as e:
    print(f"错误：{e.message}")
    print(f"恢复建议：{e.get_recovery_suggestion()}")

# 带重试的操作
def risky_operation():
    raise RateLimitError(provider="OpenAI", message="请求过于频繁")

result = BaseError.retry(
    risky_operation,
    error_classes=RateLimitError,
    config=RetryConfig(max_attempts=3)
)
```

## 错误类型

### LLM 错误（8 个）

| 错误类型 | 严重程度 | 恢复策略 | 重试 | 说明 |
|---------|---------|---------|-----|------|
| `APIKeyError` | CRITICAL | MANUAL | 否 | API 密钥无效、缺失或过期 |
| `RateLimitError` | MEDIUM | RETRY | 是 | API 速率限制 |
| `TokenLimitError` | MEDIUM | FALLBACK | 否 | Token 数量超过限制 |
| `ContextWindowError` | HIGH | FALLBACK | 否 | 上下文窗口超限 |
| `ModelNotAvailableError` | HIGH | FALLBACK | 否 | 模型不可用 |
| `ResponseParsingError` | MEDIUM | RETRY | 是 | 响应解析失败 |
| `TimeoutError` | MEDIUM | RETRY | 是 | 请求超时 |
| `ContentFilterError` | LOW | RETRY | 是 | 内容被过滤 |

### RAG 错误（6 个）

| 错误类型 | 严重程度 | 恢复策略 | 重试 | 说明 |
|---------|---------|---------|-----|------|
| `DocumentParsingError` | MEDIUM | FALLBACK | 是 | 文档解析失败 |
| `VectorizationError` | HIGH | RETRY | 是 | 向量化失败 |
| `RetrievalError` | HIGH | RETRY | 是 | 检索失败 |
| `StorageError` | HIGH | RETRY | 是 | 存储失败 |
| `QueryError` | HIGH | RETRY | 是 | 查询失败 |
| `CacheError` | LOW | SKIP | 否 | 缓存错误 |

### Agent 错误（6 个）

| 错误类型 | 严重程度 | 恢复策略 | 重试 | 说明 |
|---------|---------|---------|-----|------|
| `TaskPlanningError` | HIGH | RETRY | 是 | 任务规划失败 |
| `ToolCallError` | MEDIUM | RETRY | 是 | 工具调用失败 |
| `SelfReflectionError` | MEDIUM | RETRY | 是 | 自我反思失败 |
| `MemoryError` | HIGH | RETRY | 是 | 记忆操作失败 |
| `CollaborationError` | HIGH | RETRY | 是 | 协作失败 |
| `TimeoutError` | MEDIUM | ABORT | 否 | Agent 超时 |

## 基础用法

### 创建错误

```python
from lib.error_handling import APIKeyError

# 使用默认消息模板
error = APIKeyError(provider="OpenAI", reason="密钥已过期")

# 使用自定义消息
error = APIKeyError(message="自定义错误消息")

# 添加详细信息
error = APIKeyError(
    provider="OpenAI",
    reason="密钥已过期",
    details={"attempt_count": 3},
    context={"user_id": 123, "endpoint": "/v1/chat"}
)
```

### 转换为字典

```python
error = APIKeyError(provider="OpenAI", reason="密钥已过期")
error_dict = error.to_dict()

# 输出：
# {
#     "error_code": "LLM_API_KEY_ERROR",
#     "error_type": "APIKeyError",
#     "message": "API 密钥错误：OpenAI - 密钥已过期",
#     "severity": "critical",
#     "recovery_strategy": "manual",
#     "recovery_suggestion": "需要人工介入",
#     "details": {...},
#     "context": {...},
#     "cause": None,
#     "timestamp": 1234567890.123
# }
```

### 异常链

```python
try:
    # 底层错误
    raise ConnectionError("无法连接到 API 服务器")
except ConnectionError as e:
    # 用自定义错误包装
    raise RateLimitError(
        provider="OpenAI",
        reason="连接超时",
        cause=e
    )
```

## 高级特性

### 使用重试装饰器

```python
from lib.error_handling.retry import retry_on_exception

@retry_on_exception(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0,
    backoff_factor=2.0,
    exceptions=(RateLimitError, TimeoutError)
)
def call_llm_api(prompt: str) -> str:
    # API 调用逻辑
    pass
```

### 使用 Retryable 上下文管理器

```python
from lib.error_handling.retry import Retryable

with Retryable(max_attempts=3, initial_delay=1.0) as retry:
    for attempt in retry.attempts():
        try:
            result = risky_operation()
            retry.success(result)
            break
        except Exception as e:
            retry.record_failure(e)

if retry.succeeded:
    print(f"成功：{retry.result}")
else:
    print(f"失败：{retry.last_failure}")
```

### 自定义重试策略

```python
from lib.error_handling.base import RetryConfig

# 自定义重试配置
config = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=300.0,
    backoff_factor=2.0,
    jitter=True
)

# 使用静态方法重试
result = BaseError.retry(
    func,
    error_classes=RateLimitError,
    config=config
)
```

### 错误监控

```python
from lib.error_handling import BaseError

error_stats = {}

def monitored_operation(func):
    """带监控的装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseError as e:
            # 记录错误统计
            error_type = e.error_code
            error_stats[error_type] = error_stats.get(error_type, 0) + 1
            raise
    return wrapper

@monitored_operation
def api_call():
    # API 调用逻辑
    pass
```

## 最佳实践

### 1. 选择合适的错误类型

使用最具体的错误类型，而不是通用异常：

```python
# ✅ 好
raise RateLimitError(provider="OpenAI", message="请求过于频繁")

# ❌ 不好
raise Exception("API 调用失败")
```

### 2. 提供详细的上下文信息

总是提供足够的上下文信息，帮助调试和问题排查：

```python
error = RateLimitError(
    provider="OpenAI",
    message="请求过于频繁",
    context={
        "user_id": 123,
        "request_id": "req_abc123",
        "endpoint": "/v1/chat/completions",
        "model": "gpt-4"
    }
)
```

### 3. 使用合适的重试策略

根据错误类型选择不同的重试策略：

```python
# 速率限制：指数退避
@retry_on_exception(max_attempts=3, backoff_factor=2.0)
def rate_limited_call():
    pass

# 临时故障：快速重试
@retry_on_exception(max_attempts=2, backoff_factor=1.0)
def temporary_failure():
    pass

# 配置错误：不重试
def config_error():
    raise APIKeyError(provider="OpenAI", reason="密钥无效")
```

### 4. 记录错误日志

错误类会自动记录日志，但你也可以手动记录：

```python
import logging

logger = logging.getLogger(__name__)

try:
    risky_operation()
except RateLimitError as e:
    logger.error(
        f"API 速率限制：{e.message}",
        extra={"error_code": e.error_code, "context": e.context}
    )
```

### 5. 优雅降级

当错误发生时，提供备用方案：

```python
def get_llm_response(prompt: str):
    try:
        # 尝试主 API
        return call_openai_api(prompt)
    except RateLimitError:
        # 使用备用 API
        return call_anthropic_api(prompt)
    except ModelNotAvailableError as e:
        # 使用备用模型
        alternative = e.details.get("alternative_models", ["gpt-3.5-turbo"])[0]
        return call_openai_api(prompt, model=alternative)
```

### 6. 超时处理

为长时间运行的操作设置超时：

```python
import time
from lib.error_handling.retry import Retryable

def execute_with_timeout(func, timeout=30.0):
    start_time = time.time()

    with Retryable(max_attempts=1) as retry:
        for attempt in retry.attempts():
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    endpoint="/v1/chat",
                    timeout=timeout
                )
            result = func()
            retry.success(result)

    return retry.result
```

## 示例代码

### 完整的 LLM 客户端示例

```python
from lib.error_handling import (
    APIKeyError,
    RateLimitError,
    TokenLimitError,
    ResponseParsingError,
    TimeoutError as LLMTimeoutError
)
from lib.error_handling.retry import retry_on_exception

class LLMClient:
    def __init__(self, api_key: str, provider: str = "OpenAI"):
        self.api_key = api_key
        self.provider = provider

    @retry_on_exception(
        max_attempts=3,
        initial_delay=1.0,
        exceptions=(RateLimitError, LLMTimeoutError)
    )
    def chat_completion(self, messages: list, model: str = "gpt-4"):
        # 验证 API 密钥
        if not self.api_key:
            raise APIKeyError(
                provider=self.provider,
                reason="API 密钥未配置"
            )

        # 检查 token 限制
        total_tokens = sum(len(m.get("content", "")) for m in messages)
        if total_tokens > 8000:
            raise TokenLimitError(
                model=model,
                input_tokens=total_tokens,
                max_tokens=8000
            )

        # 调用 API
        try:
            response = self._call_api(messages, model)
            return self._parse_response(response)
        except ValueError as e:
            raise ResponseParsingError(
                parser="JSONParser",
                reason=str(e),
                raw_response=response
            )

    def _call_api(self, messages: list, model: str):
        # 实际的 API 调用
        pass

    def _parse_response(self, response: str):
        # 响应解析
        pass
```

### 完整的 RAG 系统示例

```python
from lib.error_handling import (
    DocumentParsingError,
    VectorizationError,
    RetrievalError,
    StorageError,
    CacheError
)

class RAGSystem:
    def __init__(self, embedding_model: str, vector_store: str):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def ingest_document(self, file_path: str, content: str):
        # 步骤 1：解析文档
        try:
            self._parse_document(file_path, content)
        except Exception as e:
            raise DocumentParsingError(
                file_type=file_path.split(".")[-1],
                file_name=file_path.split("/")[-1],
                reason=str(e),
                file_path=file_path,
                cause=e
            )

        # 步骤 2：向量化
        try:
            embeddings = self._vectorize(content)
        except Exception as e:
            raise VectorizationError(
                embedding_model=self.embedding_model,
                reason=str(e),
                text_length=len(content),
                cause=e
            )

        # 步骤 3：存储
        try:
            self._store(embeddings)
        except Exception as e:
            raise StorageError(
                storage_type=self.vector_store,
                reason=str(e),
                cause=e
            )

    def retrieve(self, query: str, top_k: int = 5):
        # 尝试从缓存获取
        try:
            cached = self._get_from_cache(query)
            if cached:
                return cached
        except Exception as e:
            raise CacheError(
                cache_type="Redis",
                reason=str(e),
                cache_key=f"query:{query}"
            )

        # 从向量数据库检索
        try:
            return self._search_vector_store(query, top_k)
        except Exception as e:
            raise RetrievalError(
                vector_store=self.vector_store,
                reason=str(e),
                query=query,
                top_k=top_k,
                cause=e
            )
```

## 常见问题

### Q1: 如何判断一个错误是否应该重试？

**A:** 查看 `retry_config` 属性。如果 `retry_config` 不为 `None`，则可以重试：

```python
if error.retry_config:
    max_attempts = error.retry_config.max_attempts
    print(f"可以重试，最多 {max_attempts} 次")
```

### Q2: 如何自定义错误的重试策略？

**A:** 可以在错误类中覆盖 `retry_config`，或在捕获错误后使用自定义配置重试：

```python
# 方法 1：在错误类中覆盖
class CustomRateLimitError(RateLimitError):
    retry_config = RetryConfig(max_attempts=5, initial_delay=5.0)

# 方法 2：使用自定义配置重试
result = BaseError.retry(
    func,
    error_classes=RateLimitError,
    config=RetryConfig(max_attempts=5, initial_delay=5.0)
)
```

### Q3: 错误日志会自动记录吗？

**A:** 是的，所有错误都会在初始化时自动记录日志。日志级别根据错误严重程度确定：

- LOW: DEBUG
- MEDIUM: WARNING
- HIGH: ERROR
- CRITICAL: CRITICAL

### Q4: 如何禁用自动日志记录？

**A:** 可以覆盖 `_log_error` 方法：

```python
class SilentError(BaseError):
    def _log_error(self):
        pass  # 不记录日志
```

### Q5: 如何在生产环境中使用？

**A:** 建议的配置：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 生产环境使用较长的重试延迟
production_config = RetryConfig(
    max_attempts=3,
    initial_delay=5.0,
    max_delay=300.0,
    backoff_factor=2.0,
    jitter=True
)

# 集成到监控系统（如 Sentry）
import sentry_sdk

sentry_sdk.init(dsn="your-sentry-dsn")

try:
    risky_operation()
except BaseError as e:
    sentry_sdk.capture_exception(e)
```

## 总结

本错误处理库提供了完整的错误管理解决方案，帮助你在 AI 系统中：

1. **快速定位问题**：结构化错误信息和详细上下文
2. **自动恢复**：内置重试机制和恢复策略
3. **监控和分析**：自动日志记录和错误统计
4. **优雅降级**：支持备用方案和错误处理

通过正确使用这个库，你可以构建更加健壮和可靠的 AI 系统。

---

**版本**: 1.0.0
**最后更新**: 2024-01-01
