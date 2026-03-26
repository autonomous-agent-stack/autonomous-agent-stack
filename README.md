# 🤖 Autonomous Agent Stack

> 一个面向多智能体编排、审计、面板接入与迁移验证的工程化框架。

---

## 项目概览

Autonomous Agent Stack 目前已经把核心链路落到了代码里，重点覆盖以下几类能力：

- 多智能体图编排与 prompt 驱动执行
- OpenClaw / Autoresearch 兼容会话与运行记录
- MCP 工具注册、上下文桥接与动态工具合成
- Docker 沙盒执行与 AppleDouble 清理
- Telegram 网关、面板鉴权与审计
- 静态安全审计、知识图谱与业务红线约束
- 检查点恢复、人机协同拦截与标准 MCP 兼容能力

这份 README 以“仓库里已实现什么”为准，而不是以愿景为准。

---

## 已实现功能

### 1. 多智能体编排

- 基于图的编排引擎
- Planner / Generator / Executor / Evaluator 节点链路
- 支持 prompt 直接生成编排图
- 支持 VS Code 任务驱动的 prompt 文件执行
- 支持失败重试和流程回环

### 2. OpenClaw / Autoresearch 兼容层

- SQLite 持久化会话与运行记录
- OpenClaw 兼容服务入口
- Claude 子 agent 调度接口
- 会话、评估、运行状态可追踪

### 3. MCP 工具体系

- MCPContextBlock 上下文桥接
- MCPToolRegistry 工具注册与缓存
- 动态工具发现、合成与调用路径
- 标准 MCP manifest 解析与导出
- JSON Schema 输入校验

### 4. 沙盒与执行环境

- Docker 动态沙盒后端
- 代码执行路由到容器
- AppleDouble / `.DS_Store` 清理器
- 适配本地开发和迁移验证流程

### 5. Telegram 网关与面板安全

- Telegram webhook 网关
- `/status` 魔法链接流程
- `x-telegram-bot-api-secret-token` 校验
- 面板 JWT 鉴权
- Telegram Mini App `initData` 验签
- Telegram UID 白名单
- 面板操作审计写入 SQLite
- localhost / Tailscale 绑定限制

### 6. 静态安全与业务约束

- AST + 正则双通道安全审计
- 高危调用拦截
- Micro-GraphRAG 轻量知识图谱
- 业务红线词汇约束
- 基础安全扫描脚本与迁移校验脚本

### 7. 高级工程特性

- Checkpointing 节点快照与恢复
- HITL 人机协同审批拦截
- 标准 MCP 兼容层
- 运行状态与回退记录

---

## 现状说明

下面这些是仓库里已经有代码落点的能力，但其中有些仍是简化实现或需要特定环境验证：

- WebAuthn 生物识别路由与前后端拦截器
- P4 / OpenSage 自动发现与修复流程骨架
- 并发稳定性与真实高压场景验证
- 部分生态插件在真实业务场景下的收益评估

如果你要判断“能不能直接上生产”，建议先看 `STATUS_AND_RELEASE_NOTES.md` 和各模块测试结果。

---

## 快速开始

### 1. 后端 API

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
pip install -r requirements.txt
uvicorn src.autoresearch.api.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
open http://127.0.0.1:8000/healthz
```

### 2. Dashboard

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/dashboard
npm install
npm run dev
```

打开：

```bash
open http://localhost:3000
```

### 3. OpenClaw 迁移配置

```bash
cp migration/openclaw/templates/openclaw-to-autoresearch.env.example migration/openclaw/.env.local
```

---

## 主要入口

- API 服务：`src/autoresearch/api/main.py`
- OpenClaw 兼容服务：`src/autoresearch/core/services/openclaw_compat.py`
- 面板路由：`src/autoresearch/api/routers/panel.py`
- Telegram 网关：`src/autoresearch/api/routers/gateway_telegram.py`
- WebAuthn 路由：`src/autoresearch/api/routers/webauthn.py`
- MCP 上下文：`src/orchestrator/mcp_context.py`
- 沙盒清理：`src/orchestrator/sandbox_cleaner.py`
- 静态安全审计：`src/gatekeeper/static_analyzer.py`

---

## 文档与看板

- 根目录 README：项目总览
- `dashboard/README.md`：前端看板说明
- `dashboard/QUICKSTART.md`：看板快速启动
- `STATUS_AND_RELEASE_NOTES.md`：真实状态与发布说明
- `FINAL_DELIVERY_REPORT.md`：收尾交付报告
- `NIGHT_SPRINT_REPORT.md`：夜间冲刺报告

---

## 开发约定

- 以代码和测试为准，不把愿景默认当成已完成
- 新增能力尽量补充到对应模块 README 或状态说明
- 涉及安全、鉴权、审批链路的改动，优先补测试再合并

---

## 许可证

MIT License
