# Distributed Control Plane Architecture: One Brain, Many Hands

> **Decision date:** 2026-04-08
> **Status:** Active
> **Applies to:** Multi-machine agent cluster, cross-platform worker coordination

---

## Core Principle

> **一个控制面，多个能力节点；节点不互相指挥，只向控制面领活和回报。**

One control plane, multiple capability nodes; nodes do not command each other, they only claim work from and report back to the control plane.

---

## Problem Statement

As the agent stack grows from single-machine to multi-machine:

- Linux butler needs Mac's DD GitHub assistant capability
- Mac has Lisa/DD GitHub agents
- Each machine may have different capabilities (OpenHands, YouTube, Excel audit, GitHub assistant)
- Point-to-point communication becomes unmanageable as nodes scale
- Need unified orchestration, routing, audit, and failure recovery

**Key question:** Should we use blockchain for consensus?

**Answer:** No. This is an orchestration problem, not a consensus problem.

---

## Industry References

This architecture draws from:

| System | Concept We Adopt |
|--------|------------------|
| **Kubernetes** | Control plane / node registration, heartbeat / lease model |
| **Celery / NATS** | Broker / queue / request-reply pattern |
| **Temporal** | Durable workflow orchestration, saga pattern |
| **Blockchain** (only) | Append-only audit ledger思想 (not as primary scheduler) |

We do **not** adopt blockchain's consensus algorithm because:

- Single team / single ops domain
- Machines are relatively trusted
- Problem is orchestration, not Byzantine fault tolerance
- Need low-latency scheduling, not distributed consensus

---

## Architecture Overview

### Phase 1: One Brain, Many Hands

```
┌─────────────────────────────────────────────────────────────────┐
│                     Control Plane (Linux)                       │
│  - API Server                                                   │
│  - Task Queue / Broker                                          │
│  - Capability Registry                                          │
│  - Orchestrator / Scheduler                                     │
│  - Audit Log                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ enqueue / claim / report
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Mac Worker 1 │    │ Mac Worker 2 │    │ Linux Worker │
│ Capabilities:│    │ Capabilities:│    │ Capabilities:│
│ - github:dd  │    │ - github:lisa│    │ - openhands  │
│ - claude_rt  │    │ - claude_rt  │    │ - youtube    │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Phase 2: Capability-Based Routing

Workers register with capabilities, not personalities:

```json
{
  "worker_id": "mac-mini-01",
  "capabilities": [
    "github_assistant:dd",
    "github_assistant:lisa",
    "claude_runtime"
  ],
  "constraints": {
    "os": "macos",
    "interactive_login": true,
    "network_zone": "tailscale"
  }
}
```

Control plane routes by capability:

```
Task: "Review PR on repo X with DD profile"
→ Filter: workers with "github_assistant:dd"
→ Select: healthy, low-load worker
→ Enqueue: to selected worker's queue
```

---

## Worker Task Type Extension

### Current State

Existing `WorkerTaskType` in codebase:

```python
class WorkerTaskType(str, Enum):
    NOOP = "noop"
    CLEANUP = "cleanup"
    YOUTUBE_ACTION = "youtube_action"
    YOUTUBE_AUTOFLOW = "youtube_autoflow"
    CLAUDE_RUNTIME = "claude_runtime"
    EXCEL_AUDIT = "excel_audit"
```

### Required Addition

GitHub assistant is NOT yet a first-class worker task type. Need to add:

```python
class WorkerTaskType(str, Enum):
    # ... existing ...
    GITHUB_ASSISTANT_TRIAGE = "github_assistant_triage"
    GITHUB_ASSISTANT_REVIEW_PR = "github_assistant_review_pr"
    GITHUB_ASSISTANT_RELEASE_PLAN = "github_assistant_release_plan"
    GITHUB_ASSISTANT_ACTION = "github_assistant_action"  # unified
```

### Mac Worker Executor Extension

`src/autoresearch/workers/mac/executor.py` needs new branches:

```python
async def execute_github_assistant(task: WorkerTask) -> TaskResult:
    """Execute GitHub assistant task on Mac worker."""
    action = task.payload.get("action")
    profile = task.payload.get("profile", "dd")

    # Call local GitHub assistant API or CLI
    result = await github_assistant_service.execute(
        action=action,
        profile=profile,
        **task.payload.get("params", {})
    )

    return TaskResult(
        status="completed",
        output=result
    )
