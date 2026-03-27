# AI Agent 完整部署脚本集

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:58
> **脚本数**: 15+

---

## 🚀 部署脚本

### 1. 环境初始化脚本

```bash
#!/bin/bash
# init_environment.sh - 初始化环境

set -e

echo "🚀 初始化 AI Agent 环境..."

# 1. 检查系统
check_system() {
    echo "📋 检查系统..."
    
    # Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装"
        exit 1
    fi
    
    # pip
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3 未安装"
        exit 1
    fi
    
    # git
    if ! command -v git &> /dev/null; then
        echo "❌ Git 未安装"
        exit 1
    fi
    
    echo "✅ 系统检查通过"
}

# 2. 创建虚拟环境
create_venv() {
    echo "📦 创建虚拟环境..."
    
    python3 -m venv venv
    source venv/bin/activate
    
    echo "✅ 虚拟环境已激活"
}

# 3. 安装依赖
install_dependencies() {
    echo "📚 安装依赖..."
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ 依赖安装完成"
}

# 4. 配置环境变量
setup_env() {
    echo "⚙️ 配置环境变量..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "📝 请编辑 .env 文件并填入你的 API keys"
        exit 1
    fi
    
    echo "✅ 环境变量已配置"
}

# 5. 运行测试
run_tests() {
    echo "🧪 运行测试..."
    
    pytest tests/ -v
    
    echo "✅ 测试通过"
}

# 主函数
main() {
    check_system
    create_venv
    install_dependencies
    setup_env
    run_tests
    
    echo "🎉 环境初始化完成！"
    echo "运行 'python main.py' 启动服务"
}

main "$@"
```

---

### 2. Docker 部署脚本

```bash
#!/bin/bash
# docker_deploy.sh - Docker 部署

set -e

echo "🐳 Docker 部署..."

# 1. 构建镜像
build_image() {
    echo "🏗️ 构建 Docker 镜像..."
    
    docker build -t agent:v1.0 .
    docker tag agent:v1.0 agent:latest
    
    echo "✅ 镜像构建完成"
}

# 2. 推送镜像
push_image() {
    echo "📤 推送镜像..."
    
    docker tag agent:v1.0 registry.example.com/agent:v1.0
    docker push registry.example.com/agent:v1.0
    
    echo "✅ 镜像已推送"
}

# 3. 运行容器
run_container() {
    echo "🏃 运行容器..."
    
    docker run -d \
        --name agent \
        -p 8000:8000 \
        -e OPENAI_API_KEY=$OPENAI_API_KEY \
        -v $(pwd)/data:/app/data \
        agent:v1.0
    
    echo "✅ 容器已启动"
}

# 4. 健康检查
health_check() {
    echo "🏥 健康检查..."
    
    sleep 10
    
    curl -f http://localhost:8000/health || {
        echo "❌ 健康检查失败"
        docker logs agent
        exit 1
    }
    
    echo "✅ 健康检查通过"
}

# 主函数
main() {
    build_image
    push_image
    run_container
    health_check
    
    echo "🎉 Docker 部署完成！"
}

main "$@"
```

---

### 3. Kubernetes 部署脚本

```bash
#!/bin/bash
# k8s_deploy.sh - Kubernetes 部署

set -e

echo "☸️ Kubernetes 部署..."

# 1. 创建命名空间
create_namespace() {
    echo "📦 创建命名空间..."
    
    kubectl apply -f k8s/namespace.yaml
    
    echo "✅ 命名空间已创建"
}

# 2. 创建 Secrets
create_secrets() {
    echo "🔐 创建 Secrets..."
    
    kubectl create secret generic agent-secrets \
        --from-literal=openai-api-key=$OPENAI_API_KEY \
        --namespace=agent \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo "✅ Secrets 已创建"
}

# 3. 部署应用
deploy_app() {
    echo "🚀 部署应用..."
    
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    
    echo "✅ 应用已部署"
}

# 4. 等待就绪
wait_for_ready() {
    echo "⏳ 等待应用就绪..."
    
    kubectl rollout status deployment/agent \
        --namespace=agent \
        --timeout=300s
    
    echo "✅ 应用已就绪"
}

# 5. 验证部署
verify_deployment() {
    echo "🔍 验证部署..."
    
    # 检查 Pods
    kubectl get pods -n agent
    
    # 检查服务
    kubectl get services -n agent
    
    # 测试访问
    POD=$(kubectl get pods -n agent -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n agent $POD -- curl -f http://localhost:8000/health
    
    echo "✅ 部署验证通过"
}

# 主函数
main() {
    create_namespace
    create_secrets
    deploy_app
    wait_for_ready
    verify_deployment
    
    echo "🎉 Kubernetes 部署完成！"
}

main "$@"
```

