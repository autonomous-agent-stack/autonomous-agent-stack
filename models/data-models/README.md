# 数据模型库文档

为 AI 系统提供完整的数据模型支持。

## 概述

本模型库包含 **16 个核心数据模型**，分为 4 个类别：

1. **LLM 数据模型** (4个) - 大语言模型相关
2. **RAG 数据模型** (4个) - 检索增强生成相关
3. **Agent 数据模型** (4个) - 智能体相关
4. **System 数据模型** (4个) - 系统基础相关

所有模型均基于 **Pydantic v2** 构建，提供：
- 完整的类型注解
- 自动数据验证
- JSON 序列化支持
- 丰富的验证逻辑

---

## 1. LLM 数据模型

### 1.1 Message - 消息模型

表示 LLM 对话中的单条消息。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 消息唯一标识符 |
| role | Literal["user", "assistant", "system"] | ✅ | 消息角色 |
| content | str | ✅ | 消息内容 |
| timestamp | datetime | ❌ | 消息时间戳（默认当前时间） |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| tool_calls | List[Dict[str, Any]] | ❌ | 工具调用信息 |
| token_count | Optional[int] | ❌ | 消息 token 数量 |

**验证规则：**
- id 不能为空
- content 不能为空，长度不超过 100,000 字符

**使用示例：**

```python
from models.data_models import Message

message = Message(
    id="msg_001",
    role="user",
    content="你好，请帮我写一段代码",
    metadata={"source": "web"},
    token_count=42
)
```

---

### 1.2 Conversation - 对话模型

表示完整的 LLM 对话。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 对话唯一标识符 |
| messages | List[Message] | ❌ | 消息列表 |
| title | Optional[str] | ❌ | 对话标题 |
| model_name | str | ✅ | 使用的模型名称 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| total_tokens | int | ❌ | 总 token 数量 |
| is_active | bool | ❌ | 是否活跃 |

**方法：**
- `add_message(message: Message)` - 添加消息到对话
- `get_last_message()` - 获取最后一条消息

**使用示例：**

```python
from models.data_models import Conversation, Message

conv = Conversation(
    id="conv_001",
    model_name="gpt-4",
    title="代码助手对话"
)

msg = Message(
    id="msg_001",
    role="user",
    content="写一个 Python 函数"
)
conv.add_message(msg)
```

---

### 1.3 Completion - 生成模型

表示 LLM 的生成结果。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 生成唯一标识符 |
| prompt | str | ✅ | 输入提示 |
| completion | str | ✅ | 生成内容 |
| model | str | ✅ | 使用的模型 |
| finish_reason | Literal["stop", "length", "content_filter"] | ❌ | 结束原因 |
| created_at | datetime | ❌ | 创建时间 |
| usage | Dict[str, int] | ❌ | token 使用情况 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| temperature | Optional[float] | ❌ | 温度参数 (0-2) |
| max_tokens | Optional[int] | ❌ | 最大 token 数 |

**验证规则：**
- prompt 不能为空
- temperature 必须在 0-2 之间
- max_tokens 必须大于 0

**使用示例：**

```python
from models.data_models import Completion

comp = Completion(
    id="comp_001",
    prompt="写一个 Python 函数",
    completion="def hello():\n    return 'Hello World'",
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000
)
```

---

### 1.4 Embedding - 向量模型

表示文本的向量表示。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 向量唯一标识符 |
| text | str | ✅ | 原始文本 |
| embedding | List[float] | ✅ | 向量数据 |
| model | str | ✅ | 使用的模型 |
| dimensions | int | ✅ | 向量维度 |
| created_at | datetime | ❌ | 创建时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| token_count | Optional[int] | ❌ | 文本 token 数量 |

**方法：**
- `similarity(other: Embedding) -> float` - 计算余弦相似度

**使用示例：**

```python
from models.data_models import Embedding

emb1 = Embedding(
    id="emb_001",
    text="这是一段文本",
    embedding=[0.1, 0.2, 0.3, 0.4],
    model="text-embedding-ada-002",
    dimensions=4
)

emb2 = Embedding(
    id="emb_002",
    text="这是另一段文本",
    embedding=[0.2, 0.3, 0.4, 0.5],
    model="text-embedding-ada-002",
    dimensions=4
)

similarity = emb1.similarity(emb2)
print(f"相似度: {similarity}")
```

