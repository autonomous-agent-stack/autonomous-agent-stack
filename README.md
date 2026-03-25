# 🤖 Autonomous Agent Stack

> **现代化多智能体编排框架** - 基于 MASFactory 的图编排引擎

---

## 📋 项目简介

Autonomous Agent Stack 是一个基于 MASFactory 的多智能体编排框架，用于把若干开源能力整合为统一的"微观执行底座"。

**核心特性**：
- 🎯 **图编排引擎**：基于 MASFactory 的 Vibe Graphing
- 🔧 **MCP 集成**：通过 ContextBlock 统一管理工具链
- 🖥️ **M1 优化**：本地沙盒 + AppleDouble 自动清理
- 📊 **可视化监控**：实时看板 + Mermaid 图
- 🔄 **自愈能力**：自动重试 + 回滚机制

> 说明：本仓库以“能跑、能接、能审计”为优先，不把文档里的愿景默认当作已上线事实。

---

## 🏗️ 架构设计

### 核心流程

```
Planner Node → Generator Node → Executor Node → Evaluator Node
      ↑                                                    ↓
      └────────────── Retry Loop ──────────────────────────┘
```

### 6 部分架构

| 部分 | 核心技术 | 价值 |
|------|---------|------|
| **Part 1** | MetaClaw 自演化 | 准确率 +89.7% |
| **Part 2** | Autoresearch API-first | 最小闭环 ✅ |
| **Part 3** | Deer-flow 并发隔离 | 会话零污染 |
| **Part 4** | InfoQuest/MCP 深度耦合 | Token 优化 |
| **Part 5** | Claude Code 终端集成 | 自动重连 |
| **Part 6** | OpenClaw 持久化架构 | 污染防治 ✅ |

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 安装依赖
pip install -r requirements.txt

# 复制安全模板（填写 Telegram/Tailscale/JWT 参数）
cp .env.security.example .env.local
```

### 2. 运行最小闭环

```python
from src.orchestrator import create_minimal_loop
import asyncio

async def main():
    # 创建最小闭环
    graph = create_minimal_loop()
    
    # 设置初始输入
    graph.context.set("goal", "优化代码性能")
    
    # 执行图
    results = await graph.execute()
    print(results)

asyncio.run(main())
```

### 3. 启动监控看板

```bash
# 生成 HTML 看板
python src/orchestrator/visualizer.py

