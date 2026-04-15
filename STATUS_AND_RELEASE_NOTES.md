# Status & Release Notes

---

## Requirement #4 Ready Baseline (v0.2.0-req4-ready)

**Status**: ✅ Engineering Scaffold Complete - **NOT Production Complete**
**Branch**: `feat/single-machine-aas-ready-for-req4`
**Date**: 2026-04-09
**Label**: "Stable single-machine requirement-4 ready baseline"

### What This Branch Provides

This branch establishes a **complete engineering scaffold** for requirement #4 (Excel commission processing). The scaffold is ready for immediate business logic implementation once the required assets arrive.

⚠️ **This is NOT production complete**. It is "requirement-4 ready" - meaning all engineering preparation is done, but business rules are blocked until assets are provided.

### Engineering Scaffold (COMPLETE)

| Component | Status | Notes |
|-----------|--------|-------|
| **Commission Engine Interface** | ✅ Complete | Deterministic-only, blocks without contracts |
| **Excel Jobs Repository** | ✅ Complete | SQLite-backed, audit trail support |
| **Excel Ops Service** | ✅ Complete | Orchestration layer with pipeline stages |
| **Excel Ops Router** | ✅ Complete | REST API endpoints (awaiting wiring) |
| **Model Contracts** | ✅ Complete | Request/response models defined |
| **Fixture Directories** | ✅ Complete | README placeholders for samples/golden/contracts |
| **Contract Tests** | ✅ Complete | Verify explicit blocking behavior |
| **Validation Script** | ✅ Complete | `make validate-req4` checks scaffold |

### Business Assets Required (NOT YET PROVIDED)

| Asset | Status | Location |
|-------|--------|----------|
| **Input/Output Excel Contracts** | ❌ Awaiting business | `tests/fixtures/requirement4_contracts/` |
| **Ambiguity Checklist (7 categories)** | ❌ Awaiting business | `tests/fixtures/requirement4_contracts/` |
| **1-3 Real Excel Samples** | ❌ Awaiting business | `tests/fixtures/requirement4_samples/` |
| **Golden Outputs + Audit Loop** | ❌ Awaiting business | `tests/fixtures/requirement4_golden/` |

### Safety Guarantees

This branch enforces these safety guarantees:

1. **No Silent Calculations**
   - All calculations return `blocked_awaiting_contracts` status without valid contracts
   - Explicit error messages explain what's missing
   - No fallback or guessing behavior

2. **Deterministic Only**
   - No LLM/freeform reasoning in production path
   - All rules must be explicitly defined
   - Calculation results are reproducible

3. **Audit Trail**
   - All jobs tracked with validation/review/approval markers
   - SQLite persistence for job state
   - Runtime artifacts excluded from patches

### Quick Start

```bash
# 1. Setup
make setup

# 2. Validate environment
make doctor

# 3. Validate requirement #4 scaffold
make validate-req4

# 4. Run contract tests
pytest tests/test_excel_ops_service.py -v

# 5. Start API (minimal mode)
make start
```

### What Happens When Assets Arrive

Once business provides the 4 required assets:

1. **Day 1**: Accept assets, map to contracts
2. **Week 1**: Implement business rules in `CommissionEngine`
3. **Week 2**: Validate against golden outputs
4. **Go-live**: Enable pilot workflow

**Estimated time**: 7-12 days from asset delivery to pilot readiness.

**See**: `docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md` for detailed implementation sequence.

### Hardening & Verification (2026-04-09)

The baseline has been hardened and verified with:

- **44 passing tests** covering:
  - E2E pipeline verification (13 tests)
  - Router API contracts (14 tests)
  - Service and repository tests (17 tests)

- **Granular blocked-state model** with explicit status values:
  - `blocked_awaiting_contracts` - Business rule contracts not provided
  - `blocked_awaiting_ambiguity_decisions` - 7-category checklist missing
  - `blocked_awaiting_samples` - Real Excel sample files missing
  - `blocked_awaiting_golden_outputs` - Golden outputs + audit loop missing
  - `blocked_awaiting_audit_workflow` - Approval workflow undefined

- **Runtime artifact exclusion verified** - logs/, .masfactory_runtime/, memory/, .git/ paths filtered from promotion patches

- **Enhanced validation script** - `scripts/validate_stable_baseline.sh` checks:
  - Python version and environment
  - Core import availability
  - SQLite setup
  - Router registration
  - Runtime artifact exclusion
  - Contract tests

**See**: `docs/requirement4/BASELINE_HARDENING_PLAN.md` for hardening checklist.

