# OpenClaw Rollback Plan - 回滚方案与应急响应

**版本**: 1.0  
**创建时间**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent

---

## 📋 执行摘要

### 回滚目标

本方案用于应对以下紧急情况：
- 部署失败导致服务不可用
- 数据损坏或丢失
- 性能严重退化
- 安全漏洞被利用

### 回滚原则

1. **数据优先**: 保护数据完整性
2. **最小停机**: 快速恢复服务
3. **可追溯**: 记录所有回滚操作
4. **可验证**: 回滚后必须验证服务正常

---

## 🚨 回滚触发条件

### 自动触发（严重）

- ❌ **服务完全不可用**: 5 分钟内连续 10 次失败
- ❌ **数据损坏**: 关键数据验证失败
- ❌ **安全漏洞**: 检测到未授权访问
- ❌ **严重性能退化**: 响应时间 > 10 秒，持续 5 分钟

### 手动触发（运维人员判断）

- ⚠️ **执行成功率下降**: 从 95% 降至 80% 以下
- ⚠️ **内存泄漏**: 内存使用持续增长超过阈值
- ⚠️ **异常日志激增**: ERROR 日志 > 100 条/小时
- ⚠️ **用户投诉**: 收到 > 5 个严重投诉

---

## 🔄 回滚策略

### 策略一：代码回滚（最快，5-10 分钟）

**适用场景**：
- 新代码引入 Bug
- 配置错误
- 逻辑错误

**回滚步骤**：

```bash
# 1. 停止服务
sudo systemctl stop openclaw-nightly

# 2. 查看最近提交
git log --oneline -10

# 3. 回滚到上一个稳定提交（例如：a1b2c3d）
git reset --hard a1b2c3d

# 4. 恢复服务
sudo systemctl start openclaw-nightly

# 5. 验证服务
sudo systemctl status openclaw-nightly
tail -20 logs/nightly.log
```

**验证清单**：
- [ ] 服务状态正常
- [ ] 日志无 ERROR
- [ ] 执行一个测试任务成功
- [ ] 监控指标恢复到正常水平

---

### 策略二：数据回滚（中等，10-30 分钟）

**适用场景**：
- 数据损坏
- 错误的数据库迁移
- 误删除

**回滚步骤**：

```bash
# 1. 停止服务
sudo systemctl stop openclaw-nightly

# 2. 备份当前数据（以防万一）
cp -r /data/openclaw /data/openclaw.backup.$(date +%Y%m%d%H%M%S)

# 3. 恢复到上一个备份
cp -r /backups/openclaw/20260325020000/* /data/openclaw/

# 4. 验证数据完整性
python3 -c "
import json
with open('/data/openclaw/session_state.json', 'r') as f:
    data = json.load(f)
    assert 'sessions' in data
    print('数据验证通过')
"

# 5. 恢复服务
sudo systemctl start openclaw-nightly
```

**验证清单**：
- [ ] 数据完整性检查通过
- [ ] 服务正常启动
- [ ] 执行一个测试任务
- [ ] 数据与备份一致

---

### 策略三：配置回滚（快速，5 分钟）

**适用场景**：
- 配置文件错误
- 环境变量错误
- 权限设置错误

**回滚步骤**：

```bash
# 1. 备份当前配置
cp .env .env.backup.$(date +%Y%m%d%H%M%S)

# 2. 恢复到上一个配置
cp .env.prev .env

# 3. 重新加载配置
sudo systemctl daemon-reload
sudo systemctl restart openclaw-nightly

# 4. 验证配置
systemctl show openclaw-nightly | grep Environment
```

**验证清单**：
- [ ] 配置加载正确
- [ ] 服务正常启动
- [ ] 日志无配置错误
- [ ] 功能正常

---

### 策略四：完整回滚（最慢，30-60 分钟）

**适用场景**：
- 多个组件同时故障
- 无法确定故障原因
- 前面三种策略都失败

**回滚步骤**：

```bash
# 1. 停止所有服务
sudo systemctl stop openclaw-nightly
sudo systemctl stop openclaw-api

# 2. 回滚代码
git reset --hard <stable_commit>

# 3. 恢复数据
cp -r /backups/openclaw/20260325020000/* /data/openclaw/

# 4. 恢复配置
cp .env.prev .env

# 5. 重新构建 Docker 镜像
docker-compose build --no-cache

# 6. 启动所有服务
sudo systemctl start openclaw-nightly
sudo systemctl start openclaw-api

# 7. 完整验证
./scripts/health_check.sh
```

**验证清单**：
- [ ] 所有服务正常
- [ ] 数据完整性检查通过
- [ ] 配置加载正确
- [ ] 功能测试通过
- [ ] 监控指标正常

