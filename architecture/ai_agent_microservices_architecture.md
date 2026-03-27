# AI Agent 微服务架构设计

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:41
> **架构模式**: 12 种

---

## 🏗️ 微服务架构

### 1. API Gateway

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
@app.post("/api/v1/chat")
async def chat(request: Request):
    """聊天网关"""
    data = await request.json()
    
    # 路由到 Agent 服务
    response = await agent_service.chat(data["message"])
    
    return {"response": response}

@app.get("/api/v1/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}
```

---

### 2. Agent 服务

```python
# agent_service.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentService:
    """Agent 服务"""
    
    model: str = "gpt-4"
    temperature: float = 0.7
    
    async def chat(self, message: str) -> str:
        """聊天"""
        # 调用 LLM
        response = await self._call_llm(message)
        
        # 记录日志
        await self._log_interaction(message, response)
        
        return response
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        # 实现 LLM 调用
        pass
    
    async def _log_interaction(self, message: str, response: str):
        """记录交互"""
        # 实现日志记录
        pass
```

---

### 3. Memory 服务

```python
# memory_service.py
from typing import List, Optional

class MemoryService:
    """记忆服务"""
    
    async def add(self, user_id: str, content: str) -> str:
        """添加记忆"""
        # 存储到数据库
        memory_id = await self._save(user_id, content)
        
        return memory_id
    
    async def search(self, user_id: str, query: str) -> List[dict]:
        """搜索记忆"""
        # 向量搜索
        results = await self._vector_search(user_id, query)
        
        return results
    
    async def clear(self, user_id: str) -> int:
        """清空记忆"""
        count = await self._delete_all(user_id)
        
        return count
```

---

### 4. Tool 服务

```python
# tool_service.py
from typing import Dict, Any

class ToolService:
    """工具服务"""
    
    def __init__(self):
        self.tools = {}
    
    def register(self, name: str, func: callable):
        """注册工具"""
        self.tools[name] = func
    
    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        """执行工具"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        
        return await self.tools[name](**params)
    
    def list_tools(self) -> List[str]:
        """列出工具"""
        return list(self.tools.keys())
```

---

### 5. LLM 服务

```python
# llm_service.py
from openai import AsyncOpenAI

class LLMService:
    """LLM 服务"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def call(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """调用 LLM"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
```

---

### 6. Cache 服务

```python
# cache_service.py
import redis.asyncio as redis

class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """设置缓存"""
        await self.client.setex(key, ttl, value)
    
    async def delete(self, key: str):
        """删除缓存"""
        await self.client.delete(key)
```

---

### 7. Queue 服务

```python
# queue_service.py
from typing import Any
import asyncio

class QueueService:
    """队列服务"""
    
    def __init__(self):
        self.queues = {}
    
    async def enqueue(self, queue_name: str, task: Any):
        """入队"""
        if queue_name not in self.queues:
            self.queues[queue_name] = asyncio.Queue()
        
        await self.queues[queue_name].put(task)
    
    async def dequeue(self, queue_name: str) -> Any:
        """出队"""
        if queue_name not in self.queues:
            return None
        
        return await self.queues[queue_name].get()
```

---

### 8. Logger 服务

```python
# logger_service.py
import logging
from datetime import datetime

class LoggerService:
    """日志服务"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 添加处理器
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self.logger.error(message, extra=kwargs)
```

---

## 📊 服务通信

### 1. HTTP REST

```python
# REST API
@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent"""
    agent = await agent_service.get(agent_id)
    return agent

@app.post("/api/v1/agents")
async def create_agent(agent: AgentCreate):
    """创建 Agent"""
    new_agent = await agent_service.create(agent)
    return new_agent
```

---

### 2. gRPC

```python
# gRPC 服务
import grpc
from concurrent import futures

class AgentServicer(agent_pb2_grpc.AgentServicer):
    """Agent gRPC 服务"""
    
    async def Chat(self, request, context):
        """聊天"""
        response = await agent_service.chat(request.message)
        
        return agent_pb2.ChatResponse(response=response)

# 启动 gRPC 服务器
server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
agent_pb2_grpc.add_AgentServicer_to_server(AgentServicer(), server)
server.add_insecure_port('[::]:50051')
await server.start()
```

---

### 3. 消息队列

```python
# 消息队列
import aio_pika

async def publish_message(queue_name: str, message: str):
    """发布消息"""
    connection = await aio_pika.connect_robust("amqp://localhost")
    
    async with connection:
        channel = await connection.channel()
        
        await channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=queue_name
        )

async def consume_messages(queue_name: str, callback):
    """消费消息"""
    connection = await aio_pika.connect_robust("amqp://localhost")
    
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await callback(message.body.decode())
```

---

## 🔧 服务发现

```python
# consul_client.py
import consul

class ServiceDiscovery:
    """服务发现"""
    
    def __init__(self, consul_host: str = "localhost"):
        self.client = consul.Consul(host=consul_host)
    
    async def register(self, name: str, port: int):
        """注册服务"""
        self.client.agent.service.register(
            name=name,
            port=port,
            check=consul.Check.http(f"http://localhost:{port}/health", interval="10s")
        )
    
    async def discover(self, name: str) -> List[str]:
        """发现服务"""
        services = self.client.catalog.service(name)[1]
        
        return [f"http://{s['ServiceAddress']}:{s['ServicePort']}" for s in services]
```

---

## 📦 容器化

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api-gateway:
    build: ./api-gateway
    ports:
      - "8000:8000"
    depends_on:
      - agent-service
      - redis
  
  agent-service:
    build: ./agent-service
    ports:
      - "8001:8001"
    depends_on:
      - llm-service
      - memory-service
  
  llm-service:
    build: ./llm-service
    ports:
      - "8002:8002"
  
  memory-service:
    build: ./memory-service
    ports:
      - "8003:8003"
    depends_on:
      - postgres
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:14-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: password
```

---

## 📊 服务监控

```python
# health_check.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """健康检查"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "llm": await check_llm()
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks
    }

async def check_database() -> bool:
    """检查数据库"""
    try:
        # 测试连接
        await db.execute("SELECT 1")
        return True
    except:
        return False
```

---

## 🎯 微服务最佳实践

1. ✅ **单一职责** - 每个服务只做一件事
2. ✅ **独立部署** - 服务可以独立部署
3. ✅ **去中心化** - 避免单点故障
4. ✅ **容错设计** - 服务失败不影响整体
5. ✅ **可观测性** - 日志、指标、追踪
6. ✅ **自动化** - CI/CD 自动化部署
7. ✅ **文档化** - API 文档清晰
8. ✅ **版本管理** - API 版本控制

---

**生成时间**: 2026-03-27 16:43 GMT+8
