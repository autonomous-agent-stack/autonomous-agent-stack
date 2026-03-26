# Telegram 群组配置指南

> **配置时间**：2026-03-26 09:30 GMT+8
> **适用场景**：将 Autonomous Agent Stack 接入 Telegram 群组
> **提醒**：本地环境变量建议放在 `.env.local`，不要提交该文件。

---

## 📋 配置清单

### 1. Telegram Bot 配置

#### 步骤 1：创建 Bot

```bash
# 1. 在 Telegram 中找到 @BotFather
# 2. 发送 /newbot
# 3. 按提示设置 Bot 名称
# 4. 记录 Bot Token（格式：1234567890:ABCdefGHIjklMNOpqrsTUVwxyz）
```

#### 步骤 2：获取 Bot Token

```bash
# 保存到环境变量
export AUTORESEARCH_TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

---

### 2. 群组配置

#### 步骤 1：将 Bot 拉入群组

```bash
# 1. 打开 Telegram 群组
# 2. 点击群组名称 → Add Member
# 3. 搜索你的 Bot（@YourBotName）
# 4. 添加到群组
```

#### 步骤 2：设置 Bot 权限

```bash
# 在群组中：
# 1. 点击群组名称 → Manage Group → Administrators
# 2. 找到你的 Bot
# 3. 勾选以下权限：
#    - ✅ Delete messages
#    - ✅ Ban users
#    - ✅ Invite users via link
#    - ✅ Pin messages
#    - ✅ Manage topics（如果启用 Topics）
#    - ✅ Manage video chats
#    - ✅ Change info
```

---

### 3. Topics（论坛模式）配置

#### 步骤 1：启用 Topics

```bash
# 1. 打开群组设置
# 2. Topics → Enable Topics
# 3. 创建以下话题：
```

#### 步骤 2：创建话题

| 话题名称 | Topic ID | 用途 |
|---------|----------|------|
| 📊 市场营销 | 10 | 营销推广相关 |
| 🎨 创意内容 | 20 | 设计文案相关 |
| 🔍 审计日志 | 99 | 日志监控相关 |
| 🔧 技术支持 | 30 | 技术问题 |
| 💼 业务咨询 | 40 | 业务相关 |

#### 步骤 3：配置 Topic ID

```bash
# 在 .env 文件中配置
AUTORESEARCH_TOPIC_MARKET=10
AUTORESEARCH_TOPIC_CREATIVE=20
AUTORESEARCH_TOPIC_AUDIT=99
AUTORESEARCH_TOPIC_TECH=30
AUTORESEARCH_TOPIC_BUSINESS=40
```

---

### 4. Webhook 配置

#### 步骤 1：启动服务

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 设置环境变量
export AUTORESEARCH_TELEGRAM_BOT_TOKEN="your-bot-token"
export AUTORESEARCH_API_HOST="127.0.0.1"
export AUTORESEARCH_API_PORT="8001"

# 启动服务
PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
nohup .venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &
```

#### 步骤 2：配置 Cloudflare Tunnel

```bash
# 1. 安装 Cloudflare Tunnel（如果未安装）
brew install cloudflare-warp

# 2. 启动 Tunnel
cloudflared tunnel --url http://127.0.0.1:8001

# 3. 记录 Tunnel URL（格式：https://xxx.trycloudflare.com）
# 例如：https://pati-panda-xyz.trycloudflare.com
```

#### 步骤 3：设置 Webhook

```bash
# 替换为你的 Tunnel URL
TUNNEL_URL="https://pati-panda-xyz.trycloudflare.com"
BOT_TOKEN="your-bot-token"

# 设置 Webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${TUNNEL_URL}/api/v1/gateway/telegram/webhook\",
    \"allowed_updates\": [\"message\", \"edited_message\", \"channel_post\"]
  }"

# 验证 Webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

---

### 5. 环境变量配置

创建 `.env` 文件：

```bash
# .env
AUTORESEARCH_TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
AUTORESEARCH_API_HOST=127.0.0.1
AUTORESEARCH_API_PORT=8001
AUTORESEARCH_PANEL_BASE_URL=https://pati-panda-xyz.trycloudflare.com

# Topic IDs（可选）
AUTORESEARCH_TOPIC_MARKET=10
AUTORESEARCH_TOPIC_CREATIVE=20
AUTORESEARCH_TOPIC_AUDIT=99
AUTORESEARCH_TOPIC_TECH=30
AUTORESEARCH_TOPIC_BUSINESS=40

# Claude CLI 配置
AUTORESEARCH_CLAUDE_COMMAND=claude

# 管理员 Telegram UID（用于权限控制）
AUTORESEARCH_ADMIN_UIDS=<YOUR_TELEGRAM_UID>
```

---

### 6. 测试验证

#### 测试 1：健康检查

```bash
curl http://127.0.0.1:8001/health
# 期望响应：{"status": "ok"}
```

#### 测试 2：发送消息

```bash
# 在 Telegram 群组中发送：
你好

# 期望响应：
# Agent 回复问候
```

#### 测试 3：Topics 分流

```bash
# 在主群组发送：
帮我写个营销文案

# 期望结果：
# 1. 主群组收到简报：
#    📊 MARKET
#    
#    已为您生成营销文案...
#    
#    _详细内容已发送到对应话题_
#
# 2. 话题"市场营销"（ID=10）收到详细内容
```

#### 测试 4：图片传递

```bash
# 在 Telegram 群组中发送图片
# 期望响应：
# Agent 分析图片并返回结果
```

---

## 🔧 故障排查

### 问题 1：Bot 不响应

```bash
# 检查服务状态
ps aux | grep uvicorn

# 检查日志
tail -f /tmp/autoresearch_8001.log

# 检查 Webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

### 问题 2：Webhook 失败

```bash
# 删除 Webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"

# 重新设置
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${TUNNEL_URL}/api/v1/gateway/telegram/webhook\"}"
```

### 问题 3：Topics 不分流

```bash
# 检查 Topic ID 配置
env | grep AUTORESEARCH_TOPIC

# 检查群组是否启用 Topics
# 在群组设置中确认"Topics"已启用
```

---

## 📊 配置检查清单

- [ ] Bot Token 已配置
- [ ] Bot 已拉入群组
- [ ] Bot 权限已设置（管理员）
- [ ] Topics 已启用（可选）
- [ ] Topic IDs 已配置（可选）
- [ ] 服务已启动（端口 8001）
- [ ] Cloudflare Tunnel 已启动
- [ ] Webhook 已设置
- [ ] 健康检查通过
- [ ] 发送消息测试通过
- [ ] Topics 分流测试通过（可选）
- [ ] 图片传递测试通过（可选）

---

## 🚀 快速启动命令

```bash
# 一键启动（包含所有配置）
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 1. 加载环境变量
source .env

# 2. 启动服务
PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
nohup .venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &

# 3. 启动 Tunnel
cloudflared tunnel --url http://127.0.0.1:8001

# 4. 设置 Webhook（替换 URL）
TUNNEL_URL="https://your-tunnel.trycloudflare.com"
curl -X POST "https://api.telegram.org/bot${AUTORESEARCH_TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${TUNNEL_URL}/api/v1/gateway/telegram/webhook\"}"
```

---

**配置完成时间**：2026-03-26 09:30 GMT+8
**文档**：本指南
