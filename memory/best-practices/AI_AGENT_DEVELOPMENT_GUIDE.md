# AI Agent 开发最佳实践指南

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **适用**: Python 开发者
> **难度**: 中级

---

## 🎯 核心原则

### 1. Agent 设计原则

**KISS（Keep It Simple, Stupid）**:
- ✅ 从简单 Agent 开始
- ✅ 逐步增加复杂度
- ❌ 避免过度设计

**单一职责原则**:
- ✅ 每个 Agent 只做一件事
- ✅ 职责清晰
- ❌ 避免"超级 Agent"

**可测试性**:
- ✅ 每个 Agent 都可独立测试
- ✅ 使用 Mock 工具
- ❌ 避免不可预测的外部依赖

---

## 🏗️ 架构设计

### 基础架构

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class Tool(BaseModel):
    """工具基类"""
    name: str
    description: str
    parameters: Dict[str, Any]

class AgentState(BaseModel):
    """Agent 状态"""
    messages: List[Dict[str, str]] = []
    tools: List[Tool] = []
    memory: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, model: str, tools: List[Tool]):
        self.model = model
        self.tools = tools
        self.state = AgentState(tools=tools)
    
    @abstractmethod
    def think(self, input: str) -> str:
        """思考过程"""
        pass
    
    @abstractmethod
    def act(self, thought: str) -> str:
        """行动过程"""
        pass
    
    def run(self, input: str) -> str:
        """执行 Agent"""
        thought = self.think(input)
        action = self.act(thought)
        return action
```

---

## 🛠️ 工具设计

### 工具定义规范

```python
from typing import Literal
from pydantic import BaseModel, Field

class SearchTool(Tool):
    """搜索工具"""
    name: Literal["search_web"] = "search_web"
    description: str = "搜索互联网信息"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量",
                "default": 10
            }
        },
        "required": ["query"]
    }

class CalculatorTool(Tool):
    """计算器工具"""
    name: Literal["calculator"] = "calculator"
    description: str = "执行数学计算"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2 + 3 * 4'"
            }
        },
        "required": ["expression"]
    }
```

### 工具实现最佳实践

```python
import subprocess
import json

def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    """执行工具"""
    
    if tool_name == "search_web":
        query = parameters["query"]
        limit = parameters.get("limit", 10)
        # 实现搜索逻辑
        results = search_google(query, limit)
        return json.dumps(results, ensure_ascii=False)
    
    elif tool_name == "calculator":
        expression = parameters["expression"]
        # 安全计算
        try:
            result = eval(expression, {"__builtins__": None}, {})
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    else:
        return f"Unknown tool: {tool_name}"
```

---

## 💾 记忆系统

### 短期记忆

```python
from collections import deque

class ShortTermMemory:
    """短期记忆（滑动窗口）"""
    
    def __init__(self, max_size: int = 10):
        self.memory = deque(maxlen=max_size)
    
    def add(self, message: Dict[str, str]):
        """添加记忆"""
        self.memory.append(message)
    
    def get_all(self) -> List[Dict[str, str]]:
        """获取所有记忆"""
        return list(self.memory)
    
    def clear(self):
        """清空记忆"""
        self.memory.clear()
```

### 长期记忆

```python
import chromadb
from chromadb.config import Settings

class LongTermMemory:
    """长期记忆（向量数据库）"""
    
    def __init__(self, persist_dir: str = "./memory_db"):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir
        ))
        self.collection = self.client.get_or_create_collection("agent_memory")
    
    def add(self, text: str, metadata: Dict[str, Any] = None):
        """添加记忆"""
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[str(hash(text))]
        )
    
    def search(self, query: str, n_results: int = 5) -> List[str]:
        """搜索记忆"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results["documents"][0]
```

---

## 🔍 错误处理

### 重试机制

```python
import time
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))  # 指数退避
        return wrapper
    return decorator

@retry(max_attempts=3, delay=1.0)
def call_llm(prompt: str) -> str:
    """调用 LLM（带重试）"""
    # 实现 LLM 调用
    pass
```

### 降级策略

```python
class FallbackStrategy:
    """降级策略"""
    
    def __init__(self, primary_model: str, fallback_model: str):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
    
    def call(self, prompt: str) -> str:
        """调用（带降级）"""
        try:
            # 尝试主模型
            return self._call_model(self.primary_model, prompt)
        except Exception as e:
            print(f"Primary model failed: {e}")
            # 降级到备用模型
            return self._call_model(self.fallback_model, prompt)
    
    def _call_model(self, model: str, prompt: str) -> str:
        """调用模型"""
        # 实现模型调用
        pass
```

---

## 📊 监控和日志

### 结构化日志

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
    
    def log(self, level: str, message: str, **kwargs):
        """记录日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def log_tool_call(self, tool_name: str, parameters: Dict, result: str):
        """记录工具调用"""
        self.log(
            "INFO",
            f"Tool call: {tool_name}",
            tool_name=tool_name,
            parameters=parameters,
            result=result[:200]  # 截断结果
        )
    
    def log_agent_run(self, input: str, output: str, duration: float):
        """记录 Agent 运行"""
        self.log(
            "INFO",
            "Agent run completed",
            input=input[:100],
            output=output[:100],
            duration_seconds=duration
        )
