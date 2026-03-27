# AI Agent 配置文件集

> **版本**: v1.0
> **更新时间**: 2026-03-28 00:11
> **配置文件**: 30+

---

## 📝 配置文件模板

### 1. 环境配置

#### .env 模板

```bash
# .env.example
# LLM API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/aiagent
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Features
ENABLE_CACHE=true
ENABLE_MONITORING=true
ENABLE_RATE_LIMITING=true
```

---

### 2. 应用配置

#### config.yaml 模板

```yaml
# config.yaml
app:
  name: AI Agent Service
  version: 1.0.0
  environment: production
  host: 0.0.0.0
  port: 8000

llm:
  default_model: gpt-3.5-turbo
  models:
    - name: gpt-3.5-turbo
      provider: openai
      temperature: 0.7
      max_tokens: 2000
    - name: gpt-4
      provider: openai
      temperature: 0.3
      max_tokens: 4000
    - name: claude-3-opus
      provider: anthropic
      temperature: 0.5
      max_tokens: 4000

database:
  postgresql:
    host: localhost
    port: 5432
    database: aiagent
    user: user
    password: pass
    pool_size: 20
    max_overflow: 10
  
  redis:
    host: localhost
    port: 6379
    db: 0
    password: null
  
  qdrant:
    host: localhost
    port: 6333
    collection: documents

tools:
  - name: search
    enabled: true
    config:
      api_key: ${SEARCH_API_KEY}
  - name: calculator
    enabled: true
  - name: database
    enabled: true
    config:
      connection_string: ${DATABASE_URL}

memory:
  type: hybrid
  short_term:
    type: conversation
    max_tokens: 4000
  long_term:
    type: vector
    collection: memory

monitoring:
  enabled: true
  prometheus:
    enabled: true
    port: 9090
  grafana:
    enabled: true
    port: 3000
  logging:
    level: INFO
    format: json
    output: stdout

security:
  cors:
    enabled: true
    origins:
      - https://example.com
  rate_limiting:
    enabled: true
    requests_per_minute: 100
  authentication:
    enabled: true
    type: jwt
    secret: ${JWT_SECRET}
    expiry: 3600
```

---

### 3. Docker 配置

#### Dockerfile 模板

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 生产镜像
FROM python:3.11-slim

WORKDIR /app

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 复制依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用
COPY --chown=appuser:appuser . .

# 切换用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### docker-compose.yml 模板

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/aiagent
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - db
      - redis
      - qdrant
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=aiagent
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  grafana_data:
```

---

### 4. Kubernetes 配置

#### deployment.yaml 模板

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
  namespace: ai-agent
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
      - name: ai-agent
        image: ai-agent:v1.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ai-agent-config
        - secretRef:
            name: ai-agent-secrets
        resources:
          limits:
            cpu: 2
            memory: 4Gi
          requests:
            cpu: 1
            memory: 2Gi
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

#### service.yaml 模板

```yaml
# kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-agent
  namespace: ai-agent
spec:
  type: LoadBalancer
  selector:
    app: ai-agent
  ports:
  - port: 80
    targetPort: 8000
```

---

#### configmap.yaml 模板

```yaml
# kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-agent-config
  namespace: ai-agent
data:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/aiagent"
  REDIS_URL: "redis://redis:6379/0"
  QDRANT_URL: "http://qdrant:6333"
  LOG_LEVEL: "INFO"
```

---

#### secret.yaml 模板

```yaml
# kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-agent-secrets
  namespace: ai-agent
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-xxx"
  ANTHROPIC_API_KEY: "sk-ant-xxx"
  DATABASE_PASSWORD: "secure_password"
  JWT_SECRET: "your-jwt-secret"
```

---

### 5. 监控配置

#### prometheus.yml 模板

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-agent'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts.yml'
```

---

#### alerts.yml 模板

```yaml
# prometheus/alerts.yml
groups:
  - name: ai-agent-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: Error rate is {{ $value }} per second
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, agent_latency_seconds) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High latency detected
          description: P95 latency is {{ $value }} seconds
      
      - alert: ServiceDown
        expr: up{job="ai-agent"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: Service is down
          description: AI Agent service is down
```

---

### 6. CI/CD 配置

#### .github/workflows/deploy.yml 模板

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
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
        run: pytest tests/ --cov=app --cov-report=xml
      
      - name: Build Docker image
        run: docker build -t ai-agent:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag ai-agent:${{ github.sha }} registry.example.com/ai-agent:${{ github.sha }}
          docker push registry.example.com/ai-agent:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/ai-agent ai-agent=registry.example.com/ai-agent:${{ github.sha }}
          kubectl rollout status deployment/ai-agent
```

---

### 7. 日志配置

#### logging.conf 模板

```ini
# logging.conf
[loggers]
keys=root,ai-agent

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=jsonFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_ai-agent]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=ai-agent
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=jsonFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=DEBUG
formatter=jsonFormatter
args=('/var/log/ai-agent/app.log',)

[formatter_jsonFormatter]
format={"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}
datefmt=%Y-%m-%dT%H:%M:%S
```

---

**生成时间**: 2026-03-28 00:15 GMT+8
