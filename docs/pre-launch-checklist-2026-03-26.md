# 🚀 "合龙"前准备清单

> **执行时间**：2026-03-26 09:47 GMT+8
> **目标**：启动全链路压测

---

## ✅ 已完成步骤

### 1. Kill 旧进程 ✅

```bash
# 已 kill 端口 8000 和 8001 的进程
pkill -f "uvicorn.*8000"
pkill -f "uvicorn.*8001"
```

---

### 2. 重启服务（端口 8001）✅

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
nohup .venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &

# 验证健康检查
curl http://127.0.0.1:8001/health
# 期望响应：{"status": "ok"}
```

---

## 🔧 待完成步骤

### 1. 获取 Topic ID（物理对齐）

```bash
# 在 Telegram 群组中：
# 1. 点击话题（如"市场营销"）
# 2. 发送测试消息
# 3. 右键消息 → 复制链接
# 4. 链接格式：https://t.me/c/1234567890/2
#                                           ↑ 这就是 Topic ID
```

### 2. 更新 .env 文件

```bash
# 编辑 .env
nano /Volumes/PS1008/Github/autonomous-agent-stack/.env

# 更新为实际的 Topic ID
AUTORESEARCH_TOPIC_MARKET=实际ID
AUTORESEARCH_TOPIC_CREATIVE=实际ID
AUTORESEARCH_TOPIC_AUDIT=实际ID
```

---

### 3. 检查 Cloudflare Tunnel

```bash
# 检查是否已启动
ps aux | grep cloudflared

# 如果未启动，启动 Tunnel
cloudflared tunnel --url http://127.0.0.1:8001

# 记录 Tunnel URL（https://xxx.trycloudflare.com）
```

---

### 4. Webhook 预检

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

## 🎯 全链路压测指令

**在 Telegram #General 话题发送**：

```
启动系统自检：请视觉专家解析当前 UI 截图，情报官抓取最新 AI 动态，审计员执行物理清理，并在各自频道汇报。
```

**预期效果**：

| 话题 | 响应 |
|------|------|
| #General | 任务已接收 |
| #审计日志 | [环境防御] 日志，.DS_Store 已清理 |
| #创意内容 | UI 截图结构化分析 |
| #市场营销 | AI 行业趋势 JSON |

---

## 🔧 故障排查

### 服务未启动？

```bash
# 检查日志
tail -f /tmp/autoresearch_8001.log

# 检查端口
lsof -i :8001
```

### Webhook 失败？

```bash
# 删除旧 Webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"

# 重新设置
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${TUNNEL_URL}/api/v1/gateway/telegram/webhook\"}"
```

---

## 📊 状态检查

- [x] Kill 旧进程（8000, 8001）
- [x] 重启服务（端口 8001）
- [ ] 健康检查通过（`/health`）
- [ ] 获取 Topic ID（物理对齐）
- [ ] 更新 .env 文件
- [ ] Cloudflare Tunnel 启动
- [ ] Webhook 预检（访问 `/docs`）
- [ ] 设置 Webhook
- [ ] 全链路压测

---

**准备时间**：2026-03-26 09:47 GMT+8
**下一步**：等待健康检查通过，然后获取 Topic ID