**See**: `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES.md` (English) or `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md` (中文) for using Claude Code CLI to implement requirement #4 once assets arrive.

**See**: `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md` (中文) for detailed action plan when business assets arrive - includes examples of the 4 required assets and step-by-step implementation guide.

---

## Stable Single-Machine Baseline (v0.1.0-stable)

**Status**: ✅ Verified (superseded by v0.2.0-req4-ready)
**Branch**: `feat/stable-single-machine-release`
**Date**: 2026-04-09

### What Is Verified

This release establishes a **stable, local-first baseline** for running Autonomous Agent Stack on a single machine without external dependencies.

| Component | Status | Notes |
|-----------|--------|-------|
| **FastAPI Application** | ✅ Verified | Starts reliably in minimal mode |
| **SQLite Control Plane** | ✅ Verified | `artifacts/api/evaluations.sqlite3` |
| **Local Artifacts** | ✅ Verified | `.masfactory_runtime/runs/` |
| **AEP Runner (Mock)** | ✅ Verified | End-to-end with mock adapter |
| **Runtime Artifact Exclusion** | ✅ Verified | Deny prefixes enforced |
| **Health/Docs Endpoints** | ✅ Verified | `/health`, `/docs`, `/` respond |
| **Environment Validation** | ✅ Verified | `make doctor` checks pass |

### Quick Start (Stable Mode)

```bash
# 1. Setup
make setup

# 2. Validate environment
make doctor

# 3. Start API (minimal mode is default)
make start

# 4. Verify
curl http://127.0.0.1:8001/health
open http://127.0.0.1:8001/docs

# 5. Run smoke test
make smoke-local
```

### Configuration

Stable mode is controlled by `AUTORESEARCH_MODE`:

```bash
# Default: minimal (stable)
export AUTORESEARCH_MODE=minimal

# Full mode: includes experimental features
export AUTORESEARCH_MODE=full
```

In **minimal mode** (default):
- Core routers only: capabilities, approvals, workers, worker_runs, panel
- Optional routers are non-blocking (logged as warnings if skipped)
- Telegram, WebAuthn, cluster features disabled by default
- Suitable for local development and testing

In **full mode**:
- All routers enabled
- May fail if optional dependencies missing
- For experimental features and distributed workflows

### Tested Workflows

1. **Application Startup**
   ```bash
   AUTORESEARCH_MODE=minimal make start
   ```
   Expected: API starts at `http://127.0.0.1:8001`

2. **Mock AEP Run**
   ```bash
   make agent-run AEP_AGENT=mock AEP_TASK='Create test file'
   ```
   Expected: Run artifacts in `.masfactory_runtime/runs/aep-mock-*/`

3. **Smoke Test**
   ```bash
   make smoke-local
   ```
   Expected: All tests pass

### Explicit Non-Goals

This baseline explicitly does NOT include:

| Feature | Status | Reason |
|---------|--------|--------|
| **Distributed Execution** | ❌ Non-goal | Requires queue infrastructure (future) |
| **Telegram Integration** | ⚠️ Optional | Requires bot token configuration |
| **WebAuthn** | ⚠️ Optional | Requires additional setup |
| **Cluster Mode** | ❌ Non-goal | Distributed coordination |
| **OpenHands Backend** | ⚠️ Experimental | Requires ai-lab setup |
| **Production Hardening** | ❌ Non-goal | This is a development baseline |

### Architecture Notes

The stable baseline maintains these invariants:

1. **Patch-Only Execution**
   - Workers produce patch candidates, not direct git mutations
   - Runtime artifacts (`logs/`, `.masfactory_runtime/`, `memory/`) excluded

2. **Zero-Trust Promotion**
   - GitPromotionGateService validates before branch/PR operations
   - Clean base requirement prevents local edits from masquerading as agent output

3. **Graceful Degradation**
   - Optional routers fail without blocking startup
   - Clear logging indicates which features were skipped

4. **Local Control Plane**
   - SQLite for approvals, capabilities, worker runs
   - File-based artifacts for execution history

### Verification Checklist

Before declaring this baseline stable:

- [x] `make setup`, `make doctor`, `make start` work on clean Mac
- [x] `/health`, `/docs`, `/panel` respond (panel shows "not built" fallback)
- [x] AEP runner works end-to-end with mock backend
- [x] SQLite-backed state persists across restarts
- [x] Runtime artifacts excluded from promotion patches
- [x] Smoke test passes: `make smoke-local`
- [x] README updated with "Stable Single-Machine Mode"
- [x] STATUS_AND_RELEASE_NOTES.md updated
- [x] All unstable features clearly marked experimental

