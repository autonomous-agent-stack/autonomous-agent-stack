# Nightly OpenClaw Runbook - 夜间无人值守运行手册

**版本**: 1.0  
**创建时间**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent

---

## 📋 执行摘要

### 使用场景

本手册适用于**夜间无人值守**场景，支持以下任务：
- 自动化工作流执行
- 定时任务调度
- 异常监控与告警
- 自动回滚与恢复

### 前置条件

- ✅ GraphEngine 已部署（`src/orchestrator/`）
- ✅ Docker 运行环境
- ✅ 日志系统已配置（`src/orchestrator/structured_logger.py`）
- ✅ 监控告警通道（推荐：Telegram Bot 或 Lark/Feishu）

---

## 🚀 快速启动

### 方式一：单次执行（测试用）

```bash
# 进入工作目录
cd /Users/iCloud_GZ/github_GZ/openclaw-memory

# 激活虚拟环境（如有）
source venv/bin/activate  # 或使用 poetry/uv

# 执行单次任务
python3 -c "
from src.orchestrator.graph_engine import GraphEngine, GraphNode, NodeType

engine = GraphEngine('nightly_task')

engine.add_node(GraphNode(
    id='task_001',
    type=NodeType.EXECUTOR,
    handler=lambda inputs: {'status': 'completed'}
))

results = engine.execute()
print(f'结果: {results}')
"
```

### 方式二：定时执行（生产用）

```bash
# 使用 cron 定时执行（每天凌晨 2 点）
# 编辑 crontab
crontab -e

# 添加以下行
0 2 * * * cd /Users/iCloud_GZ/github_GZ/openclaw-memory && python3 scripts/nightly_run.py >> logs/nightly.log 2>&1
```

### 方式三：守护进程（推荐）

```bash
# 使用 systemd（Linux）
sudo nano /etc/systemd/system/openclaw-nightly.service

# 内容：
[Unit]
Description=OpenClaw Nightly Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/Users/iCloud_GZ/github_GZ/openclaw-memory
ExecStart=/usr/bin/python3 scripts/nightly_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl enable openclaw-nightly
sudo systemctl start openclaw-nightly
sudo systemctl status openclaw-nightly
```

---

## 📊 状态监控

### 实时监控

```bash
# 监控日志输出
tail -f logs/nightly.log

# 监控特定节点
tail -f logs/nightly.log | grep "node_id:fetch_data"

# 监控错误
tail -f logs/nightly.log | grep "ERROR"
```

### 检查执行状态

```bash
# 查看最新执行日志
ls -lt logs/ | head -5

# 查看执行统计
python3 -c "
import json
with open('logs/nightly_stats.json', 'r') as f:
    stats = json.load(f)
    print(f'总执行: {stats[\"total_executions\"]}')
    print(f'成功: {stats[\"completed\"]}')
    print(f'失败: {stats[\"failed\"]}')
    print(f'成功率: {stats[\"success_rate\"]*100:.1f}%')
"
```

### 健康检查

```bash
# 检查 Docker 是否运行
docker ps

# 检查日志文件是否存在
ls -lh logs/nightly.log

# 检查进程是否存活
ps aux | grep "nightly"
```

---

## 🛑 停止运行

### 优雅停止

```bash
# 如果使用 systemd
sudo systemctl stop openclaw-nightly

# 如果使用 cron
crontab -e
# 注释掉或删除对应的 cron 行

# 如果是手动运行的进程
ps aux | grep "nightly"
kill -TERM <pid>  # 使用 SIGTERM 优雅停止
```

### 强制停止（紧急情况）

```bash
# 如果优雅停止失败
kill -9 <pid>  # 使用 SIGKILL 强制停止

# 清理 Docker 容器
docker ps -a | grep "openclaw" | awk '{print $1}' | xargs docker rm -f
```

---

## 🔄 回滚方案

### 回滚触发条件

以下情况触发自动回滚：
- ❌ 节点执行失败超过 3 次
- ❌ 执行时间超过阈值（默认 30 分钟）
- ❌ 日志中出现 ERROR 级别超过 5 次
- ❌ 关键指标异常（CPU > 90%，内存 > 80%）

### 回滚步骤

#### 步骤 1：停止当前执行

```bash
# 停止服务
sudo systemctl stop openclaw-nightly

# 或者 kill 进程
ps aux | grep "nightly" | grep -v grep | awk '{print $2}' | xargs kill -9
```

#### 步骤 2：回滚到上一个稳定版本

```bash
# 查看最近 10 个提交
git log --oneline -10

# 回滚到上一个稳定提交（例如：a1b2c3d）
git reset --hard a1b2c3d

# 或者创建回滚分支
git checkout -b rollback-$(date +%Y%m%d) a1b2c3d
```

#### 步骤 3：清理临时数据

```bash
# 清理日志
mv logs/nightly.log logs/nightly.log.backup

# 清理 Docker 容器
docker ps -a | grep "openclaw" | awk '{print $1}' | xargs docker rm -f

# 清理临时文件
rm -rf /tmp/openclaw_*
```

#### 步骤 4：恢复服务

```bash
# 重启服务
sudo systemctl start openclaw-nightly

# 验证服务状态
sudo systemctl status openclaw-nightly

# 检查日志
tail -20 logs/nightly.log
```

### 一键回滚脚本

创建 `scripts/rollback.sh`：

