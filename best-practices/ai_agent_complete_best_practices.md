# AI Agent 完整最佳实践集

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:56
> **最佳实践**: 100+

---

## 🎯 最佳实践分类

### 1. 架构设计

#### 1.1 微服务架构
```python
# ✅ 好的设计：松耦合
class AgentService:
    def __init__(self, llm_client, tool_registry, memory_store):
        self.llm = llm_client
        self.tools = tool_registry
        self.memory = memory_store

# ❌ 坏的设计：紧耦合
class AgentService:
    def __init__(self):
        self.llm = OpenAI()  # 硬编码依赖
        self.tools = [SearchTool()]  # 硬编码工具
        self.memory = ChromaDB()  # 硬编码存储
```

**最佳实践**：
- [ ] 使用依赖注入
- [ ] 接口抽象
- [ ] 配置外部化
- [ ] 服务隔离

---

#### 1.2 事件驱动架构
```python
# ✅ 好的设计：事件驱动
from events import EventEmitter

class AgentEventEmitter(EventEmitter):
    def on_task_start(self, task):
        self.emit('task_started', task)
    
    def on_task_complete(self, result):
        self.emit('task_completed', result)

# 订阅事件
agent.on('task_started', lambda task: log.info(f'Started: {task}'))
agent.on('task_completed', lambda result: log.info(f'Completed: {result}'))
```

---

### 2. 代码质量

#### 2.1 类型提示
```python
# ✅ 好的实践：完整类型提示
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class AgentConfig:
    name: str
    model: str
    tools: List[str]
    temperature: float = 0.7
    max_tokens: int = 2000

def create_agent(config: AgentConfig) -> Agent:
    """创建 Agent
    
    Args:
        config: Agent 配置对象
    
    Returns:
        Agent: 创建的 Agent 实例
    
    Raises:
        ValueError: 如果配置无效
    """
    if not config.name:
        raise ValueError('Agent name is required')
    return Agent(**config.__dict__)
```

---

#### 2.2 错误处理
```python
# ✅ 好的实践：结构化错误处理
class AgentError(Exception):
    """Agent 基础异常"""
    pass

class LLMError(AgentError):
    """LLM 调用异常"""
    pass

class ToolError(AgentError):
    """工具调用异常"""
    pass

def safe_llm_call(prompt: str) -> str:
    """安全的 LLM 调用"""
    try:
        response = llm.invoke(prompt)
        return response.content
    except TimeoutError:
        raise LLMError('LLM call timed out')
    except APIError as e:
        raise LLMError(f'LLM API error: {e}')
    except Exception as e:
        raise LLMError(f'Unexpected error: {e}')
```

---

#### 2.3 日志记录
```python
# ✅ 好的实践：结构化日志
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(self, level: str, message: str, **kwargs):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level),
            json.dumps(log_data)
        )

# 使用
logger = StructuredLogger('agent')
logger.log('INFO', 'Task started', task_id='123', user='user1')
```

---

### 3. 性能优化

#### 3.1 缓存策略
```python
# ✅ 好的实践：多层缓存
from functools import lru_cache
import redis
import hashlib

class MultiLayerCache:
    def __init__(self):
        self.local_cache = {}
        self.redis = redis.Redis()
    
    def get(self, key: str):
        # L1: 本地缓存
        if key in self.local_cache:
            return self.local_cache[key]
        
        # L2: Redis 缓存
        value = self.redis.get(key)
        if value:
            self.local_cache[key] = value
            return value
        
        return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        self.local_cache[key] = value
        self.redis.setex(key, ttl, value)

# 使用 LRU 缓存
@lru_cache(maxsize=1000)
def cached_llm_call(prompt_hash: str):
    return llm.invoke(prompt_hash)
```

---

#### 3.2 异步处理
```python
# ✅ 好的实践：异步并发
import asyncio
from typing import List

async def batch_process(items: List[str], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(item):
        async with semaphore:
            return await process_item(item)
    
    return await asyncio.gather(*[process_with_limit(item) for item in items])

# 使用
results = await batch_process(items, max_concurrent=20)
```

---

### 4. 安全实践