---

### 4. 监控配置脚本

```bash
#!/bin/bash
# setup_monitoring.sh - 配置监控

set -e

echo "📊 配置监控..."

# 1. 部署 Prometheus
deploy_prometheus() {
    echo "📈 部署 Prometheus..."
    
    kubectl apply -f monitoring/prometheus.yaml
    
    echo "✅ Prometheus 已部署"
}

# 2. 部署 Grafana
deploy_grafana() {
    echo "📉 部署 Grafana..."
    
    kubectl apply -f monitoring/grafana.yaml
    
    # 导入 Dashboard
    kubectl create configmap grafana-dashboards \
        --from-file=monitoring/dashboards \
        --namespace=monitoring
    
    echo "✅ Grafana 已部署"
}

# 3. 配置告警
setup_alerts() {
    echo "🔔 配置告警..."
    
    kubectl apply -f monitoring/alerts.yaml
    
    echo "✅ 告警已配置"
}

# 4. 验证监控
verify_monitoring() {
    echo "🔍 验证监控..."
    
    # Prometheus
    kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
    sleep 5
    curl -f http://localhost:9090/-/healthy
    kill %1
    
    # Grafana
    kubectl port-forward -n monitoring svc/grafana 3000:3000 &
    sleep 5
    curl -f http://localhost:3000/api/health
    kill %1
    
    echo "✅ 监控验证通过"
}

# 主函数
main() {
    deploy_prometheus
    deploy_grafana
    setup_alerts
    verify_monitoring
    
    echo "🎉 监控配置完成！"
}

main "$@"
```

---

### 5. 日志配置脚本

```bash
#!/bin/bash
# setup_logging.sh - 配置日志

set -e

echo "📝 配置日志..."

# 1. 部署 ELK Stack
deploy_elk() {
    echo "🔍 部署 ELK Stack..."
    
    # Elasticsearch
    kubectl apply -f logging/elasticsearch.yaml
    
    # Logstash
    kubectl apply -f logging/logstash.yaml
    
    # Kibana
    kubectl apply -f logging/kibana.yaml
    
    echo "✅ ELK Stack 已部署"
}

# 2. 配置 Fluentd
setup_fluentd() {
    echo "📊 配置 Fluentd..."
    
    kubectl apply -f logging/fluentd.yaml
    
    echo "✅ Fluentd 已配置"
}

# 3. 创建索引
create_indices() {
    echo "📇 创建索引..."
    
    # 等待 Elasticsearch 就绪
    sleep 30
    
    # 创建索引模板
    curl -X PUT "http://localhost:9200/_template/agent" -H 'Content-Type: application/json' -d'
    {
        "index_patterns": ["agent-*"],
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 1
        }
    }
    '
    
    echo "✅ 索引已创建"
}

# 4. 验证日志
verify_logging() {
    echo "🔍 验证日志..."
    
    # 生成测试日志
    kubectl logs -n agent $(kubectl get pods -n agent -o jsonpath='{.items[0].metadata.name}')
    
    # 检查 Elasticsearch
    curl -f http://localhost:9200/_cluster/health
    
    # 检查 Kibana
    curl -f http://localhost:5601/api/status
    
    echo "✅ 日志验证通过"
}

# 主函数
main() {
    deploy_elk
    setup_fluentd
    create_indices
    verify_logging
    
    echo "🎉 日志配置完成！"
}

main "$@"
```

---

## 📊 脚本分类

| 类别 | 脚本 | 用途 |
|------|------|------|
| **初始化** | init_environment.sh | 环境初始化 |
| **Docker** | docker_deploy.sh | 容器部署 |
| **K8s** | k8s_deploy.sh | K8s 部署 |
| **监控** | setup_monitoring.sh | 监控配置 |
| **日志** | setup_logging.sh | 日志配置 |

---

## 🎯 使用指南

1. ✅ 给脚本添加执行权限：`chmod +x *.sh`
2. ✅ 按顺序执行：init → deploy → monitor
3. ✅ 检查日志：`tail -f /var/log/agent.log`
4. ✅ 验证服务：`curl http://localhost:8000/health`

---

**生成时间**: 2026-03-27 17:01 GMT+8