---

## 🛠️ 回滚工具

### 一键回滚脚本

创建 `scripts/emergency_rollback.sh`：

```bash
#!/bin/bash
# OpenClaw Emergency Rollback Script

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚨 OpenClaw Emergency Rollback${NC}"
echo "================================"

# 参数检查
if [ $# -lt 1 ]; then
    echo -e "${RED}错误: 请指定回滚策略${NC}"
    echo "用法: $0 <strategy> [commit_id]"
    echo "策略: code, data, config, full"
    exit 1
fi

STRATEGY=$1
COMMIT_ID=${2:-HEAD~1}

echo "回滚策略: $STRATEGY"
echo "回滚目标: $COMMIT_ID"
echo ""

# 确认
read -p "确认回滚? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "取消回滚"
    exit 0
fi

# 执行回滚
case $STRATEGY in
    code)
        echo -e "${YELLOW}🔄 执行代码回滚...${NC}"
        sudo systemctl stop openclaw-nightly
        git reset --hard $COMMIT_ID
        sudo systemctl start openclaw-nightly
        echo -e "${GREEN}✅ 代码回滚完成${NC}"
        ;;
    data)
        echo -e "${YELLOW}🔄 执行数据回滚...${NC}"
        sudo systemctl stop openclaw-nightly
        LATEST_BACKUP=$(ls -t /backups/openclaw/ | head -1)
        cp -r /backups/openclaw/$LATEST_BACKUP/* /data/openclaw/
        sudo systemctl start openclaw-nightly
        echo -e "${GREEN}✅ 数据回滚完成${NC}"
        ;;
    config)
        echo -e "${YELLOW}🔄 执行配置回滚...${NC}"
        cp .env.prev .env
        sudo systemctl daemon-reload
        sudo systemctl restart openclaw-nightly
        echo -e "${GREEN}✅ 配置回滚完成${NC}"
        ;;
    full)
        echo -e "${YELLOW}🔄 执行完整回滚...${NC}"
        sudo systemctl stop openclaw-nightly
        git reset --hard $COMMIT_ID
        LATEST_BACKUP=$(ls -t /backups/openclaw/ | head -1)
        cp -r /backups/openclaw/$LATEST_BACKUP/* /data/openclaw/
        cp .env.prev .env
        sudo systemctl daemon-reload
        sudo systemctl start openclaw-nightly
        echo -e "${GREEN}✅ 完整回滚完成${NC}"
        ;;
    *)
        echo -e "${RED}错误: 未知策略 $STRATEGY${NC}"
        exit 1
        ;;
esac

# 验证
echo ""
echo -e "${YELLOW}🔍 验证服务状态...${NC}"
sleep 5
sudo systemctl status openclaw-nightly --no-pager

echo ""
echo -e "${GREEN}✅ 回滚完成，请检查服务是否正常${NC}"
```

使用：
```bash
chmod +x scripts/emergency_rollback.sh

# 代码回滚
./scripts/emergency_rollback.sh code a1b2c3d

# 数据回滚
./scripts/emergency_rollback.sh data

# 配置回滚
./scripts/emergency_rollback.sh config

# 完整回滚
./scripts/emergency_rollback.sh full a1b2c3d
```

---

## 📊 回滚监控

### 回滚指标

```python
# monitoring/rollback_metrics.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RollbackMetrics:
    rollback_id: str
    strategy: str
    timestamp: datetime
    duration_seconds: int
    success: bool
    rollback_from: str
    rollback_to: str
    data_restored: bool
    services_restarted: list
    verification_passed: bool

    def to_dict(self):
        return {
            "rollback_id": self.rollback_id,
            "strategy": self.strategy,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "rollback_from": self.rollback_from,
            "rollback_to": self.rollback_to,
            "data_restored": self.data_restored,
            "services_restarted": self.services_restarted,
            "verification_passed": self.verification_passed
        }
```

### 回滚日志

```json
{
  "rollback_id": "rollback-20260326-001",
  "strategy": "code",
  "timestamp": "2026-03-26T01:30:00Z",
  "duration_seconds": 120,
  "success": true,
  "rollback_from": "d4e5f6g",
  "rollback_to": "a1b2c3d",
  "data_restored": false,
  "services_restarted": ["openclaw-nightly"],
  "verification_passed": true
}
```

---

## 🧪 回滚后验证

### 健康检查脚本

创建 `scripts/health_check.sh`：

