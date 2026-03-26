# Claude Code CLI 生产部署与监控最佳实践

> **创建时间**: 2026-03-22 20:15
> **目的**: 确保 Claude Code 在生产环境稳定运行
> **状态**: 🟢 完整

---

## 🎯 生产部署目标

| 指标 | 开发环境 | 生产环境 |
|------|---------|----------|
| **可用性** | 90% | 99.9% |
| **响应时间** | 10秒 | 3秒 |
| **错误率** | 5% | 0.1% |
| **监控** | 基础 | 完整 |

---

## 🐳 Docker 部署

### **1. Dockerfile**

```dockerfile
# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 启动命令
CMD ["python", "main.py"]
```

---

### **2. docker-compose.yml**

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
      - CACHE_REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres
    restart: always
    networks:
      - backend
    volumes:
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: always

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=claude_code
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - backend
    restart: always

volumes:
  redis_data:
  postgres_data:

networks:
  backend:
    driver: bridge
```

---

## ☸️ Kubernetes 部署

### **1. Deployment**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claude-code-api
  labels:
    app: claude-code-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: claude-code-api
  template:
    metadata:
      labels:
        app: claude-code-api
    spec:
      containers:
      - name: api
        image: your-registry/claude-code-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: claude-code-secrets
              key: anthropic-api-key
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

### **2. Service**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: claude-code-api-service
spec:
  selector:
    app: claude-code-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

### **3. HorizontalPodAutoscaler**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: claude-code-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: claude-code-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 📊 监控系统

### **1. Prometheus 指标**

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 定义指标
REQUEST_COUNT = Counter(
    'claude_code_requests_total',
    'Total requests',
    ['method', 'endpoint']
)
REQUEST_LATENCY = Histogram(
    'claude_code_request_latency_seconds',
    'Request latency',
    ['method', 'endpoint']
)
ACTIVE_REQUESTS = Gauge(
    'claude_code_active_requests',
    'Active requests'
)
TOKEN_USAGE = Counter(
    'claude_code_tokens_total',
    'Tokens used',
    ['type', 'model']
)
ERROR_COUNT = Counter(
    'claude_code_errors_total',
    'Total errors',
    ['type']
)

# 装饰器
def track_metrics(func):
    """跟踪指标装饰器"""
    def wrapper(*args, **kwargs):
        REQUEST_COUNT.labels(
            method='POST',
            endpoint='/generate'
        ).inc()
        ACTIVE_REQUESTS.inc()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            REQUEST_LATENCY.labels(
                method='POST',
                endpoint='/generate'
            ).observe(time.time() - start_time)
            return result
        except Exception as e:
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            raise
        finally:
            ACTIVE_REQUESTS.dec()
    
    return wrapper
```

---

### **2. Grafana 仪表盘**

**关键指标**:
1. **请求速率**: `rate(claude_code_requests_total[5m])`
2. **延迟**: `histogram_quantile(0.95, rate(claude_code_request_latency_seconds_bucket[5m]))`
3. **错误率**: `rate(claude_code_errors_total[5m])`
4. **Token使用**: `rate(claude_code_tokens_total[1h])`
5. **活跃请求**: `claude_code_active_requests`

---

### **3. 告警规则**

```yaml
# alerts.yml
groups:
- name: claude-code-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(claude_code_errors_total[5m]) > 0.01
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
      
  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(claude_code_request_latency_seconds_bucket[5m])) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High latency detected
      
  - alert: APIKeyQuotaExceeded
    expr: claude_code_tokens_total > 1000000
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: API key quota exceeded
```

---

## 🔒 安全加固

### **1. API Key 管理**

```python
# config.py
import os
from cryptography.fernet import Fernet

class APIKeyManager:
    """API Key 管理器"""
    
    def __init__(self):
        self.cipher = Fernet(os.environ.get('ENCRYPTION_KEY'))
    
    def encrypt_key(self, api_key: str) -> bytes:
        """加密 API Key"""
        return self.cipher.encrypt(api_key.encode())
    
    def decrypt_key(self, encrypted_key: bytes) -> str:
        """解密 API Key"""
        return self.cipher.decrypt(encrypted_key).decode()
    
    def rotate_key(self, old_key: str, new_key: str):
        """轮换 API Key"""
        # 验证新 Key
        self.validate_key(new_key)
        
        # 更新配置
        encrypted = self.encrypt_key(new_key)
        # 保存到安全存储
        self.save_to_vault(encrypted)
```

---

### **2. 速率限制**

