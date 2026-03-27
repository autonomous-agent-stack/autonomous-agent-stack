# AI Agent 完整测试策略

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:41
> **测试类型**: 15+

---

## 🧪 测试策略

### 测试金字塔

```
        E2E Tests (10%)
       ────────────────
      Integration Tests (20%)
     ──────────────────────
    Unit Tests (70%)
   ────────────────────────
```

---

## 📦 单元测试

### 1. 基础单元测试

```python
import pytest
from app.agent import Agent
from app.tools import Calculator

class TestAgent:
    def test_agent_creation(self):
        """测试 Agent 创建"""
        agent = Agent(name='Test Agent', model='gpt-3.5-turbo')
        assert agent.name == 'Test Agent'
        assert agent.model == 'gpt-3.5-turbo'
    
    def test_agent_with_tools(self):
        """测试 Agent 工具配置"""
        tools = [Calculator()]
        agent = Agent(name='Test', tools=tools)
        assert len(agent.tools) == 1
        assert agent.tools[0].name == 'calculator'
    
    @pytest.mark.asyncio
    async def test_agent_run(self):
        """测试 Agent 运行"""
        agent = Agent(name='Test', model='gpt-3.5-turbo')
        response = await agent.arun('Hello')
        assert response is not None
        assert len(response) > 0
```

---

### 2. Mock 测试

```python
from unittest.mock import Mock, patch, MagicMock

class TestAgentWithMock:
    @patch('openai.ChatCompletion.create')
    def test_llm_call(self, mock_openai):
        """测试 LLM 调用"""
        # 配置 Mock
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='Test response'))]
        mock_openai.return_value = mock_response
        
        # 运行测试
        agent = Agent(model='gpt-3.5-turbo')
        result = agent.run('Test query')
        
        # 验证
        assert result == 'Test response'
        mock_openai.assert_called_once()
    
    @patch('app.tools.search')
    def test_tool_call(self, mock_search):
        """测试工具调用"""
        mock_search.return_value = 'Search result'
        
        tool = SearchTool()
        result = tool.run('test query')
        
        assert result == 'Search result'
        mock_search.assert_called_once_with('test query')
```

---

### 3. 参数化测试

```python
import pytest

@pytest.mark.parametrize('query,expected', [
    ('What is AI?', 'AI is...'),
    ('How to code?', 'Coding is...'),
    ('Weather today', 'The weather is...'),
])
def test_agent_queries(query, expected):
    """测试不同查询"""
    agent = Agent(model='gpt-3.5-turbo')
    response = agent.run(query)
    assert expected in response or len(response) > 0

@pytest.mark.parametrize('model', ['gpt-3.5-turbo', 'gpt-4', 'claude-3'])
def test_different_models(model):
    """测试不同模型"""
    agent = Agent(model=model)
    assert agent.model == model
```

---

## 🔗 集成测试

### 1. API 集成测试

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAPI:
    def test_health_check(self):
        """测试健康检查"""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
    
    def test_create_agent(self):
        """测试创建 Agent"""
        response = client.post('/agents', json={
            'name': 'Test Agent',
            'model': 'gpt-3.5-turbo'
        })
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'Test Agent'
    
    def test_chat_endpoint(self):
        """测试聊天端点"""
        # 先创建 Agent
        agent_response = client.post('/agents', json={
            'name': 'Test Agent',
            'model': 'gpt-3.5-turbo'
        })
        agent_id = agent_response.json()['id']
        
        # 发送消息
        chat_response = client.post(f'/agents/{agent_id}/chat', json={
            'message': 'Hello'
        })
        assert chat_response.status_code == 200
        assert 'response' in chat_response.json()
```

---

### 2. 数据库集成测试

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models import Agent

@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

class TestDatabase:
    def test_create_agent(self, db_session):
        """测试创建 Agent"""
        agent = Agent(name='Test', model='gpt-3.5-turbo')
        db_session.add(agent)
        db_session.commit()
        
        assert agent.id is not None
        assert agent.name == 'Test'
    
    def test_query_agents(self, db_session):
        """测试查询 Agent"""
        agents = [
            Agent(name='Agent 1', model='gpt-3.5-turbo'),
            Agent(name='Agent 2', model='gpt-4')
        ]
        db_session.add_all(agents)
        db_session.commit()
        
        result = db_session.query(Agent).all()
        assert len(result) == 2
```

---

### 3. 外部服务集成测试

```python
import pytest
from app.integrations import OpenAIClient

@pytest.mark.integration
class TestOpenAIIntegration:
    @pytest.fixture
    def client(self):
        return OpenAIClient()
    
    def test_chat_completion(self, client):
        """测试 OpenAI Chat Completion"""
        response = client.chat_completion(
            model='gpt-3.5-turbo',
            messages=[{'role': 'user', 'content': 'Hello'}]
        )
        
        assert response is not None
        assert 'choices' in response
        assert len(response['choices']) > 0
    
    @pytest.mark.skip(reason="需要真实 API 密钥")
    def test_embedding(self, client):
        """测试 Embedding"""
        embedding = client.create_embedding('test text')
        assert len(embedding) == 1536
```