---

## 2. RAG 数据模型

### 2.1 Document - 文档模型

表示 RAG 中的文档。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 文档唯一标识符 |
| title | str | ✅ | 文档标题 |
| content | str | ✅ | 文档内容 |
| source | str | ✅ | 文档来源 |
| doc_type | Literal["text", "pdf", "markdown", "html", "json"] | ❌ | 文档类型 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| tags | List[str] | ❌ | 文档标签 |
| chunk_count | int | ❌ | 分块数量 |
| is_indexed | bool | ❌ | 是否已索引 |

**使用示例：**

```python
from models.data_models import Document

doc = Document(
    id="doc_001",
    title="Python 入门指南",
    content="Python 是一种高级编程语言...",
    source="https://example.com/python",
    doc_type="markdown",
    tags=["编程", "Python", "入门"],
    is_indexed=True
)
```

---

### 2.2 Chunk - 分块模型

表示文档的一个分块。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 分块唯一标识符 |
| document_id | str | ✅ | 所属文档 ID |
| content | str | ✅ | 分块内容 |
| chunk_index | int | ✅ | 分块索引 |
| created_at | datetime | ❌ | 创建时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| embedding_id | Optional[str] | ❌ | 关联的向量 ID |
| token_count | Optional[int] | ❌ | 分块 token 数量 |
| char_count | int | ❌ | 分块字符数 |

**使用示例：**

```python
from models.data_models import Chunk

chunk = Chunk(
    id="chunk_001",
    document_id="doc_001",
    content="这是文档的第一个分块...",
    chunk_index=0,
    token_count=100,
    char_count=500
)
```

---

### 2.3 Query - 查询模型

表示 RAG 查询。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 查询唯一标识符 |
| text | str | ✅ | 查询文本 |
| embedding_id | Optional[str] | ❌ | 查询向量 ID |
| created_at | datetime | ❌ | 创建时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| filters | Dict[str, Any] | ❌ | 查询过滤条件 |
| top_k | int | ❌ | 返回前 k 个结果 (默认5, 最大100) |
| threshold | Optional[float] | ❌ | 相似度阈值 (0-1) |
| query_type | Literal["semantic", "keyword", "hybrid"] | ❌ | 查询类型 |

**验证规则：**
- text 不能为空，长度不超过 2000 字符
- top_k 必须在 1-100 之间
- threshold 必须在 0-1 之间

**使用示例：**

```python
from models.data_models import Query

query = Query(
    id="query_001",
    text="如何使用 Python 进行数据可视化？",
    top_k=5,
    threshold=0.7,
    filters={"doc_type": "markdown"},
    query_type="semantic"
)
```

---

### 2.4 Result - 结果模型

表示 RAG 查询结果。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 结果唯一标识符 |
| query_id | str | ✅ | 关联查询 ID |
| chunk_id | str | ✅ | 分块 ID |
| document_id | str | ✅ | 文档 ID |
| score | float | ✅ | 相似度分数 (0-1) |
| rank | int | ✅ | 排名 |
| created_at | datetime | ❌ | 创建时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| is_selected | bool | ❌ | 是否被选中 |

**验证规则：**
- score 必须在 0-1 之间
- rank 不能为负数

**使用示例：**

```python
from models.data_models import Result

result = Result(
    id="result_001",
    query_id="query_001",
    chunk_id="chunk_001",
    document_id="doc_001",
    score=0.85,
    rank=1,
    is_selected=True
)
```

---

## 3. Agent 数据模型

### 3.1 Task - 任务模型

表示 Agent 的任务。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 任务唯一标识符 |
| title | str | ✅ | 任务标题 |
| description | str | ✅ | 任务描述 |
| status | Literal["pending", "running", "completed", "failed", "cancelled"] | ❌ | 任务状态 |
| priority | Literal["low", "medium", "high", "critical"] | ❌ | 任务优先级 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| started_at | Optional[datetime] | ❌ | 开始时间 |
| completed_at | Optional[datetime] | ❌ | 完成时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| parent_task_id | Optional[str] | ❌ | 父任务 ID |
| subtasks | List[str] | ❌ | 子任务 ID 列表 |
| progress | float | ❌ | 进度 (0.0-1.0) |
| error_message | Optional[str] | ❌ | 错误信息 |