### References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Canonical system architecture
- [docs/QUICK_START.md](docs/QUICK_START.md) - Detailed setup guide
- [docs/IMPLEMENTATION_PLAN_STABLE_SINGLE_MACHINE.md](docs/IMPLEMENTATION_PLAN_STABLE_SINGLE_MACHINE.md) - Implementation plan

---

## Historical Notes (Pre-Stable)

最后更新：2026-03-26
目标版本：MVP 集成版（基于 main 分支）
**Last Updated**: 2026-04-08
**Target Version**: MVP Integration (main branch)

This file objectively tracks the engineering progress and availability of Autonomous Agent Stack, based only on code commits and verification results.

## 🟢 Implemented & Verified

The following modules have complete code paths and verified base logic:

- **SQLite Repository & Session Layer**: OpenClawCompat interface implemented with persistent dialog and evaluation records.
- **Dynamic Docker Sandbox**: Routes code execution to containers with AppleDouble (`._*`) cleaner implemented.
- **Telegram Gateway**: Webhook connected, supports `/status` command returning short-lived JWT magic links.
- **Zero-Trust Panel**: JWT verification and Telegram UID whitelist logic active at router layer, basic light theme UI available.
- **Static Security Scanning (AST)**: Dual-channel audit scripts intercepting high-risk operations like `os.system`.
- **Knowledge Graph (Micro-GraphRAG)**: Triple storage based on pure Python + SQLite implemented, Maru Redline vocabulary assertions (substitute, OEM factory) in place.
- **GitHub Assistant Template**: Local-first GitHub assistant skeleton with `/api/v1/github-assistant/*` endpoints integrated.
- **Excel Audit Engine**: Deterministic engine with commission_check DSL (#53).
- **Butler Intent Router + Async Telegram Flow**: Intent routing and async excel_audit via Telegram (#55).
- **GitHub Admin Execute-Prep**: Dry-run readiness checks for GitHub operations (#56).
- **Foundation Minimal Closure**: Foundation contracts for unified agent layer (#58).
- **Content KB Agent**: Subtitle ingestion, topic classification, and index building (#60).

## 🟡 Partially Implemented / Mocked

The following modules have scaffolding but use simplified logic in production:

- **WebAuthn Biometric**: `/api/v1/auth/webauthn` route and frontend/backend interceptor code exists, but currently includes mock bypass logic. Real fingerprint/face hardware validation not enforced.
- **P4 Self-Integration Protocol (OpenSage)**: Skeleton for discovery, adapter generation, and testing exists. The "auto-fix in sandbox with hot-reload" path is semi-automated and requires human intervention.
- **GitHub Real Execution**: `execute-transfer` returns 501. GitHub admin remains in dry-run / execute-prep boundary. Real GitHub operations not enabled.

## 🟠 Pending Environment Validation

Due to development environment limitations, the following status is based on code projection without stable live verification:

- **Concurrency Stability**: Deer-flow concurrent control and event bus stability under high-concurrency real API callbacks needs load testing.
- **Ecosystem Plugin Benefits**: P3 phase OpenViking (Token compression) and MiroFish (predictive gate) are mounted as plugins. Real Token savings in long-text business scenarios lack data support.
- **Full Test Pass Rate**: Codebase contains many tests. Direct execution without specific environment configuration may fail due to missing dependencies or path issues.

## 📝 Current Guardrails

- `execute-transfer` returns 501 (not implemented)
- GitHub real execution is disabled
- `github_admin` remains in dry-run / execute-prep boundary
- Foundation contracts merged but not extended to real entry main chain rewrite

## 🔎 Reference Entry Points

- OpenClaw compatibility service: `src/autoresearch/core/services/openclaw_compat.py`
- Panel auth: `src/autoresearch/core/services/panel_access.py`
- Panel router: `src/autoresearch/api/routers/panel.py`
- Telegram gateway: `src/autoresearch/api/routers/gateway_telegram.py`
- WebAuthn simplified route: `src/autoresearch/api/routers/webauthn.py`
- Dynamic tool synthesis: `src/orchestrator/mcp_context.py`
- Sandbox cleaner: `src/orchestrator/sandbox_cleaner.py`
- Static security audit: `src/gatekeeper/static_analyzer.py`
- GitHub assistant: `src/autoresearch/api/routers/github_assistant.py`
- Excel audit: `src/excel_audit/`
- Butler router: `src/butler/`
- GitHub admin: `src/github_admin/`
- Foundation contracts: `src/foundation/`
- Content KB: `src/content_kb/`