# 在浏览器中打开
open dashboard.html
```

---

## 🎯 核心组件

### 1. 图编排引擎 (`src/orchestrator/graph_engine.py`)

**4 个核心节点**：
- **PlannerNode**: 规划节点，对接 OpenClaw
- **GeneratorNode**: 生成节点，写代码或调用工具
- **ExecutorNode**: 执行节点，沙盒环境
- **EvaluatorNode**: 评估节点，承载 MetaClaw 逻辑

### 2. MCP 上下文块 (`src/orchestrator/mcp_context.py`)

**统一工具管理**：
- Web Search
- Link Reader
- File Reader
- Code Analyzer

### 3. 可视化工具 (`src/orchestrator/visualizer.py`)

**监控看板功能**：
- 实时节点状态
- 评估分数展示
- Mermaid 图渲染
- 浅色主题

---

## ✅ 实现判定

下面不是愿景表，而是按仓库代码和路由落点整理的状态判断。

### 已实现

- **OpenClaw 兼容会话层**
  - SQLite 持久化的会话与运行记录已接入
  - 相关入口已挂到 `/api/v1/openclaw/sessions`
  - Claude 子 agent 调度已接到 `/api/v1/openclaw/agents`
- **Telegram 网关**
  - `/api/v1/gateway/telegram/webhook` 已实现
  - 支持 `x-telegram-bot-api-secret-token` 校验
  - 支持 `/status` 魔法链接流程
- **Web 面板安全**
  - `/api/v1/panel/*` 已实现
  - 支持短期 JWT 魔法链接
  - 支持 Telegram Mini App `initData` 验签
  - 支持 Telegram UID 白名单
  - 面板操作审计已写入 SQLite
  - 绑定主机限制为 localhost / Tailscale IP
- **动态工具合成与沙盒清理**
  - `MCPContextBlock` 已支持动态工具合成
  - 默认沙盒后端是 `docker`
  - AppleDouble / `.DS_Store` 清理器已实现
- **MCP 工具注册与上下文桥接**
  - `MCPContextBlock` 和 `MCPToolRegistry` 已存在
  - 基础工具发现、缓存、调用路径已实现
- **静态安全审计**
  - AST 与正则双通道审计已实现
  - `os.system`、`eval`、`exec`、鉴权层文件等红线已纳入检测
- **SQLite 仓储层**
  - 评估、报告、变体、实验、集成等模型仓储已接入 SQLite

### 部分实现

- **WebAuthn 生物识别闸门**
  - 已有 `/api/v1/auth/webauthn` 路由
  - 已有 challenge / assertion 基础流程
  - 但当前实现是简化版，包含 mock 验证逻辑，不等于完整生产级 WebAuthn 闭环
- **P3 生态融合（OpenViking + MiroFish）**
  - 文档、接口契约和配置位已存在
  - 适合作为插件化接入骨架
  - 但是否达到“全面上线”需要单独按运行证据确认
- **P4 自主集成协议**
  - discover / prototype / promote 的骨架已存在
  - 目前更偏向“生成计划 + 回滚模板”的半自动流程
- **群组访问与实时查岗**
  - 群组 JWT、成员检查、审计流程已有实现
  - 但部分审计落库路径仍可继续补强

### 仍待验证

- **“生产维稳阶段”**
  - 这是目标描述，不应直接等同于生产结论
- **“WebAuthn 100% 贯通”**
  - 目前仓库证据只支持“已有简化实现”
- **“全量测试通过”**
  - 仓库里有测试文件，但当前环境未能直接复核测试命令

### 参考入口

- OpenClaw 兼容服务：`src/autoresearch/core/services/openclaw_compat.py`
- 面板鉴权：`src/autoresearch/core/services/panel_access.py`
- 面板路由：`src/autoresearch/api/routers/panel.py`
- Telegram 网关：`src/autoresearch/api/routers/gateway_telegram.py`
- WebAuthn 简化路由：`src/autoresearch/api/routers/webauthn.py`
- 动态工具合成：`src/orchestrator/mcp_context.py`
- 沙盒清理：`src/orchestrator/sandbox_cleaner.py`
- 静态安全审计：`src/gatekeeper/static_analyzer.py`

---

## 📚 文档

- **[架构文档](docs/architecture.md)**: 6 部分完整架构
- **[关键工程决策](docs/critical-designs.md)**: 短路机制 + 节点协议 + 并发安全 ⭐ **NEW**
- **[OpenClaw 替代迁移手册](docs/openclaw-replacement-migration-playbook.md)**: 最佳实践 + 分阶段迁移 + 回滚方案 ⭐ **NEW**
- **[P3 生态融合手册](docs/p3-ecosystem-fusion-playbook.md)**: OpenViking + MiroFish 接入与 API 契约 ⭐ **NEW**
- **[P4 自主集成协议](docs/p4-self-integration-protocol.md)**: discover/prototype/promote 设计与契约 ⭐ **NEW**
- **[MASFactory 集成](docs/masfactory-integration.md)**: 集成指南
- **[集成指南](docs/integration-guide.md)**: 快速集成
- **[API 参考](docs/api-reference.md)**: API 详细说明
- **[路线图](docs/roadmap.md)**: 未来演进方向
- **[贡献指南](CONTRIBUTING.md)**: 如何贡献

---

## 🎯 使用场景

### 1. 软件工程
- 自动化代码优化
- 架构演进
- Bug 修复

### 2. 科学研究
- 自动化实验
- 参数优化
- 论文生成

### 3. 数据分析
- 自动化分析
- 可视化生成
- 报告生成

---

## 📊 项目统计

| 指标 | 数值 |
|------|------|
| **文件数量** | 58 个 |
| **代码行数** | 4,000+ 行 |
| **文档字数** | 30,000+ 字 |
| **测试覆盖率** | 60%+ |

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🔗 相关链接

- **GitHub**: https://github.com/srxly888-creator/autonomous-agent-stack
- **MASFactory**: https://github.com/BUPT-GAMMA/MASFactory
- **OpenClaw**: https://github.com/openclaw/openclaw

---

**一起构建未来！** 🚀
