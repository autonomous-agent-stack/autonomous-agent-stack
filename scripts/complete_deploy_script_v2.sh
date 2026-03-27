# AI Agent 完整部署脚本 2.0

> **版本**: v2.0
> **更新时间**: 2026-03-27 14:25
> **脚本数**: 10+

---

## 🚀 完整部署脚本

```bash
#!/bin/bash
# complete_deploy.sh - 完整部署脚本

set -e

# 1. 检查环境
check_environment() {
    echo "🔍 检查环境..."
    
    # 检查 Python
    python3 --version
    
    # 检查 Docker
    docker --version
    
    # 检查 Git
    git --version
    
    echo "✅ 环境检查完成"
}

# 2. 安装依赖
install_dependencies() {
    echo "📦 安装依赖..."
    
    pip install -r requirements.txt
    
    echo "✅ 依赖安装完成"
}

# 3. 配置环境
configure_environment() {
    echo "⚙️ 配置环境..."
    
    # 复制配置文件
    cp config/.env.example .env
    
    # 生成密钥
    python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env
    
    echo "✅ 环境配置完成"
}

# 4. 运行测试
run_tests() {
    echo "🧪 运行测试..."
    
    pytest tests/ -v
    
    echo "✅ 测试通过"
}

# 5. 构建镜像
build_image() {
    echo "🏗️ 构建 Docker 镜像..."
    
    docker build -t agent:v1.0 .
    
    echo "✅ 镜像构建完成"
}

# 6. 部署
deploy() {
    echo "🚀 部署..."
    
    # Kubernetes
    kubectl apply -f k8s/
    
    # 验证
    kubectl get pods
    
    echo "✅ 部署完成"
}

# 7. 健康检查
health_check() {
    echo "🏥 健康检查..."
    
    # 等待服务启动
    sleep 30
    
    # 检查健康
    curl -f http://localhost:8000/health
    
    echo "✅ 健康检查通过"
}

# 8. 监控
setup_monitoring() {
    echo "📊 设置监控..."
    
    # Prometheus
    kubectl apply -f monitoring/
    
    echo "✅ 监控设置完成"
}

# 9. 备份
setup_backup() {
    echo "💾 设置备份..."
    
    # 配置定时备份
    echo "0 2 * * * /app/scripts/backup.sh" | crontab -
    
    echo "✅ 备份设置完成"
}

# 10. 日志
setup_logging() {
    echo "📝 设置日志..."
    
    # 创建日志目录
    mkdir -p /var/log/agent
    
    echo "✅ 日志设置完成"
}

# 主函数
main() {
    echo "🚀 开始完整部署..."
    
    check_environment
    install_dependencies
    configure_environment
    run_tests
    build_image
    deploy
    health_check
    setup_monitoring
    setup_backup
    setup_logging
    
    echo "🎉 部署完成！"
}

# 执行
main "$@"
```

---

## 📊 脚本特性

| 特性 | 支持 | 说明 |
|------|------|------|
| **环境检查** | ✅ | 自动检测 |
| **依赖安装** | ✅ | 一键安装 |
| **配置生成** | ✅ | 自动生成 |
| **测试运行** | ✅ | 自动化测试 |
| **镜像构建** | ✅ | Docker 支持 |
| **部署验证** | ✅ | 健康检查 |
| **监控设置** | ✅ | Prometheus |
| **备份配置** | ✅ | 定时备份 |
| **日志管理** | ✅ | 集中日志 |

---

**生成时间**: 2026-03-27 14:26 GMT+8
