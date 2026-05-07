# RFC: Enterprise Runtime Governance Blueprint

**Status**: Draft | **Author**: AAS Core Team | **Created**: 2026-05-07
**Depends on**: [Architecture](../architecture.md), [Evergreen Agent Control Plane](../evergreen-agent-control-plane.md), [Runtime Isolation](../runtime-isolation.md), [Federation-ready v1](../federation-ready-v1.md), [Distributed Execution Model](./distributed-execution.md), [Federation Protocol](./federation-protocol.md), [Roadmap](../roadmap.md)

[Simplified Chinese](enterprise-runtime-governance-blueprint.zh-CN.md)

## Summary

This RFC is an umbrella alignment document for the long-term AAS runtime governance boundary. It does not replace the existing distributed execution, federation, runtime isolation, evergreen control-plane, or roadmap documents. It constrains how those tracks evolve together.

The current Python/FastAPI control plane remains authoritative. `/api/v2`, `SessionEvent`, `PolicyDecision`, `Approval`, `Artifact`, `Promotion`, and `Lease` remain the system record and governance spine.

## Motivation

AAS already separates the control plane from replaceable execution surfaces. The next long-term risk is not lack of runtime ambition; it is accidental fragmentation. Distributed workers, federation peers, model gateways, MCP tools, sandbox profiles, and future low-level supervisors must not grow into competing authorities.

This RFC defines the alignment contract for future work:

- control-plane facts stay above runtimes,
- evidence attaches to facts but does not replace them,
- supervisors may harden execution but must not own governance,
- resources remain accounted through AAS quota, lease, audit, and artifact ledgers.

## Authority Boundary

AAS is not rewriting the control plane in this track. The following remain authoritative:

- the Python/FastAPI control plane,
- `/api/v2` control-plane APIs,
- `SessionEvent` as the append-only factual timeline,
- `PolicyDecision` as the policy decision record,
- `Approval` as the human or delegated approval record,
- `Artifact` and `ArtifactRef` as result evidence references,
- `Promotion` as the explicit upgrade gate,
- `Lease` as the bounded authority for workers, peers, secrets, and mutable transitions.

Future runtime infrastructure must integrate under these records. A faster runtime, a stronger sandbox, or a supervisor sidecar may improve execution fidelity, but it cannot become the source of truth.

## RuntimeExecutionEnvelope

`RuntimeExecutionEnvelope` is the proposed contract carried from the control plane to any runtime, worker, tool boundary, federation peer, or future supervisor sidecar. It is a governance envelope, not a new scheduler.

Minimum fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `contract_version` | yes | Envelope schema version, for example `runtime-envelope/v1`. |
| `envelope_id` | yes | Unique envelope identifier. |
| `idempotency_key` | yes | Stable key used to avoid duplicate dispatch or duplicate evidence attachment. |
| `session_id` | yes | Authoritative AAS session id. |
| `task_id` | yes | Control-plane task id. |
| `run_id` | yes | Control-plane run id or worker-backed run id. |
| `capability_id` | yes | Capability being invoked. |
| `principal` | yes | Actor or service principal for the execution. |
| `policy_decision_ids` | yes | Policy decisions that authorize or constrain this execution. |
| `approval_id` | optional | Approval record required for sensitive or external actions. |
| `secret_lease_ids` | optional | Secret leases made available to the runtime by reference only. |
| `quota_entry_ids` | optional | Quota ledger entries reserved for this execution. |
| `isolation_profile` | yes | Runtime isolation profile selected by policy. |
| `network_policy_ref` | optional | Reference to the policy that governs external communication. |
| `model_policy_ref` | optional | Reference to the model policy governing model calls. |
| `deadline` | yes | Execution deadline used by the scheduler, worker, or supervisor. |
| `artifact_root` | yes | Authorized artifact output root for this execution. |
| `evidence_refs` | optional | Existing evidence references that the runtime may append to but not overwrite. |

Rules:

- The envelope is issued by AAS, not by the runtime.
- The runtime may reject an envelope it cannot satisfy.
- The runtime may add evidence references through authorized result reporting.
- The runtime must not widen policy, approval, quota, secret, or artifact authority beyond the envelope.

## GovernanceEvidenceEnvelope

`GovernanceEvidenceEnvelope` is a proposed attachment format for runtime evidence. It is not a source of truth. The source of truth remains `SessionEvent`.

Evidence may only become visible to the system through:

- a `SessionEvent` that references the evidence,
- an `ArtifactRef` that references the evidence.

Recommended evidence fields:

