# Autonomous Agent Stack - 愿景调整

> **调整时间**: 2026-04-09
> **调整原因**: 在 2026-03-31 那次“从超级体叙事收敛到 control plane”之后，继续根据当前架构现实与最新 runtime 基础设施判断做第二次收敛。

---

## 新愿景

### 从

**一个受控的 agent execution control plane，统一调度代码 agent、Linux worker、Mac worker、Windows RPA worker**

### 到

**一个受治理、以 session 为中心的 long-running agent control plane。**

repo patch / Draft PR 仍然是当前最重要的落地场景，但它不再是唯一的愿景定义；它是验证这套控制面抽象是否成立的第一垂直场景。

---

## 为什么还要再调一次

上一次调整解决的是：

- 不再追“无需人类干预的自我进化超级智能体网络”
- 承认仓库当前现实是 bounded control plane，而不是神话中的自主超级体

这一次调整解决的是另一个更长期的问题：

**当模型能力持续变化时，系统里什么应该被做成稳定接口，什么应该被留给未来反复重写？**

我们的答案是：

- session 应该稳定
- policy 边界应该稳定
- capability / hand 抽象应该稳定
- 具体 harness 实现不应该被神化成最终形态

---

## 这次愿景调整后的核心判断

### 1. Session 比 prompt 更高阶

- 会话不是消息列表
- 会话不是上下文窗口的镜像
- 会话应该被建模为 append-only execution fact log
- 摘要、prompt bundle、PR、patch 都只是会话的派生投影

如果历史只能活在 prompt 里，系统就没有真正的可恢复性。

### 2. Harness 是策略层，不是宪法

- 当前 planner -> worker -> validation -> promotion 流程是现实主线
- 但任务分解、上下文组装、重试、checkpoint、评估策略都应该可替换
- 随着模型能力变强，应优先替换 policy，而不是重写系统骨架

### 3. Sandbox / Tool / Worker 都应该被看作 hand

- 执行环境不应成为系统本体
- 本地 sandbox、remote worker、MCP server、browser、git proxy 都是 capability hands
- brain 应只感知“我有哪些手可用”，而不是把具体基础设施写死进主流程

### 4. 安全不能押在模型能力不足上

- 凭证、审批、写权限、promotion authority 必须留在控制面边界内
- 不假设“模型应该不会想到某条攻击路径”
- patch-only、deny-wins、single-writer、promotion gate 仍然是底座

---

## 这意味着 AAS 的价值重心要怎么变

不是去做：

- 更会写 prompt 的 Agent
- 某家模型 runtime 的开源复刻
- 追求表面上“更强自治”的概念项目

而是去做：

- vendor-neutral control plane
- durable session spine
- policy-first orchestration
- capability-based execution substrate
- governed promotion and audit trail

一句话说：

**从“自动改代码系统”升级为“可恢复、可治理、可晋升的 Agent runtime 外层”。**

---

## 最近最该做的三刀

### 第一刀：先把 harness 做薄

这是最近最该立刻开始的工作。

理由：

- 工程代价相对低
- 能马上降低“把今天最佳实践写死”的技术债
- 能为后续 session 化让路

### 第二刀：把 session 提升为一级抽象

这是最值钱，但也最伤筋动骨的一刀。

目标不是再多存一点日志，而是把系统的 source of truth 从“散落的 run 记录”升级为“统一的事实流”。

### 第三刀：把 hands 抽象统一

这一步要建立 capability metadata，统一管理不同执行环境的信任、成本、恢复性与审批边界。

---

## 近期不做什么

- 不追“完全自治”叙事
- 不把 repo patch 主路径让位给抽象层重写工程
- 不为了概念完整度一次性铺开 multi-agent / multi-task 平台
- 不把 AAS 做成 Anthropic 影子产品

---

## 最终判断

这个项目的方向不是错了，而是该继续向上收敛。

它已经不是一个“prompt loop 外面包一层壳”的普通 Agent 项目；它已经有了零信任控制面、隔离执行、验证门、晋升门这些真正有长期价值的骨架。

接下来要做的，不是更激进地追求自治，而是更克制地投资稳定抽象：

- session-first
- policy-first
- capability-first

只要这三件事做对，AAS 的长期位置就不是“另一个 agent runtime”，而是更外层、也更稳定的 Agent control plane / runtime substrate。
