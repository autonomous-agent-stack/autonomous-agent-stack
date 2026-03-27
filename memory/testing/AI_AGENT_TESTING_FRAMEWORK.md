# AI Agent 测试框架

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **测试类型**: 单元测试 + 集成测试 + E2E 测试

---

## 🧪 测试框架设计

### 测试层次

```
E2E 测试（端到端）
    ↓
集成测试（模块间）
    ↓
单元测试（单个函数）
    ↓
工具测试（工具函数）
```

---

## 📋 测试用例模板

### 1. Agent 单元测试

```python
"""
Agent 单元测试模板
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from your_agent import YourAgent

class TestYourAgent:
    """Agent 单元测试"""
    
    @pytest.fixture
    def agent(self):
        """创建 Agent 实例"""
        return YourAgent(model="test-model")
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        mock = Mock()
        mock.call.return_value = "测试响应"
        return mock
    
    def test_init(self, agent):
        """测试初始化"""
        assert agent.model == "test-model"
        assert agent.tools is not None
    
    def test_run_success(self, agent, mock_llm):
        """测试成功运行"""
        # Mock LLM
        agent.llm = mock_llm
        
        # 运行
        result = agent.run("测试任务")
        
        # 验证
        assert result is not None
        assert isinstance(result, str)
        mock_llm.call.assert_called_once()
    
    def test_run_with_tools(self, agent, mock_llm):
        """测试带工具运行"""
        # Mock 工具
        mock_tool = Mock()
        mock_tool.execute.return_value = "工具结果"
        agent.tools = {"test_tool": mock_tool}
        
        # Mock LLM 返回工具调用
        mock_llm.call.return_value = "Action: test_tool\nAction Input: test"
        
        # 运行
        result = agent.run("使用工具")
        
        # 验证
        mock_tool.execute.assert_called_once()
    
    def test_error_handling(self, agent, mock_llm):
        """测试错误处理"""
        # Mock LLM 抛出异常
        mock_llm.call.side_effect = Exception("LLM 错误")
        
        # 验证异常处理
        with pytest.raises(Exception):
            agent.run("测试任务")
    
    @pytest.mark.parametrize("input,expected", [
        ("你好", "问候"),
        ("订单查询", "查询"),
        ("退款", "退款"),
    ])
    def test_intent_classification(self, agent, input, expected):
        """测试意图识别"""
        intent = agent.classify_intent(input)
        assert intent == expected
    
    @pytest.mark.asyncio
    async def test_async_run(self, agent, mock_llm):
        """测试异步运行"""
        agent.llm = mock_llm
        
        result = await agent.async_run("异步任务")
        
        assert result is not None
```

### 2. 工具测试

```python
"""
工具测试模板
"""

import pytest
from your_tools import SearchTool, CalculatorTool

class TestSearchTool:
    """搜索工具测试"""
    
    @pytest.fixture
    def tool(self):
        """创建工具实例"""
        return SearchTool()
    
    @pytest.fixture
    def mock_api(self):
        """Mock API"""
        with patch('requests.get') as mock:
            mock.return_value.json.return_value = {
                "results": [
                    {"title": "测试结果 1", "url": "http://test1.com"},
                    {"title": "测试结果 2", "url": "http://test2.com"}
                ]
            }
            yield mock
    
    def test_execute_success(self, tool, mock_api):
        """测试成功执行"""
        result = tool.execute({"query": "测试", "limit": 2})
        
        assert "results" in result
        assert len(result["results"]) == 2
    
    def test_execute_empty_query(self, tool):
        """测试空查询"""
        with pytest.raises(ValueError):
            tool.execute({"query": ""})
    
    def test_execute_api_error(self, tool):
        """测试 API 错误"""
        with patch('requests.get') as mock:
            mock.side_effect = Exception("API 错误")
            
            with pytest.raises(Exception):
                tool.execute({"query": "测试"})


class TestCalculatorTool:
    """计算器工具测试"""
    
    @pytest.fixture
    def tool(self):
        return CalculatorTool()
    
    @pytest.mark.parametrize("expression,expected", [
        ("2 + 3", 5),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("20 / 5", 4),
        ("2 ** 3", 8),
    ])
    def test_execute_basic(self, tool, expression, expected):
        """测试基础运算"""
        result = tool.execute({"expression": expression})
        assert float(result) == expected
    
    def test_execute_complex(self, tool):
        """测试复杂运算"""
        result = tool.execute({"expression": "(2 + 3) * 4 - 5"})
        assert float(result) == 15
    
    def test_execute_invalid(self, tool):
        """测试无效表达式"""
        with pytest.raises(ValueError):
            tool.execute({"expression": "2 + + 3"})
    
    def test_execute_security(self, tool):
        """测试安全性（防止注入）"""
        # 尝试执行危险代码
        with pytest.raises(ValueError):
            tool.execute({"expression": "__import__('os').system('ls')"})
```

