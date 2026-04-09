# 状态与发布说明 (Status & Release Notes)

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

本文件用于客观记录 Autonomous Agent Stack 的真实工程进度与可用性判定，仅基于代码落点与实机验证结果编写。

## 🟢 核心已验证 (Implemented & Verified)

以下模块已在代码层面存在完整链路，且基础逻辑跑通：

- SQLite 仓储与会话层：OpenClawCompat 接口已实现，对话、评估记录支持断电持久化。
- Docker 动态沙盒：能够将代码路由至容器执行，AppleDouble (`._*`) 清理器代码已实装。
- Telegram 网关：Webhook 连通，支持 `/status` 指令返回短效 JWT 魔法链接。
- 零信任面板：JWT 验签与 Telegram UID 白名单逻辑已在路由层生效，基础浅色看板 UI 可用。
- 静态安全扫描 (AST)：拦截 `os.system` 等高危操作的双通道审计脚本已就绪。
- 知识图谱 (Micro-GraphRAG)：基于纯 Python + SQLite 的三元组存储已实现，玛露红线词汇（平替、代工厂）断言逻辑已就绪。

## 🟡 部分实现 / 简化版 (Partially Implemented / Mocked)

以下模块骨架已搭好，但在生产环境中采用了简化逻辑，尚未达成严格意义上的闭环：

- WebAuthn 生物识别：`/api/v1/auth/webauthn` 路由和前后端拦截器代码存在，但当前包含模拟（Mock）放行逻辑，未强制打通所有设备的真实指纹/面容硬件校验。
- P4 自主集成协议 (OpenSage)：发现、生成适配器并测试的流程骨架已写好，但“在沙盒中自主修复并热更新”的链路目前偏向于半自动化，需人为介入辅助。

## 🟠 仍待验证 (Pending Environment Validation)

由于当前开发环境存在限制，以下状态仅基于代码推演，缺乏稳定的实机运行证据：

- 并发稳定性：Deer-flow 并发控制与事件总线在应对高并发真实 API 回调时的稳定性，尚需实弹压测。
- 生态插件真实收益：P3 阶段的 OpenViking（Token 压缩）与 MiroFish（预测闸门）已作为插件挂载，但在长文本真实业务场景下的 Token 节约率尚无确切数据支撑。
- 全量测试通过率：代码库中包含大量测试用例，但在无特定环境配置的机器上直接执行，可能会因为依赖缺失或路径问题产生报错。

## 📝 下一步行动建议

1. 环境对齐：在目标 M1 宿主机上建立干净的 `venv`，全量安装 `requirements.txt` 并跑通 `pytest`，获取真实的测试覆盖率和通过率报告。
2. 红线实弹测试：向 Telegram 网关发送一张竞品截图或文案，验证视觉解析 + Micro-GraphRAG + Gatekeeper 拦截的完整业务链路是否按预期阻断“工厂化词汇”。
3. 移除 WebAuthn Mock：当准备好真正的生产部署时，清理 `webauthn.py` 中的模拟代码，对接真实的外部可信硬件配置。

## 🔎 参考入口

- OpenClaw 兼容服务：`src/autoresearch/core/services/openclaw_compat.py`
- 面板鉴权：`src/autoresearch/core/services/panel_access.py`
- 面板路由：`src/autoresearch/api/routers/panel.py`
- Telegram 网关：`src/autoresearch/api/routers/gateway_telegram.py`
- WebAuthn 简化路由：`src/autoresearch/api/routers/webauthn.py`
- 动态工具合成：`src/orchestrator/mcp_context.py`
- 沙盒清理：`src/orchestrator/sandbox_cleaner.py`
- 静态安全审计：`src/gatekeeper/static_analyzer.py`
