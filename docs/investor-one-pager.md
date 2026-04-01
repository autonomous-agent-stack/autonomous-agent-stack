# 投资人一页纸

## 一句话

`autonomous-agent-stack` 不是另一个自治 agent 框架，而是一个**受控的 agent execution control plane**。它要做的是把不同的 agent/runtime/worker 纳入同一套可治理执行面里，统一完成任务路由、隔离执行、审批、审计、回滚、重放和迁移。

## 现在做到什么

这个项目已经不是概念稿，主线已经收口到“控制面 + worker fabric + governance layer + migration hub”。

已经具备的能力：

- 统一的 task / run / gate / worker contract
- 真实的 worker registry
- Linux supervisor 生产路径接线
- heartbeat / registration 的统一状态读取
- OpenClaw 兼容与迁移骨架
- prompt orchestration 只作为计划层，不绕过控制面
- checkpoint / replay / knowledge 三层 memory 规则

这意味着现在系统已经能做的，不是“自由长出一个 agent 大脑”，而是：

- 把 code agent 当作受控执行器来跑
- 把 Linux worker 当作生产执行节点来调度
- 把失败过程记录下来，支持审计和回放
- 把 worker 状态统一收口到同一个 registry

## 未来能实现什么

短中期，这个项目可以继续扩展成一个真正可运营的执行底座：

- 统一接入 OpenHands、Claude CLI、浏览器自动化、本地脚本、Linux worker、Windows RPA worker
- 让不同 runtime 通过同一套 contract、bridge、gate、acceptance 接入
- 把 OpenClaw 生态的 session、skills、Telegram、workflow 平滑挂进来
- 把“能跑”升级成“可回滚、可审计、可复盘、可接管”

长期，这个项目可以成为：

- 多 runtime 的治理层
- 多 worker 的编排层
- 多入口的迁移层
- 企业里真正能接流程、接审批、接审计的执行底座

## Win + 影刀能做什么

Windows + 影刀是这个项目最直接的业务落地场景之一，因为它适合解决大量重复、规则明确、但又没法用纯 API 一次性打通的桌面流程。

典型场景：

- ERP / 后台录入
  - 自动填表、提交、截图留证
  - 处理 Windows-only 的老系统

- 财务与运营对账
  - 在 Excel、桌面工具、网页系统之间搬运数据
  - 做批量检查、批量更新、批量核对

- 客服与运营操作
  - 更新订单、地址、票据、工单
  - 处理重复性 UI 操作

- 合规审计流程
  - 保留步骤日志、截图、执行结果
  - 异常自动转人工复核

- 系统间最后一公里连接
  - API 接不上的地方，用 RPA 补最后一段

为什么这条线值钱：

- 任务重复，人工成本高
- 业务量一大，ROI 很容易算
- control plane 能把 RPA 从“脆弱脚本”变成“可治理执行”
- 对企业来说，这比单纯做一个 agent demo 更容易落地付费

## 为什么它有投资价值

市场上很多 agent 项目停在 demo 层，或者只做“更聪明的对话”。这个项目的差异点是：

- 它解决的是执行面，不是单纯聊天面
- 它解决的是治理，不是放任自治
- 它解决的是多 runtime / 多 worker 的统一接入，不是单一框架
- 它解决的是企业真的关心的审计、回滚、人工接管、兼容迁移

## 一句话总结

`autonomous-agent-stack` 的目标，是成为企业级的受控执行底座：既能接 code agent，也能接 RPA worker，既能接 OpenClaw 生态，也能接真实业务流程，并且全程可控、可回滚、可审计。

