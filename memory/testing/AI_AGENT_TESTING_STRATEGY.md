# AI Agent 完整测试策略

> **版本**: v1.0
> **更新时间**: 2026-03-27 13:50
> **测试类型**: 20+

---

## 🧪 测试金字塔

```
         /\
        /  \
       / E2E\         10%
      /______\
     /        \
    / Integration\    20%
   /______________\
  /                \
 /   Unit Tests     \  70%
/____________________\
```

---

## 🎯 单元测试

### 1. 工具测试

```python
import pytest
from unittest.mock import Mock, patch

class TestSearchTool:
    """搜索工具测试"""
    
    @pytest.fixture
    def tool(self):
        return SearchTool(api_key="test_key")
    
    def test_search_success(self, tool):
        """测试成功搜索"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "results": [
                    {"title": "Test", "url": "http://test.com"}
                ]
            }
            
            result = tool.search("AI", limit=5)
            
            assert len(result) == 1
            assert result[0]["title"] == "Test"
    
    def test_search_invalid_query(self, tool):
        """测试无效查询"""
        with pytest.raises(ValueError):
            tool.search("", limit=5)
    
    def test_search_network_error(self, tool):
        """测试网络错误"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = NetworkError("Connection failed")
            
            with pytest.raises(NetworkError):
                tool.search("AI", limit=5)
```

---

### 2. Agent 测试

```python
class TestAgent:
    """Agent 测试"""
    
    @pytest.fixture
    def agent(self):
        llm = MockLLM(return_value="test response")
        return Agent(llm=llm)
    
    def test_run_success(self, agent):
        """测试成功运行"""
        result = agent.run("test task")
        
        assert result == "test response"
    
    def test_run_with_tools(self, agent):
        """测试带工具运行"""
        tool = Mock()
        tool.execute.return_value = "tool result"
        
        agent.add_tool(tool)
        result = agent.run("use tool")
        
        assert result is not None
    
    def test_run_max_iterations(self, agent):
        """测试最大轮数"""
        agent.max_iterations = 3
        
        # 模拟无限循环
        with patch.object(agent, '_execute', return_value="continue"):
            result = agent.run("test")
            
            assert "超过最大轮数" in result
```

---

### 3. 记忆系统测试

```python
class TestMemory:
    """记忆系统测试"""
    
    @pytest.fixture
    def memory(self):
        return MemorySystem()
    
    def test_add_short_term(self, memory):
        """测试短期记忆"""
        memory.add("test message")
        
        assert len(memory.short_term) == 1
        assert "test message" in memory.short_term[0]
    
    def test_add_long_term(self, memory):
        """测试长期记忆"""
        memory._is_important = lambda x: True
        
        memory.add("important message")
        
        assert memory.long_term.count() == 1
    
    def test_retrieve(self, memory):
        """测试检索"""
        memory.add("AI is great")
        memory.add("Python is awesome")
        
        results = memory.retrieve("AI")
        
        assert len(results) > 0
        assert "AI" in results[0]
```

---

## 🔗 集成测试

### 1. API 集成测试

```python
from fastapi.testclient import TestClient

class TestAgentAPI:
    """API 集成测试"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_run_endpoint(self, client):
        """测试运行端点"""
        response = client.post(
            "/agent/run",
            json={"task": "test task"}
        )
        
        assert response.status_code == 200
        assert "result" in response.json()
    
    def test_health_endpoint(self, client):
        """测试健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

---

### 2. 数据库集成测试

```python
class TestDatabase:
    """数据库集成测试"""
    
    @pytest.fixture
    def db(self):
        # 使用测试数据库
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        
        yield engine
        
        # 清理
        Base.metadata.drop_all(engine)
    
    def test_save_memory(self, db):
        """测试保存记忆"""
        memory = Memory(
            content="test",
            embedding=[0.1, 0.2, 0.3]
        )
        
        with db.connect() as conn:
            conn.execute(insert(Memory).values(memory))
            conn.commit()
        
        with db.connect() as conn:
            result = conn.execute(select(Memory)).fetchone()
            
            assert result.content == "test"