```

---

## Communication Patterns

### ❌ Anti-Pattern: Point-to-Point Mesh

```
Linux butler ──direct call──> Mac butler ──direct call──> Windows
     ↑                                ↓
     └────────────────────────────────┘
```

Problems:
- Unmanaged dependency graph
- No unified retry/failure handling
- Hard to audit
- Scalability nightmare

### ✅ Pattern: Star Topology via Control Plane

```
                Control Plane
                     │
     ┌───────┬───────┼───────┬───────┐
     │       │       │       │       │
 Linux   Mac-1   Mac-2  Win-1  Win-2
```

Benefits:
- Single orchestration point
- Unified routing and scheduling
- Centralized audit
- Easy to add/remove workers

---

## Short-Term Solution (Phase 1)

### Linux Butler → Mac GitHub Assistant

**Recommended approach:** HTTP API bridge

```
Linux Butler
    │
    └─> HTTP POST → Mac GitHub Assistant API
                      /api/v1/github-assistant/*
                      (executed with DD profile on Mac)
```

**Why this works:**

1. DD GitHub credentials stay on Mac
2. Linux doesn't need GitHub login
3. Mac API already has `doctor`, `triage`, `execute`, `review-pr`, `release-plan`
4. Tailscale/private network for security

**Implementation sketch:**

```python
# Linux butler calls Mac
async def call_mac_github_assistant(action: str, params: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://mac-mini:8000/api/v1/github-assistant/{action}",
            json=params,
            headers={"X-Profile": "dd"}  # DD profile on Mac
        ) as resp:
            return await resp.json()
```

---

## Medium-Term Solution (Phase 2)

### Integrate GitHub Assistant into Worker Queue

**Step 1:** Add task types

```python
# src/autoresearch/workers/models.py
class WorkerTaskType(str, Enum):
    GITHUB_ASSISTANT_TRIAGE = "github_assistant_triage"
    GITHUB_ASSISTANT_REVIEW_PR = "github_assistant_review_pr"
    GITHUB_ASSISTANT_RELEASE_PLAN = "github_assistant_release_plan"
    GITHUB_ASSISTANT_EXECUTE = "github_assistant_execute"
```

**Step 2:** Extend Mac executor

```python
# src/autoresearch/workers/mac/executor.py
async def execute_task(task: WorkerTask) -> TaskResult:
    if task.type == WorkerTaskType.GITHUB_ASSISTANT_REVIEW_PR:
        return await execute_github_assistant_review(task)
    elif task.type == WorkerTaskType.GITHUB_ASSISTANT_TRIAGE:
        return await execute_github_assistant_triage(task)
    # ... other types
```

**Step 3:** Capability registration

```python
# Worker startup registration
worker.register_capabilities({
    "worker_id": "mac-dd-github",
    "capabilities": [
        "github_assistant:triage",
        "github_assistant:review_pr",
        "github_assistant:release_plan",
        "github_assistant:execute"
    ],
    "default_profile": "dd"
})
```

---

## Long-Term Solution (Phase 3)

### Workflow Engine for Long-Running Chains

When task chains become complex:

```
YouTube Ingest → Content KB → GitHub PR → Approval → Release
```

Need durable workflow orchestration (Temporal-style):

- Persistent workflow state
- Automatic retry with backoff
- Human approval steps
- Long-running activity support
- Saga pattern for compensation

**This is NOT blockchain.** This is workflow orchestration.

---

## Capability Registry Design

### Registration Schema

```json
{
  "worker_id": "mac-mini-dd-worker",
  "hostname": "mac-mini.local",
  "capabilities": [
    {
      "type": "github_assistant",
      "profile": "dd",
      "actions": ["triage", "review_pr", "release_plan", "execute"],
      "constraints": {
        "requires_interactive_login": true,
        "network_zone": "tailscale"
      }
    },
    {
      "type": "claude_runtime",
      "version": "4.6",
      "constraints": {
        "gpu_required": false
      }
    }
  ],
  "health_check_url": "http://mac-mini:8000/health",
  "last_heartbeat": "2026-04-08T10:30:00Z"
}
```

### Routing Logic

```python
def route_task(task: Task) -> Optional[str]:
    """Select worker_id for task, or None if no capable worker."""
    required_capability = task.required_capability

    candidates = [
        w for w in registry.workers
        if required_capability in w.capabilities
        and w.is_healthy()
        and w.load < w.capacity
    ]

    if not candidates:
        return None

    # Select by least load
    return min(candidates, key=lambda w: w.load).worker_id
```

---

## Audit and Observability

### Unified Audit Log

All task executions MUST log:

```json
{
  "run_id": "run_20260408_103000_xyz",
  "timestamp": "2026-04-08T10:30:00Z",
  "task_type": "github_assistant_review_pr",
  "worker_id": "mac-mini-dd-worker",
  "capability_used": "github_assistant:dd",
  "params_hash": "sha256:...",
  "result_status": "completed",
  "result_hash": "sha256:...",
  "duration_ms": 15230,
  "requester": "linux-butler",
  "approval_required": false
}
```

### Observability Stack

- **Metrics:** queue depth, worker load, task latency
- **Logs:** structured JSON per run
- **Traces:** distributed tracing for multi-step workflows
- **Alerts:** worker heartbeat loss, task timeout, queue buildup

---

## Security Considerations

### Network

- Use Tailscale or private network for worker-control communication
- Never expose worker APIs to public internet
- Mutual TLS for control plane → worker communication

### Credentials

- GitHub profiles (DD, Lisa) stay on respective Macs
- Linux never stores GitHub tokens
- Each worker manages its own credential lifecycle

### Approval Gates

- Dangerous operations (repo mutation, release) require explicit approval
- Approval linked to `run_id`, not worker
- Audit trail records who approved what

---

## Implementation Roadmap

### Phase 1: HTTP Bridge (Immediate)

- [ ] Linux butler can call Mac GitHub assistant API
- [ ] Document Mac API endpoints
- [ ] Add simple retry logic
- [ ] Basic audit logging

### Phase 2: Worker Queue Integration (Next Sprint)

- [ ] Add `GITHUB_ASSISTANT_*` task types
- [ ] Extend Mac worker executor
- [ ] Implement capability registration
- [ ] Implement capability-based routing

### Phase 3: Durable Workflows (Future)

- [ ] Evaluate Temporal or similar
- [ ] Design workflow schema
- [ ] Implement saga pattern for compensating transactions
- [ ] Add human approval steps

---

## Design Principles

1. **Single Control Plane** — Only one logical scheduler/routing authority
2. **Capability-Based** — Workers expose capabilities, control plane routes by need
3. **No Peer-to-Peer Commands** — Workers don't command each other
4. **Audit Everything** — Every task execution is logged with full provenance
5. **Fail Gracefully** — No worker = queue and wait, not cascade failure
6. **Credentials Stay Local** — GitHub profiles, API keys remain on source machine

---

## Anti-Patterns to Avoid

| ❌ Don't | ✅ Do Instead |
|---------|---------------|
| Each machine runs a "butler" that commands others | Single control plane, multiple workers |
| Point-to-point HTTP calls between machines | Star topology via control plane |
| Blockchain for consensus | Centralized orchestration + audit log |
| Hardcode machine names in routing | Capability-based dynamic routing |
| Duplicate credentials across machines | Local credentials, remote execution |
| Ad-hoc shell scripts for cross-machine calls | Typed worker task protocol |

---

## Summary

**Architecture slogan:**

> 一个控制面，多个能力节点；节点不互相指挥，只向控制面领活和回报。

**Key takeaways:**

1. This is orchestration, not consensus — Kubernetes/Celery/Temporal are better references than blockchain
2. Control plane routes by capability, not machine personality
3. Workers claim tasks and report results; they don't command peers
4. GitHub assistant will become a first-class worker task type
5. Short term: HTTP bridge from Linux to Mac GitHub assistant API
6. Long term: Unified worker queue with capability registry

---

## References

- Kubernetes: https://kubernetes.io/docs/concepts/architecture/control-plane/
- Celery: https://docs.celeryq.io/en/stable/
- Temporal: https://temporal.io/
- Current worker queue: `src/autoresearch/workers/`
- GitHub assistant API: `src/autoresearch/api/routes/github_assistant.py`
