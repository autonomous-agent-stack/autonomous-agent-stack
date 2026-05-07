# RFC：企业级 Runtime 治理蓝图

**状态**：Draft | **作者**：AAS Core Team | **创建时间**：2026-05-07
**依赖**：[架构](../architecture.zh-CN.md)、[Evergreen Agent Control Plane](../evergreen-agent-control-plane.md)、[Runtime Isolation](../runtime-isolation.md)、[Federation-ready v1](../federation-ready-v1.md)、[Distributed Execution Model](./distributed-execution.md)、[Federation Protocol](./federation-protocol.md)、[路线图](../roadmap.md)

[English](enterprise-runtime-governance-blueprint.md)

## 摘要

本文是一份 umbrella alignment RFC，用来约束 AAS 长期 runtime 治理边界。它不替代现有的 distributed execution、federation、runtime isolation、evergreen control-plane 或 roadmap 文档，而是约束这些方向如何一起演进。

当前 Python/FastAPI control plane 继续是权威。`/api/v2`、`SessionEvent`、`PolicyDecision`、`Approval`、`Artifact`、`Promotion` 和 `Lease` 继续构成系统事实记录与治理主干。

## 动机

AAS 已经把控制面和可替换执行面分开。下一阶段最大的长期风险不是 runtime 想象力不足，而是意外碎片化。分布式 worker、联邦 peer、模型网关、MCP 工具、沙箱 profile 和未来低层 supervisor 都不能长成相互竞争的权威。

本文定义未来工作的对齐合同：

- control-plane facts 必须位于 runtime 之上，
- evidence 可以附着到事实，但不能替代事实，
- supervisor 可以强化执行，但不能拥有治理权，
- resource 必须继续通过 AAS 的 quota、lease、audit 与 artifact ledger 记账。

## 权威边界

本方向不重写 AAS control plane。以下对象继续是权威：

- Python/FastAPI control plane，
- `/api/v2` control-plane APIs，
- 作为 append-only 事实时间线的 `SessionEvent`，
- 作为策略决策记录的 `PolicyDecision`，
- 作为人工或委托审批记录的 `Approval`，
- 作为结果证据引用的 `Artifact` 和 `ArtifactRef`，
- 作为显式升级门的 `Promotion`，
- 作为 worker、peer、secret 和可变状态转换边界授权的 `Lease`。

未来 runtime 基础设施必须接入这些记录之下。更快的 runtime、更强的沙箱或 supervisor sidecar 可以提升执行质量，但不能成为事实源。

## RuntimeExecutionEnvelope

`RuntimeExecutionEnvelope` 是从 control plane 传给 runtime、worker、tool boundary、federation peer 或未来 supervisor sidecar 的拟议合同。它是治理 envelope，不是新的 scheduler。

最小字段：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `contract_version` | 是 | Envelope schema 版本，例如 `runtime-envelope/v1`。 |
| `envelope_id` | 是 | 唯一 envelope 标识。 |
| `idempotency_key` | 是 | 用于避免重复 dispatch 或重复挂载 evidence 的稳定键。 |
| `session_id` | 是 | 权威 AAS session id。 |
| `task_id` | 是 | Control-plane task id。 |
| `run_id` | 是 | Control-plane run id 或 worker-backed run id。 |
| `capability_id` | 是 | 被调用的 capability。 |
| `principal` | 是 | 本次执行的 actor 或 service principal。 |
| `policy_decision_ids` | 是 | 授权或约束本次执行的 policy decision。 |
| `approval_id` | 可选 | 敏感或外部动作需要的 approval record。 |
| `secret_lease_ids` | 可选 | 以引用方式提供给 runtime 的 secret lease。 |
| `quota_entry_ids` | 可选 | 为本次执行保留的 quota ledger entry。 |
| `isolation_profile` | 是 | 由 policy 选择的 runtime isolation profile。 |
| `network_policy_ref` | 可选 | 约束外部通信的 policy 引用。 |
| `model_policy_ref` | 可选 | 约束模型调用的 model policy 引用。 |
| `deadline` | 是 | Scheduler、worker 或 supervisor 使用的执行截止时间。 |
| `artifact_root` | 是 | 本次执行授权的 artifact 输出根目录。 |
| `evidence_refs` | 可选 | Runtime 可以追加但不能覆盖的已有 evidence 引用。 |

规则：

- Envelope 由 AAS 签发，不由 runtime 签发。
- Runtime 可以拒绝无法满足的 envelope。
- Runtime 可以通过授权结果回传追加 evidence 引用。
- Runtime 不能扩大 envelope 中的 policy、approval、quota、secret 或 artifact 权限。

## GovernanceEvidenceEnvelope

`GovernanceEvidenceEnvelope` 是 runtime evidence 的拟议附件格式。它不是事实源。事实源仍然是 `SessionEvent`。

Evidence 只能通过以下方式进入系统可见记录：

- 被某个 `SessionEvent` 引用，
- 被某个 `ArtifactRef` 引用。

推荐 evidence 字段：

