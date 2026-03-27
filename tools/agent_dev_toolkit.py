# AI Agent 开发工具箱

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **工具数**: 20+

---

## 🛠️ 开发工具

### 1. 代码生成器

```python
# tool_generator.py
def generate_tool(name: str, description: str) -> str:
    """生成工具代码"""
    template = f'''
class {name}:
    """{description}"""
    
    def __init__(self):
        self.name = "{name.lower()}"
    
    def execute(self, **kwargs):
        """执行工具"""
        # TODO: 实现逻辑
        return "Not implemented"
'''
    return template
```

### 2. Prompt 模板库

```python
# prompt_templates.py
TEMPLATES = {
    "react": """
Question: {question}

Thought: {thought}
Action: {action}
Action Input: {action_input}

Observation: {observation}

Final Answer: {answer}
""",
    
    "rag": """
Based on the following documents:

{context}

Answer the question: {question}
""",
    
    "code_review": """
Review this code:

```{language}
{code}
```

Provide:
1. Code quality score (0-100)
2. Issues found
3. Suggestions
"""
}
```

---

## 🧪 测试工具

### 1. Mock LLM

```python
# mock_llm.py
class MockLLM:
    """Mock LLM for testing"""
    
    def __init__(self, return_value: str = "test"):
        self.return_value = return_value
        self.calls = []
    
    def call(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.return_value
    
    def assert_called_with(self, expected: str):
        assert expected in self.calls
```

### 2. 性能测试器

```python
# performance_tester.py
import time
import statistics

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def test(self, tasks: List[str], runs: int = 10):
        times = []
        
        for _ in range(runs):
            start = time.time()
            
            for task in tasks:
                self.agent.run(task)
            
            elapsed = time.time() - start
            times.append(elapsed)
        
        return {
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "p95": sorted(times)[int(len(times) * 0.95)]
        }
```

---

## 📊 监控工具

### 1. Token 计数器

```python
# token_counter.py
import tiktoken

class TokenCounter:
    """Token 计数器"""
    
    def __init__(self, model: str = "gpt-4"):
        self.encoding = tiktoken.encoding_for_model(model)
    
    def count(self, text: str) -> int:
        """计算 Token 数"""
        return len(self.encoding.encode(text))
    
    def estimate_cost(self, tokens: int, model: str) -> float:
        """估算成本"""
        prices = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
        
        price = prices[model]["input"]
        return tokens * price / 1000
```

### 2. 成本追踪器

```python
# cost_tracker.py
class CostTracker:
    """成本追踪器"""
    
    def __init__(self, daily_budget: float = 100.0):
        self.daily_budget = daily_budget
        self.daily_cost = 0.0
        self.history = []
    
    def record(self, cost: float):
        """记录成本"""
        self.daily_cost += cost
        self.history.append({
            "cost": cost,
            "total": self.daily_cost,
            "timestamp": time.time()
        })
        
        if self.daily_cost > self.daily_budget:
            self._alert()
    
    def _alert(self):
        """告警"""
        print(f"⚠️ 预算超限: ${self.daily_cost:.2f} / ${self.daily_budget:.2f}")
```

---

## 🔧 调试工具

### 1. 日志查看器

```python
# log_viewer.py
class LogViewer:
    """日志查看器"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
    
    def tail(self, n: int = 10):
        """查看最近 n 条日志"""
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            return lines[-n:]
    
    def search(self, keyword: str):
        """搜索日志"""
        with open(self.log_file, 'r') as f:
            return [line for line in f if keyword in line]
    
    def filter_by_level(self, level: str):
        """按级别过滤"""
        with open(self.log_file, 'r') as f:
            return [line for line in f if f"[{level}]" in line]
```

### 2. 请求追踪器

```python
# request_tracer.py
class RequestTracer:
    """请求追踪器"""
    
    def __init__(self):
        self.requests = []
    
    def trace(self, request: dict):
        """追踪请求"""
        self.requests.append({
            **request,
            "timestamp": time.time()
        })
    
    def get_timeline(self):
        """获取时间线"""
        return sorted(
            self.requests,
            key=lambda x: x["timestamp"]
        )
    
    def export(self, filename: str):
        """导出"""
        import json
        
        with open(filename, 'w') as f:
            json.dump(self.requests, f, indent=2)
```

---

## 🚀 部署工具

### 1. 配置生成器

```python
# config_generator.py
import yaml

class ConfigGenerator:
    """配置生成器"""
    
    def generate(self, env: str = "dev") -> dict:
        """生成配置"""
        configs = {
            "dev": {
                "model": "gpt-3.5-turbo",
                "cache": False,
                "debug": True
            },
            "prod": {
                "model": "gpt-4",
                "cache": True,
                "debug": False
            }
        }
        
        return configs[env]
    
    def save(self, config: dict, filename: str):
        """保存配置"""
        with open(filename, 'w') as f:
            yaml.dump(config, f)
```

### 2. 健康检查器

```python
# health_checker.py
class HealthChecker:
    """健康检查器"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    
    def check(self) -> dict:
        """检查健康状态"""
        try:
            response = requests.get(
                f"{self.endpoint}/health",
                timeout=5
            )
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
```

---

## 📚 文档工具

### 1. API 文档生成器

```python
# api_doc_generator.py
class APIDocGenerator:
    """API 文档生成器"""
    
    def generate(self, endpoints: List[dict]) -> str:
        """生成 API 文档"""
        doc = "# API Documentation\n\n"
        
        for endpoint in endpoints:
            doc += f"## {endpoint['method']} {endpoint['path']}\n\n"
            doc += f"{endpoint['description']}\n\n"
            doc += f"### Parameters\n\n"
            
            for param in endpoint.get('parameters', []):
                doc += f"- `{param['name']}`: {param['type']}\n"
            
            doc += "\n"
        
        return doc
```

---

**生成时间**: 2026-03-27 14:45 GMT+8