```bash
#!/bin/bash
# OpenClaw Health Check Script

echo "🔍 OpenClaw Health Check"
echo "========================"

# 1. 检查服务状态
echo "1. 检查服务状态..."
if systemctl is-active --quiet openclaw-nightly; then
    echo "✅ openclaw-nightly: running"
else
    echo "❌ openclaw-nightly: not running"
    exit 1
fi

# 2. 检查日志错误
echo "2. 检查日志错误..."
ERROR_COUNT=$(tail -100 logs/nightly.log | grep -c "ERROR" || echo 0)
if [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ 无错误日志"
else
    echo "❌ 发现 $ERROR_COUNT 个错误"
    tail -20 logs/nightly.log | grep "ERROR"
fi

# 3. 检查数据完整性
echo "3. 检查数据完整性..."
python3 -c "
import json
try:
    with open('/data/openclaw/session_state.json', 'r') as f:
        data = json.load(f)
        if 'sessions' in data:
            print('✅ 数据完整性检查通过')
        else:
            print('❌ 数据完整性检查失败')
            exit(1)
except Exception as e:
    print(f'❌ 数据完整性检查失败: {e}')
    exit(1)
"

# 4. 检查 Docker 容器
echo "4. 检查 Docker 容器..."
DOCKER_COUNT=$(docker ps | grep -c "openclaw" || echo 0)
if [ $DOCKER_COUNT -gt 0 ]; then
    echo "✅ Docker 容器运行正常"
else
    echo "❌ 无 Docker 容器运行"
fi

# 5. 检查资源使用
echo "5. 检查资源使用..."
MEMORY_USAGE=$(ps aux | grep -E "openclaw-nightly" | grep -v grep | awk '{sum+=$4} END {print sum}')
if [ $(echo "$MEMORY_USAGE < 80" | bc -l) -eq 1 ]; then
    echo "✅ 内存使用: ${MEMORY_USAGE}%"
else
    echo "⚠️ 内存使用过高: ${MEMORY_USAGE}%"
fi

echo ""
echo "✅ 健康检查完成"
```

使用：
```bash
chmod +x scripts/health_check.sh
./scripts/health_check.sh
```

---

## 📞 应急联系

### 紧急联系人

| 角色 | 姓名 | 联系方式 | 响应时间 |
|------|------|----------|----------|
| 主要负责人 | 大佬 | Telegram/Lark | 5 分钟 |
| 技术负责人 | - | - | 15 分钟 |
| 运维负责人 | - | - | 30 分钟 |

### 告警通知

```python
# 发送紧急告警
def send_emergency_alert(message: str):
    """发送紧急告警到多个渠道"""
    # 1. 发送到 Lark/Feishu
    requests.post(
        "https://open.feishu.cn/open-apis/bot/v2/hook/<webhook>",
        json={"msg_type": "text", "content": {"text": message}}
    )
    
    # 2. 发送到 Telegram
    requests.post(
        f"https://api.telegram.org/bot<token>/sendMessage",
        json={"chat_id": "<chat_id>", "text": f"🚨 {message}"}
    )
    
    # 3. 发送邮件
    send_email("紧急告警", message)
```

---

## 📝 回滚记录

### 回滚报告模板

```markdown
# 回滚报告 - YYYY-MM-DD HH:MM

## 回滚信息

- **回滚 ID**: rollback-20260326-001
- **回滚策略**: code
- **回滚时间**: 2026-03-26 01:30:00
- **回滚时长**: 120 秒
- **回滚原因**: 节点执行失败率过高（从 95% 降至 60%）

## 回滚操作

- **从版本**: d4e5f6g
- **到版本**: a1b2c3d
- **代码变更**: 回滚 2 个提交
- **数据恢复**: 无
- **配置变更**: 无

## 验证结果

- [x] 服务状态正常
- [x] 日志无错误
- [x] 数据完整性检查通过
- [x] 测试任务执行成功

## 影响评估

- **停机时间**: 2 分钟
- **数据丢失**: 无
- **用户影响**: 轻微（夜间低峰期）
- **后续措施**: 分析失败原因，修复后重新部署

## 回顾

**问题原因**:
- 节点依赖配置错误，导致 DAG 拓扑排序失败
- 错误的重试策略，导致无限重试

**改进措施**:
- 增加节点依赖验证测试
- 优化重试策略，增加最大重试次数限制
- 部署前执行完整的集成测试

**责任人**: glm-4.7-5 Subagent
**审批人**: 大佬
```

---

## 🔗 相关文档

- Nightly Runbook: `docs/nightly-openclaw-runbook.md`
- Parity Matrix: `docs/openclaw-native-parity.md`
- Structured Logger Report: `docs/E5-logging-implementation-report.md`

---

**最后更新**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent  
**状态**: ✅ 初版完成