**方法：**
- `update_progress(progress: float)` - 更新任务进度
- `mark_completed()` - 标记任务为完成
- `mark_failed(error: str)` - 标记任务为失败

**使用示例：**

```python
from models.data_models import Task

task = Task(
    id="task_001",
    title="数据预处理",
    description="对原始数据进行清洗和格式化",
    status="running",
    priority="high",
    progress=0.5
)

task.update_progress(0.8)
task.mark_completed()
```

---

### 3.2 Tool - 工具模型

表示 Agent 可用的工具。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 工具唯一标识符 |
| name | str | ✅ | 工具名称 |
| description | str | ✅ | 工具描述 |
| type | Literal["function", "api", "custom"] | ❌ | 工具类型 |
| parameters | List[ToolParameter] | ❌ | 工具参数列表 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| is_enabled | bool | ❌ | 是否启用 |
| usage_count | int | ❌ | 使用次数 |
| execution_time_ms | Optional[int] | ❌ | 平均执行时间（毫秒） |

**ToolParameter 字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | ✅ | 参数名称 |
| type | Literal["string", "number", "boolean", "array", "object"] | ✅ | 参数类型 |
| required | bool | ❌ | 是否必需 |
| description | str | ❌ | 参数描述 |
| default | Optional[Any] | ❌ | 默认值 |
| enum | Optional[List[Any]] | ❌ | 枚举值 |

**方法：**
- `record_usage(execution_time_ms: int)` - 记录工具使用

**使用示例：**

```python
from models.data_models import Tool, ToolParameter

tool = Tool(
    id="tool_001",
    name="web_search",
    description="执行网络搜索并返回结果",
    type="function",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            required=True,
            description="搜索关键词"
        ),
        ToolParameter(
            name="limit",
            type="number",
            required=False,
            default=10
        )
    ]
)

tool.record_usage(500)
print(f"工具已使用 {tool.usage_count} 次")
```

---

### 3.3 Plan - 计划模型

表示 Agent 的执行计划。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 计划唯一标识符 |
| task_id | str | ✅ | 关联任务 ID |
| goal | str | ✅ | 计划目标 |
| steps | List[PlanStep] | ✅ | 计划步骤列表 |
| status | Literal["draft", "approved", "executing", "completed", "failed", "cancelled"] | ❌ | 计划状态 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| started_at | Optional[datetime] | ❌ | 开始执行时间 |
| completed_at | Optional[datetime] | ❌ | 完成时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| reasoning | str | ❌ | 计划推理过程 |
| estimated_duration | Optional[int] | ❌ | 预计总耗时（秒） |

**PlanStep 字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| step_id | str | ✅ | 步骤 ID |
| action | str | ✅ | 动作描述 |
| tool_id | Optional[str] | ❌ | 使用的工具 ID |
| parameters | Dict[str, Any] | ❌ | 参数 |
| depends_on | List[str] | ❌ | 依赖的步骤 ID |
| estimated_duration | Optional[int] | ❌ | 预计耗时（秒） |
| status | Literal["pending", "running", "completed", "failed", "skipped"] | ❌ | 步骤状态 |
| result | Optional[Any] | ❌ | 执行结果 |
| error | Optional[str] | ❌ | 错误信息 |

**方法：**
- `get_progress() -> float` - 计算计划进度
- `get_pending_steps()` - 获取待执行的步骤
- `get_executable_steps()` - 获取可执行的步骤（依赖已满足）

**使用示例：**

