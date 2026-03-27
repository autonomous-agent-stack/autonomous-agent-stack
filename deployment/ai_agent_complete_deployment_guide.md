# AI Agent 完整部署指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:35
> **部署方式**: 6 种

---

## 🚀 部署架构

### 架构选型

| 方案 | 适用场景 | 复杂度 | 成本 | 可用性 |
|------|---------|--------|------|--------|
| **单机 Docker** | 开发/测试 | ⭐ | $10/月 | 95% |
| **Docker Compose** | 小型生产 | ⭐⭐ | $50/月 | 99% |
| **Kubernetes** | 中型生产 | ⭐⭐⭐ | $200/月 | 99.9% |
| **Serverless** | 不定期使用 | ⭐⭐ | 按需 | 99.9% |
| **Hybrid** | 大型生产 | ⭐⭐⭐⭐ | $500+/月 | 99.99% |
| **Multi-Region** | 全球化 | ⭐⭐⭐⭐⭐ | $1000+/月 | 99.999% |

---

## 🐳 Docker 部署

### 1. Dockerfile

```dockerfile
# 使用多阶段构建
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

### 2. 构建镜像

```bash
# 构建镜像
docker build -t ai-agent:v1.0 .

# 优化镜像大小
docker build --squash -t ai-agent:v1.0 .

# 扫描漏洞
trivy image ai-agent:v1.0
```

---

### 3. 运行容器

```bash
# 基础运行
docker run -d \
  --name ai-agent \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-xxx \
  ai-agent:v1.0

# 带配置文件
docker run -d \
  --name ai-agent \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -e OPENAI_API_KEY=sk-xxx \
  ai-agent:v1.0

# 带资源限制
docker run -d \
  --name ai-agent \
  -p 8000:8000 \
  --memory="2g" \
  --cpus="2.0" \
  -e OPENAI_API_KEY=sk-xxx \
  ai-agent:v1.0
```

---

## 🐙 Docker Compose 部署

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    image: ai-agent:v1.0
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/aiagent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
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

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

---

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 扩展服务
docker-compose up -d --scale app=3

# 停止服务
docker-compose down
```

---

## ☸️ Kubernetes 部署

### 1. Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-agent
```

---

### 2. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-agent-config
  namespace: ai-agent
data:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/aiagent"
  REDIS_URL: "redis://redis:6379/0"
  LOG_LEVEL: "INFO"
```

---

### 3. Secret

```yaml
# secret.yaml
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
```

---

### 4. Deployment

```yaml
# deployment.yaml
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

### 5. Service

```yaml
# service.yaml
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

### 6. Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-agent-ingress
  namespace: ai-agent
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.aiagent.com
    secretName: ai-agent-tls
  rules:
  - host: api.aiagent.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-agent
            port:
              number: 80
```

---

### 7. HPA (Horizontal Pod Autoscaler)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-agent-hpa
  namespace: ai-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-agent
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

### 8. 部署命令

```bash
# 创建命名空间
kubectl apply -f namespace.yaml

# 部署所有资源
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# 查看状态
kubectl get pods -n ai-agent
kubectl get services -n ai-agent
kubectl get ingress -n ai-agent

# 查看日志
kubectl logs -f deployment/ai-agent -n ai-agent

# 扩展副本
kubectl scale deployment ai-agent --replicas=5 -n ai-agent
```

---

## ☁️ 云服务部署

### AWS ECS

```yaml
# task-definition.json
{
  "family": "ai-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "ai-agent",
      "image": "ai-agent:v1.0",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

---

### Google Cloud Run

```bash
# 部署到 Cloud Run
gcloud run deploy ai-agent \
  --image gcr.io/PROJECT_ID/ai-agent:v1.0 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars LOG_LEVEL=INFO \
  --set-secrets OPENAI_API_KEY=openai-key:latest \
  --memory 4Gi \
  --cpu 2 \
  --max-instances 10
```

---

### Azure Container Instances

```bash
# 部署到 Azure
az container create \
  --resource-group myResourceGroup \
  --name ai-agent \
  --image ai-agent:v1.0 \
  --dns-name-label ai-agent \
  --ports 8000 \
  --environment-variables LOG_LEVEL=INFO \
  --secure-environment-variables OPENAI_API_KEY=sk-xxx \
  --cpu 2 \
  --memory 4
```

---

## 📊 监控部署

### Prometheus

```yaml
# prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'ai-agent'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            regex: ai-agent
            action: keep
```

---

### Grafana

```yaml
# grafana.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: admin
```

---

## 🔒 安全加固

### 网络策略

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-agent-network-policy
spec:
  podSelector:
    matchLabels:
      app: ai-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

---

## 🚀 CI/CD 流程

### GitHub Actions

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

## 📝 部署清单

### 部署前检查
- [ ] 代码审查完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 配置文件准备就绪
- [ ] 密钥管理配置
- [ ] 监控配置完成

### 部署后验证
- [ ] 健康检查通过
- [ ] 功能测试通过
- [ ] 性能指标正常
- [ ] 日志正常输出
- [ ] 监控告警正常
- [ ] 备份策略就绪
- [ ] 回滚方案准备

---

**生成时间**: 2026-03-27 22:40 GMT+8