---

## 🎭 E2E 测试

### Playwright 测试

```typescript
// e2e/chat.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Chat E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('should create agent and send message', async ({ page }) => {
    // 创建 Agent
    await page.click('[data-testid="create-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Test Agent');
    await page.selectOption('[data-testid="agent-model"]', 'gpt-3.5-turbo');
    await page.click('[data-testid="submit"]');

    // 等待创建完成
    await expect(page.locator('[data-testid="agent-card"]')).toBeVisible();

    // 发送消息
    await page.fill('[data-testid="chat-input"]', 'Hello');
    await page.click('[data-testid="send-button"]');

    // 验证响应
    await expect(page.locator('[data-testid="message-response"]')).toBeVisible();
  });

  test('should handle tool calls', async ({ page }) => {
    // 测试工具调用流程
    await page.click('[data-testid="create-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Tool Agent');
    await page.check('[data-testid="tool-search"]');
    await page.click('[data-testid="submit"]');

    // 发送需要工具的查询
    await page.fill('[data-testid="chat-input"]', 'Search for AI news');
    await page.click('[data-testid="send-button"]');

    // 验证工具调用
    await expect(page.locator('[data-testid="tool-call"]')).toBeVisible();
  });
});
```

---

## ⚡ 性能测试

### Locust 测试

```python
# locustfile.py
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户开始时创建 Agent"""
        response = self.client.post('/agents', json={
            'name': 'Load Test Agent',
            'model': 'gpt-3.5-turbo'
        })
        self.agent_id = response.json()['id']
    
    @task(3)
    def chat(self):
        """聊天任务（权重 3）"""
        self.client.post(f'/agents/{self.agent_id}/chat', json={
            'message': 'Hello, this is a load test'
        })
    
    @task(1)
    def health_check(self):
        """健康检查任务（权重 1）"""
        self.client.get('/health')
```

**运行命令**：
```bash
locust -f locustfile.py --host http://localhost:8000
```

---

## 🔒 安全测试

### 1. SQL 注入测试

```python
import pytest
from fastapi.testclient import TestClient

class TestSecurity:
    def test_sql_injection(self):
        """测试 SQL 注入"""
        client = TestClient(app)
        
        # 尝试 SQL 注入
        malicious_input = "'; DROP TABLE agents; --"
        response = client.post('/agents', json={
            'name': malicious_input,
            'model': 'gpt-3.5-turbo'
        })
        
        # 应该被安全处理
        assert response.status_code in [201, 400]
        
        # 验证表格未被删除
        agents = client.get('/agents')
        assert agents.status_code == 200
```

---

### 2. XSS 测试

```python
def test_xss_protection(self):
    """测试 XSS 防护"""
    client = TestClient(app)
    
    # 尝试 XSS 攻击
    xss_payload = '<script>alert("XSS")</script>'
    response = client.post('/agents', json={
        'name': xss_payload,
        'model': 'gpt-3.5-turbo'
    })
    
    # 验证脚本被转义
    if response.status_code == 201:
        agent = client.get(f'/agents/{response.json()["id"]}')
        assert '<script>' not in agent.json()['name']
```

---

## 📊 测试覆盖率

### pytest-cov 配置

```ini
# pytest.ini
[pytest]
addopts = --cov=app --cov-report=term-missing --cov-report=html
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**运行命令**：
```bash
pytest --cov=app --cov-report=html
```

**目标覆盖率**：
- 单元测试：>80%
- 集成测试：>60%
- E2E 测试：>40%

---

## 🔄 CI/CD 测试流程

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: pytest tests/unit --cov=app --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 📝 测试清单

### 单元测试
- [ ] Agent 创建/更新/删除
- [ ] 工具调用
- [ ] 记忆管理
- [ ] 错误处理
- [ ] 边界条件

### 集成测试
- [ ] API 端点
- [ ] 数据库操作
- [ ] 外部服务调用
- [ ] 缓存系统
- [ ] 消息队列

### E2E 测试
- [ ] 完整用户流程
- [ ] 多 Agent 协作
- [ ] 工具调用链
- [ ] 错误恢复

### 性能测试
- [ ] 负载测试
- [ ] 压力测试
- [ ] 并发测试
- [ ] 延迟测试

### 安全测试
- [ ] SQL 注入
- [ ] XSS 攻击
- [ ] CSRF 攻击
- [ ] 认证绕过

---

**生成时间**: 2026-03-27 22:45 GMT+8
