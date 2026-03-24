# Kubernetes 部署方案

## 📋 方案概述

**适用场景：**
- 大规模生产环境（> 10000 用户）
- 高可用性要求
- 自动扩缩容需求
- 多租户环境
- 复杂微服务架构

**优势：**
- ✅ 自动扩缩容
- ✅ 自愈能力
- ✅ 滚动更新
- ✅ 服务发现
- ✅ 配置管理
- ✅ 存储编排

**限制：**
- ⚠️ 复杂度高
- ⚠️ 学习曲线陡
- ⚠️ 运维成本高
- ⚠️ 需要专业团队

---

## 🏗️ 集群架构

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Control Plane"
            API[API Server]
            Scheduler[Scheduler]
            CM[Controller Manager]
            DNS[CoreDNS]
        end
        
        subgraph "Node 1"
            Kubelet1[Kubelet]
            Proxy1[Kube Proxy]
            Pod1[App Pod]
            Pod2[Nginx Pod]
        end
        
        subgraph "Node 2"
            Kubelet2[Kubelet]
            Proxy2[Kube Proxy]
            Pod3[App Pod]
            Pod4[Worker Pod]
        end
        
        subgraph "Node 3 - GPU"
            Kubelet3[Kubelet]
            Proxy3[Kube Proxy]
            Pod5[Model Pod]
        end
        
        subgraph "Storage"
            PV1[(PV: PostgreSQL)]
            PV2[(PV: Redis)]
            PV3[(PV: Models)]
        end
    end
    
    Ingress[Ingress Controller] --> API
    User[用户] --> Ingress
    
    API --> Scheduler
    Scheduler --> Kubelet1
    Scheduler --> Kubelet2
    Scheduler --> Kubelet3
    
    Pod1 --> PV1
    Pod2 --> PV2
    Pod5 --> PV3
    
    style API fill:#FF5722
    style Scheduler fill:#FF9800
    style Pod5 fill:#9C27B0
```

---

## 📦 部署配置

### 1. Namespace 配置

```yaml
# k8s/00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-system
  labels:
    name: ai-system
    environment: production

---
# ConfigMap for application config
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: ai-system
data:
  DJANGO_SETTINGS_MODULE: "config.settings"
  DEBUG: "False"
  ALLOWED_HOSTS: "ai.example.com"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379/0"
  
---
# Secret for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: ai-system
type: Opaque
stringData:
  POSTGRES_PASSWORD: "your_secure_password"
  SECRET_KEY: "your_django_secret_key"
  REDIS_PASSWORD: "your_redis_password"
```

### 2. PostgreSQL 部署

```yaml
# k8s/10-postgres.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: ai-system
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: ai-system
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          value: "ai_system"
        - name: POSTGRES_USER
          value: "ai_user"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: POSTGRES_PASSWORD
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - sh
            - -c
            - pg_isready -U ai_user -d ai_system
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - pg_isready -U ai_user -d ai_system
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: ai-system
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None
```

### 3. Redis 部署

```yaml
# k8s/20-redis.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: ai-system
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: ai-system
spec:
  serviceName: redis-service
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --requirepass
        - $(REDIS_PASSWORD)
        ports:
        - containerPort: 6379
          name: redis
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: REDIS_PASSWORD
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: ai-system
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
```

### 4. 应用部署

```yaml
# k8s/30-app.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: ai-system
data:
  DATABASE_URL: "postgresql://ai_user:$(POSTGRES_PASSWORD)@postgres-service:5432/ai_system"
  REDIS_URL: "redis://:$(REDIS_PASSWORD)@redis-service:6379/0"

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: media-pvc
  namespace: ai-system
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: nfs-storage

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-app
  namespace: ai-system
  labels:
    app: ai-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: ai-app
  template:
    metadata:
      labels:
        app: ai-app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      initContainers:
      - name: migrate
        image: ai-app:latest
        command: ["python", "manage.py", "migrate", "--noinput"]
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DATABASE_URL
      containers:
      - name: app
        image: ai-app:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: REDIS_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: SECRET_KEY
        volumeMounts:
        - name: media-storage
          mountPath: /app/media
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: media-storage
        persistentVolumeClaim:
          claimName: media-pvc
      - name: tmp
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: app-service
  namespace: ai-system
spec:
  selector:
    app: ai-app
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP

---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-app-hpa
  namespace: ai-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-app
  minReplicas: 3
  maxReplicas: 20
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

### 5. Model Service 部署

```yaml
# k8s/40-model.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-pvc
  namespace: ai-system
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 200Gi
  storageClassName: fast-ssd

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-service
  namespace: ai-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: model-service
  template:
    metadata:
      labels:
        app: model-service
    spec:
      containers:
      - name: model
        image: vllm/vllm-openai:latest
        command:
        - --model
        - Qwen/Qwen2-7B-Instruct
        - --host
        - 0.0.0.0
        - --port
        - "8001"
        - --tensor-parallel-size
        - "1"
        - --gpu-memory-utilization
        - "0.9"
        - --max-model-len
        - "4096"
        ports:
        - containerPort: 8001
          name: http
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache
        resources:
          requests:
            memory: "8Gi"
            cpu: "4000m"
            nvidia.com/gpu: "1"
          limits:
            memory: "16Gi"
            cpu: "8000m"
            nvidia.com/gpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 120
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 60
          periodSeconds: 10
      nodeSelector:
        gpu: "true"
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule

---
apiVersion: v1
kind: Service
metadata:
  name: model-service
  namespace: ai-system
spec:
  selector:
    app: model-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

### 6. Ingress 配置

```yaml
# k8s/50-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-ingress
  namespace: ai-system
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/limit-rps: "50"
spec:
  tls:
  - hosts:
    - ai.example.com
    secretName: ai-tls
  rules:
  - host: ai.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
