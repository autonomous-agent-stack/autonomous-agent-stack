# Autonomous Agent Stack

**A governed, session-centered control plane for long-running agents.**

Run coding agents under zero-trust execution, durable session history, isolated capabilities, and explicit promotion gates instead of handing repository ownership to a single runtime.

[![CI](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20Draft-orange)](docs/rfc/)

**English** | [简体中文](README.zh-CN.md)

---

## What AAS Is

Autonomous Agent Stack (AAS) is a governed control plane for long-running agent execution.

It separates durable session history, execution capabilities, orchestration policies, and promotion authority so that no single model runtime gets to discover work, edit code, approve its own output, and publish it.

AAS is not a generic AI agent demo. It is built for teams that want to integrate tools such as OpenHands, Codex, or custom agents without collapsing trust boundaries. In AAS, those tools are execution surfaces, not the system of record.

Today, AAS is focused on a high-value vertical: governed repository changes. Long term, the same control-plane model is intended to support broader agent work across heterogeneous runtimes, tools, and environments.

AAS is evolving toward a more Agent OS-like control layer, but today it should first be understood as a governed control plane for long-running agents.

Over time, agent distribution may look increasingly app-like, with installable and removable agent packages, tools, or skills. But that is the distribution layer. AAS is concerned with the system layer beneath it: session, capability, policy, and promotion.

In federated settings, agents are not just app-like packages. They also behave like dispatched workers: scoped, leased, auditable, and recallable across trust boundaries. Capabilities may look like apps, agents behave more like workers, and AAS exists as the control plane that governs both.

## Why This Matters

As agents take on work that spans many context windows, the hard problem is no longer just "can the model code?"

The hard problem is:

- Can the system preserve progress across sessions?
- Can it recover state after failure or handoff?
- Can it isolate capabilities without making one runtime the trusted core?
- Can it promote privileged changes explicitly instead of implicitly?

Most agent stacks hard-code temporary model limitations into permanent architecture. AAS takes the opposite approach: keep the system abstractions stable, and keep the harness replaceable.

## Core Model

```text
Session -> policy -> isolated capability -> validation -> promotion
```

Current implementation focus:

```text
Planner -> isolated worker -> validation gate -> promotion gate -> patch artifact or draft PR
```

Core invariants:

- Patch-only by default
- Deny-wins policy merging
- Single-writer promotion for mutable state
- Runtime artifacts never promote into source
- Clean-base checks before draft PR promotion

Deep implementation details live in [ARCHITECTURE.md](ARCHITECTURE.md) and the RFC index in [docs/rfc/README.en.md](docs/rfc/README.en.md).

## Stable Abstractions

### Session

A durable execution history, not a mirror of the context window.

### Capability

Sandboxes, remote workers, MCP servers, browsers, and git proxies treated as isolated hands.

### Policy

Replaceable orchestration rules for context assembly, retries, evaluation, escalation, and routing.

### Promotion

Explicit, auditable state transitions for any privileged change.

## What Makes AAS Different

| Traditional agent stack | AAS |
|---|---|
| Agent gets repository write authority | Worker produces a bounded patch candidate |
| Planning, execution, and merge authority live in one runtime | Policy, execution, and promotion are separated |
| Validation is optional or ad hoc | Validation and promotion rules are on the main path |
| External tools become the de facto control plane | Tools plug into a governed control plane |
| Runtime state leaks into source changes | Runtime artifacts and source promotion are isolated |
| Trust is implicit | Zero-trust invariants are explicit and auditable |

## Design Principles

- Do not turn temporary model weaknesses into permanent system architecture.
- Do not let a single runtime become the trusted core.
- Do not rely on the model being "not clever enough" for security.
- Keep orchestration replaceable.
- Keep privileged changes explicit.
- Preserve recoverable history outside the context window.

## Quick Start

Requirements:

- Python 3.11+
- `make`
- Docker or Colima for `ai-lab` and sandbox-backed flows (optional for basic local startup)

```bash
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

Open after startup:

- API docs: `http://127.0.0.1:8001/docs`
- Admin panel: `http://127.0.0.1:8001/panel`
- Health check: `http://127.0.0.1:8001/health`

Validate the local setup:

```bash
make test-quick
make smoke-local
make hygiene-check
```

For detailed setup and troubleshooting, read [docs/QUICK_START.md](docs/QUICK_START.md). For remote or multi-machine execution, start with [docs/linux-remote-worker.md](docs/linux-remote-worker.md).

Native Windows support is currently limited to the minimal local control-plane path:
`make setup`, `make doctor`, and `make start`. Other targets still assume Bash and/or macOS/Linux tooling.

## Stable Single-Machine Mode

**v0.1.0-stable** establishes a verified baseline for running AAS on a single machine without external dependencies.

The default mode is **minimal** (stable), which:
- Starts reliably with core features only
- Makes optional routers non-blocking
- Disables experimental features by default
- Suitable for local development and testing

```bash
# Default: minimal mode (stable)
AUTORESEARCH_MODE=minimal make start

# Full mode: all features (experimental)
AUTORESEARCH_MODE=full make start
```

### What Works in Stable Mode

| Feature | Status |
|---------|--------|
| FastAPI application | ✅ Starts at `http://127.0.0.1:8001` |
| SQLite control plane | ✅ `artifacts/api/*.sqlite3` |
| AEP runner (mock) | ✅ End-to-end execution |
| Worker schedules | ✅ APScheduler-backed `once` / `interval` schedules via `/api/v1/worker-schedules` |
| Runtime artifact exclusion | ✅ Patch hygiene enforced |
| Health/docs endpoints | ✅ All respond correctly |

### What's Explicitly Out of Scope