```

---

### 3. 外部服务集成测试

```python
class TestExternalServices:
    """外部服务集成测试"""
    
    @pytest.mark.integration
    def test_openai_integration(self):
        """测试 OpenAI 集成"""
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert response.choices[0].message.content is not None
```

---

## 🎭 E2E 测试

### 1. 完整流程测试

```python
class TestE2E:
    """E2E 测试"""
    
    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 创建 Agent
        agent = Agent(
            llm=RealLLM(),
            tools=[SearchTool(), CalculatorTool()]
        )
        
        # 2. 执行任务
        result = agent.run("搜索 AI 并计算 2+2")
        
        # 3. 验证结果
        assert result is not None
        assert len(result) > 0
        
        # 4. 检查记忆
        memories = agent.memory.retrieve("AI")
        assert len(memories) > 0
```

---

### 2. 用户场景测试

```python
class TestUserScenarios:
    """用户场景测试"""
    
    def test_customer_service_scenario(self):
        """测试客服场景"""
        agent = CustomerServiceAgent()
        
        # 用户提问
        response = agent.handle("我的订单在哪里？")
        
        # 验证
        assert "订单" in response or "order" in response.lower()
    
    def test_code_review_scenario(self):
        """测试代码审查场景"""
        agent = CodeReviewAgent()
        
        code = """
def add(a, b):
    return a + b
"""
        
        report = agent.review(code)
        
        assert report["score"] >= 0
        assert len(report["suggestions"]) >= 0
```

---

## 📊 性能测试

### 1. 负载测试

```python
import asyncio
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    """负载测试用户"""
    
    wait_time = between(1, 3)
    
    @task
    def run_agent(self):
        """运行 Agent"""
        self.client.post(
            "/agent/run",
            json={"task": "test task"}
        )

# 运行: locust -f locustfile.py
```

---

### 2. 压力测试

```python
class TestPerformance:
    """性能测试"""
    
    def test_response_time(self):
        """测试响应时间"""
        agent = Agent()
        
        start = time.time()
        result = agent.run("test task")
        elapsed = time.time() - start
        
        assert elapsed < 5  # < 5s
    
    def test_throughput(self):
        """测试吞吐量"""
        agent = Agent()
        
        tasks = ["task" + str(i) for i in range(100)]
        
        start = time.time()
        results = [agent.run(task) for task in tasks]
        elapsed = time.time() - start
        
        throughput = len(tasks) / elapsed
        
        assert throughput > 10  # > 10 RPS
```

---

## 🧪 测试工具

### 1. Mock LLM

```python
class MockLLM:
    """Mock LLM"""
    
    def __init__(self, return_value="test"):
        self.return_value = return_value
        self.calls = []
    
    def call(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.return_value
    
    def stream(self, prompt: str):
        """流式输出"""
        for word in self.return_value.split():
            yield word + " "
```

---

### 2. 测试数据生成器

```python
class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_tasks(n: int) -> List[str]:
        """生成测试任务"""
        return [f"task_{i}" for i in range(n)]
    
    @staticmethod
    def generate_documents(n: int) -> List[dict]:
        """生成测试文档"""
        return [
            {
                "id": i,
                "content": f"Document {i}",
                "metadata": {"source": "test"}
            }
            for i in range(n)
        ]
```

---

## 📋 测试清单

### 单元测试

- [ ] 工具测试
- [ ] Agent 测试
- [ ] 记忆系统测试
- [ ] 工具选择测试

### 集成测试

- [ ] API 测试
- [ ] 数据库测试
- [ ] 外部服务测试

### E2E 测试

- [ ] 完整流程测试
- [ ] 用户场景测试
- [ ] 边界情况测试

### 性能测试

- [ ] 负载测试
- [ ] 压力测试
- [ ] 稳定性测试

---

**生成时间**: 2026-03-27 13:55 GMT+8