| 字段 | 含义 |
| --- | --- |
| `contract_version` | Evidence schema 版本。 |
| `evidence_id` | 唯一 evidence 标识。 |
| `envelope_id` | 产生该 evidence 的 RuntimeExecutionEnvelope。 |
| `session_id` | Evidence 所属 session。 |
| `task_id` | Evidence 所属 task。 |
| `run_id` | Evidence 所属 run。 |
| `capability_id` | Evidence 所属 capability。 |
| `evidence_type` | Doctor report、isolation check、approval gate、quota transition、model call、tool call、artifact hash、replay check 或 resource measurement。 |
| `produced_by` | 发出 evidence 的 runtime、worker、tool broker、federation peer 或 supervisor component。 |
| `artifact_refs` | 该 evidence 创建或验证的 artifact reference。 |
| `content_hashes` | Evidence payload 或产物的 hash。 |
| `resource_usage` | 可用时记录 CPU、memory、disk、duration、model usage 或 credit-unit 数据。 |
| `policy_refs` | 该 evidence 涉及的 policy reference。 |
| `created_at` | 创建时间。 |
| `metadata` | 有边界的额外诊断 metadata。 |

Evidence 规则：

- Evidence 解释发生了什么，但不决定什么是真的。
- Evidence 不能覆盖 `PolicyDecision`。
- Evidence 不能审批、晋升或修改源码状态。
- 没有 `SessionEvent` 或 `ArtifactRef` 引用的 evidence 只是诊断残留，不是系统事实。

## 未来 Supervisor Sidecar 边界

未来可以在现有 AAS runtime adapter 合同背后引入 Rust、Zig 或其他低层 supervisor sidecar。Sidecar 是可选组件，必须服从 control plane。

Supervisor sidecar 可以：

- 启动和停止隔离执行，
- 收集 runtime evidence，
- 执行 AAS 选择的本地 sandbox profile，
- 测量资源使用，
- 向授权 artifact root 输出 artifacts。

Supervisor sidecar 不能：

- 拥有 approval，
- 拥有 promotion，
- 修改源码，
- 拥有 credential authority，
- 绕过 `PolicyDecision`，
- 绕过 `SessionEvent` facts。

如果 sidecar 无法通过 AAS control plane 回报，它的输出就不是权威结果。如果它发现违规，应 fail closed，并发出 evidence 供 AAS 记录。

## Resource Abstraction

AAS 继续拥有 resource governance。未来 runtime 基础设施必须复用这些 control-plane 概念，而不是创建平行账本：

- quota，
- lease，
- cost attribution，
- artifact evidence，
- federation ledger，
- approval 与 audit facts。

Resource layer 的范围故意大于单个 runtime process。它覆盖 local worker、remote worker、governed MCP tools、model providers、federation peers，以及未来由 supervisor 管理的执行。

## 非目标

本文不授权也不实现：

- code changes，
- Rust 或 Zig implementation，
- settlement，
- marketplace behavior，
- live external write behavior，
- replacement of the FastAPI control plane，
- replacement of current GA gates。

## 实现方向

本文应增量落地：

1. 先文档化 envelope contracts，并让后续 RFC 对齐这些合同。
2. 把现有 `SessionEvent`、`ArtifactRef`、approval、quota、lease 和 runtime isolation 记录映射到 envelope 语言。
3. 只有在后续 RFC 明确支持时才改代码，并继续明确现有 control-plane authority。

## 与现有文档的关系

本文约束以下方向：

- [Distributed Execution Model](./distributed-execution.md)：worker 接收有边界的 envelope，并把 evidence 回报给 control plane。
- [Federation Protocol](./federation-protocol.md)：peer 接收 lease-scoped envelope，不能获得 promotion 或 credential authority。
- [Runtime Isolation](../runtime-isolation.md)：isolation profile 由 AAS 选择，可以由 runtime 或未来 supervisor 执行。
- [Evergreen Agent Control Plane](../evergreen-agent-control-plane.md)：control plane 继续作为可替换执行面之上的长期系统权威。
- [路线图](../roadmap.md)：未来 supervisor 或 resource-abstraction 工作必须强化当前 control-plane spine，而不是替代它。

## 风险与缓解

- 风险：envelope 语言变成平行 API。缓解：在后续 implementation RFC 把它映射到现有 `/api/v2` models 前，本文只作为文档约束。
- 风险：supervisor sidecar 变成隐藏权威。缓解：sidecar 只能在 AAS 签发的 envelope 下输出 evidence 和 artifacts。
- 风险：evidence 被误认为事实。缓解：evidence 必须被 `SessionEvent` 或 `ArtifactRef` 引用后，才进入系统记录。
- 风险：resource accounting 碎片化。缓解：quota、lease、cost attribution、federation ledger、approval 和 audit 保持在 AAS 内。

## 参考

- [架构](../architecture.zh-CN.md)
- [Evergreen Agent Control Plane](../evergreen-agent-control-plane.md)
- [Runtime Isolation](../runtime-isolation.md)
- [Federation-ready v1](../federation-ready-v1.md)
- [Distributed Execution Model](./distributed-execution.md)
- [Federation Protocol](./federation-protocol.md)
- [路线图](../roadmap.md)
