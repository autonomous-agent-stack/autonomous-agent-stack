# Fast Policy Router and Slow Orchestration

Date: 2026-04-24

Status: proposed

## Context

AAS is evolving from a repository-change control plane into a broader agent control plane for heterogeneous workers, tools, runtimes, and trust boundaries. In that setting, a single heavyweight orchestrator should not sit on the synchronous path for every user request.

Some requests are routine and low-risk: route to a known worker, run a bounded tool, return a status update, or read a permitted capability. Other requests are high-cost or high-risk: use scarce GPU time, spend paid API budget, cross a domain boundary, request elevated authority, lease another AAS capability, or invoke human review.

If all traffic goes through the same slow orchestration path, AAS will pay unnecessary latency and cost for routine work. If all traffic bypasses orchestration, AAS loses governance, auditability, and escalation control.

## Decision

AAS should model request intake as two layers:

- **Fast policy router**: a low-latency, deterministic first hop that evaluates identity, capability, policy, budget, cost class, timeout, and whether a task is eligible for direct routing.
- **Slow orchestration layer**: a durable coordination path for escalation, cross-agent negotiation, cross-domain delegation, scarce-resource allocation, human approval, audit-heavy workflows, and failure recovery.

The fast policy router is not a replacement for orchestration. It is the default first decision point that keeps ordinary traffic responsive while preserving explicit escalation into the governed control plane.

## Default Routing Rules

The fast policy router should directly route a request only when all of these are true:

- The caller identity and trust tier are known.
- The target capability is registered and healthy.
- The capability policy allows the requested action.
- The request fits the caller's budget, quota, and cost class.
- The task can finish within the direct-route timeout.
- No elevated authority, cross-domain handoff, or human approval is required.

The router should escalate to slow orchestration when any of these are true:

- The request exceeds quota, paid-tool budget, GPU budget, or time budget.
- The request crosses an organization, account, tenant, repository, or AAS boundary.
- The request needs a lease, borrow contract, or capability not owned by the current domain.
- The policy outcome is ambiguous or conflicting.
- The request is high-risk, destructive, externally visible, or requires explicit approval.
- The direct route fails, times out, or returns a recoverable error.

## Capability Registry Implications

For the fast router to make deterministic decisions, capability descriptors should eventually include:

- `capability_id`
- `runtime_location`
- `owner_domain`
- `trust_tier`
- `allowed_actions`
- `cost_class`
- `quota_key`
- `budget_policy`
- `default_timeout_seconds`
- `direct_route_allowed`
- `requires_approval`
- `escalation_target`
- `audit_level`
- `health_status`

These fields can start as documentation-level contracts and later become typed models or API payloads.

## Resource Governance

Paid model calls, paid tools, GPU time, browser automation, file-system access, and external side effects should be treated as governed resources. The control plane should support:

- Per-user, per-team, or per-domain quotas.
- Cost classes for cheap, normal, expensive, and scarce work.
- Hard timeouts for direct-route work.
- Escalation thresholds for expensive or scarce capabilities.
- Audit events for allowance checks, denial, escalation, execution, and completion.

This keeps routine work fast while preventing a convenient interface from draining shared provider credits, local compute, or scarce worker time.

## Consequences

This decision preserves AAS's core separation of policy, capability, execution, and promotion while improving user-facing latency for routine work.

It also creates a clear path to federation: direct routing handles owned local capabilities, while slow orchestration handles leased capabilities, cross-AAS work orders, result contracts, settlement, and audit.

Implementation should start with a minimal policy table and capability metadata. The first implementation does not need distributed consensus, complex billing, or a general marketplace. It only needs to keep the direct path explicit, bounded, and auditable.
