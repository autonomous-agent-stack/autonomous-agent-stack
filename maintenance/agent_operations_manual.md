# AI Agent 完整运维手册

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:15
> **运维场景**: 50+

---

## 🛠️ 日常运维

### 1. 健康检查

```bash
# 检查服务状态
./scripts/health-check.sh

# 检查数据库
psql -h localhost -U user -d agent -c "SELECT 1"

# 检查 Redis
redis-cli ping

# 检查向量数据库
curl -X GET http://localhost:8000/api/v1/health
```

### 2. 日志查看

```bash
# 实时日志
tail -f /var/log/agent/app.log

# 错误日志
grep "ERROR" /var/log/agent/app.log | tail -100

# 性能日志
grep "PERF" /var/log/agent/app.log | tail -100

# 按时间过滤
awk '/2026-03-27 14:/' /var/log/agent/app.log
```

### 3. 监控检查

```bash
# 检查 Prometheus
curl http://localhost:9090/-/healthy

# 检查 Grafana
curl http://localhost:3000/api/health

# 查看指标
curl http://localhost:9090/api/v1/query?query=up

# 查看告警
curl http://告警.com:9090/api/v1/alerts
```

---

## 🚨 故障处理

### 场景 1: 服务无响应

**诊断**:
```bash
# 1. 检查进程
ps aux | grep agent

# 2. 检查端口
netstat -tulpn | grep 8000

# 3. 检查日志
tail -100 /var/log/agent/app.log

# 4. 检查资源
top
df -h
```

**解决**:
```bash
# 1. 重启服务
systemctl restart agent

# 2. 检查依赖
systemctl status postgresql
systemctl status redis

# 3. 清理资源
docker system prune -f

# 4. 扩容
kubectl scale deployment/agent --replicas=5
```

---

### 场景 2: 性能下降

**诊断**:
```bash
# 1. 检查响应时间
curl -w "@curl-format.txt" http://localhost:8000/health

# 2. 检查资源
top
free -h
iostat -x 1

# 3. 检查数据库
psql -c "SELECT * FROM pg_stat_activity"

# 4. 检查缓存
redis-cli info memory
```

**解决**:
```bash
# 1. 清理缓存
redis-cli FLUSHALL

# 2. 优化数据库
psql -c "VACUUM ANALYZE"

# 3. 重启服务
systemctl restart agent

# 4. 扩容
kubectl scale deployment/agent --replicas=5
```

---

### 场景 3: 成本超标

**诊断**:
```bash
# 1. 查看成本
curl http://localhost:9090/api/v1/query?query=agent_cost_total

# 2. 查看调用次数
curl http://localhost:9090/api/v1/query?query=agent_calls_total

# 3. 查看模型使用
curl http://localhost:9090/api/v1/query?query=agent_model_usage

# 4. 查看预算
curl http://localhost:9090/api/v1/query?query=agent_budget_usage
```

**解决**:
```bash
# 1. 启用缓存
export ENABLE_CACHE=true

# 2. 降级模型
export DEFAULT_MODEL=gpt-3.5-turbo

# 3. 限制并发
export MAX_CONCURRENT=5

# 4. 调整预算
export DAILY_BUDGET=50
```

---

### 场景 4: 数据库连接失败

**诊断**:
```bash
# 1. 检查数据库
systemctl status postgresql

# 2. 检查连接
psql -h localhost -U user -d agent -c "SELECT 1"

# 3. 检查连接池
psql -c "SELECT count(*) FROM pg_stat_activity"

# 4. 检查日志
tail -100 /var/log/postgresql/postgresql-15-main.log
```

**解决**:
```bash
# 1. 重启数据库
systemctl restart postgresql

# 2. 增加连接池
export DB_POOL_SIZE=20

# 3. 清理连接
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle'"

# 4. 优化配置
vim /etc/postgresql/15/main/postgresql.conf
```

---

### 场景 5: 内存泄漏

**诊断**:
```bash
# 1. 监控内存
top -p $(pgrep -f agent)

# 2. 查看堆内存
jmap -heap $(pgrep -f agent)

# 3. 堆转储
jmap -dump:format=b,file=heap.hprof $(pgrep -f agent)

# 4. 分析
jhat heap.hprof
```

**解决**:
```bash
# 1. 重启服务
systemctl restart agent

# 2. 限制内存
ulimit -v 4194304

# 3. 优化代码
# - 清理大对象
# - 释放资源
# - 使用弱引用

# 4. 增加监控
export MEMORY_LIMIT=4G
```

---

## 🔄 扩容操作

### 1. 手动扩容

```bash
# Kubernetes
kubectl scale deployment/agent --replicas=10

# Docker Compose
docker-compose up -d --scale agent=10

# 手动启动
python main.py &
```

### 2. 自动扩容

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent
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
```

---

## 📊 性能调优

### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_user_id ON users(user_id);
CREATE INDEX idx_created_at ON logs(created_at);

-- 分析表
ANalyze;

-- 清理
VACUUM FULL;

-- 重新索引
REINDEX DATABASE agent;
```

### 2. 缓存优化

```bash
# 清理缓存
redis-cli FLUSHALL

# 调整配置
redis-cli CONFIG SET maxmemory 4gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 监控
redis-cli INFO memory
```

### 3. 网络优化

```bash
# 调整 TCP 参数
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=8192

# 优化 Nginx
vim /etc/nginx/nginx.conf
# worker_processes auto;
# worker_connections 4096;
```

---

## 🛡️ 安全维护

### 1. 定期更新

```bash
# 更新系统
apt-get update && apt-get upgrade

# 更新依赖
pip install --upgrade -r requirements.txt

# 更新 Docker
docker-compose pull
docker-compose up -d
```

### 2. 证书更新

```bash
# 更新 SSL 证书
certbot renew

# 重启服务
systemctl reload nginx
```

### 3. 密钥轮换

```bash
# 生成新密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新配置
vim /etc/agent/config.yml

# 重启服务
systemctl restart agent
```

---

## 📝 运维清单

### 日常检查（每天）
- [ ] 检查服务状态
- [ ] 检查错误日志
- [ ] 检查性能指标
- [ ] 检查成本

### 周常检查（每周）
- [ ] 检查备份
- [ ] 检查证书
- [ ] 检查依赖更新
- [ ] 检查安全漏洞

### 月常检查（每月）
- [ ] 容量规划
- [ ] 成本优化
- **安全审计**
- **性能评估**

---

**生成时间**: 2026-03-27 14:20 GMT+8