```

---

## 🚀 部署脚本

### 1. 初始化脚本

```bash
#!/bin/bash
# scripts/k8s-deploy.sh

set -e

NAMESPACE="ai-system"

echo "🚀 Deploying AI System to Kubernetes..."

# 创建命名空间
echo "📁 Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 应用配置
echo "⚙️  Applying configurations..."
kubectl apply -f k8s/00-namespace.yaml

# 等待 PostgreSQL 就绪
echo "⏳ Waiting for PostgreSQL..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s

# 等待 Redis 就绪
echo "⏳ Waiting for Redis..."
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

# 部署应用
echo "📦 Deploying application..."
kubectl apply -f k8s/30-app.yaml

# 部署模型服务
echo "🤖 Deploying model service..."
kubectl apply -f k8s/40-model.yaml

# 部署 Ingress
echo "🌐 Configuring ingress..."
kubectl apply -f k8s/50-ingress.yaml

# 检查部署状态
echo "✅ Checking deployment status..."
kubectl get all -n $NAMESPACE

echo "🎉 Deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "  - Application: https://ai.example.com"
echo "  - API: https://ai.example.com/api/v1/"
echo "  - Admin: https://ai.example.com/admin"
```

### 2. 更新脚本

```bash
#!/bin/bash
# scripts/k8s-update.sh

set -e

NAMESPACE="ai-system"
IMAGE_TAG=$1

if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG=$(git rev-parse --short HEAD)
fi

echo "🔄 Updating application to version: $IMAGE_TAG"

# 更新应用镜像
kubectl set image deployment/ai-app \
    app=ai-app:$IMAGE_TAG \
    -n $NAMESPACE

# 等待滚动更新完成
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/ai-app -n $NAMESPACE

echo "✅ Update completed!"
```

---

## 📊 监控配置

### 1. Prometheus ServiceMonitor

```yaml
# k8s/60-monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ai-app-monitor
  namespace: ai-system
spec:
  selector:
    matchLabels:
      app: ai-app
  endpoints:
  - port: http
    path: /metrics
    interval: 15s

---
# Grafana Dashboard ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard
  namespace: ai-system
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "AI System Dashboard",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "rate(http_requests_total[5m])"
              }
            ]
          },
          {
            "title": "Error Rate",
            "targets": [
              {
                "expr": "rate(http_errors_total[5m])"
              }
            ]
          },
          {
            "title": "Response Time",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, http_request_duration_seconds)"
              }
            ]
          }
        ]
      }
    }
```

### 2. 日志收集

```yaml
# k8s/70-logging.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: ai-system
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>

    <match **>
      @type elasticsearch
      host elasticsearch-service
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

---

## 🧪 测试方案

### 1. 集成测试

```bash
#!/bin/bash
# scripts/k8s-test.sh

NAMESPACE="ai-system"

echo "🧪 Running Kubernetes tests..."

# 测试 Pod 状态
echo "Checking Pod status..."
kubectl get pods -n $NAMESPACE

# 测试服务连通性
echo "Testing service connectivity..."
kubectl run test-pod --rm -it --image=busybox -n $NAMESPACE --restart=Never -- \
    wget -O- http://app-service:80/health

# 测试数据库连接
kubectl run test-db --rm -it --image=postgres:15-alpine -n $NAMESPACE --restart=Never -- \
    psql postgres://ai_user:password@postgres-service:5432/ai_system -c "SELECT 1;"

echo "✅ All tests passed!"
```

### 2. 性能测试

```python
# scripts/k8s-load-test.py
import requests
import time
from concurrent.futures import ThreadPoolExecutor

SERVICE_URL = "http://ai.example.com"

def test_endpoint(endpoint):
    start = time.time()
    try:
        response = requests.get(f"{SERVICE_URL}{endpoint}", timeout=30)
        return {
            'endpoint': endpoint,
            'status': response.status_code,
            'time': time.time() - start,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {
            'endpoint': endpoint,
            'error': str(e),
            'time': time.time() - start,
            'success': False
        }

endpoints = ['/health', '/api/v1/status', '/api/v1/models']

with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(test_endpoint, endpoints * 100))

success_rate = sum(1 for r in results if r['success']) / len(results)
avg_time = sum(r['time'] for r in results) / len(results)

print(f"Success Rate: {success_rate:.2%}")
print(f"Average Response Time: {avg_time:.2f}s")
```

---

## 🔄 回滚方案

### 1. 快速回滚

```bash
#!/bin/bash
# scripts/k8s-rollback.sh

NAMESPACE="ai-system"
DEPLOYMENT=$1
VERSION=$2

if [ -z "$DEPLOYMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./k8s-rollback.sh <deployment> <version>"
    exit 1
fi

echo "🔄 Rolling back $DEPLOYMENT to version $VERSION..."

kubectl rollout undo deployment/$DEPLOYMENT \
    -n $NAMESPACE \
    --to-revision=$VERSION

echo "⏳ Waiting for rollback to complete..."
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE

echo "✅ Rollback completed!"
```

### 2. 紧急回滚

```bash
# 立即回滚到上一个版本
kubectl rollout undo deployment/ai-app -n ai-system

# 查看回滚历史
kubectl rollout history deployment/ai-app -n ai-system
```

---

## 🎯 最佳实践

### 1. 资源配额

```yaml
# k8s/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: ai-system
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
```

### 2. 网络策略

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-system-policy
  namespace: ai-system
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

### 3. Pod 中断预算

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ai-app-pdb
  namespace: ai-system
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: ai-app
```

---

## 📚 相关文档

- [容器化部署方案](./02-container-deployment.md)
- [云服务部署方案](./04-cloud-deployment.md)
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
