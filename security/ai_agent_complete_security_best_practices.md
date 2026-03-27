# AI Agent 完整安全最佳实践

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:11
> **安全措施**: 80+

---

## 🔒 安全最佳实践

### 1. API 密钥管理

#### 1.1 密钥存储
```python
# ❌ 错误：硬编码
api_key = 'sk-1234567890abcdef'

# ✅ 正确：环境变量
import os
api_key = os.getenv('OPENAI_API_KEY')

# ✅ 更好：密钥管理服务
from aws_secretsmanager import get_secret
api_key = get_secret('openai-api-key')
```

---

#### 1.2 密钥轮换
```python
import os
from datetime import datetime, timedelta

class APIKeyManager:
    def __init__(self):
        self.keys = os.getenv('API_KEYS').split(',')
        self.last_rotation = datetime.now()
        self.rotation_period = timedelta(days=90)
    
    def get_key(self):
        if datetime.now() - self.last_rotation > self.rotation_period:
            self.rotate_keys()
        return self.keys[0]
    
    def rotate_keys(self):
        # 自动轮换逻辑
        self.last_rotation = datetime.now()
        # 通知管理员
        send_alert('API keys rotated')
```

---

### 2. 数据加密

#### 2.1 传输加密
```python
# ✅ 强制 HTTPS
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)

# ✅ TLS 1.3
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
```

---

#### 2.2 存储加密
```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()

# 使用
encryptor = DataEncryption()
encrypted = encryptor.encrypt('sensitive data')
decrypted = encryptor.decrypt(encrypted)
```

---

### 3. 访问控制

#### 3.1 认证
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.getenv('JWT_SECRET'),
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired'
        )
```

---

#### 3.2 授权
```python
from functools import wraps

def require_role(role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if role not in user['roles']:
                raise HTTPException(
                    status_code=403,
                    detail='Insufficient permissions'
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用
@app.get('/admin')
@require_role('admin')
async def admin_endpoint(current_user = Depends(verify_token)):
    return {'message': 'Admin access'}
```

---

### 4. 输入验证

#### 4.1 数据清洗
```python
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

#### 4.2 SQL 注入防护
```python
# ❌ 错误：字符串拼接
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 正确：参数化查询
from sqlalchemy import text

query = text("SELECT * FROM users WHERE id = :id")
result = db.execute(query, {'id': user_id})
```

---

### 5. 速率限制

#### 5.1 API 限流
```python
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

app = FastAPI()

@app.get('/chat', dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def chat(query: str):
    return {'response': agent.run(query)}

# 启动限流
@app.on_event('startup')
async def startup():
    await FastAPILimiter.init(redis)
```

**限流策略**：
| 用户类型 | 限制 | 时间窗口 |
|---------|------|---------|
| 免费 | 10 次 | 1 分钟 |
| 付费 | 100 次 | 1 分钟 |
| 企业 | 1000 次 | 1 分钟 |

---

### 6. 日志审计

#### 6.1 操作日志
```python
import logging
from datetime import datetime

logger = logging.getLogger('audit')

def log_operation(user_id: str, action: str, details: dict):
    logger.info({
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'action': action,
        'details': details,
        'ip': request.client.host
    })

# 使用
log_operation(
    user_id='user123',
    action='query',
    details={'query': 'What is AI?', 'model': 'gpt-4'}
)
```

---

#### 6.2 访问日志
```python
from fastapi import Request
import time

@app.middleware('http')
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info({
        'method': request.method,
        'url': request.url.path,
        'status': response.status_code,
        'duration': f'{duration:.2f}s',
        'ip': request.client.host
    })
    
    return response
```

---

### 7. 错误处理

#### 7.1 安全错误消息
```python
# ❌ 错误：泄露敏感信息
try:
    result = agent.run(query)
except Exception as e:
    return {'error': str(e)}  # 可能泄露内部信息

# ✅ 正确：通用错误消息
try:
    result = agent.run(query)
except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    return {'error': 'An error occurred. Please try again.'}
```

---

### 8. 依赖安全

#### 8.1 依赖扫描
```bash
# 使用 Safety 检查漏洞
safety check

# 使用 pip-audit
pip-audit

# 使用 Dependabot（GitHub）
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: 'pip'
    directory: '/'
    schedule:
      interval: 'daily'
```

---

### 9. 容器安全

#### 9.1 Dockerfile 安全
```dockerfile
# ✅ 使用非 root 用户
FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 设置工作目录
WORKDIR /app

# 复制文件
COPY --chown=appuser:appuser . .

# 切换用户
USER appuser

# 运行应用
CMD ['python', 'app.py']
```

---

#### 9.2 镜像扫描
```bash
# 使用 Trivy 扫描
trivy image ai-agent:v1.0

# 使用 Docker Scout
docker scout cves ai-agent:v1.0
```

---

### 10. 网络安全

#### 10.1 防火墙规则
```bash
# iptables 规则
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -j DROP

# 只允许特定 IP
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 8000 -j ACCEPT
```

---

#### 10.2 VPC 配置
```yaml
# AWS VPC 配置
VPC:
  CIDR: 10.0.0.0/16
  Subnets:
    - Name: Private
      CIDR: 10.0.1.0/24
    - Name: Public
      CIDR: 10.0.2.0/24
  SecurityGroups:
    - Name: App
      Inbound:
        - Port: 443
          Source: 0.0.0.0/0
      Outbound:
        - Port: 443
          Destination: 0.0.0.0/0
```

---

## 🛡️ 安全检查清单

### 高优先级
- [ ] API 密钥加密存储
- [ ] 强制 HTTPS
- [ ] 输入验证
- [ ] SQL 注入防护
- [ ] 速率限制

### 中优先级
- [ ] 日志审计
- [ ] 访问控制
- [ ] 错误处理
- [ ] 依赖扫描

### 低优先级
- [ ] 容器安全
- [ ] 网络隔离
- [ ] 灾难恢复
- [ ] 安全培训

---

**生成时间**: 2026-03-27 22:15 GMT+8