| Field | Meaning |
| --- | --- |
| `contract_version` | Evidence schema version. |
| `evidence_id` | Unique evidence identifier. |
| `envelope_id` | RuntimeExecutionEnvelope that produced the evidence. |
| `session_id` | Session associated with the evidence. |
| `task_id` | Task associated with the evidence. |
| `run_id` | Run associated with the evidence. |
| `capability_id` | Capability associated with the evidence. |
| `evidence_type` | Doctor report, isolation check, approval gate, quota transition, model call, tool call, artifact hash, replay check, or resource measurement. |
| `produced_by` | Runtime, worker, tool broker, federation peer, or supervisor component that emitted the evidence. |
| `artifact_refs` | Artifact references created or verified by this evidence. |
| `content_hashes` | Hashes for evidence payloads or emitted artifacts. |
| `resource_usage` | Measured CPU, memory, disk, duration, model usage, or credit-unit data when available. |
| `policy_refs` | Policy references involved in the evidence. |
| `created_at` | Creation timestamp. |
| `metadata` | Additional bounded diagnostic metadata. |

Evidence rules:

- Evidence explains what happened; it does not decide what is true.
- Evidence cannot override a `PolicyDecision`.
- Evidence cannot approve, promote, or mutate source state.
- Evidence without a `SessionEvent` or `ArtifactRef` reference remains diagnostic debris, not a system fact.

## Future Supervisor Sidecar Boundary

A future Rust, Zig, or other low-level supervisor sidecar may be introduced behind existing AAS runtime adapter contracts. The sidecar is optional and must remain subordinate to the control plane.

The supervisor sidecar may:

- start and stop isolated execution,
- collect runtime evidence,
- enforce the local sandbox profile selected by AAS,
- measure resource usage,
- emit artifacts into the authorized artifact root.

The supervisor sidecar must not:

- own approval,
- own promotion,
- mutate source,
- own credential authority,
- bypass `PolicyDecision`,
- bypass `SessionEvent` facts.

If a sidecar cannot report through the AAS control plane, its output is not authoritative. If it detects a violation, it should fail closed and emit evidence for AAS to record.

## Resource Abstraction

AAS continues to own resource governance. Future runtime infrastructure must reuse these control-plane concepts instead of creating parallel ledgers:

- quota,
- lease,
- cost attribution,
- artifact evidence,
- federation ledger,
- approval and audit facts.

The resource layer is intentionally broader than a single runtime process. It covers local workers, remote workers, governed MCP tools, model providers, federation peers, and future supervisor-managed execution.

## Non-Goals

This RFC does not authorize or implement:

- code changes,
- Rust or Zig implementation,
- settlement,
- marketplace behavior,
- live external write behavior,
- replacement of the FastAPI control plane,
- replacement of current GA gates.

## Implementation Direction

This RFC should be implemented incrementally:

1. Document the envelope contracts and align future RFCs to them.
2. Map existing `SessionEvent`, `ArtifactRef`, approval, quota, lease, and runtime isolation records to the envelope language.
3. Add code only in future RFC-backed changes, after the existing control-plane authority remains explicit.

## Relationship to Existing Documents

This RFC constrains the direction of:

- [Distributed Execution Model](./distributed-execution.md): workers receive bounded envelopes and report evidence back to the control plane.
- [Federation Protocol](./federation-protocol.md): peers receive lease-scoped envelopes and cannot receive promotion or credential authority.
- [Runtime Isolation](../runtime-isolation.md): isolation profiles are selected by AAS and may be enforced by runtimes or future supervisors.
- [Evergreen Agent Control Plane](../evergreen-agent-control-plane.md): the control plane remains the long-lived system authority above replaceable execution surfaces.
- [Roadmap](../roadmap.md): future supervisor or resource-abstraction work must strengthen the current control-plane spine rather than replace it.

## Risks and Mitigations

- Risk: envelope language becomes a parallel API. Mitigation: keep this RFC documentary until a later implementation RFC maps it to existing `/api/v2` models.
- Risk: supervisor sidecars become hidden authorities. Mitigation: sidecars can only emit evidence and artifacts under AAS-issued envelopes.
- Risk: evidence is mistaken for truth. Mitigation: require `SessionEvent` or `ArtifactRef` references before evidence becomes part of the system record.
- Risk: resource accounting fragments. Mitigation: quota, lease, cost attribution, federation ledgers, approvals, and audits stay in AAS.

## References

- [Architecture](../architecture.md)
- [Evergreen Agent Control Plane](../evergreen-agent-control-plane.md)
- [Runtime Isolation](../runtime-isolation.md)
- [Federation-ready v1](../federation-ready-v1.md)
- [Distributed Execution Model](./distributed-execution.md)
- [Federation Protocol](./federation-protocol.md)
- [Roadmap](../roadmap.md)
