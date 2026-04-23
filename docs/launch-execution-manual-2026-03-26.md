# 🚀 "合龙"执行手册

> **执行时间**：2026-03-26 09:50 GMT+8
> **当前状态**：服务已启动 ✅

---

## ✅ 当前状态

### 1. 服务状态

```bash
✅ 端口 8001：已启动
✅ 健康检查：通过
✅ Cloudflare Tunnel：运行中（PID 72958）
```

### 2. 获取 Tunnel URL

```bash
# 查看 Tunnel URL
cat /tmp/cloudflared_8001.log | grep "trycloudflare.com"

# 示例输出：
# https://pati-panda-xyz.trycloudflare.com
```

---

## 🔧 下一步操作

### 步骤 1：创建 .env 文件

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 复制模板
cp .env.example .env

# 编辑 .env
nano .env

# 填写以下必需项：
# 1. AUTORESEARCH_TELEGRAM_BOT_TOKEN（你的 Bot Token）
# 2. AUTORESEARCH_PANEL_BASE_URL（Tunnel URL）
```

---

### 步骤 2：获取 Topic ID（物理对齐）

**重要**：Topic ID 需要从实际群组获取，不是固定的 10, 20, 99！

#### 操作步骤：

```bash
1. 打开 Telegram 群组
2. 点击话题（如"市场营销"）
3. 发送测试消息
4. 右键消息 → 复制链接
5. 链接格式：https://t.me/c/1234567890/2
                                          ↑ 这就是 Topic ID
6. 更新 .env 中的 AUTORESEARCH_TOPIC_MARKET=实际ID
```

---

### 步骤 3：重启服务（加载 .env）

```bash
# Kill 旧进程
pkill -f "uvicorn.*8001"

# 重新启动（加载 .env）
cd /Volumes/PS1008/Github/autonomous-agent-stack
source .env

PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
.venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &

# 验证
curl http://127.0.0.1:8001/health
```

---

### 步骤 4：Webhook 预检

```bash
# 1. 在浏览器访问（确认服务 Ready）
# https://your-tunnel.trycloudflare.com/docs

# 2. 设置 Webhook
TUNNEL_URL="https://your-tunnel.trycloudflare.com"
BOT_TOKEN="你的Bot Token"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${TUNNEL_URL}/api/v1/gateway/telegram/webhook\",
    \"allowed_updates\": [\"message\", \"edited_message\"]
  }"

# 3. 验证 Webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

---

### 步骤 5：全链路压测

**在 Telegram #General 话题发送**：

```
启动系统自检：请视觉专家解析当前 UI 截图，情报官抓取最新 AI 动态，审计员执行物理清理，并在各自频道汇报。
```

**预期效果**：

| 话题 | 响应 |
|------|------|
| #General | 任务已接收 |
| #审计日志 | [环境防御] 日志 |
| #创意内容 | UI 截图分析 |
| #市场营销 | AI 趋势 JSON |

---

## 📊 检查清单

- [x] Kill 旧进程（8000, 8001）
- [x] 重启服务（端口 8001）
- [x] 健康检查通过
- [ ] 获取 Tunnel URL
- [ ] 创建 .env 文件
- [ ] 获取 Topic ID（物理对齐）
- [ ] 重启服务（加载 .env）
- [ ] Webhook 预检
- [ ] 设置 Webhook
- [ ] 全链路压测

---

## 🔧 快速命令

```bash
# 一键获取 Tunnel URL
cat /tmp/cloudflared_8001.log | grep "trycloudflare.com" | tail -1

# 一键创建 .env
cd /Volumes/PS1008/Github/autonomous-agent-stack
cp .env.example .env
nano .env

# 一键重启服务
pkill -f "uvicorn.*8001"
sleep 2
cd /Volumes/PS1008/Github/autonomous-agent-stack
source .env
PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
.venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &
sleep 3
curl http://127.0.0.1:8001/health
```

---

**准备时间**：2026-03-26 09:50 GMT+8
**当前状态**：等待配置 .env 文件