```

---

## 🧪 测试策略

### 单元测试

```python
import pytest
from unittest.mock import Mock, patch

class TestSearchAgent:
    """搜索 Agent 测试"""
    
    @pytest.fixture
    def agent(self):
        """创建 Agent 实例"""
        return SearchAgent(model="gpt-4", tools=[SearchTool()])
    
    def test_search_success(self, agent):
        """测试搜索成功"""
        with patch('agent.search_google') as mock_search:
            mock_search.return_value = [{"title": "Test", "url": "http://test.com"}]
            
            result = agent.run("搜索 Python 教程")
            
            assert "Python" in result
            assert "http://test.com" in result
    
    def test_search_empty_query(self, agent):
        """测试空查询"""
        with pytest.raises(ValueError):
            agent.run("")
    
    def test_search_no_results(self, agent):
        """测试无结果"""
        with patch('agent.search_google') as mock_search:
            mock_search.return_value = []
            
            result = agent.run("搜索不存在的关键词")
            
            assert "没有找到" in result
```

---

## 🔒 安全最佳实践

### 1. 输入验证

```python
from pydantic import BaseModel, validator, constr

class UserInput(BaseModel):
    """用户输入验证"""
    query: constr(min_length=1, max_length=1000)  # 长度限制
    
    @validator('query')
    def validate_query(cls, v):
        """验证查询内容"""
        # 检查危险字符
        dangerous_chars = ['<', '>', '{', '}', ';']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Invalid character: {char}")
        return v
```

### 2. 敏感信息保护

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """配置管理"""
    API_KEY: str = os.getenv("API_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.API_KEY:
            raise ValueError("API_KEY not set")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
```

### 3. 工具权限控制

```python
from enum import Enum

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"

class PermissionManager:
    """权限管理"""
    
    def __init__(self):
        self.permissions = {}
    
    def grant(self, tool_name: str, permission: Permission):
        """授予权限"""
        if tool_name not in self.permissions:
            self.permissions[tool_name] = set()
        self.permissions[tool_name].add(permission)
    
    def check(self, tool_name: str, permission: Permission) -> bool:
        """检查权限"""
        return permission in self.permissions.get(tool_name, set())
```

---

## 🚀 性能优化

### 1. 异步调用

```python
import asyncio
from typing import List

async def call_tools_parallel(tools: List[Tool], inputs: List[Dict]) -> List[str]:
    """并行调用工具"""
    tasks = [
        asyncio.to_thread(execute_tool, tool.name, input)
        for tool, input in zip(tools, inputs)
    ]
    return await asyncio.gather(*tasks)
```

### 2. 缓存策略

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_llm_call(prompt_hash: str, prompt: str) -> str:
    """缓存的 LLM 调用"""
    # 实现 LLM 调用
    pass

def call_llm_with_cache(prompt: str) -> str:
    """带缓存的 LLM 调用"""
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    return cached_llm_call(prompt_hash, prompt)
```

---

## 📚 推荐资源

### 书籍

1. **"Designing Data-Intensive Applications"** - Martin Kleppmann
2. **"Building Machine Learning Powered Applications"** - Emmanuel Ameisen
3. **"Clean Code"** - Robert C. Martin

### 课程

1. **DeepLearning.AI** - AI Agent 课程
2. **FastAPI 官方文档** - Web 框架
3. **Pydantic 文档** - 数据验证

### 开源项目

1. **LangChain** - Agent 框架
2. **AutoGen** - 多 Agent 框架
3. **CrewAI** - 角色 Agent 框架

---

## 🎯 Checklist

### 开发前

- [ ] 明确 Agent 的单一职责
- [ ] 设计清晰的工具接口
- [ ] 准备测试数据
- [ ] 配置日志和监控

### 开发中

- [ ] 使用类型注解（Type Hints）
- [ ] 编写单元测试
- [ ] 实现错误处理
- [ ] 添加文档字符串

### 开发后

- [ ] 性能测试
- [ ] 安全审计
- [ ] 用户测试
- [ ] 部署上线

---

**生成时间**: 2026-03-27 12:40 GMT+8
**版本**: v1.0
**下次更新**: 2026-04-27