- Distributed execution (requires queue infrastructure)
- Telegram integration (requires bot token)
- WebAuthn (requires additional setup)
- Cluster mode (distributed coordination only)
- Complex cron syntax and multi-node scheduling

See [STATUS_AND_RELEASE_NOTES.md](STATUS_AND_RELEASE_NOTES.md) for complete details.

## Requirement #4 Ready Baseline

**Branch**: `feat/single-machine-aas-ready-for-req4`
**Status**: ✅ Engineering Scaffold Complete - **NOT Production Complete**

This branch provides a **complete engineering scaffold** for requirement #4 (Excel commission processing). All preparation is done - business logic implementation can start immediately when required assets arrive.

⚠️ **This is a "stable single-machine requirement-4 ready baseline"** - engineering scaffold is complete and verified, but business logic implementation is blocked awaiting business assets.

### What's Ready

| Component | File | Status |
|-----------|------|--------|
| Commission Engine | `src/autoresearch/core/services/commission_engine.py` | ✅ Deterministic interface |
| Excel Jobs Repository | `src/autoresearch/core/repositories/excel_jobs.py` | ✅ SQLite-backed |
| Excel Ops Service | `src/autoresearch/core/services/excel_ops.py` | ✅ Orchestration layer |
| Excel Ops Router | `src/autoresearch/api/routers/excel_ops.py` | ✅ REST API |
| Models & Contracts | `src/autoresearch/shared/excel_ops_models.py` | ✅ Schemas defined |
| Contract Tests | `tests/test_excel_ops_service.py` | ✅ Verify blocking |
| Validation Script | `scripts/validate_stable_baseline.sh` | ✅ `make validate-req4` |

### Awaiting Business Assets

| Asset | Purpose | Location |
|-------|---------|----------|
| Excel contracts | File schemas, column mappings | `tests/fixtures/requirement4_contracts/` |
| Ambiguity checklist | 7 categories of edge case decisions | `tests/fixtures/requirement4_contracts/` |
| Sample Excel files | Real input data for testing | `tests/fixtures/requirement4_samples/` |
| Golden outputs | Expected calculation results | `tests/fixtures/requirement4_golden/` |

### Validate Scaffold

```bash
# Validate requirement #4 readiness
make validate-req4

# Run contract tests
pytest tests/test_excel_ops_service.py -v

# Check readiness status
cat docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md
```

### Safety Guarantees

- **No Silent Calculations**: Blocks without valid contracts
- **Deterministic Only**: No LLM reasoning in production path
- **Audit Trail**: Job state tracked in SQLite
- **Runtime Artifact Exclusion**: Patches exclude `.masfactory_runtime/`, `logs/`, `memory/`

**See**: [docs/requirement4/](docs/requirement4/) for complete preparation details.

**For implementation**:
- English: [docs/requirement4/CLAUDE_CODE_BEST_PRACTICES.md](docs/requirement4/CLAUDE_CODE_BEST_PRACTICES.md)
- 中文: [docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md](docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md)
- **资产到达后的行动指南**: [docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md](docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md) ⭐ **推荐** - 包含 4 个必需资产的详细说明和示例

---

## Controlled Integrations

## Controlled Integrations

AAS is designed to integrate agent runtimes without turning them into the trusted core:

- OpenHands as a constrained worker behind patch-only contracts and promotion gates
- Codex and custom adapters through controlled execution and AEP-style job specs
- Remote workers for machine-specific capabilities, credentials, or isolated execution surfaces
- GitHub and chat-triggered workflows routed back into the same control plane

See [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md), [docs/agent-execution-protocol.md](docs/agent-execution-protocol.md), and [docs/linux-remote-worker.md](docs/linux-remote-worker.md).

## Documentation

Start here:

- [WHY_AAS.md](WHY_AAS.md): project motivation and design direction
- [docs/QUICK_START.md](docs/QUICK_START.md): detailed setup and troubleshooting
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution workflow and expectations

Go deeper:

- [ARCHITECTURE.md](ARCHITECTURE.md): canonical current architecture
- [docs/agent-execution-protocol.md](docs/agent-execution-protocol.md): execution contract and policy model
- [docs/api-reference.md](docs/api-reference.md): API surface

Explore integrations and evolution:

- [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md): OpenHands as a controlled worker
- [docs/github-assistant-quickstart.md](docs/github-assistant-quickstart.md): GitHub assistant flows
- [docs/rfc/README.en.md](docs/rfc/README.en.md): RFC index and design process

## Roadmap

### Now

A stable single-repo control plane with isolated execution and promotion checks.

### Next

- Session-first recovery and replay
- Capability registry for heterogeneous workers and tools
- Policy seams for orchestration strategies
- Distributed execution with durable queues, leases, and heartbeats

### Long Term

A governed runtime substrate for long-running agent work across multiple models, multiple hands, and multiple trust boundaries.

## Who This Is For

AAS is for teams that want:

- autonomous execution without repository ownership
- durable progress across long-running tasks
- zero-trust safety boundaries
- auditable promotion workflows
- multi-runtime interoperability without surrendering control

## Contributing

If you want to contribute, start with [CONTRIBUTING.md](CONTRIBUTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Small documentation fixes and focused bug fixes are good first contributions. Architectural changes should start as an RFC in [docs/rfc/](docs/rfc/).

A typical local loop is:

```bash
make review-setup
make test-quick
make hygiene-check
make review-gates-local
```

`make review-setup` installs mypy, bandit, and semgrep into `.venv-review` so the
main `.venv` can stay aligned with `make setup`.

Open an issue or discussion if you want to validate a design direction before implementation.

## License

[MIT](LICENSE)
