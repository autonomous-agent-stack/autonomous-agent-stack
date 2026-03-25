# OpenClaw Migration Scaffold

这个目录用于把现有 OpenClaw 逐步接到 `autonomous-agent-stack`，先支持：
- OpenClaw 会话兼容
- Claude Agent 调度
- Telegram 网关接入

## 目录说明

- `templates/openclaw-to-autoresearch.env.example`: 环境变量映射模板
- `requests/openclaw-compat-smoke.sh`: API 样例请求（会话 + agent）
- `scripts/discover-openclaw-data.sh`: 自动探测旧数据位置（sqlite/json）
- `scripts/verify-migration.sh`: 一键验证（环境 + API + 兼容接口）
- `logs/`: 迁移探测与验证日志

## Telegram 机器人令牌写哪里

这个仓库的 Telegram Webhook 校验依赖的是：
- `AUTORESEARCH_TELEGRAM_SECRET_TOKEN`

建议把以下变量写进你本机的 `~/.openclaw/openclaw.json` 对应启动环境，或在启动 `uvicorn` 前 `export`：

- `AUTORESEARCH_TELEGRAM_SECRET_TOKEN`: 对应 Telegram 设置 webhook 时的 `secret_token`
- `TELEGRAM_BOT_TOKEN`: Telegram BotFather 给你的 bot token（建议写在 `migration/openclaw/.env.local`）
- `AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE` (可选): 覆盖 telegram 路由专用 claude 命令
- `AUTORESEARCH_CLAUDE_COMMAND`: 全局 claude 命令（你当前是 `claude`）

注意：
- Bot Token 本身用于你调用 Telegram `setWebhook` API，不直接由当前代码读取。
- 当前代码校验的是请求头 `x-telegram-bot-api-secret-token` 与 `AUTORESEARCH_TELEGRAM_SECRET_TOKEN` 是否一致。

## 快速使用

1. 复制模板并按需修改：

```bash
cp migration/openclaw/templates/openclaw-to-autoresearch.env.example migration/openclaw/.env.local
```

2. 探测旧数据路径：

```bash
bash migration/openclaw/scripts/discover-openclaw-data.sh
```

3. 启动 API（新终端）

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
set -a; source migration/openclaw/.env.local; set +a
uvicorn src.autoresearch.api.main:app --host 127.0.0.1 --port 8000
```

4. 运行一键验证：

```bash
bash migration/openclaw/scripts/verify-migration.sh
```

## 关于 `../openclaw`

你机器上已经存在同级仓库：
- `/Volumes/PS1008/Github/openclaw`

因此不需要重复 clone。若未来要重新拉取，可用：

```bash
cd /Volumes/PS1008/Github
git clone https://github.com/openclaw/openclaw.git openclaw
```

## 常驻运行命令

```bash
# API 常驻
bash migration/openclaw/scripts/start-api-daemon.sh
bash migration/openclaw/scripts/status-api-daemon.sh
bash migration/openclaw/scripts/logs-api-daemon.sh
bash migration/openclaw/scripts/stop-api-daemon.sh

# 公网隧道（cloudflared）
bash migration/openclaw/scripts/start-cloudflared-tunnel.sh
bash migration/openclaw/scripts/stop-cloudflared-tunnel.sh

# 配置 Telegram webhook（优先使用 WEBHOOK_BASE_URL；否则尝试 cloudflared 日志中的 trycloudflare URL）
bash migration/openclaw/scripts/configure-telegram-webhook.sh

# Telegram 长轮询桥接（不依赖 webhook 公网域名）
bash migration/openclaw/scripts/start-telegram-poller.sh
bash migration/openclaw/scripts/status-telegram-poller.sh
bash migration/openclaw/scripts/logs-telegram-poller.sh
bash migration/openclaw/scripts/stop-telegram-poller.sh
```

## 面板查看

1. 在 Telegram 给机器人发送：`/status`（或“状态”）
2. 机器人会返回摘要 + Web 面板 magic link（需配置以下环境变量）：
   - `AUTORESEARCH_PANEL_JWT_SECRET`
   - `AUTORESEARCH_PANEL_BASE_URL`
   - `AUTORESEARCH_TELEGRAM_ALLOWED_UIDS`
3. 默认面板地址为：`http://127.0.0.1:8000/api/v1/panel/view`
