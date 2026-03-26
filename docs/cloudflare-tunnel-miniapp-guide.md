# Cloudflare Tunnel + Telegram Mini App（Mac）

目标：在手机端保留现有 VPN 的同时，通过 Cloudflare Tunnel 安全访问 `127.0.0.1:8000` 面板，并在 Telegram `/status` 里直接打开 Mini App。

## 1) 一次性初始化

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 安装并登录 Cloudflare
brew install cloudflared
cloudflared tunnel login

# 复制环境模板
cp migration/openclaw/templates/openclaw-to-autoresearch.env.example migration/openclaw/.env.local

# 创建命名 Tunnel、绑定 DNS、生成 config、回填 .env.local
bash migration/openclaw/scripts/setup-cloudflared-tunnel.sh panel.malu.com
```

## 2) 启动服务

```bash
# 启动 API
bash migration/openclaw/scripts/start-api-daemon.sh

# 启动 Tunnel（会优先使用命名 Tunnel 配置）
bash migration/openclaw/scripts/start-cloudflared-tunnel.sh

# 配置 Telegram webhook（自动读取 WEBHOOK_BASE_URL / CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL）
bash migration/openclaw/scripts/configure-telegram-webhook.sh
```

## 3) 验证

```bash
bash migration/openclaw/scripts/status-api-daemon.sh
bash migration/openclaw/scripts/status-cloudflared-tunnel.sh
```

然后在 Telegram 给机器人发 `/status`：
- 会返回状态摘要 + 魔法链接
- 若设置了 `AUTORESEARCH_TELEGRAM_MINI_APP_URL`，消息里会带 “打开面板（Mini App）” 按钮

## 4) 关键环境变量

`migration/openclaw/.env.local` 中至少确认：

```bash
AUTORESEARCH_PANEL_JWT_SECRET=...
AUTORESEARCH_TELEGRAM_ALLOWED_UIDS=你的TelegramUID
AUTORESEARCH_TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_BOT_TOKEN=123456:ABC...
CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL=https://panel.malu.com
AUTORESEARCH_PANEL_BASE_URL=https://panel.malu.com/api/v1/panel/view
AUTORESEARCH_TELEGRAM_MINI_APP_URL=https://panel.malu.com/api/v1/panel/view
```
