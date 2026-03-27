# 工具集

> OpenClaw 相关工具、脚本和自动化工具集

---

## 📋 目录

- [部署工具](#部署工具)
- [监控工具](#监控工具)
- [数据处理](#数据处理)
- [自动化工具](#自动化工具)

---

## 🚀 部署工具

### 1. 一键部署脚本

```bash
#!/bin/bash
# deploy.sh

set -e

# 配置
APP_NAME="openclaw"
ENVIRONMENT="production"
VERSION="latest"

# 颜色输出
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 开始部署 $APP_NAME...${NC}"

# 1. 拉取最新代码
echo "📦 拉取最新代码..."
git pull origin main

# 2. 安装依赖
echo "📚 安装依赖..."
npm ci --production

# 3. 构建
echo "🔨 构建应用..."
npm run build

# 4. 运行测试
echo "🧪 运行测试..."
npm test

# 5. 部署
echo "🚀 部署到 $ENVIRONMENT..."
docker build -t $APP_NAME:$VERSION .
docker push registry/$APP_NAME:$VERSION

kubectl set image deployment/$APP_NAME \
  $APP_NAME=registry/$APP_NAME:$VERSION \
  --namespace $ENVIRONMENT

echo -e "${GREEN}✅ 部署完成！${NC}"
```

### 2. 回滚脚本

```bash
#!/bin/bash
# rollback.sh

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "用法: ./rollback.sh <version>"
  exit 1
fi

echo "🔄 回滚到版本 $VERSION..."

kubectl rollout undo deployment/$APP_NAME \
  --to-revision=$VERSION \
  --namespace production

echo "✅ 回滚完成！"
```

---

## 📊 监控工具

### 1. 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

# 检查服务
check_service() {
  local service=$1
  local url=$2
  
  response=$(curl -s -o /dev/null -w "%{http_code}" $url)
  
  if [ $response -eq 200 ]; then
    echo "✅ $service: 正常"
  else
    echo "❌ $service: 异常 (HTTP $response)"
    # 发送告警
    send_alert "$service is down"
  fi
}

# 发送告警
send_alert() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$message\"}" \
    $SLACK_WEBHOOK_URL
}

# 执行检查
check_service "API" "https://api.example.com/health"
check_service "Web" "https://example.com/health"
check_service "Database" "https://db.example.com/health"
```

### 2. 性能监控脚本

```bash
#!/bin/bash
# monitor_performance.sh

# CPU 监控
monitor_cpu() {
  cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
  echo "CPU: $cpu_usage%"
  
  if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    send_alert "CPU 使用率过高: $cpu_usage%"
  fi
}

# 内存监控
monitor_memory() {
  mem_usage=$(free -m | awk 'NR==2{print $3/$2*100}')
  echo "内存: $mem_usage%"
  
  if (( $(echo "$mem_usage > 80" | bc -l) )); then
    send_alert "内存使用率过高: $mem_usage%"
  fi
}

# 磁盘监控
monitor_disk() {
  disk_usage=$(df -h | awk '$NF=="/"{print $5}' | sed 's/%//')
  echo "磁盘: $disk_usage%"
  
  if [ $disk_usage -gt 90 ]; then
    send_alert "磁盘使用率过高: $disk_usage%"
  fi
}

# 执行监控
while true; do
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  echo "系统监控 $(date '+%Y-%m-%d %H:%M:%S')"
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  monitor_cpu
  monitor_memory
  monitor_disk
  echo ""
  sleep 60
done
```

---

## 🔄 数据处理

### 1. 数据迁移脚本

```python
#!/usr/bin/env python3
# migrate_data.py

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data():
    """数据迁移"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host="localhost",
            database="mydb",
            user="user",
            password="password"
        )
        
        cursor = conn.cursor()
        
        # 执行迁移
        logger.info("开始数据迁移...")
        
        # 1. 创建新表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_new (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # 2. 迁移数据
        cursor.execute("""
            INSERT INTO users_new (id, name, email, created_at)
            SELECT id, name, email, created_at FROM users
        """)
        
        # 3. 重命名表
        cursor.execute("ALTER TABLE users RENAME TO users_old")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # 提交事务
        conn.commit()
        
        logger.info("✅ 数据迁移完成！")
        
    except Exception as e:
        logger.error(f"❌ 数据迁移失败: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_data()
```

### 2. 数据备份脚本

```bash
#!/bin/bash
# backup_data.sh

# 配置
DB_NAME="mydb"
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
echo "📦 开始备份 $DB_NAME..."
pg_dump $DB_NAME > $BACKUP_FILE

# 压缩
gzip $BACKUP_FILE

# 上传到 S3
aws s3 cp ${BACKUP_FILE}.gz s3://my-backups/

# 清理旧备份（保留 7 天）
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "✅ 备份完成: ${BACKUP_FILE}.gz"
```

---

## 🤖 自动化工具

### 1. 自动化测试

```bash
#!/bin/bash
# auto_test.sh

# 运行单元测试
npm run test:unit

# 运行集成测试
npm run test:integration

# 运行 E2E 测试
npm run test:e2e

# 生成覆盖率报告
npm run test:coverage

# 上传到 Codecov
bash <(curl -s https://codecov.io/bash)
```

### 2. 自动化部署

```yaml
# .github/workflows/auto-deploy.yml
name: Auto Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Dependencies
        run: npm ci
      
      - name: Run Tests
        run: npm test
      
      - name: Build
        run: npm run build
      
      - name: Deploy to Production
        run: ./deploy.sh production
```

### 3. 自动化文档生成

```bash
#!/bin/bash
# generate_docs.sh

# 生成 API 文档
npm run docs:api

# 生成代码文档
npm run docs:code

# 生成架构图
npm run docs:architecture

# 部署到 GitHub Pages
npm run docs:deploy
```

---

## 📊 工具对比

### 部署工具

| 工具 | 类型 | 特点 |
|------|------|------|
| **Docker** | 容器化 | 标准化部署 |
| **Kubernetes** | 容器编排 | 自动扩展 |
| **Terraform** | 基础设施即代码 | 云无关 |
| **Ansible** | 配置管理 | 简单易用 |

### 监控工具

| 工具 | 类型 | 特点 |
|------|------|------|
| **Prometheus** | 指标收集 | 开源 |
| **Grafana** | 可视化 | 美观 |
| **ELK Stack** | 日志管理 | 功能强大 |
| **Datadog** | APM | 企业级 |

---

## 📚 学习资源

### 官方文档

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform Documentation](https://www.terraform.io/docs)

### 最佳实践

- [The Twelve-Factor App](https://12factor.net/)
- [DevOps Best Practices](https://www.atlassian.com/devops)
- [SRE Handbook](https://sre.google/sre-book/)

---

<div align="center">
  <p>🛠️ 工欲善其事，必先利其器！</p>
</div>
