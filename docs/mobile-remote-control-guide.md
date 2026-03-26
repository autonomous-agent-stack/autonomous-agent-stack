# 📱 手机端远程操控指南

> 适用场景：外出时只有手机，需要远程操控 M1 Mac 底座
> 前提条件：M1 Mac 已开机且联网

---

## 🚨 当前状态（2026-03-26 10:17）

**服务运行状态**：
- ✅ uvicorn 进程运行中（PID 66551，端口 8000）
- ✅ API 服务正常（healthz 返回 {"status":"ok"}）
- ⚠️ Telegram Bot Token 未配置（需从 OpenClaw 配置获取）

---

## 📋 手机端操作方案

### 方案 A：远程 SSH 配置（5 分钟）

**前提条件**：
- ✅ M1 Mac 已开启 SSH 服务
- ✅ 手机已安装 SSH 客户端（Termius / Blink Shell）
- ✅ 已配置 Tailscale 或在同一局域网

**操作步骤**：

#### Step 1：SSH 连接

```bash
# 使用 Termius 或 Blink Shell
# 连接到您的 M1 Mac

# 如果在同一局域网
ssh iCloud_GZ@<M1的局域网IP>

# 如果使用 Tailscale
ssh iCloud_GZ@<Tailscale IP>
```

#### Step 2：获取 Bot Token

```bash
# 从 OpenClaw 配置中读取
cat ~/.openclaw/openclaw.json | jq '.channels[] | select(.type == "telegram") | .token'
```

#### Step 3：配置 .env

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 备份原文件
cp .env .env.backup

# 编辑 .env
nano .env

# 找到并修改这行
# TELEGRAM_BOT_TOKEN=<粘贴您的Token>
```

#### Step 4：重启服务

```bash
# 杀掉旧进程
pkill uvicorn

# 启动新进程
cd /Volumes/PS1008/Github/autonomous-agent-stack
nohup uvicorn src.autoresearch.api.main:app --host 0.0.0.0 --port 8000 &

# 验证
curl http://127.0.0.1:8000/healthz
```

#### Step 5：测试

- 在 Telegram 群组发送 `/status`
- 检查 Topic 1 (#General) 是否收到镜像

---

### 方案 B：直接使用 OpenClaw（立即可用）

**如果您已配置 OpenClaw**：

1. **OpenClaw 已有完整的 Telegram Bot 功能**
2. **可以直接使用 OpenClaw 与底座交互**

**操作方式**：
- 直接在 Telegram 群组中与 OpenClaw 对话
- OpenClaw 会自动路由到底座 API

**优势**：
- ✅ 无需额外配置
- ✅ 立即可用
- ✅ 功能完整

---

## 🎯 推荐方案

### 如果您有 SSH 访问权限：

**执行方案 A**（5 分钟）
- ✅ 完全控制底座
- ✅ 独立运行
- ✅ 可定制化

---

### 如果您已配置 OpenClaw：

**直接使用 OpenClaw**（即时）
- ✅ 无需配置
- ✅ 功能完整
- ✅ 已有 Bot Token

---

### 如果两者都没有：

**等待回家后配置**（今晚）
- ✅ 安全可靠
- ✅ 从容配置

---

## 📊 功能对比

| 方案 | 配置时间 | 功能完整度 | 推荐度 |
|------|---------|-----------|--------|
| **方案 A（SSH）** | 5 分钟 | 100% | ⭐⭐⭐⭐⭐ |
| **方案 B（OpenClaw）** | 0 分钟 | 100% | ⭐⭐⭐⭐⭐ |
| **等待回家** | - | 0% | ⭐⭐⭐ |

---

## 💡 我的建议

**如果您有 OpenClaw**：
→ **直接使用 OpenClaw**（最快）

**如果您有 SSH 访问**：
→ **执行方案 A**（完全控制）

**如果都没有**：
→ **等待回家配置**（最安全）

---

**当前状态**：⚠️ 部分运行（API ✅，Bot ❌）
**推荐方案**：方案 B（OpenClaw）或 方案 A（SSH）
**预计时间**：0-5 分钟

---

**创建时间**：2026-03-26 10:17