### 3. 记忆系统测试

```python
"""
记忆系统测试模板
"""

import pytest
from your_memory import ConversationMemory, VectorMemory

class TestConversationMemory:
    """对话记忆测试"""
    
    @pytest.fixture
    def memory(self):
        return ConversationMemory(max_messages=5)
    
    def test_add_message(self, memory):
        """测试添加消息"""
        memory.add_message("user", "你好")
        memory.add_message("assistant", "你好！")
        
        history = memory.get_history()
        assert len(history) == 2
    
    def test_max_messages(self, memory):
        """测试最大消息数"""
        # 添加 10 条消息
        for i in range(10):
            memory.add_message("user", f"消息 {i}")
        
        # 应该只保留 5 条
        history = memory.get_history()
        assert len(history) == 5
    
    def test_clear(self, memory):
        """测试清空"""
        memory.add_message("user", "测试")
        memory.clear()
        
        assert len(memory.get_history()) == 0


class TestVectorMemory:
    """向量记忆测试"""
    
    @pytest.fixture
    def memory(self):
        return VectorMemory()
    
    def test_add_and_search(self, memory):
        """测试添加和搜索"""
        # 添加文档
        memory.add("Python 是一种编程语言")
        memory.add("JavaScript 是一种脚本语言")
        memory.add("机器学习是 AI 的分支")
        
        # 搜索
        results = memory.search("编程语言", n_results=2)
        
        assert len(results) == 2
        assert "Python" in results[0]
    
    def test_similarity(self, memory):
        """测试相似度"""
        memory.add("今天天气不错")
        memory.add("今天天气很好")
        memory.add("我喜欢吃苹果")
        
        # 搜索相似内容
        results = memory.search("天气好", n_results=2)
        
        # 应该返回前两个
        assert "天气" in results[0]
        assert "天气" in results[1]
```

### 4. 集成测试

```python
"""
集成测试模板
"""

import pytest
from your_agent import YourAgent
from your_tools import SearchTool, CalculatorTool
from your_memory import ConversationMemory

class TestAgentIntegration:
    """Agent 集成测试"""
    
    @pytest.fixture
    def agent(self):
        """创建完整 Agent"""
        tools = {
            "search": SearchTool(),
            "calculator": CalculatorTool()
        }
        memory = ConversationMemory()
        
        return YourAgent(
            model="test-model",
            tools=tools,
            memory=memory
        )
    
    @pytest.mark.integration
    def test_full_conversation(self, agent):
        """测试完整对话流程"""
        # 1. 问候
        response1 = agent.run("你好")
        assert response1 is not None
        
        # 2. 查询
        response2 = agent.run("帮我搜索 Python 教程")
        assert "Python" in response2 or "搜索" in response2
        
        # 3. 计算
        response3 = agent.run("2 + 3 等于多少？")
        assert "5" in response3
        
        # 4. 验证记忆
        history = agent.memory.get_history()
        assert len(history) >= 6  # 3 对话 * 2 (user + assistant)
    
    @pytest.mark.integration
    def test_tool_chain(self, agent):
        """测试工具链"""
        # 复杂任务：搜索 + 计算
        response = agent.run(
            "搜索 Python 的最新版本，然后计算 3.11 + 0.1"
        )
        
        assert response is not None
        # 验证工具调用
        assert "search" in agent.tool_calls or "calculator" in agent.tool_calls
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_conversation(self, agent):
        """测试长对话"""
        # 10 轮对话
        for i in range(10):
            response = agent.run(f"第 {i+1} 轮对话")
            assert response is not None
        
        # 验证记忆
        history = agent.memory.get_history()
        assert len(history) == 20  # 10 * 2
```