```python
from models.data_models import Plan, PlanStep

plan = Plan(
    id="plan_001",
    task_id="task_001",
    goal="完成数据分析和报告生成",
    steps=[
        PlanStep(
            step_id="step_001",
            action="收集数据",
            tool_id="tool_001",
            parameters={"source": "database"},
            estimated_duration=30,
            status="completed"
        ),
        PlanStep(
            step_id="step_002",
            action="分析数据",
            tool_id="tool_002",
            depends_on=["step_001"],
            estimated_duration=60,
            status="pending"
        )
    ],
    reasoning="先收集数据，再进行分析"
)

progress = plan.get_progress()
print(f"计划进度: {progress:.0%}")
executable_steps = plan.get_executable_steps()
print(f"可执行步骤: {[s.step_id for s in executable_steps]}")
```

---

### 3.4 Result - 结果模型

表示 Agent 执行结果。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 结果唯一标识符 |
| task_id | str | ✅ | 关联任务 ID |
| plan_id | Optional[str] | ❌ | 关联计划 ID |
| success | bool | ✅ | 是否成功 |
| data | Optional[Any] | ❌ | 结果数据 |
| output | str | ❌ | 输出文本 |
| error | Optional[str] | ❌ | 错误信息 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| execution_time_ms | Optional[int] | ❌ | 执行时间（毫秒） |
| confidence | Optional[float] | ❌ | 置信度 (0.0-1.0) |
| tokens_used | Optional[int] | ❌ | 使用的 token 数量 |
| tool_calls | List[Dict[str, Any]] | ❌ | 工具调用记录 |

**方法：**
- `to_dict() -> Dict[str, Any]` - 转换为字典
- `get_summary() -> str` - 获取结果摘要

**使用示例：**

```python
from models.data_models import Result

result = Result(
    id="result_001",
    task_id="task_001",
    plan_id="plan_001",
    success=True,
    output="分析完成，预测下季度增长5%",
    execution_time_ms=1500,
    confidence=0.95,
    tokens_used=2500,
    tool_calls=[
        {
            "tool_id": "tool_001",
            "action": "query_database",
            "parameters": {"query": "SELECT * FROM sales"},
            "execution_time_ms": 500
        }
    ]
)

summary = result.get_summary()
print(summary)
```

---

## 4. System 数据模型

### 4.1 User - 用户模型

表示系统用户。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 用户唯一标识符 |
| username | str | ✅ | 用户名 |
| email | EmailStr | ✅ | 邮箱地址 |
| full_name | Optional[str] | ❌ | 全名 |
| role | Literal["admin", "user", "guest"] | ❌ | 用户角色 |
| status | Literal["active", "inactive", "suspended"] | ❌ | 用户状态 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| last_login_at | Optional[datetime] | ❌ | 最后登录时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| preferences | Dict[str, Any] | ❌ | 用户偏好设置 |
| session_count | int | ❌ | 会话数量 |
| total_tokens_used | int | ❌ | 总 token 使用量 |

**方法：**
- `update_last_login()` - 更新最后登录时间
- `add_tokens_used(tokens: int)` - 添加使用的 token

**使用示例：**

```python
from models.data_models import User

user = User(
    id="user_001",
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    role="user",
    preferences={
        "language": "zh-CN",
        "theme": "dark"
    }
)

user.update_last_login()
user.add_tokens_used(1000)
print(f"用户已使用 {user.total_tokens_used} tokens")
```

---

### 4.2 Session - 会话模型

表示用户会话。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 会话唯一标识符 |
| user_id | str | ✅ | 关联用户 ID |
| session_type | Literal["chat", "api", "bot"] | ❌ | 会话类型 |
| status | Literal["active", "inactive", "expired"] | ❌ | 会话状态 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| expired_at | Optional[datetime] | ❌ | 过期时间 |
| last_activity_at | datetime | ❌ | 最后活动时间 |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| message_count | int | ❌ | 消息数量 |
| token_count | int | ❌ | token 数量 |
| client_info | Optional[Dict[str, Any]] | ❌ | 客户端信息 |

**方法：**
- `is_expired() -> bool` - 检查会话是否过期
- `update_activity()` - 更新活动时间
- `add_message(token_count: int)` - 添加消息记录
- `close()` - 关闭会话

**使用示例：**

