# 为什么选择 AAS？

## 核心问题

随着 AI Agent 能力持续增强，真正的问题已经不只是“怎么给它加个沙箱”。

更根本的问题是：

**当模型能力持续变化时，系统里什么应该保持稳定，什么应该被设计成可替换？**

### 大多数 Agent Stack 的问题

1. **把模型的暂时短板固化成永久架构**
   - 一次阶段性的规划不足，最后变成固定 DAG
   - 一次 prompt workaround，最后变成框架原语
   - 整个系统围着今天的 harness 技巧长死

2. **把历史和上下文混为一谈**
   - 把 session 当聊天记录
   - 把 summary 当唯一记忆
   - 恢复依赖重新拼 prompt，而不是查询事实

3. **让执行运行时悄悄变成 trusted core**
   - 一个 worker runtime 同时拿走规划、执行、审批、发布权
   - 工具和沙箱边界不断外溢
   - 安全建立在“模型大概想不到这里吧”的侥幸上

## AAS 的回答

AAS 围绕三类应该比具体 harness 更稳定的抽象来设计：

### 1. Session 是 durable fact history

- Session 不是 context window 的镜像
- Session 应该是 append-only execution history
- summary、prompt bundle、patch、PR 都只是派生视图，不是 source of truth
- 恢复和 handoff 应该首先基于事实，而不是脆弱的 prompt 重建

### 2. Policy 是可替换的编排层

- 规划、上下文组装、重试、checkpoint、评估、晋升都应该成为 policy 边界
- 系统不应该把今天最好用的 harness 永久写死
- 随着模型变强，AAS 应该更多替换 policy，而不是重写整个平台

### 3. Capability 是隔离的 hands

- sandbox、remote worker、MCP server、browser、git proxy 都是 execution hands
- 控制面应该始终压在它们上层
- brain 应该面向 typed capabilities 路由，而不是依赖某个特权 runtime

## 零信任仍然是底座

session-first 不等于边界变软。

现有安全不变量仍然是核心：

- **Patch-Only**：Agent 只提议有边界的改动，不直接拥有仓库
- **Deny-Wins**：更严格的策略永远生效
- **Single-Writer**：可变状态的晋升不能并发乱写
- **Artifact Isolation**：运行时状态不会悄悄进入源码
- **Promotion Gate**：执行权和批准权始终分离

关键不是“更信任模型”。
关键是：**更信任稳定接口，而不是模型相关的技巧。**

## 为什么是现在

现在正好有三件事同时成立：

1. **模型越来越强**
   - 越来越多的工作可以交给模型
   - 也意味着越来越多旧 harness 假设会很快过时

2. **durable execution 的系统模式已经成熟**
   - lease、heartbeat、append-only log、replay、promotion gate 都不是新问题
   - Agent 基础设施可以借鉴分布式系统，而不是全靠拍脑袋

3. **团队真正需要的是治理，不只是 demo**
   - 他们想要 Agent 带来的效率
   - 但不愿直接交出仓库写权限、凭证和审批边界
   - 他们需要 vendor-neutral 的控制面

## AAS 正在建设什么

### 今天

AAS 还是一个面向 autonomous repository changes 的 bounded control plane：

- planner 选择有边界的任务
- worker 在隔离环境里改动
- validator 检查策略和执行结果
- promotion gate 决定结果是否能升级为 patch artifact 或 Draft PR

### 下一步

AAS 正在往 long-running agents 的 governed runtime substrate 演进：

- 从 prompt-first memory 转向 session-first state
- 从固定 harness doctrine 转向 policy-first orchestration
- 从 adapter 拼盘转向 capability-first routing

### 更远处

这会打开这些能力：

- 跨异构 worker 的 distributed execution
- many brains / many hands 协同
- governed AAS instances 之间的 federation
- 超出 repo patch 场景的 durable agent operations

## AAS 不打算成为什么

- 不是不受约束的自我编辑超级体
- 不是某一家模型厂商 runtime 的复刻品
- 不是把今天 prompt 技巧硬编码成明天系统骨架的框架

## 最终下注

我们相信 Agent 基础设施里最耐久的层，不是“当前最聪明的 harness”。

而是：

- durable session state
- replaceable orchestration policy
- isolated capabilities
- governed promotion

AAS 想站的位置，就是这一层。

---

*[阅读完整文档](README.zh-CN.md) | [阅读当前路线图](docs/roadmap.md) | [加入讨论](https://github.com/srxly888-creator/autonomous-agent-stack/discussions)*
