# AI Agent 常见错误速查表

> **版本**: v1.0
> **错误类型**: 20+

---

## 🚨 常见错误

### 1. Token 超限

**错误**:
```
Error: This model's maximum context length is 8192 tokens
```

**解决**:
```python
def safe_call(prompt: str, max_tokens: int = 7000):
    if len(prompt) > max_tokens:
        prompt = prompt[:max_tokens]
    
    return llm.call(prompt)
```

---

### 2. API 限流

**错误**:
```
Error: Rate limit exceeded
```

**解决**:
```python
import time
from functools import wraps

def rate_limit(calls_per_minute: int = 60):
    def decorator(func):
        min_interval = 60.0 / calls_per_minute
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left = min_interval - elapsed
            
            if left > 0:
                time.sleep(left)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@rate_limit(calls_per_minute=50)
def safe_call(prompt: str):
    return llm.call(prompt)
```

---

### 3. 无限循环

**错误**:
```
Agent keeps looping forever
```

**解决**:
```python
class SafeAgent:
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
    
    def run(self, task: str) -> str:
        for i in range(self.max_iterations):
            result = self._execute(task)
            
            if self._is_complete(result):
                return result
        
        return "超过最大轮数"
```

---

### 4. JSON 解析错误

**错误**:
```
Error: Expecting value: line 1 column 1 (char 0)
```

**解决**:
```python
import json

def safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except:
        # 尝试提取 JSON
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        return {"error": "Failed to parse JSON"}
```

---

### 5. 网络超时

**错误**:
```
Error: Request timeout
```

**解决**:
```python
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def safe_request(url: str, timeout: int = 10):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
```

---

## 📊 错误分类

| 类型 | 频率 | 严重度 | 解决难度 |
|------|------|--------|---------|
| **Token 超限** | 高 | 中 | ⭐ |
| **API 限流** | 高 | 低 | ⭐ |
| **无限循环** | 中 | 高 | ⭐⭐ |
| **JSON 错误** | 中 | 低 | ⭐ |
| **网络超时** | 低 | 中 | ⭐⭐ |

---

## 🛡️ 防御性编程

```python
class RobustAgent:
    """健壮的 Agent"""
    
    def __init__(self):
        self.max_retries = 3
        self.max_tokens = 7000
        self.rate_limiter = RateLimiter()
    
    def run(self, task: str) -> str:
        # 1. 输入验证
        if not task or len(task) > 10000:
            raise ValueError("Invalid input")
        
        # 2. Token 限制
        task = task[:self.max_tokens]
        
        # 3. 重试机制
        for i in range(self.max_retries):
            try:
                # 4. 速率限制
                self.rate_limiter.wait()
                
                # 5. 执行
                result = self._execute(task)
                
                # 6. 验证输出
                if not result:
                    raise ValueError("Empty response")
                
                return result
            
            except Exception as e:
                if i == self.max_retries - 1:
                    return f"Error: {e}"
                
                time.sleep(2 ** i)
        
        return "Failed"
```

---

**生成时间**: 2026-03-27 14:48 GMT+8