```python
# rate_limiter.py
from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)

@app.post("/generate")
@limiter.limit("100/minute")
async def generate_code(request: Request):
    """生成代码，带速率限制"""
    # 验证请求
    if not validate_request(request):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # 处理请求
    return process_request(request)

def validate_request(request: Request) -> bool:
    """验证请求"""
    # 检查 IP
    client_ip = get_remote_address(request)
    if is_blocked_ip(client_ip):
        return False
    
    # 检查 User-Agent
    user_agent = request.headers.get('user-agent')
    if is_suspicious_ua(user_agent):
        return False
    
    return True
```

---

### **3. 审计日志**

```python
# audit.py
import logging
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self):
        self.logger = logging.getLogger('audit')
    
    def log_request(self, request: Dict[str, Any], response: Dict[str, Any]):
        """记录请求"""
        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': request.get('user_id'),
            'action': request.get('action'),
            'resource': request.get('resource'),
            'ip_address': request.get('ip_address'),
            'user_agent': request.get('user_agent'),
            'request_size': len(str(request)),
            'response_size': len(str(response)),
            'status': response.get('status')
        }
        
        self.logger.info(audit_data)
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """记录错误"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        self.logger.error(error_data)
```

---

## 🚀 CI/CD 流程

### **1. GitHub Actions**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

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
    
    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t claude-code-api:${{ github.sha }} .
        docker tag claude-code-api:${{ github.sha }} claude-code-api:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push claude-code-api:${{ github.sha }}
        docker push claude-code-api:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      run: |
        kubectl set image deployment/claude-code-api api=claude-code-api:${{ github.sha }}
        kubectl rollout status deployment/claude-code-api
```

---

### **2. 蓝绿部署**

```bash
#!/bin/bash
# blue-green-deploy.sh

# 当前版本
CURRENT=$(kubectl get service claude-code-api -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT" == "blue" ]; then
    NEW="green"
else
    NEW="blue"
fi

# 部署新版本
kubectl apply -f k8s/deployment-$NEW.yaml

# 等待就绪
kubectl rollout status deployment/claude-code-api-$NEW

# 切换流量
kubectl patch service claude-code-api -p "{\"spec\":{\"selector\":{\"version\":\"$NEW\"}}}"

# 清理旧版本
kubectl delete deployment claude-code-api-$CURRENT
```

---

## 📈 性能优化

### **1. 缓存策略**

```python
# cache.py
from redis import Redis
import hashlib
import json

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)
    
    def get_cached_response(self, prompt: str) -> dict:
        """获取缓存响应"""
        key = self._generate_key(prompt)
        cached = self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def cache_response(self, prompt: str, response: dict, ttl: int = 3600):
        """缓存响应"""
        key = self._generate_key(prompt)
        self.redis.setex(key, ttl, json.dumps(response))
    
    def _generate_key(self, prompt: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(prompt.encode()).hexdigest()
```

---

### **2. 连接池**

```python
# connection_pool.py
from anthropic import Anthropic
from queue import Queue
import threading

class ConnectionPool:
    """连接池"""
    
    def __init__(self, max_connections: int = 10):
        self.pool = Queue(max_connections)
        self.lock = threading.Lock()
        
        # 初始化连接
        for _ in range(max_connections):
            self.pool.put(Anthropic())
    
    def get_connection(self) -> Anthropic:
        """获取连接"""
        return self.pool.get()
    
    def return_connection(self, conn: Anthropic):
        """归还连接"""
        self.pool.put(conn)
    
    def __enter__(self):
        return self.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.return_connection(self)
```

---

## 🔍 故障排查

### **1. 常见问题**

**问题1: API 超时**
```python
# 解决方案：增加超时时间
client = Anthropic(timeout=60.0)
```

**问题2: 内存泄漏**
```python
# 解决方案：定期清理
import gc

def cleanup():
    gc.collect()
```

**问题3: 连接泄漏**
```python
# 解决方案：使用上下文管理器
with ConnectionPool() as client:
    response = client.messages.create(...)
```

---

### **2. 日志分析**

```bash
# 查看错误日志
kubectl logs -f deployment/claude-code-api | grep ERROR

# 查看慢请求
kubectl logs -f deployment/claude-code-api | grep "latency > 5s"

# 查看API使用情况
kubectl logs -f deployment/claude-code-api | grep "tokens"
```

---

## ✅ 部署检查清单

**部署前**:
- [ ] 代码审查完成
- [ ] 测试覆盖率 > 80%
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 文档更新

**部署中**:
- [ ] 备份当前版本
- [ ] 蓝绿部署就绪
- [ ] 监控配置完成
- [ ] 告警规则激活

**部署后**:
- [ ] 健康检查通过
- [ ] 性能指标正常
- [ ] 错误率 < 0.1%
- [ ] 用户反馈良好

---

**创建时间**: 2026-03-22 20:15
**版本**: 1.0
**状态**: 🟢 完整
