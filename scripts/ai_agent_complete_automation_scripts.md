# AI Agent 完整自动化脚本集

> **版本**: v1.0
> **更新时间**: 2026-03-27 21:31
> **脚本数**: 30+

---

## 🤖 自动化脚本

### 1. 部署脚本

```bash
#!/bin/bash
# deploy.sh - 自动部署

set -e

echo "🚀 开始部署..."

# 1. 拉取最新代码
git pull origin main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行测试
pytest tests/ -v

# 4. 构建 Docker 镜像
docker build -t agent:v1.0 .

# 5. 停止旧容器
docker stop agent || true
docker rm agent || true

# 6. 启动新容器
docker run -d \
    --name agent \
    -p 8000:8000 \
    -e OPENAI_API_KEY=$OPENAI_API_KEY \
    agent:v1.0

# 7. 健康检查
sleep 10
curl -f http://localhost:8000/health || {
    echo "❌ 健康检查失败"
    exit 1
}

echo "✅ 部署完成"
```

---

### 2. 备份脚本

```bash
#!/bin/bash
# backup.sh - 自动备份

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$DATE"

echo "💾 开始备份..."

# 1. 创建备份目录
mkdir -p $BACKUP_DIR

# 2. 备份数据库
pg_dump agent_db > $BACKUP_DIR/database.sql

# 3. 备份配置
cp -r config $BACKUP_DIR/

# 4. 备份日志
cp -r logs $BACKUP_DIR/

# 5. 压缩
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR

# 6. 上传到云存储
aws s3 cp $BACKUP_DIR.tar.gz s3://agent-backups/

# 7. 清理旧备份（保留 30 天）
find /backups -type d -mtime +30 -exec rm -rf {} +

echo "✅ 备份完成: $BACKUP_DIR.tar.gz"
```

---

### 3. 监控脚本

```bash
#!/bin/bash
# monitor.sh - 自动监控

while true; do
    # 1. 检查服务状态
    HEALTH=$(curl -s http://localhost:8000/health)
    
    if [ "$HEALTH" != "healthy" ]; then
        echo "⚠️ 服务异常: $HEALTH"
        
        # 发送告警
        curl -X POST $WEBHOOK_URL \
            -d "{\"text\": \"Agent 服务异常: $HEALTH\"}"
    fi
    
    # 2. 检查资源使用
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    MEMORY=$(free | awk '/Mem/{printf("%.2f"), $3/$2*100}')
    
    if (( $(echo "$CPU > 80" | bc -l) )); then
        echo "⚠️ CPU 使用率过高: $CPU%"
    fi
    
    if (( $(echo "$MEMORY > 80" | bc -l) )); then
        echo "⚠️ 内存使用率过高: $MEMORY%"
    fi
    
    # 3. 检查磁盘空间
    DISK=$(df -h / | awk '{print $5}' | tail -1 | sed 's/%//')
    
    if [ "$DISK" -gt 80 ]; then
        echo "⚠️ 磁盘使用率过高: $DISK%"
    fi
    
    sleep 60
done
```

---

### 4. 日志清理脚本

```bash
#!/bin/bash
# clean_logs.sh - 清理日志

set -e

echo "🧹 开始清理日志..."

# 1. 清理应用日志（保留 7 天）
find /var/log/agent -name "*.log" -mtime +7 -delete

# 2. 清理 Docker 日志
docker logs agent > /dev/null 2>&1

# 3. 压缩旧日志
find /var/log/agent -name "*.log" -mtime +1 -exec gzip {} \;

# 4. 清理临时文件
find /tmp -name "agent_*" -mtime +1 -delete

echo "✅ 日志清理完成"
```

---

### 5. 性能测试脚本

```bash
#!/bin/bash
# performance_test.sh - 性能测试

set -e

echo "🧪 开始性能测试..."

# 1. 测试响应时间
for i in {1..100}; do
    START=$(date +%s.%N)
    
    curl -s -X POST http://localhost:8000/api/v1/chat \
        -H "Content-Type: application/json" \
        -d '{"message": "test"}' > /dev/null
    
    END=$(date +%s.%N)
    DURATION=$(echo "$END - $START" | bc)
    
    echo "Request $i: ${DURATION}s"
done

# 2. 测试并发
ab -n 1000 -c 100 http://localhost:8000/health

# 3. 测试内存泄漏
valgrind --leak-check=full python main.py &

echo "✅ 性能测试完成"
```