```bash
#!/bin/bash
# OpenClaw Nightly Rollback Script

echo "🛑 停止服务..."
sudo systemctl stop openclaw-nightly

echo "📦 回滚代码..."
git reset --hard HEAD~1

echo "🧹 清理临时数据..."
mv logs/nightly.log logs/nightly.log.backup 2>/dev/null
docker ps -a | grep "openclaw" | awk '{print $1}' | xargs docker rm -f

echo "🚀 恢复服务..."
sudo systemctl start openclaw-nightly

echo "✅ 回滚完成"
```

使用：
```bash
chmod +x scripts/rollback.sh
./scripts/rollback.sh
```

---

## 🔍 常见故障排查

### 故障 1：节点执行失败

**症状**：
```
ERROR: node_id:task_001, error: 'KeyError: data'
```

**排查步骤**：
```bash
# 查看完整错误日志
grep -A 10 "node_id:task_001" logs/nightly.log

# 检查节点定义
grep -r "task_001" src/

# 验证输入数据
python3 -c "
from src.orchestrator.graph_engine import GraphEngine
# 加载并验证图定义
"
```

**解决方案**：
- 检查节点依赖是否正确
- 验证输入数据格式
- 增加重试次数

---

### 故障 2：Docker 容器启动失败

**症状**：
```
ERROR: Docker container failed to start
```

**排查步骤**：
```bash
# 检查 Docker 状态
docker ps
docker info

# 查看容器日志
docker logs <container_id>

# 检查镜像是否存在
docker images | grep openclaw
```

**解决方案**：
- 重启 Docker 服务：`sudo systemctl restart docker`
- 重新构建镜像：`docker build -t openclaw/sandbox .`
- 检查 Docker 资源限制

---

### 故障 3：日志文件过大

**症状**：
```
磁盘空间不足
```

**排查步骤**：
```bash
# 检查日志文件大小
du -sh logs/

# 查看最大的日志文件
ls -lhS logs/ | head -5
```

**解决方案**：
```bash
# 压缩旧日志
gzip logs/nightly.log.20260324

# 删除超过 7 天的日志
find logs/ -name "*.log.*" -mtime +7 -delete

# 配置日志轮转（logrotate）
sudo nano /etc/logrotate.d/openclaw-nightly

# 内容：
/path/to/logs/nightly.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 your_username your_group
}
```

---

### 故障 4：内存泄漏

**症状**：
```
系统内存使用持续增长
```

**排查步骤**：
```bash
# 监控内存使用
top -p $(pgrep -f nightly)

# 查看进程详情
ps aux | grep "nightly" | grep -v grep

# 检查对象引用（Python）
python3 -m objgraph
```

**解决方案**：
- 重启服务：`sudo systemctl restart openclaw-nightly`
- 检查代码中的循环引用
- 增加内存限制
- 使用内存分析工具

---

## 📈 性能优化

### 1. 减少日志开销

```python
# 仅在生产环境启用详细日志
import os
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

if DEBUG:
    logger.debug(...)
```

### 2. Docker 容器复用

```python
# 复用现有容器而不是每次创建新容器
synthesizer = ToolSynthesis(reuse_containers=True)
```

### 3. 并发执行（未来）

```python
# 待实现：并发节点执行
engine = GraphEngine("concurrent_task")
engine.add_concurrency_policy(max_concurrent=5)
```

---

## 🔔 告警配置

### 告警规则

```yaml
# alerts/alert_rules.yaml
alerts:
  - name: node_failure
    condition: "error_count > 3"
    severity: critical
    message: "节点执行失败超过 3 次"

  - name: execution_timeout
    condition: "duration_ms > 1800000"  # 30 分钟
    severity: warning
    message: "执行时间超过阈值"

  - name: high_memory
    condition: "memory_usage > 80"
    severity: warning
    message: "内存使用超过 80%"
```

### 告警通知

```python
# 发送告警到 Telegram
import requests

def send_alert(alert: dict):
    webhook_url = "https://api.telegram.org/bot<token>/sendMessage"
    data = {
        "chat_id": "<chat_id>",
        "text": f"🚨 告警: {alert['message']}"
    }
    requests.post(webhook_url, json=data)
```

---

## 📝 维护清单

### 每日检查

- [ ] 检查日志是否有错误
- [ ] 检查执行统计是否正常
- [ ] 检查磁盘空间是否充足

### 每周维护

- [ ] 备份日志文件
- [ ] 清理临时文件
- [ ] 更新依赖包

### 每月维护

- [ ] 性能分析报告
- [ ] 安全审计
- [ ] 容量规划

---

## 🎯 最佳实践

1. **始终使用版本控制**
   - 每次改动前提交
   - 使用语义化版本
   - 保留回滚标签

2. **日志分级记录**
   - DEBUG: 调试信息
   - INFO: 正常操作
   - WARNING: 警告
   - ERROR: 错误

3. **监控关键指标**
   - 执行成功率
   - 平均耗时
   - 错误类型分布

4. **自动化测试**
   - 单元测试覆盖核心逻辑
   - 集成测试覆盖关键路径
   - 定期运行测试套件

---

## 🔗 相关文档

- Parity Matrix: `docs/openclaw-native-parity.md`
- Rollback Plan: `docs/openclaw-rollback-plan.md`
- Structured Logger Report: `docs/E5-logging-implementation-report.md`

---

**最后更新**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent  
**状态**: ✅ 初版完成