#### 4.1 输入验证
```python
# ✅ 好的实践：Pydantic 验证
from pydantic import BaseModel, validator, constr
import html

class UserInput(BaseModel):
    query: constr(min_length=1, max_length=1000)
    
    @validator('query')
    def sanitize(cls, v):
        # XSS 防护
        v = html.escape(v)
        # 移除危险字符
        v = v.replace('<script>', '').replace('</script>', '')
        return v

# 使用
@app.post('/chat')
async def chat(input: UserInput):
    safe_query = input.query
    return {'response': agent.run(safe_query)}
```

---

#### 4.2 密钥管理
```python
# ✅ 好的实践：密钥管理服务
import os
from aws_secretsmanager import get_secret

class SecretManager:
    def __init__(self):
        self.cache = {}
    
    def get_secret(self, key: str) -> str:
        # 优先从环境变量获取
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # 从缓存获取
        if key in self.cache:
            return self.cache[key]
        
        # 从密钥管理服务获取
        secret = get_secret(key)
        self.cache[key] = secret
        return secret

# 使用
secret_manager = SecretManager()
api_key = secret_manager.get_secret('OPENAI_API_KEY')
```

---

### 5. 测试实践

#### 5.1 测试金字塔
```python
# 单元测试（70%）
def test_agent_creation():
    agent = Agent(name='Test', model='gpt-3.5-turbo')
    assert agent.name == 'Test'

# 集成测试（20%）
def test_api_integration():
    client = TestClient(app)
    response = client.post('/agents', json={'name': 'Test'})
    assert response.status_code == 201

# E2E 测试（10%）
def test_full_workflow():
    # 完整用户流程测试
    pass
```

---

#### 5.2 Mock 最佳实践
```python
# ✅ 好的实践：使用 pytest fixtures
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_llm():
    mock = Mock()
    mock.invoke.return_value = 'Test response'
    return mock

def test_with_mock(mock_llm):
    agent = Agent(llm=mock_llm)
    result = agent.run('test')
    assert result == 'Test response'
    mock_llm.invoke.assert_called_once()
```

---

### 6. 监控实践

#### 6.1 指标收集
```python
# ✅ 好的实践：Prometheus 指标
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
request_count = Counter('agent_requests_total', 'Total requests')
latency = Histogram('agent_latency_seconds', 'Request latency')
active_agents = Gauge('agent_active_count', 'Active agents')

# 使用指标
@latency.time()
def process_request(query):
    request_count.inc()
    active_agents.inc()
    try:
        return agent.run(query)
    finally:
        active_agents.dec()
```

---

#### 6.2 告警规则
```yaml
# prometheus/alerts.yml
groups:
  - name: agent_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: Error rate is {{ $value }} per second
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, agent_latency_seconds) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High latency detected
          description: P95 latency is {{ $value }} seconds
```

---

### 7. 部署实践

#### 7.1 容器化
```dockerfile
# ✅ 好的实践：多阶段构建
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --chown=appuser:appuser . .
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### 7.2 健康检查
```python
# ✅ 好的实践：健康检查端点
from fastapi import FastAPI

app = FastAPI()

@app.get('/health')
async def health():
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'components': {
            'llm': check_llm_health(),
            'database': check_database_health(),
            'cache': check_cache_health()
        }
    }

@app.get('/ready')
async def ready():
    # 检查服务是否准备好接收流量
    if not is_ready():
        raise HTTPException(status_code=503, detail='Service not ready')
    return {'status': 'ready'}
```

---

## 📋 最佳实践清单

### 架构设计
- [ ] 使用微服务架构
- [ ] 依赖注入
- [ ] 配置外部化
- [ ] 事件驱动

### 代码质量
- [ ] 类型提示
- [ ] 文档字符串
- [ ] 错误处理
- [ ] 结构化日志

### 性能优化
- [ ] 多层缓存
- [ ] 异步处理
- [ ] 批量处理
- [ ] 连接池

### 安全实践
- [ ] 输入验证
- [ ] 密钥管理
- [ ] 访问控制
- [ ] 数据加密

### 测试实践
- [ ] 单元测试 >80%
- [ ] 集成测试 >60%
- [ ] E2E 测试 >40%
- [ ] Mock 测试

### 监控实践
- [ ] 指标收集
- [ ] 日志聚合
- [ ] 告警规则
- [ ] 分布式追踪

### 部署实践
- [ ] 容器化
- [ ] CI/CD
- [ ] 健康检查
- [ ] 自动扩缩容

---

**生成时间**: 2026-03-27 23:00 GMT+8