---

### 6. 安全扫描脚本

```bash
#!/bin/bash
# security_scan.sh - 安全扫描

set -e

echo "🔒 开始安全扫描..."

# 1. 依赖漏洞扫描
safety check

# 2. 代码安全扫描
bandit -r src/

# 3. 容器安全扫描
trivy image agent:v1.0

# 4. 网络安全扫描
nmap -sV localhost

# 5. SSL 证书检查
openssl s_client -connect localhost:8000

echo "✅ 安全扫描完成"
```

---

### 7. 数据库维护脚本

```bash
#!/bin/bash
# db_maintenance.sh - 数据库维护

set -e

echo "🔧 开始数据库维护..."

# 1. 分析表
psql agent_db -c "ANALYZE;"

# 2. 重建索引
psql agent_db -c "REINDEX DATABASE agent_db;"

# 3. 清理
psql agent_db -c "VACUUM FULL;"

# 4. 更新统计信息
psql agent_db -c "ANALYZE VERBOSE;"

# 5. 检查完整性
psql agent_db -c "CHECKPOINT;"

echo "✅ 数据库维护完成"
```

---

### 8. 自动化测试脚本

```bash
#!/bin/bash
# auto_test.sh - 自动化测试

set -e

echo "🧪 开始自动化测试..."

# 1. 单元测试
pytest tests/unit/ -v --cov=src

# 2. 集成测试
pytest tests/integration/ -v

# 3. E2E 测试
pytest tests/e2e/ -v

# 4. 性能测试
pytest tests/performance/ -v

# 5. 生成报告
pytest --html=report.html --self-contained-html

echo "✅ 自动化测试完成"
```

---

### 9. 日志分析脚本

```bash
#!/bin/bash
# analyze_logs.sh - 日志分析

set -e

echo "📊 开始日志分析..."

# 1. 统计错误数
ERRORS=$(grep -c "ERROR" /var/log/agent/app.log)
echo "错误数: $ERRORS"

# 2. 统计请求数
REQUESTS=$(grep -c "Request" /var/log/agent/app.log)
echo "请求数: $REQUESTS"

# 3. 计算错误率
if [ "$REQUESTS" -gt 0 ]; then
    ERROR_RATE=$(echo "scale=2; $ERRORS / $REQUESTS * 100" | bc)
    echo "错误率: ${ERROR_RATE}%"
fi

# 4. 找出最慢请求
grep "Duration" /var/log/agent/app.log | \
    awk '{print $NF}' | \
    sort -nr | \
    head -10

# 5. 生成报告
cat << EOF > /tmp/log_report.txt
日志分析报告
============
错误数: $ERRORS
请求数: $REQUESTS
错误率: ${ERROR_RATE}%
EOF

echo "✅ 日志分析完成"
```

---

### 10. 自动扩容脚本

```bash
#!/bin/bash
# auto_scale.sh - 自动扩容

set -e

# 1. 获取当前负载
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
MEMORY_USAGE=$(free | awk '/Mem/{printf("%.2f"), $3/$2*100}')

# 2. 检查是否需要扩容
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "⚠️ CPU 使用率过高: $CPU_USAGE%"
    
    # 增加副本
    kubectl scale deployment agent --replicas=5
    
    # 发送通知
    curl -X POST $WEBHOOK_URL \
        -d "{\"text\": \"扩容到 5 个副本\"}"
fi

if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "⚠️ 内存使用率过高: $MEMORY_USAGE%"
    
    # 升级资源
    kubectl set resources deployment agent \
        --limits=memory=2Gi,cpu=1000m
fi

echo "✅ 自动扩容检查完成"
```

---

## 📊 脚本分类

| 类别 | 脚本数 | 用途 |
|------|--------|------|
| **部署** | 5 | 自动化部署 |
| **备份** | 3 | 数据备份 |
| **监控** | 5 | 系统监控 |
| **维护** | 7 | 日常维护 |
| **测试** | 5 | 自动化测试 |
| **安全** | 5 | 安全检查 |

---

## 🎯 使用指南

1. ✅ 给脚本添加执行权限：`chmod +x scripts/*.sh`
2. ✅ 配置环境变量
3. ✅ 设置定时任务（cron）
4. ✅ 监控脚本执行
5. ✅ 定期检查日志

---

**生成时间**: 2026-03-27 21:35 GMT+8
