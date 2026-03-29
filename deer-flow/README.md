# deer-flow

deer-flow 多智能体系统研究。

---

## 📋 项目概述

deer-flow 是一个多智能体协作系统，支持并发执行、沙盒隔离和动态上下文工程。

---

## 🔬 核心特性

### 1️⃣ 多智能体并发
- 并行执行多个 Agent
- 智能任务分配
- 结果聚合

### 2️⃣ 沙盒隔离
- Docker 容器隔离
- 安全执行环境
- 资源限制

### 3️⃣ 动态上下文工程
- 上下文动态组装
- Token 优化
- 相关性过滤

### 4️⃣ 工作流编排
- 状态机管理
- 条件分支
- 错误处理

---

## 🏗️ 架构设计

### 核心节点

```
┌─────────────┐
│   Planner   │ ← 规划任务
└──────┬──────┘
       │
┌──────▼──────┐
│  Generator  │ ← 生成内容
└──────┬──────┘
       │
┌──────▼──────┐
│  Executor   │ ← 执行操作
└──────┬──────┘
       │
┌──────▼──────┐
│  Evaluator  │ ← 评估结果
└─────────────┘
```

### 执行流程
1. **Planner**: 分析任务，制定计划
2. **Generator**: 生成执行方案
3. **Executor**: 执行具体操作
4. **Evaluator**: 评估执行结果

---

## 🔗 集成方案

### OpenClaw 集成
- 作为 OpenClaw 的多智能体引擎
- 复用 OpenClaw 的 MCP 网关
- 共享 ContextBlock 系统

### MCP 网关集成
- 统一工具管理
- 动态工具注册
- 权限控制

### MASFactory 集成
- 图节点重构（5 API → 4 节点）
- M1 本地执行沙盒
- 可视化监控看板

---

## 📚 相关文档

### 深度分析
- [deer-flow 核心设计分析](../memory/tech-learning/deer-flow-core-design-analysis-2026-03-25.md)
- [deer-flow 整合蓝图](../memory/tech-learning/deer-flow-integration-roadmap-2026-03-25.md)

### 实现方案
- [autoresearch 设计](../autoresearch/README.md)
- [autonomous-agent-stack](https://github.com/srxly888-creator/autonomous-agent-stack)

---

## 🎯 实施路线

### Phase 1: autoresearch（当前）
- API-first 架构
- Karpathy 循环实现
- 最小闭环验证

### Phase 2: OpenClaw 集成
- 作为 OpenClaw 子模块
- MCP 网关对接
- 多智能体协作

### Phase 3: MetaClaw
- 自演化机制
- 双循环学习
- 超级智能体网络

---

## 🔧 技术栈

- **语言**: Python
- **框架**: FastAPI
- **容器**: Docker
- **编排**: LangChain / AutoGen
- **监控**: Mermaid + HTML

---

## 📌 状态

- **研究阶段**: ✅ 完成
- **设计阶段**: ✅ 完成
- **实现阶段**: 🚧 进行中
- **集成阶段**: ⏳ 计划中

---

**最后更新**: 2026-03-29 12:00 GMT+8
