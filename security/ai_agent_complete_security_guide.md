# AI Agent 安全防护完整指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:47
> **安全措施**: 20+

---

## 🛡️ 安全架构

### 1. 输入验证

```python
from pydantic import BaseModel, validator, constr
from typing import Optional

class ChatRequest(BaseModel):
    """聊天请求验证"""
    
    message: constr(min_length=1, max_length=10000)
    user_id: Optional[str] = None
    context: Optional[dict] = None
    
    @validator('message')
    def validate_message(cls, v):
        """验证消息"""
        # 检查恶意模式
        forbidden_patterns = [
            r'ignore.*instructions',
            r'system:',
            r'<script>',
            r'javascript:',
            r'onerror=',
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Forbidden pattern detected: {pattern}")
        
        return v
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """验证用户 ID"""
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid user ID format")
        
        return v
```

---

### 2. API 认证

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI()
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证 Token"""
    token = credentials.credentials
    
    # 验证 Token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/chat")
async def chat(request: ChatRequest, user: dict = Depends(verify_token)):
    """需要认证的聊天"""
    # 处理请求
    pass
```

---

### 3. 速率限制

```python
from fastapi import FastAPI, Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

app = FastAPI()

# 初始化速率限制
@app.on_event("startup")
async def startup():
    redis = redis.asyncio.from_url("redis://localhost")
    await FastAPILimiter.init(redis)

@app.post("/api/v1/chat", dependencies=[Depends(RateLimiter(times=100, minutes=1))])
async def chat(request: ChatRequest):
    """限制每分钟 100 次请求"""
    pass
```

---

### 4. 数据加密

```python
from cryptography.fernet import Fernet
import base64

class EncryptionService:
    """加密服务"""
    
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """加密"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# 使用
encryption = EncryptionService(SECRET_KEY)

# 加密敏感数据
encrypted = encryption.encrypt("sensitive data")

# 解密
decrypted = encryption.decrypt(encrypted)
```

---

### 5. SQL 注入防护

```python
# ❌ 错误示例
def unsafe_query(user_id: str):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)

# ✅ 正确示例
def safe_query(user_id: str):
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))
```

---

### 6. XSS 防护

```python
from html import escape

def sanitize_html(text: str) -> str:
    """清理 HTML"""
    # 转义 HTML
    escaped = escape(text)
    
    # 移除脚本
    cleaned = re.sub(r'<script.*?</script>', '', escaped, flags=re.DOTALL)
    
    return cleaned

# 使用
user_input = "<script>alert('xss')</script>"
safe_output = sanitize_html(user_input)
print(safe_output)  # &lt;script&gt;alert('xss')&lt;/script&gt;
```

---

### 7. Prompt 注入防护

```python
class PromptInjectionProtection:
    """Prompt 注入防护"""
    
    FORBIDDEN_PATTERNS = [
        r'ignore.*previous',
        r'disregard.*instructions',
        r'you are now',
        r'system prompt',
        r'forget everything',
    ]
    
    @classmethod
    def sanitize(cls, prompt: str) -> str:
        """清理 Prompt"""
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise ValueError(f"Potential prompt injection detected")
        
        return prompt
    
    @classmethod
    def escape_special_chars(cls, prompt: str) -> str:
        """转义特殊字符"""
        # 转义可能的注入字符
        prompt = prompt.replace('{', '{{').replace('}', '}}')
        prompt = prompt.replace('<', '&lt;').replace('>', '&gt;')
        
        return prompt
```

---

### 8. 敏感数据过滤

```python
import re

class SensitiveDataFilter:
    """敏感数据过滤器"""
    
    PATTERNS = {
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',
    }
    
    @classmethod
    def redact(cls, text: str) -> str:
        """过滤敏感数据"""
        for name, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f'[{name.upper()}_REDACTED]', text)
        
        return text

# 使用
text = "My credit card is 1234-5678-9012-3456"
safe_text = SensitiveDataFilter.redact(text)
print(safe_text)  # My credit card is [CREDIT_CARD_REDACTED]
```

---

### 9. 访问控制

```python
from enum import Enum
from functools import wraps

class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

def require_role(role: Role):
    """角色验证装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            
            if not user or user.role != role.value:
                raise PermissionError(f"Requires {role.value} role")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# 使用
@app.post("/api/v1/admin/config")
@require_role(Role.ADMIN)
async def update_config(config: dict, user: dict):
    """管理员配置"""
    pass
```

---

### 10. 日志脱敏

```python
import logging

class SensitiveDataFilter(logging.Filter):
    """日志过滤器"""
    
    def filter(self, record):
        """过滤敏感数据"""
        # 脱敏处理
        if hasattr(record, 'msg'):
            record.msg = self._redact(record.msg)
        
        return True
    
    def _redact(self, text: str) -> str:
        """脱敏"""
        # 使用 SensitiveDataFilter
        return SensitiveDataFilter.redact(text)

# 配置日志
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())
```

---

## 🔒 安全检查清单

- [ ] 输入验证
- [ ] API 认证
- [ ] 速率限制
- [ ] 数据加密
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] Prompt 注入防护
- [ ] 敏感数据过滤
- [ ] 访问控制
- [ ] 日志脱敏
- [ ] HTTPS
- [ ] CORS 配置
- [ ] 安全头部
- [ ] 依赖更新
- [ ] 安全审计

---

## 📊 安全等级

| 等级 | 描述 | 措施 |
|------|------|------|
| **L1** | 基础 | 输入验证 + HTTPS |
| **L2** | 标准 | + 认证 + 速率限制 |
| **L3** | 高级 | + 加密 + 访问控制 |
| **L4** | 企业 | + 审计 + 监控 |

---

**生成时间**: 2026-03-27 16:49 GMT+8
