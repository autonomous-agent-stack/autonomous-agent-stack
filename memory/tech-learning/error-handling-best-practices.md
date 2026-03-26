# Claude Code CLI 错误处理最佳实践

> **创建时间**: 2026-03-22
> **目的**: 提高代码健壮性，减少生产事故

---

## 🎯 错误处理目标

| 指标 | 目标 | 测量方法 |
|------|------|---------|
| **异常捕获率** | 100% | 所有异常都被捕获 |
| **错误恢复率** | 95% | 错误后能恢复运行 |
| **用户友好性** | 高 | 清晰的错误提示 |
| **日志完整性** | 100% | 所有错误都有日志 |

---

## 🚨 常见错误类型

### **1. API 错误**

```python
# ❌ 不好：无错误处理
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

```python
# ✅ 好：完整错误处理
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
import time
import logging

logger = logging.getLogger(__name__)

def call_claude_api(prompt, max_retries=3):
    """调用 Claude API，带重试机制"""
    client = Anthropic()
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        
        except RateLimitError as e:
            logger.warning(f"Rate limit hit, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(60)  # 等待1分钟
                continue
            raise
        
        except APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise
        
        except APIError as e:
            logger.error(f"API error: {e}")
            raise
        
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise
```

---

### **2. 文件操作错误**

```python
# ❌ 不好：无错误处理
def read_file(path):
    with open(path) as f:
        return f.read()
```

```python
# ✅ 好：完整错误处理
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def read_file(path):
    """读取文件，带完整错误处理"""
    try:
        # 检查文件存在
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        # 检查文件权限
        if not os.access(path, os.R_OK):
            raise PermissionError(f"No read permission: {path}")
        
        # 检查文件大小
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise ValueError(f"File too large: {file_size} bytes")
        
        # 读取文件
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Successfully read file: {path}")
        return content
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise
    
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {path}: {e}")
        # 尝试其他编码
        try:
            with open(path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            raise ValueError(f"Cannot decode file: {path}")
    
    except Exception as e:
        logger.exception(f"Unexpected error reading {path}: {e}")
        raise
```

---

### **3. 数据验证错误**

```python
# ❌ 不好：无验证
def process_user_data(data):
    return {
        "name": data["name"],
        "email": data["email"],
        "age": data["age"]
    }
```

```python
# ✅ 好：完整验证
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserData(BaseModel):
    name: str
    email: EmailStr
    age: int
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0:
            raise ValueError('Age cannot be negative')
        if v > 150:
            raise ValueError('Age must be less than 150')
        return v

def process_user_data(data):
    """处理用户数据，带验证"""
    try:
        # 验证数据
        user = UserData(**data)
        
        logger.info(f"Processed user data: {user.email}")
        return user.dict()
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    
    except TypeError as e:
        logger.error(f"Type error: {e}")
        raise
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
```

---

## 🛡️ 错误处理模式

### **1. Try-Except-Raise 模式**

```python
def operation():
    try:
        # 执行操作
        result = do_something()
        return result
    
    except SpecificError as e:
        # 处理特定错误
        logger.error(f"Specific error: {e}")
        raise  # 重新抛出
    
    except Exception as e:
        # 捕获所有其他错误
        logger.exception(f"Unexpected error: {e}")
        raise
```

---

### **2. 重试模式**

```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1, backoff=2):
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
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
        
        return wrapper
    return decorator

# 使用
@retry(max_attempts=3, delay=1)
def call_api():
    return external_api_call()
```

---

### **3. 断路器模式**

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """断路器"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """调用函数，带断路器保护"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        
        except Exception as e:
            self.on_failure()
            raise
    
    def on_success(self):
        """成功回调"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# 使用
breaker = CircuitBreaker()

def protected_api_call():
    return breaker.call(external_api_call)
```

---

## 📝 日志最佳实践

### **1. 结构化日志**

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def log(self, level, message, **kwargs):
        """记录结构化日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        self.logger.log(
            getattr(logging, level),
            json.dumps(log_data)
        )

# 使用
logger = StructuredLogger(__name__)

logger.log(
    "INFO",
    "API call completed",
    endpoint="/api/users",
    method="GET",
    status=200,
    duration_ms=45
)
```

---

### **2. 错误日志**

```python
def log_error(error, context=None):
    """记录错误日志"""
    logger.error(
        "Error occurred",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        },
        exc_info=True
    )
```

---

## 🎯 实战案例

### **案例1: API 调用错误处理**

```python
import requests
from requests.exceptions import RequestException
import logging

logger = logging.getLogger(__name__)

def call_external_api(url, params=None, max_retries=3):
    """调用外部 API，带完整错误处理"""
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=10
            )
            
            # 检查状态码
            response.raise_for_status()
            
            # 解析 JSON
            data = response.json()
            
            logger.info(f"API call successful: {url}")
            return data
        
        except requests.Timeout:
            logger.warning(f"Timeout, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise TimeoutError(f"API timeout after {max_retries} attempts")
        
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            if response.status_code == 404:
                raise NotFoundError(f"Resource not found: {url}")
            elif response.status_code == 401:
                raise AuthError("Authentication failed")
            elif response.status_code == 429:
                logger.warning("Rate limited, waiting...")
                time.sleep(60)
                continue
            raise
        
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise
        
        except ValueError as e:
            logger.error(f"JSON decode error: {e}")
            raise ValueError("Invalid JSON response")
        
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise
```

---

### **案例2: 数据库操作错误处理**

```python
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

logger = logging.getLogger(__name__)

def save_to_database(session, data):
    """保存数据到数据库，带错误处理"""
    try:
        # 验证数据
        if not data:
            raise ValueError("Data cannot be empty")
        
        # 创建记录
        record = MyModel(**data)
        session.add(record)
        
        # 提交事务
        session.commit()
        
        logger.info(f"Saved record: {record.id}")
        return record
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error: {e}")
        raise ValueError("Duplicate entry or constraint violation")
    
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    
    except Exception as e:
        session.rollback()
        logger.exception(f"Unexpected error: {e}")
        raise
```

---

## 📊 错误监控

### **1. 错误统计**

```python
from collections import defaultdict
import time

class ErrorMonitor:
    """错误监控器"""
    
    def __init__(self):
        self.errors = defaultdict(list)
    
    def record_error(self, error_type, error_message):
        """记录错误"""
        self.errors[error_type].append({
            "message": error_message,
            "timestamp": time.time()
        })
    
    def get_error_rate(self, error_type, window_seconds=3600):
        """获取错误率"""
        now = time.time()
        recent_errors = [
            e for e in self.errors[error_type]
            if now - e["timestamp"] < window_seconds
        ]
        return len(recent_errors)

monitor = ErrorMonitor()

# 使用
try:
    operation()
except Exception as e:
    monitor.record_error(type(e).__name__, str(e))
    raise
```

---

### **2. 告警系统**

```python
def send_alert(error_type, error_message, severity="high"):
    """发送告警"""
    alert_data = {
        "type": error_type,
        "message": error_message,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    
    # 发送到监控系统
    requests.post(
        "https://alerts.example.com/api/alerts",
        json=alert_data
    )
```

---

## ✅ 错误处理检查清单

**代码审查时检查**:

- [ ] 所有外部调用都有 try-except
- [ ] 所有文件操作都检查存在性和权限
- [ ] 所有用户输入都有验证
- [ ] 所有错误都有日志
- [ ] 关键操作有重试机制
- [ ] 敏感信息不在日志中
- [ ] 错误消息用户友好
- [ ] 有断路器保护
- [ ] 有错误监控
- [ ] 有告警机制

---

**创建时间**: 2026-03-22 20:00
**版本**: 1.0
**状态**: 🟢 持续更新
