"""
数据模型库 - 为 AI 系统提供完整的数据模型

本模块包含 16 个核心数据模型，分为 4 个类别：

1. LLM 数据模型:
   - Message: 消息模型
   - Conversation: 对话模型
   - Completion: 生成模型
   - Embedding: 向量模型

2. RAG 数据模型:
   - Document: 文档模型
   - Chunk: 分块模型
   - Query: 查询模型
   - Result: 结果模型

3. Agent 数据模型:
   - Task: 任务模型
   - Tool: 工具模型
   - Plan: 计划模型
   - Result: 结果模型

4. System 数据模型:
   - User: 用户模型
   - Session: 会话模型
   - Config: 配置模型
   - Log: 日志模型
"""

# LLM 模型
from .llm import (
    Message,
    Conversation,
    Completion,
    Embedding,
)

# RAG 模型
from .rag import (
    Document,
    Chunk,
    Query as RAGQuery,
    Result as RAGResult,
)

# Agent 模型
from .agent import (
    Task,
    Tool,
    ToolParameter,
    Plan,
    PlanStep,
    Result as AgentResult,
)

# System 模型
from .system import (
    User,
    Session,
    Config,
    Log,
)

__all__ = [
    # LLM
    "Message",
    "Conversation",
    "Completion",
    "Embedding",
    # RAG
    "Document",
    "Chunk",
    "RAGQuery",
    "RAGResult",
    # Agent
    "Task",
    "Tool",
    "ToolParameter",
    "Plan",
    "PlanStep",
    "AgentResult",
    # System
    "User",
    "Session",
    "Config",
    "Log",
]
