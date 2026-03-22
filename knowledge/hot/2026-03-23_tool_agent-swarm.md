# Agent Swarm & Coordination 研究

**日期**: 2026-03-23
**来源**: GitHub Search

## 🔥 热门项目

### Agent Swarm 框架

| Stars | 名称 | 说明 |
|-------|------|------|
| 22k | [ruflo](https://github.com/ruvnet/ruflo) | Claude Agent 编排平台，分布式群体智能 |
| 3.1k | [OpenAI_Agent_Swarm](https://github.com/daveshap/OpenAI_Agent_Swarm) | HAAS 分层自主群体 |
| 2.7k | [ClawTeam](https://github.com/HKUDS/ClawTeam) | 港大开源，一条命令全自动化 |
| 1.4k | [swarm-ide](https://github.com/ApeBug/swarm-ide) | Agent Swarm 专用 IDE |
| 600 | [fractals](https://github.com/TinyAGI/fractals) | 递归任务编排器 |
| 592 | [swarm-tools](https://github.com/joelhooks/swarm-tools) | OpenCode 多 agent 协调 |
| 506 | [ClawTeam-OpenClaw](https://github.com/win4r/ClawTeam-OpenClaw) | ClawTeam 的 OpenClaw 适配版 |
| 267 | [swarmzero](https://github.com/swarmzero/swarmzero) | SDK 构建 agent swarms |
| 290 | [agent-swarm](https://github.com/desplega-ai/agent-swarm) | AI coding agents 框架 |

### 协调平台

| Stars | 名称 | 说明 |
|-------|------|------|
| 310 | [OwnPilot](https://github.com/ownpilot/OwnPilot) | 隐私优先的 AI 助手平台 |
| 4 | [MCP-Swarm](https://github.com/AbdrAbdr/MCP-Swarm) | 54 个智能工具，多 agent 协作 |

## 🏗️ Swarm 架构

### 1. Hierarchical (分层)

```
        ┌─────────┐
        │ Supervisor │
        └─────┬─────┘
              │
    ┌─────────┼─────────┐
    ↓         ↓         ↓
┌───────┐ ┌───────┐ ┌───────┐
│Agent 1│ │Agent 2│ │Agent 3│
└───────┘ └───────┘ └───────┘
```

### 2. Mesh (网状)

```
Agent 1 ←→ Agent 2
   ↕         ↕
Agent 3 ←→ Agent 4
```

### 3. Pipeline (流水线)

```
Input → Agent 1 → Agent 2 → Agent 3 → Output
```

### 4. Fractal (递归)

```
Task
  ├── Subtask 1
  │     ├── Sub-subtask 1.1
  │     └── Sub-subtask 1.2
  └── Subtask 2
        └── Sub-subtask 2.1
```

## 🧠 核心概念

### 群体智能 (Swarm Intelligence)

- **涌现行为** — 简单规则产生复杂行为
- **自组织** — 无中心控制
- **分布式** — 多节点并行

### 协调机制

1. **消息传递** — Agent 间通信
2. **共享记忆** — 全局状态
3. **投票/共识** — 决策机制
4. **任务队列** — 工作分发

## 💡 洞察

1. **ruflo 22k stars** — Agent 编排已成热点
2. **ClawTeam 港大出品** — 学术界入场
3. **Swarm IDE** — 专用工具链出现
4. **MCP + Swarm** — 协议融合
5. **Fractal 递归** — 复杂任务分解

## 📊 对比

| 框架 | 架构 | 特点 |
|------|------|------|
| ruflo | 分布式 | 企业级，RAG 集成 |
| ClawTeam | 分层 | 一键自动化 |
| fractals | 递归 | 任务分解 |
| swarmzero | SDK | 灵活构建 |

## 🔗 待研究

- [ ] ruflo 的分布式实现
- [ ] ClawTeam 的自动化机制
- [ ] Fractals 的递归算法
- [ ] MCP-Swarm 的工具生态
