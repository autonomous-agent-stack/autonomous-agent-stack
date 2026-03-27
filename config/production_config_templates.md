# AI Agent 生产级配置模板

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:00
> **配置模板**: 20+

---

## 🔧 基础配置

### 1. OpenClaw 配置

```yaml
# openclaw.yml
version: "1.0"

# 基础配置
app:
  name: "AI Agent"
  version: "1.0.0"
  env: "production"

# LLM 配置
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 4000
  timeout: 30
  
  # 降级策略
  fallback:
    enabled: true
    model: "gpt-3.5-turbo"
    threshold: 0.5  # 错误率 > 50% 时降级

# 记忆配置
memory:
  short_term:
    enabled: true
    max_length: 10  # 最近 10 轮
  
  long_term:
    enabled: true
    provider: "chromadb"
    collection: "agent_memory"
    embedding_model: "text-embedding-ada-002"
    persist_directory: "./data/chroma"

# 工具配置
tools:
  enabled: true
  timeout: 10
  max_retries: 3
  
  # 工具列表
  tools:
    - name: "search"
      enabled: true
      api_key: "${SEARCH_API_KEY}"
    
    - name: "calculator"
      enabled: true
    
    - name: "code_execute"
      enabled: true
      sandbox: true
      timeout: 5

# 监控配置
monitoring:
  enabled: true
  prometheus:
    enabled: true
    port: 9090
  
  logging:
    level: "INFO"
    format: "json"
    file: "./logs/agent.log"
    max_size: "100MB"
    max_backups: 5

# 安全配置
security:
  input_validation:
    enabled: true
    max_length: 10000
  
  rate_limiting:
    enabled: true
    max_requests: 100
    window_seconds: 60
  
  authentication:
    enabled: true
    type: "api_key"
    header: "X-API-Key"

# 成本控制
cost_control:
  enabled: true
  daily_budget: 100  # 美元
  alert_thresholds:
    - 0.5   # 50%
    - 0.8   # 80%
    - 1.0   # 100%
```

---

### 2. Docker 配置

```dockerfile
# Dockerfile
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

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py"]
```

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
      - DATABASE_URL=postgresql://user:pass@db:5432/agent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=agent
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
  
  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

### 3. Kubernetes 配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
  labels:
    app: ai-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-agent
  template:
    metadata:
      labels:
        app: ai-agent
    spec:
      containers:
      - name: agent
        image: ai-agent:v1.0
        ports:
        - containerPort: 8000
        
        # 环境变量
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-key
        
        # 资源限制
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        
        # 健康检查
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
        
        # 卷挂载
        volumeMounts:
        - name: data
          mountPath: /app/data
      
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: agent-pvc

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-agent-service
spec:
  selector:
    app: ai-agent
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-agent
  minReplicas: 2
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

### 4. 监控配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-agent'
    static_configs:
      - targets: ['localhost:8000']
    
    metrics_path: '/metrics'

# 告警规则
rule_files:
  - 'alert_rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
```

```yaml
# grafana/dashboards/agent.json
{
  "dashboard": {
    "title": "AI Agent Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_request_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
          }
        ]
      }
    ]
  }
}
```

---

### 5. 日志配置

```python
# logging_config.py
import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "logs/agent.log",
            "maxBytes": 104857600,  # 100MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

---

### 6. 环境变量

```bash
# .env.production
# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/agent
REDIS_URL=redis://localhost:6379/0

# Vector DB
CHROMA_PERSIST_DIR=./data/chroma

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Security
API_KEY_HEADER=X-API-Key
JWT_SECRET=your-secret-key
ALLOWED_ORIGINS=https://example.com

# Cost Control
DAILY_BUDGET=100
ALERT_EMAIL=admin@example.com
SLACK_WEBHOOK=https://hooks.slack.com/...
```

---

### 7. CI/CD 配置

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
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t ai-agent:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag ai-agent:${{ github.sha }} registry.example.com/ai-agent:${{ github.sha }}
          docker push registry.example.com/ai-agent:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/ai-agent \
            ai-agent=registry.example.com/ai-agent:${{ github.sha }}
          
          kubectl rollout status deployment/ai-agent
```

---

## 📋 配置清单

### 开发环境
- [ ] .env.development 配置
- [ ] Docker Compose 配置
- [ ] 本地数据库配置
- [ ] 日志级别 DEBUG

### 测试环境
- [ ] .env.staging 配置
- [ ] 测试数据库配置
- [ ] 监控配置
- [ ] CI/CD 配置

### 生产环境
- [ ] .env.production 配置
- [ ] 生产数据库配置
- [ ] 完整监控配置
- [ ] 安全加固配置
- [ ] 备份配置

---

**生成时间**: 2026-03-27 14:05 GMT+8
