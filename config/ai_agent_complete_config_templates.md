# AI Agent 完整配置模板库

> **版本**: v1.0
> **更新时间**: 2026-03-27 18:07
> **模板数**: 30+

---

## ⚙️ 配置模板

### 1. 环境变量配置

```bash
# .env
# API Keys
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-api-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agent_db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
MAX_WORKERS=10
TIMEOUT=30
CACHE_TTL=3600
```

---

### 2. YAML 配置文件

```yaml
# config.yaml
agent:
  name: "AI Agent"
  version: "1.0.0"
  
  llm:
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 4000
    timeout: 30
    
  memory:
    enabled: true
    type: "chromadb"
    max_history: 10
    
  tools:
    enabled: true
    timeout: 10
    max_retries: 3
    
  monitoring:
    enabled: true
    metrics_port: 9090
    
  logging:
    level: "INFO"
    format: "json"
    file: "./logs/agent.log"
```

---

### 3. Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./data:/app/data
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:14-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

### 4. Kubernetes 配置

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
        image: agent:v1.0
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
```

---

### 5. Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agent'
    static_configs:
      - targets: ['agent:8000']
    
    metrics_path: /metrics
    scheme: http

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

---

### 6. 日志配置

```json
// logging_config.json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "json": {
      "format": "{\"timestamp\": \"%(asctime)s\", \"level\": \"%(levelname)s\", \"message\": \"%(message)s\"}"
    },
    "standard": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "standard"
    },
    "file": {
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "logs/agent.log",
      "maxBytes": 10485760,
      "backupCount": 5,
      "formatter": "json"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console", "file"]
  }
}
```

---

### 7. 安全配置

```yaml
# security_config.yaml
security:
  authentication:
    enabled: true
    type: "api_key"
    header: "X-API-Key"
  
  authorization:
    enabled: true
    type: "rbac"
  
  encryption:
    enabled: true
    algorithm: "AES-256-GCM"
  
  rate_limiting:
    enabled: true
    requests_per_minute: 60
  
  input_validation:
    enabled: true
    max_length: 10000
    forbidden_patterns:
      - "ignore.*instructions"
      - "system:"
```

---

### 8. 监控配置

```yaml
# monitoring_config.yaml
monitoring:
  prometheus:
    enabled: true
    port: 9090
    metrics_prefix: "agent"
  
  grafana:
    enabled: true
    port: 3000
    dashboards:
      - "agent_dashboard.json"
  
  alerts:
    enabled: true
    rules:
      - name: "HighErrorRate"
        expr: "rate(agent_errors_total[5m]) > 0.1"
        severity: "critical"
      
      - name: "HighLatency"
        expr: "histogram_quantile(0.95, agent_request_latency_seconds) > 5"
        severity: "warning"
```

---

### 9. 缓存配置

```yaml
# cache_config.yaml
cache:
  enabled: true
  type: "redis"
  
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: null
  
  ttl:
    default: 3600
    short_term: 300
    long_term: 86400
  
  memory:
    enabled: true
    max_size: 1000
  
  compression:
    enabled: true
    threshold: 1024
```

---

### 10. 数据库配置

```yaml
# database_config.yaml
database:
  type: "postgresql"
  
  connection:
    host: "localhost"
    port: 5432
    database: "agent_db"
    user: "agent"
    password: "password"
  
  pool:
    min_connections: 5
    max_connections: 20
    timeout: 30
  
  migrations:
    enabled: true
    directory: "./migrations"
  
  backup:
    enabled: true
    schedule: "0 2 * * *"
    retention_days: 30
```

---

## 📊 配置分类

| 类别 | 配置数 | 用途 |
|------|--------|------|
| **环境变量** | 10 | 基础配置 |
| **应用配置** | 5 | Agent 配置 |
| **容器化** | 2 | Docker/K8s |
| **监控** | 3 | Prometheus/Grafana |
| **安全** | 5 | 安全设置 |
| **其他** | 5 | 日志/缓存/数据库 |

---

## 🎯 使用指南

1. ✅ 复制模板到项目
2. ✅ 修改为实际值
3. ✅ 验证配置正确性
4. ✅ 加密敏感信息
5. ✅ 测试配置

---

**生成时间**: 2026-03-27 18:10 GMT+8
