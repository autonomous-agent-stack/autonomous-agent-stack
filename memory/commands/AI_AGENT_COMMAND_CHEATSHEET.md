# AI Agent 完整命令速查表

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:15
> **命令数**: 100+

---

## 🛠️ 开发命令

### Python

```bash
# 运行脚本
python agent.py

# 安装依赖
pip install -r requirements.txt

# 虚拟环境
python -m venv venv
source venv/bin/activate

# 测试
pytest tests/

# 类型检查
mypy src/

# 代码格式化
black src/
isort src/

# Lint
flake8 src/
pylint src/
```

### Git

```bash
# 初始化
git init

# 添加文件
git add .

# 提交
git commit -m "feat: add new feature"

# 推送
git push origin main

# 拉取
git pull origin main

# 分支
git checkout -b feature/new-feature

# 合并
git merge feature/new-feature

# 查看日志
git log --oneline

# 回滚
git reset --hard HEAD~1
```

---

## 🐳 Docker

```bash
# 构建镜像
docker build -t agent:v1.0 .

# 运行容器
docker run -p 8000:8000 agent:v1.0

# 查看容器
docker ps

# 查看日志
docker logs <container_id>

# 进入容器
docker exec -it <container_id> /bin/bash

# 停止容器
docker stop <container_id>

# 删除容器
docker rm <container_id>

# 删除镜像
docker rmi agent:v1.0

# 推送镜像
docker push registry.example.com/agent:v1.0
```

---

## ☸️ Kubernetes

```bash
# 查看节点
kubectl get nodes

# 查看 pods
kubectl get pods

# 查看服务
kubectl get services

# 部署
kubectl apply -f deployment.yaml

# 删除
kubectl delete -f deployment.yaml

# 查看日志
kubectl logs <pod_name>

# 进入 pod
kubectl exec -it <pod_name> -- /bin/bash

# 扩容
kubectl scale deployment/agent --replicas=5

# 查看描述
kubectl describe pod <pod_name>

# 查看事件
kubectl get events --sort-by=.metadata.creationTimestamp
```

---

## 📊 监控命令

### Prometheus

```bash
# 查看指标
curl http://localhost:9090/api/v1/query?query=up

# 查看目标
curl http://localhost:9090/api/v1/targets

# 查看告警
curl http://localhost:9090/api/v1/alerts
```

### Grafana

```bash
# 启动
docker run -d -p 3000:3000 grafana/grafana

# 查看仪表板
curl http://localhost:3000/api/dashboards
```

---

## 🔧 调试命令

### 日志

```bash
# 实时日志
tail -f /var/log/agent.log

# 搜索日志
grep "ERROR" /var/log/agent.log

# 按时间过滤
awk '/2026-03-27 14:/' /var/log/agent.log

# 统计错误
grep "ERROR" /var/log/agent.log | wc -l
```

### 网络

```bash
# 检查端口
netstat -tulpn | grep 8000

# 测试连接
curl -I http://localhost:8000/health

# DNS 查询
nslookup api.openai.com

# 抓包
tcpdump -i eth0 port 443
```

### 资源

```bash
# CPU/内存
top
htop

# 磁盘
df -h
du -sh /var/log/*

# 进程
ps aux | grep python

# 网络连接
ss -tulpn
```

---

## 🚀 部署命令

### CI/CD

```bash
# GitHub Actions
gh workflow run deploy.yml

# 查看运行状态
gh run list

# 查看日志
gh run view <run_id>
```

### 云服务

```bash
# AWS
aws ec2 describe-instances

# GCP
gcloud compute instances list

# Azure
az vm list
```

---

## 🔒 安全命令

### 加密

```bash
# 生成密钥
openssl rand -hex 32

# 加密文件
openssl enc -aes-256-cbc -salt -in file.txt -out file.enc

# 解密文件
openssl enc -aes-256-cbc -d -in file.enc -out file.txt
```

### SSL

```bash
# 生成证书
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 查看证书
openssl x509 -in cert.pem -text -noout

# 测试 SSL
openssl s_client -connect api.openai.com:443
```

---

## 📝 文档命令

### Markdown

```bash
# 生成目录
doctoc README.md

# 检查链接
markdown-link-check README.md

# 格式化
prettier --write README.md
```

### API 文档

```bash
# 生成 OpenAPI
python -c "from app import app; print(app.openapi())"

# Swagger UI
docker run -p 8080:8080 -e SWAGGER_JSON=/api/openapi.json -v $(pwd):/api swaggerapi/swagger-ui
```

---

## 🧪 测试命令

### 单元测试

```bash
# 运行测试
pytest tests/

# 带覆盖率
pytest --cov=src tests/

# 并行测试
pytest -n auto tests/

# 详细输出
pytest -v tests/
```

### 压力测试

```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api

# wrk
wrk -t12 -c400 -d30s http://localhost:8000/api

# Locust
locust -f locustfile.py
```

---

## 🎯 常用组合

### 快速启动

```bash
# 一键启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 快速部署

```bash
# 构建 + 推送 + 部署
docker build -t agent:v1.0 . && \
docker push registry.example.com/agent:v1.0 && \
kubectl set image deployment/agent agent=registry.example.com/agent:v1.0
```

### 快速调试

```bash
# 日志 + 监控 + 性能
tail -f /var/log/agent.log & \
curl http://localhost:9090/api/v1/query?query=up & \
top
```

---

**生成时间**: 2026-03-27 14:20 GMT+8