```python
from datetime import datetime, timedelta
from models.data_models import Session

session = Session(
    id="session_001",
    user_id="user_001",
    session_type="chat",
    expired_at=datetime.now() + timedelta(hours=1)
)

if not session.is_expired():
    session.add_message(150)
    print(f"会话活跃，已发送 {session.message_count} 条消息")
```

---

### 4.3 Config - 配置模型

表示系统配置。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 配置唯一标识符 |
| key | str | ✅ | 配置键 |
| value | Any | ✅ | 配置值 |
| description | Optional[str] | ❌ | 配置描述 |
| config_type | str | ❌ | 配置类型 |
| is_sensitive | bool | ❌ | 是否敏感信息 |
| is_readonly | bool | ❌ | 是否只读 |
| created_at | datetime | ❌ | 创建时间 |
| updated_at | datetime | ❌ | 更新时间 |
| updated_by | Optional[str] | ❌ | 更新者 ID |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| validation_rules | Optional[Dict[str, Any]] | ❌ | 验证规则 |

**方法：**
- `validate_value() -> bool` - 验证配置值是否有效
- `update_value(new_value: Any, updated_by: str)` - 更新配置值

**使用示例：**

```python
from models.data_models import Config

config = Config(
    id="config_001",
    key="llm.model_name",
    value="gpt-4",
    description="默认 LLM 模型",
    config_type="string",
    validation_rules={
        "required": True,
        "enum": ["gpt-3.5-turbo", "gpt-4", "claude-3"]
    }
)

if config.validate_value():
    print("配置值有效")
    config.update_value("gpt-3.5-turbo", "user_001")
```

---

### 4.4 Log - 日志模型

表示系统日志。

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | ✅ | 日志唯一标识符 |
| level | Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | ✅ | 日志级别 |
| message | str | ✅ | 日志消息 |
| source | str | ✅ | 日志来源 |
| timestamp | datetime | ❌ | 时间戳 |
| user_id | Optional[str] | ❌ | 关联用户 ID |
| session_id | Optional[str] | ❌ | 关联会话 ID |
| metadata | Dict[str, Any] | ❌ | 额外元数据 |
| tags | List[str] | ❌ | 日志标签 |
| exception | Optional[Dict[str, Any]] | ❌ | 异常信息 |
| duration_ms | Optional[int] | ❌ | 持续时间（毫秒） |
| request_id | Optional[str] | ❌ | 请求 ID |

**方法：**
- `add_tag(tag: str)` - 添加标签
- `has_tag(tag: str) -> bool` - 检查是否包含标签
- `to_dict() -> Dict[str, Any]` - 转换为字典
- `is_error() -> bool` - 检查是否为错误日志

**使用示例：**

```python
from models.data_models import Log

log = Log(
    id="log_001",
    level="INFO",
    message="任务执行成功",
    source="agent.task",
    user_id="user_001",
    session_id="session_001",
    duration_ms=1500,
    request_id="req_001"
)

log.add_tag("task")
log.add_tag("success")

if not log.is_error():
    print(f"[{log.level}] {log.message}")
```

---

## 安装依赖

```bash
pip install pydantic[email]
```

## 快速开始

```python
from models.data_models import (
    # LLM
    Message, Conversation, Completion, Embedding,
    # RAG
    Document, Chunk, Query as RAGQuery, Result as RAGResult,
    # Agent
    Task, Tool, ToolParameter, Plan, PlanStep, Result as AgentResult,
    # System
    User, Session, Config, Log
)

# 创建消息
message = Message(
    id="msg_001",
    role="user",
    content="你好！"
)

# 创建对话
conversation = Conversation(
    id="conv_001",
    model_name="gpt-4"
)
conversation.add_message(message)

# 创建任务
task = Task(
    id="task_001",
    title="数据分析",
    description="完成数据分析任务"
)
task.mark_completed()
```

## 最佳实践

1. **使用类型注解** - 所有模型都支持完整的类型检查
2. **验证数据** - Pydantic 会自动验证数据有效性
3. **利用方法** - 使用模型内置的方法简化常见操作
4. **元数据** - 使用 `metadata` 字段存储额外信息
5. **错误处理** - 捕获 `ValidationError` 处理验证失败

## 许可证

MIT License
