# 离机自动化巡航配置

> 启用时间：2026-03-26 12:08
> 状态：待启动（需用户回家后执行）

---

## 🤖 自动巡航任务

### Topic 4：市场情报自动抓取

**频率**：每 4 小时  
**执行内容**：
- 抓取 Twitter/Reddit/微博 关键词
- 过滤噪音（营销水军）
- 生成情感极性报告
- 投递到 Topic 4

**启动命令**：
```bash
# 在 API 启动时自动加载
curl -X POST http://127.0.0.1:8000/api/cron/start \
  -H "Content-Type: application/json" \
  -d '{"task": "auto_intelligence", "interval": "4h"}'
```

---

### Topic 3：系统安全自动审计

**频率**：每 1 小时  
**执行内容**：
- 清理 AppleDouble 文件
- 记录审计日志
- 投递到 Topic 3

**启动命令**：
```bash
curl -X POST http://127.0.0.1:8000/api/cron/start \
  -H "Content-Type: application/json" \
  -d '{"task": "auto_audit", "interval": "1h"}'
```

---

### Topic 2：视觉分析自动投递

**触发方式**：用户发送图片  
**执行内容**：
- 自动转码为 Base64
- 后台执行质感分析
- 投递到 Topic 2

**无需启动命令**（已集成到 Vision_Gateway）

---

## 📊 巡航监控

### 查看巡航状态

```bash
# 查看所有定时任务
curl http://127.0.0.1:8000/api/cron/status

# 停止特定任务
curl -X POST http://127.0.0.1:8000/api/cron/stop \
  -H "Content-Type: application/json" \
  -d '{"task": "auto_intelligence"}'
```

---

## 🔐 安全配置

### 环境变量

```bash
# .env
AUTO_CRUISE_ENABLED=true
AUTO_CRUISE_INTELLIGENCE_INTERVAL=4h
AUTO_CRUISE_AUDIT_INTERVAL=1h
```

---

## 📱 手机端操作

### 启动巡航（回家后）

```bash
# SSH 连接到 M1 Mac
ssh iCloud_GZ@<M1的IP>

# 启动巡航
cd /Volumes/PS1008/Github/autonomous-agent-stack
python3 -c "
from src.skills.auto_intelligence_cron import AutoIntelligenceCron
from src.security.auto_audit_cron import AutoAuditCron
import asyncio

async def start_cruise():
    intel_cron = AutoIntelligenceCron()
    audit_cron = AutoAuditCron()
    
    await intel_cron.start()
    await audit_cron.start()
    
    print('✅ 自动巡航已启动')

asyncio.run(start_cruise())
"
```

---

**配置状态**：✅ 已准备
**启动方式**：API 启动时自动加载
**监控方式**：Topic 3/4 查看日志

---

**创建时间**：2026-03-26 12:08
