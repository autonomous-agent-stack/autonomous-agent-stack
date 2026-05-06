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

Environment files: `make setup` creates `.env` from [`.env.example`](.env.example) when `.env` is missing. Prefer `.env.local` for secrets (gitignored). Do not commit real tokens.

Open after startup:

- API docs: `http://127.0.0.1:8001/docs`
- Control Plane v2 console: `http://127.0.0.1:8001/control-plane`
- Admin panel: `http://127.0.0.1:8001/panel`
- Legacy governance MVP panel: `http://127.0.0.1:8001/governance`
- Health check: `http://127.0.0.1:8001/health`

Control Plane v2 is the new production core path:

- `POST /api/v2/butler/route`: 管家自然语言路由预览，只生成任务草稿，不创建任务。
  `POST /api/v2/butler/route`: Butler natural-language route preview; creates a task draft without creating a task.
- `POST /api/v2/butler/tasks`: 管家自然语言任务入口，自动选择 capability、风险标签和优先级后交给 v2 控制面。
  `POST /api/v2/butler/tasks`: Butler natural-language task entrypoint; selects capability, risk tags, and priority before handing off to the v2 control plane.
- Telegram 管家任务卡片使用 MarkdownV2 展示入队、运行中、完成与取消状态，并标明负责 agent 与参与 agents。
  Telegram Butler task cards use MarkdownV2 for queued, running, completed, and cancellation states, and show the primary agent plus participating agents.
- Telegram 上下文追问使用原始追问做路由和任务标题，`/status` 只展示会话、worker 和最近任务摘要，避免泄露执行噪声。
  Telegram contextual follow-ups use the original follow-up for routing and task titles, while `/status` only shows session, worker, and recent-task summaries to avoid execution noise.
- `scripts/butlerctl` 与 `make butler-*` / `make agent-*` 提供本机一键启停和 Butler agent 热拔插。
  `scripts/butlerctl` plus `make butler-*` / `make agent-*` provide local one-command service control and Butler agent hot-plugging.
- `POST /api/v2/tasks`: create a governed task
- `GET /api/v2/tasks/{id}`: inspect task projection
- `POST /api/v2/tasks/{id}/approval`: approve or reject high-risk tasks
- `GET /api/v2/sessions/{id}/timeline`: replay the session fact log
- `GET /api/v2/capabilities`: list worker-backed and protocol-boundary capabilities
- `GET /api/v2/runs/{id}`: inspect the execution projection
- `GET /api/v2/runs/{id}/events`: inspect task/run/audit events

The v2 path uses the existing worker claim/report/lease scheduler as the
execution backbone. A2A, MCP, and future ADK integrations are modeled as
capability adapters and remain disabled until explicitly configured.

联邦就绪 v1 已加入 CrewAI-compatible agent adapter、受控 MCP 调用、用户/peer 配额账本、静态 peer 注册、agent/worker 租约和联邦任务 API。详见 [docs/federation-ready-v1.md](docs/federation-ready-v1.md)。
Federation-ready v1 now includes the CrewAI-compatible agent adapter, governed MCP calls, user/peer quota ledger, static peer registry, agent/worker leases, and federation task APIs. See [docs/federation-ready-v1.md](docs/federation-ready-v1.md).

Legacy governance MVP endpoints remain during the migration window:

- `POST /tasks`: create a governed task
- `GET /tasks/{id}`: inspect task state
- `POST /tasks/{id}/approve`: approve or reject high-risk tasks
- `GET /runs/{id}/events`: inspect run audit events
- `GET /adapters`: list local and protocol-boundary adapters

New development should use `/api/v2/*`. The old `/tasks` surface is kept only as
a compatibility shim while downstream callers migrate.

Validate the local setup:

```bash
make test-quick
make smoke-local
make hygiene-check
```

For detailed setup and troubleshooting, read [docs/QUICK_START.md](docs/QUICK_START.md). For remote or multi-machine execution, start with [docs/linux-remote-worker.md](docs/linux-remote-worker.md). If you want to run Hermes on Windows through WSL2 and let the base control plane take over, read [docs/windows-wsl2-hermes-control-plane.md](docs/windows-wsl2-hermes-control-plane.md).

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
- Fast policy router vs slow orchestration (butler: rules-first, model fill-in, Hermes for heavy work) — [docs/decisions/fast-policy-router-and-slow-orchestration-v1.md](docs/decisions/fast-policy-router-and-slow-orchestration-v1.md)
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
