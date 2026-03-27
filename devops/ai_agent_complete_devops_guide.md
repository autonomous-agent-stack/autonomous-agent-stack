# AI Agent DevOps 完整实践指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:50
> **实践数**: 30+

---

## 🚀 CI/CD 流水线

### 1. GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

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
  
  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: |
          docker build -t agent:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker push agent:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/agent agent=agent:${{ github.sha }}
```

---

### 2. Docker 容器化

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 3. Kubernetes 部署

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent
  template:
    metadata:
      labels:
        app: agent
    spec:
      containers:
      - name: agent
        image: agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
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

### 4. 监控配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'agent'
    static_configs:
      - targets: ['agent:8000']
```

```yaml
# grafana-dashboard.yaml
apiVersion: 1
providers:
  - name: 'Agent Dashboard'
    folder: 'Agent'
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

---

## 📊 日志管理

### 1. 结构化日志

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(self, level: str, message: str, **kwargs):
        """记录日志"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        log_json = json.dumps(log_data)
        
        if level == "INFO":
            self.logger.info(log_json)
        elif level == "ERROR":
            self.logger.error(log_json)
        elif level == "WARNING":
            self.logger.warning(log_json)

# 使用
logger = StructuredLogger(__name__)
logger.log("INFO", "Request received", user_id="123", duration=1.5)
```

---

### 2. 日志聚合

```yaml
# fluentd.conf
<source>
  @type forward
  port 24224
</source>

<match agent.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
  logstash_prefix agent
</match>
```

---

## 🔧 配置管理

### 1. 环境变量

```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    """配置"""
    
    # API
    API_KEY: str
    API_URL: str = "https://api.openai.com/v1"
    
    # 数据库
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # 日志
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

# 使用
settings = Settings()
```

---

### 2. 配置中心

```python
# consul_config.py
import consul

class ConsulConfig:
    """Consul 配置中心"""
    
    def __init__(self, host: str = "localhost"):
        self.client = consul.Consul(host=host)
    
    def get(self, key: str) -> str:
        """获取配置"""
        _, data = self.client.kv.get(key)
        return data['Value'].decode() if data else None
    
    def set(self, key: str, value: str):
        """设置配置"""
        self.client.kv.put(key, value)

# 使用
config = ConsulConfig()
api_key = config.get("agent/api_key")
```

---

## 📈 性能优化

### 1. 缓存策略

```python
# cache.py
from functools import lru_cache
import redis.asyncio as redis

class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """设置缓存"""
        await self.redis.setex(key, ttl, value)
    
    async def delete(self, key: str):
        """删除缓存"""
        await self.redis.delete(key)

# 使用
cache = CacheService("redis://localhost:6379")

# 内存缓存
@lru_cache(maxsize=1000)
def cached_function(param: str):
    """内存缓存函数"""
    return expensive_operation(param)
```

---

### 2. 连接池

```python
# connection_pool.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# 数据库连接池
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# HTTP 连接池
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

---

## 🔍 故障排查

### 1. 健康检查

```python
# health.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """健康检查"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "llm": await check_llm()
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks
    }

async def check_database() -> bool:
    """检查数据库"""
    try:
        await db.execute("SELECT 1")
        return True
    except:
        return False
```

---

### 2. 分布式追踪

```python
# tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider

# 配置追踪
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

# 使用追踪
with tracer.start_as_current_span("process_request"):
    # 处理请求
    pass
```

---

## 📊 DevOps 最佳实践

1. ✅ 自动化测试
2. ✅ 持续集成
3. ✅ 持续部署
4. ✅ 容器化
5. ✅ 基础设施即代码
6. ✅ 监控告警
7. ✅ 日志聚合
8. ✅ 配置管理
9. ✅ 安全扫描
10. ✅ 性能优化

---

**生成时间**: 2026-03-27 16:52 GMT+8
