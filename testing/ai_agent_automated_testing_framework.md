# AI Agent 自动化测试框架

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:38
> **测试类型**: 15+

---

## 🧪 测试框架架构

### 1. 单元测试

```python
import pytest
from unittest.mock import Mock, patch

class TestAgent:
    """Agent 单元测试"""
    
    @pytest.fixture
    def agent(self):
        """创建测试 Agent"""
        return Agent(model="gpt-3.5-turbo")
    
    def test_run_success(self, agent):
        """测试成功运行"""
        result = agent.run("test task")
        
        assert result is not None
        assert len(result) > 0
    
    def test_run_with_mock(self, agent):
        """测试 Mock LLM"""
        with patch.object(agent, '_call_llm') as mock_llm:
            mock_llm.return_value = "mocked response"
            
            result = agent.run("test task")
            
            assert result == "mocked response"
            mock_llm.assert_called_once()
    
    @pytest.mark.parametrize("task,expected", [
        ("calculate 2+2", "4"),
        ("search AI", "results"),
        ("translate hello", "hola"),
    ])
    def test_different_tasks(self, agent, task, expected):
        """测试不同任务"""
        result = agent.run(task)
        assert expected in result.lower()
```

---

### 2. 集成测试

```python
class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from main import app
        
        return TestClient(app)
    
    async def test_api_endpoint(self, client):
        """测试 API 端点"""
        response = client.post("/api/v1/chat", json={
            "message": "Hello"
        })
        
        assert response.status_code == 200
        assert "response" in response.json()
    
    async def test_database_integration(self, db_session):
        """测试数据库集成"""
        # 创建记录
        agent = await Agent.create(name="test")
        
        # 查询记录
        found = await Agent.get(name="test")
        
        assert found.id == agent.id
```

---

### 3. E2E 测试

```python
from playwright.sync_api import sync_playwright

class TestE2E:
    """端到端测试"""
    
    def test_chat_flow(self):
        """测试聊天流程"""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # 打开页面
            page.goto("http://localhost:3000")
            
            # 输入消息
            page.fill("#input", "Hello")
            page.click("#send")
            
            # 等待响应
            response = page.wait_for_selector("#response", timeout=5000)
            
            assert response is not None
            
            browser.close()
```

---

### 4. 性能测试

```python
import asyncio
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    """性能测试用户"""
    
    wait_time = between(1, 3)
    
    @task
    def chat(self):
        """聊天任务"""
        self.client.post("/api/v1/chat", json={
            "message": "Test message"
        })

# 运行性能测试
# locust -f performance_test.py --host=http://localhost:8000
```

---

### 5. 压力测试

```python
class StressTest:
    """压力测试"""
    
    async def test_concurrent_requests(self):
        """测试并发请求"""
        tasks = []
        
        for i in range(100):
            task = agent.run(f"Task {i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(r is not None for r in results)
```

---

### 6. 负载测试

```python
class LoadTest:
    """负载测试"""
    
    async def test_sustained_load(self):
        """测试持续负载"""
        for i in range(1000):
            result = agent.run(f"Task {i}")
            
            # 验证响应时间
            start = time.time()
            result = agent.run("test")
            duration = time.time() - start
            
            assert duration < 5.0  # 5 秒内完成
```

---

### 7. 安全测试

```python
class SecurityTest:
    """安全测试"""
    
    def test_sql_injection(self, client):
        """测试 SQL 注入"""
        malicious = "'; DROP TABLE users; --"
        
        response = client.post("/api/v1/chat", json={
            "message": malicious
        })
        
        # 应该被拒绝或转义
        assert response.status_code in [200, 400]
    
    def test_xss(self, client):
        """测试 XSS"""
        malicious = "<script>alert('xss')</script>"
        
        response = client.post("/api/v1/chat", json={
            "message": malicious
        })
        
        # 不应该执行脚本
        assert "<script>" not in response.json()["response"]
    
    def test_rate_limiting(self, client):
        """测试速率限制"""
        for i in range(100):
            response = client.get("/api/v1/metrics")
        
        # 应该被限制
        assert response.status_code == 429
```

---

### 8. 回归测试

```python
class RegressionTest:
    """回归测试"""
    
    @pytest.mark.regression
    def test_previous_fixes(self):
        """测试之前修复的 Bug"""
        # Bug #123: 空输入导致崩溃
        result = agent.run("")
        assert result is not None  # 应该返回默认响应
        
        # Bug #456: 特殊字符处理
        result = agent.run("!@#$%^&*()")
        assert "error" not in result.lower()
```

---

### 9. A/B 测试

```python
class ABTest:
    """A/B 测试"""
    
    async def test_two_models(self):
        """测试两个模型"""
        # A 组
        agent_a = Agent(model="gpt-3.5-turbo")
        result_a = await agent_a.run("test")
        
        # B 组
        agent_b = Agent(model="gpt-4")
        result_b = await agent_b.run("test")
        
        # 比较结果
        assert len(result_a) > 0
        assert len(result_b) > 0
        
        # 记录指标
        metrics = {
            "model_a": {"quality": 0.8, "cost": 0.002},
            "model_b": {"quality": 0.95, "cost": 0.03}
        }
        
        return metrics
```

---

### 10. 模糊测试

```python
import hypothesis
from hypothesis import strategies as st

class FuzzTest:
    """模糊测试"""
    
    @hypothesis.given(st.text())
    def test_random_input(self, text):
        """测试随机输入"""
        try:
            result = agent.run(text)
            assert result is not None
        except Exception as e:
            # 应该优雅处理错误
            assert "unexpected" not in str(e).lower()
```

---

## 📊 测试覆盖率

```python
# pytest.ini
[pytest]
minversion = 6.0
addopts = -ra -q --cov=src --cov-report=html --cov-report=term
testpaths = tests

# 运行测试
# pytest --cov=src --cov-report=html
```

---

## 🔧 CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📊 测试类型对比

| 测试类型 | 速度 | 覆盖范围 | 频率 |
|---------|------|---------|------|
| **单元测试** | 快 | 单个函数 | 每次提交 |
| **集成测试** | 中 | 模块间 | 每次提交 |
| **E2E 测试** | 慢 | 完整流程 | 每日 |
| **性能测试** | 慢 | 性能指标 | 每周 |
| **压力测试** | 慢 | 极限情况 | 每月 |
| **负载测试** | 慢 | 持续负载 | 每月 |
| **安全测试** | 中 | 安全漏洞 | 每周 |
| **回归测试** | 快 | 已修复 Bug | 每次提交 |
| **A/B 测试** | 中 | 功能对比 | 按需 |
| **模糊测试** | 慢 | 边界情况 | 每周 |

---

## 🎯 测试策略

### 测试金字塔

```
        /\
       /  \      E2E (10%)
      /----\     
     /      \    集成 (20%)
    /--------\
   /          \  单元 (70%)
  /--------------\
```

### 覆盖率目标

- **单元测试**: 80%+
- **集成测试**: 60%+
- **E2E 测试**: 40%+
- **总体覆盖率**: 70%+

---

## 📝 测试最佳实践

1. ✅ 每个功能都有测试
2. ✅ 测试应该快速
3. ✅ 测试应该独立
4. ✅ 测试应该可重复
5. ✅ 测试应该有清晰的断言
6. ✅ 使用 Mock 隔离外部依赖
7. ✅ 参数化测试减少重复
8. ✅ 定期运行测试
9. ✅ 测试失败应该清晰说明原因
10. ✅ 保持测试代码质量

---

**生成时间**: 2026-03-27 16:40 GMT+8
