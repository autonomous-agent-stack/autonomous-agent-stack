# AI 系统错误处理库

一个专为 AI 系统设计的完整错误处理解决方案，涵盖 LLM、RAG 和 Agent 三大场景。

## 特性

✅ **全面的错误类型**：20+ 个专用错误类，覆盖 AI 系统常见问题

✅ **统一接口**：所有错误类共享一致的 API 和行为

✅ **自动重试**：内置可配置的重试机制，支持指数退避

✅ **结构化信息**：错误详情、上下文、恢复策略一应俱全

✅ **自动日志**：根据严重程度自动记录日志

✅ **易于集成**：简单清晰的 API，快速上手

## 快速开始

### 安装

```bash
# 复制到你的项目
cp -r lib/error-handling /path/to/your/project/lib/
```

### 基础使用

```python
from lib.error_handling import APIKeyError, RateLimitError, BaseError

# 创建错误
error = APIKeyError(provider="OpenAI", reason="密钥已过期")

# 抛出和捕获
try:
    raise APIKeyError(provider="OpenAI", reason="密钥无效")
except APIKeyError as e:
    print(f"错误：{e.message}")
    print(f"恢复建议：{e.get_recovery_suggestion()}")

# 带重试的操作
result = BaseError.retry(
    risky_operation,
    error_classes=RateLimitError,
    config=RetryConfig(max_attempts=3)
)
```

## 错误类型

### LLM 错误（8 个）

- `APIKeyError` - API 密钥错误
- `RateLimitError` - 速率限制错误
- `TokenLimitError` - Token 限制错误
- `ContextWindowError` - 上下文窗口错误
- `ModelNotAvailableError` - 模型不可用错误
- `ResponseParsingError` - 响应解析错误
- `TimeoutError` - 请求超时错误
- `ContentFilterError` - 内容过滤错误

### RAG 错误（6 个）

- `DocumentParsingError` - 文档解析错误
- `VectorizationError` - 向量化错误
- `RetrievalError` - 检索错误
- `StorageError` - 存储错误
- `QueryError` - 查询错误
- `CacheError` - 缓存错误

### Agent 错误（6 个）

- `TaskPlanningError` - 任务规划错误
- `ToolCallError` - 工具调用错误
- `SelfReflectionError` - 自我反思错误
- `MemoryError` - 记忆错误
- `CollaborationError` - 协作错误
- `TimeoutError` - Agent 超时错误

## 文档

- **[错误处理指南](ERROR_HANDLING_GUIDE.md)** - 完整的使用文档
- **[基础用法示例](examples/basic_usage.py)** - 基础功能演示
- **[高级用法示例](examples/advanced_usage.py)** - 高级特性演示
- **[实际场景示例](examples/real_world_scenarios.py)** - 真实应用案例

## 运行测试

```bash
# 运行所有测试
python -m pytest lib/error-handling/tests/

# 运行特定测试文件
python -m pytest lib/error-handling/tests/test_base_errors.py

# 运行示例
python lib/error-handling/examples/basic_usage.py
python lib/error-handling/examples/advanced_usage.py
python lib/error-handling/examples/real_world_scenarios.py
```

## 目录结构

```
lib/error-handling/
├── __init__.py              # 库入口
├── base.py                  # 基础错误类
├── llm_errors.py            # LLM 错误类
├── rag_errors.py            # RAG 错误类
├── agent_errors.py          # Agent 错误类
├── retry.py                 # 重试策略工具
├── README.md                # 本文件
├── ERROR_HANDLING_GUIDE.md  # 完整指南
├── examples/                # 示例代码
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   └── real_world_scenarios.py
└── tests/                   # 单元测试
    ├── test_base_errors.py
    ├── test_llm_errors.py
    ├── test_rag_errors.py
    ├── test_agent_errors.py
    └── test_retry.py
```

## 核心概念

### 错误严重程度

所有错误都有严重程度分级，用于确定日志级别和处理优先级：

- **LOW** - 低严重性，可以自动恢复（如内容过滤）
- **MEDIUM** - 中等严重性，需要特殊处理（如速率限制）
- **HIGH** - 高严重性，可能导致功能失败（如检索失败）
- **CRITICAL** - 致命错误，需要立即处理（如 API 密钥错误）

### 恢复策略

每个错误都有推荐的恢复策略：

- **RETRY** - 重试操作（带可配置的重试机制）
- **FALLBACK** - 使用备用方案（如切换模型或解析器）
- **SKIP** - 跳过当前操作（如缓存失败）
- **ABORT** - 终止操作（如超时）
- **MANUAL** - 需要人工介入（如配置错误）

### 重试配置

错误类可以配置重试参数：

```python
from lib.error_handling.base import RetryConfig

config = RetryConfig(
    max_attempts=3,      # 最大重试次数
    initial_delay=1.0,   # 初始延迟（秒）
    max_delay=60.0,      # 最大延迟（秒）
    backoff_factor=2.0, # 退避因子
    jitter=True         # 添加随机抖动
)
```

## 最佳实践

### 1. 使用具体的错误类型

```python
# ✅ 好
raise RateLimitError(provider="OpenAI", message="请求过于频繁")

# ❌ 不好
raise Exception("API 调用失败")
```

### 2. 提供详细的上下文信息

```python
error = RateLimitError(
    provider="OpenAI",
    message="请求过于频繁",
    context={
        "user_id": 123,
        "request_id": "req_abc123",
        "endpoint": "/v1/chat/completions"
    }
)
```

### 3. 使用重试装饰器

```python
from lib.error_handling.retry import retry_on_exception

@retry_on_exception(
    max_attempts=3,
    initial_delay=1.0,
    exceptions=(RateLimitError, TimeoutError)
)
def call_llm_api(prompt: str) -> str:
    # API 调用逻辑
    pass
```

### 4. 优雅降级

```python
def get_llm_response(prompt: str):
    try:
        return call_openai_api(prompt)
    except RateLimitError:
        return call_anthropic_api(prompt)  # 备用 API
    except ModelNotAvailableError as e:
        alternative = e.details.get("alternative_models", ["gpt-3.5-turbo"])[0]
        return call_openai_api(prompt, model=alternative)
```

## 常见问题

### Q: 如何判断一个错误是否应该重试？

A: 检查 `error.retry_config` 是否为 `None`。如果不为 `None`，则可以重试。

### Q: 错误日志会自动记录吗？

A: 是的，所有错误在初始化时都会自动记录日志。日志级别根据严重程度确定。

### Q: 如何自定义错误的重试策略？

A: 可以在错误类中覆盖 `retry_config`，或在捕获错误后使用自定义配置重试。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 版本

**当前版本**: 1.0.0

## 更新日志

### 1.0.0 (2024-01-01)

- ✅ 初始版本发布
- ✅ 20+ 错误类型
- ✅ 完整的重试机制
- ✅ 自动日志记录
- ✅ 详细文档和示例
- ✅ 全面的单元测试
