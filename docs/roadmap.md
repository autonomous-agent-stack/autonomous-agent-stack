# 路线图（2026-04-09 更新）

> 这版路线图基于当前仓库已经落地的现实架构，以及最近对 Agent runtime 基础设施的复盘。
> 目标不是追一版“最强 harness”，而是把 AAS 往更稳定的系统抽象上推进。

---

## 一句话愿景

Autonomous Agent Stack 的终局不再定义为“更强的自动改代码 Agent”。

新的表述是：

**一个受治理、以 session 为中心的 long-running agent control plane。**

短期仍然用 repo patch / Draft PR 作为最重要的落地场景；长期则把这套治理骨架扩展到更广义的 durable agent operations。

---

## 这次调整在修正什么

这次不是推翻现有 control plane 主线，而是在它之上再向前收敛一步：

- 不把今天模型的短板固化成永久 harness 结构
- 不把完整历史塞进 prompt，并把 summary 误当成 source of truth
- 不让 sandbox、MCP、remote worker、git proxy 分别长成互不兼容的子系统
- 不和模型厂商比“谁更会写某一版 harness”，而是投资更稳定的接口层

---

## AAS 接下来要守住的稳定接口

### 1. Session 是第一公民

- Session 不是消息列表，也不是 context window 的镜像
- Session 应该是 append-only execution fact log
- patch、summary、prompt bundle、Draft PR 都只是 session 的派生物
- compaction 是优化，不是事实删除
- 恢复、handoff、审计都应首先依赖 session，而不是依赖某一轮 prompt 拼装

### 2. Harness 继续存在，但降级为 policy

- Harness 仍然重要，但不应成为永久写死的系统骨架
- 当前 planner -> worker -> validation -> promotion 主路径保留
- 未来优先抽出的边界是：
  - context assembly policy
  - task selection / decomposition policy
  - retry / checkpoint / escalation policy
  - evaluation policy
  - promotion policy

核心原则：随着模型能力变化，优先替换 policy，不重写整个平台。

### 3. Sandbox / Tool / Worker 统一视为 hands

- 本地 sandbox、remote worker、MCP server、browser、git proxy 都应该视为 capability hands
- brain 面向 capability registry，而不是面向某个具体执行环境
- 每个 capability 至少要暴露：
  - trust boundary
  - credential boundary
  - recoverability
  - latency / cost
  - approval requirement

---

## 明确不做什么

- 不做某一家模型厂商 runtime 的开源复刻
- 不把“更强自治”放在“更稳边界”之前
- 不把 prompt summary 当永久记忆
- 不在最近两个迭代里把产品面扩成泛化多任务平台
- 不为了追赶概念而破坏已经验证过的 patch-only / promotion 主路径

---

## 最近规划：分三个阶段推进

### Phase 1（0-2 周）：先把 harness 做薄，继续守住 patch 主路径

目标：先降技术债，不急着重写 runtime。

交付物：

- 把当前 orchestration 中可替换的部分显式抽成 policy 接口
- 至少覆盖 context assembly、task selection、retry/escalation、evaluation、promotion 五类策略
- 保持现有 single-repo patch / Draft PR 流程不变
- 为策略切换补最小可用测试和文档，不引入第二套执行主线

完成标准：

- 控制面主流程仍然只存在一条受控主路径
- 新 policy 边界能够用默认实现跑通现有流程
- 后续 session 化工作不再被当前 harness 实现硬绑定

### Phase 2（2-6 周）：把 session 从“运行记录”升级成“系统中心”

目标：把现在分散在 SQLite、events、artifacts、run metadata 里的持久状态，收敛成统一 session spine。

交付物：

- 定义统一 Session 对象和 append-only event schema
- 提供 query / replay / handoff / compaction 的最小 API
- 明确哪些是事实事件，哪些只是派生缓存
- 让 summary / prompt bundle 成为 session 投影，而不是唯一历史
- 在不破坏现有 patch promotion 的前提下，把 run artifact 和 session 关联起来

完成标准：

- 新 session 能覆盖一次完整 patch run 的关键事实
- 故障恢复和人工接手不再依赖翻日志找上下文
- “历史”与“上下文窗口”在代码结构上明确分离

### Phase 3（6-12 周）：统一 capability hands，准备 many brains / many hands

目标：把执行环境从“若干孤立 adapter”升级成统一 capability substrate。

交付物：

- 建 capability registry，统一描述 local sandbox、remote worker、MCP、browser、git proxy
- 为 capability 增加 trust/cost/recovery/approval 元数据
- 让 routing 基于 capability，而不是机器名或执行器名写死
- 继续保持 repo patch 场景为第一验证场

完成标准：

- 新增一种 hand 不需要复制整套控制面逻辑
- 同一 session 能安全接力多个不同 hand
- 后续 distributed execution / federation RFC 能建立在统一 capability 抽象上

---

## 这条路线和 Anthropic 思路的关系

可以借鉴的部分：

- 安全不要建立在“模型暂时没那么聪明”上
- brain / hand separation
- session 应高于 prompt
- harness 应该可替换，而不是被神化为最终形态

不应该照抄的部分：

- 不把 AAS 做成 Claude Code 兼容层
- 不追某一版 Anthropic harness 细节
- 不把产品价值押在“模型厂商没开放的内部能力”上

---

## 当前判断

今天的 AAS 最强的仍然是：

- patch-only execution
- validation + promotion gate
- zero-trust repository mutation
- 可审计、可回滚、可隔离的控制面

接下来要补的是：

- session-first
- policy-first
- capability-first

这不是偏航，而是把现有“受治理的代码变更控制面”继续推进成更稳的 Agent runtime 外层。

---

## Hermes runtime lane（后续） / Hermes Runtime Lane (Follow-up)

- Hermes runtime v1 PR 1 + PR 2 已落地：合同字段、structured command builder、`error_kind` taxonomy、`CANCELLED` 取消语义、summary 收紧都已经进入主线实现。
  Hermes runtime v1 PR 1 + PR 2 are now shipped: the contract fields, structured command builder, `error_kind` taxonomy, `CANCELLED` cancel semantics, and tighter summary behavior are all in the main implementation.
- `cli_args` 与结构化 `metadata.hermes` 的优先级合同现在固定为“结构化映射先生成 argv，`cli_args` 后追加，但 denylist 不能被绕过”。
  The precedence contract between `cli_args` and structured `metadata.hermes` is now fixed as “structured mapping builds argv first, `cli_args` append later, but the denylist cannot be bypassed.”
- 下一步仍然不是多实例调度；`aas_dispatch_tool`、`target_node`、node registry 必须排在 Hermes runtime v1 hardening 之后独立推进。
  The next step is still not multi-instance scheduling; `aas_dispatch_tool`, `target_node`, and the node registry must be developed separately after Hermes runtime v1 hardening.