### 5. E2E 测试

```python
"""
E2E 测试模板
"""

import pytest
import requests
import time

class TestE2E:
    """端到端测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        # 等待服务启动
        time.sleep(2)
        
        # 检查服务状态
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
    
    @pytest.mark.e2e
    def test_chat_endpoint(self):
        """测试聊天端点"""
        # 发送请求
        response = requests.post(
            f"{self.BASE_URL}/chat",
            json={
                "customer_id": "test123",
                "message": "你好"
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
    
    @pytest.mark.e2e
    def test_conversation_flow(self):
        """测试完整对话流程"""
        session_id = "test_session_123"
        
        # 1. 发送第一条消息
        response1 = requests.post(
            f"{self.BASE_URL}/chat",
            json={
                "customer_id": session_id,
                "message": "我的订单到哪了？"
            }
        )
        assert response1.status_code == 200
        
        # 2. 发送第二条消息（测试上下文）
        response2 = requests.post(
            f"{self.BASE_URL}/chat",
            json={
                "customer_id": session_id,
                "message": "订单号是 ORD123"
            }
        )
        assert response2.status_code == 200
        
        # 3. 验证上下文连续性
        data2 = response2.json()
        # 应该能关联到上一条消息
        assert data2["response"] is not None
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_performance(self):
        """测试性能"""
        start_time = time.time()
        
        # 发送 100 个请求
        for _ in range(100):
            response = requests.post(
                f"{self.BASE_URL}/chat",
                json={
                    "customer_id": "perf_test",
                    "message": "测试"
                }
            )
            assert response.status_code == 200
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 100
        
        # 平均响应时间应 < 2 秒
        assert avg_time < 2.0, f"平均响应时间 {avg_time:.2f}s 超过阈值"
```

---

## 🚀 运行测试

### 运行所有测试

```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行 E2E 测试
pytest tests/e2e/ -v

# 运行所有测试
pytest -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term
```

### 运行特定测试

```bash
# 运行单个测试文件
pytest tests/unit/test_agent.py -v

# 运行单个测试类
pytest tests/unit/test_agent.py::TestYourAgent -v

# 运行单个测试方法
pytest tests/unit/test_agent.py::TestYourAgent::test_run_success -v

# 运行标记的测试
pytest -m integration -v
pytest -m e2e -v
pytest -m "not slow" -v
```

---

## 📊 测试覆盖率目标

| 模块 | 目标覆盖率 | 当前覆盖率 |
|------|-----------|-----------|
| **Agent 核心** | 90% | 85% |
| **工具** | 85% | 80% |
| **记忆系统** | 80% | 75% |
| **API 端点** | 95% | 90% |
| **整体** | **85%** | **82%** |

---

## 🎯 测试最佳实践

### 1. 命名规范

```python
# ✅ 好的命名
def test_classify_intent_with_empty_input():
    pass

# ❌ 差的命名
def test1():
    pass
```

### 2. Mock 使用

```python
# ✅ 正确使用 Mock
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {"data": "test"}
    # 测试代码

# ❌ 不使用 Mock
def test_api_call():
    result = requests.get("http://api.example.com")  # 依赖外部 API
```

### 3. 参数化测试

```python
# ✅ 使用参数化
@pytest.mark.parametrize("input,expected", [
    ("hello", "en"),
    ("你好", "zh"),
    ("bonjour", "fr"),
])
def test_language_detection(input, expected):
    assert detect_language(input) == expected

# ❌ 重复代码
def test_language_detection_english():
    assert detect_language("hello") == "en"

def test_language_detection_chinese():
    assert detect_language("你好") == "zh"
```

---

**生成时间**: 2026-03-27 12:55 GMT+8
