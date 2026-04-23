# Stable Single-Machine AAS Release - Implementation Plan

**Status**: Draft
**Branch**: `feat/stable-single-machine-release`
**Created**: 2026-04-09
**Owner**: AAS Release Team

## Executive Summary

This plan delivers a **stable, local-first Autonomous Agent Stack** that can run on a single Mac without distributed components, cloud services, or experimental features. The focus is on a verified baseline that works reliably out of the box.

## Target Definition

A stable single-machine AAS must provide:

1. **One FastAPI entrypoint** - `make start` launches API at `http://127.0.0.1:8001`
2. **One SQLite control-plane database** - `artifacts/api/evaluations.sqlite3`
3. **One local artifact/runtime directory** - `.masfactory_runtime/runs/`
4. **One controlled AEP execution path** - `make agent-run` with mock backend
5. **One working validation/promotion flow** - patch artifacts without runtime leakage
6. **One reproducible smoke-test** - `make test-quick` passes locally

## Audit Summary

### What Already Works ✅

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI application | ✅ Stable | `src/autoresearch/api/main.py` exists and structured |
| SQLite repositories | ✅ Implemented | Control-plane state in `artifacts/api/*.sqlite3` |
| AEP runner | ✅ Implemented | `src/autoresearch/executions/runner.py` with full policy merge |
| Agent registry | ✅ Implemented | `configs/agents/*.yaml` with mock/openhands adapters |
| Promotion gate | ✅ Implemented | Runtime artifact filtering in place |
| Environment checks | ✅ Implemented | `scripts/doctor.py` validates Python/modules |
| Local testing | ✅ Partial | `tests/test_workflow_quick.py` runs but limited |

### What Blocks Stability ❌

| Issue | Severity | Impact |
|-------|----------|--------|
| **Required routers may fail import** | HIGH | App won't start if any optional dependency missing |
| **Experimental features enabled by default** | MEDIUM | WebAuthn, cluster may fail without extra setup |
| **Telegram integration hard-required** | MEDIUM | Fails startup if bot token not configured |
| **No minimal startup mode** | HIGH | All routes load; no "local-only" mode |
| **Test coverage gap** | MEDIUM | No E2E test for happy path |
| **Documentation assumes too much** | LOW | Quick Start exists but not "stable mode" focused |

## Implementation Strategy

### Phase 1: Safe Startup Mode (Core Stability)

**Goal**: Application starts even when optional components are unavailable.

1. **Add `AUTORESEARCH_MODE` environment variable**
   - Values: `minimal` (stable), `full` (experimental)
   - Default: `minimal` for safety

2. **Graceful router loading** in `src/autoresearch/api/main.py`
   - Wrap optional routers in try/except
   - Log skipped routers clearly
   - Only critical routers (health, meta, AEP) are required

3. **Feature flags for experimental paths**
   - `enable_telegram`: default `False` in minimal mode
   - `enable_webauthn`: default `False` in minimal mode
   - `enable_cluster`: default `False` always (distributed)

### Phase 2: Verified Local Workflow (End-to-End)

**Goal**: One complete happy path that works without external services.

1. **Create minimal smoke test** `tests/test_stable_local_smoke.py`
   - Start app in minimal mode
   - Hit `/health` endpoint
   - Run mock AEP job
   - Verify patch artifact created
   - Verify runtime artifacts excluded

2. **Add `make smoke-local` target**
   - Runs `pytest tests/test_stable_local_smoke.py -v`
   - Fails fast if baseline breaks

3. **Document local AEP run**
   - `make agent-run AEP_AGENT=mock AEP_TASK='test'`
   - Verify artifacts in `.masfactory_runtime/runs/aep-mock-*/`

### Phase 3: Documentation & Release Notes

**Goal**: Clear communication about what is verified vs experimental.

1. **Update README.md**
   - Add "Stable Single-Machine Mode" section
   - Document `AUTORESEARCH_MODE=minimal`
   - Separate stable features from experimental

2. **Create STATUS_AND_RELEASE_NOTES.md**
   - List verified components (A, B, C, D, E, F from Definition of Done)
   - Mark non-goals explicitly
   - Document remaining risks

3. **Update QUICK_START.md**
   - Prerequisites section (Python 3.11+, make)
   - Minimal mode setup steps
   - Troubleshooting common issues

## Definition of Done Checklist

- [ ] `make setup`, `make doctor`, `make start` work on clean Mac
- [ ] `/health`, `/docs`, `/panel` respond (panel may show "not built")
- [ ] AEP runner works end-to-end with mock backend
- [ ] SQLite-backed state persists across restarts
- [ ] Runtime artifacts excluded from promotion patches
- [ ] Smoke test passes: `make smoke-local`
- [ ] README updated with "Stable Single-Machine Mode"
- [ ] STATUS_AND_RELEASE_NOTES.md created
- [ ] All unstable features clearly marked experimental

## Files to Modify

| File | Change | Reason |
|------|--------|--------|
| `src/autoresearch/api/settings.py` | Add `mode` field | Support minimal/full modes |
| `src/autoresearch/api/main.py` | Graceful router loading | Prevent startup failures |
| `.env.example` | Add `AUTORESEARCH_MODE` | Document new setting |
| `tests/test_stable_local_smoke.py` | **NEW** | E2E smoke test |
| `Makefile` | Add `smoke-local` target | Easy verification |
| `README.md` | Add stable mode section | User-facing docs |
| `STATUS_AND_RELEASE_NOTES.md` | **NEW** | Release communication |
| `docs/QUICK_START.md` | Update for minimal mode | Better onboarding |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Router import fails | Wrap all optional routers in try/except |
| SQLite init fails | Add directory creation with parents=True |
| Mock adapter missing | Verify configs/agents/mock.yaml exists |
| Test flakiness | Use deterministic run IDs and temp directories |
| Documentation drift | Link docs to specific git refs/tags |

## Additional Gates (Per User Requirement)

Before treating branch as releasable, enforce:

1. **Ambiguities → Explicit documented decisions**
   - Every `TODO` becomes either a task or documented non-goal
   - All environment variables documented in `.env.example`

2. **Real sample workflow**
   - `examples/stable_local_demo.py` showing mock AEP run
   - Golden output in `tests/fixtures/golden_mock_run/`

3. **Golden output checked in**
   - `tests/fixtures/golden_mock_run/summary.json`
   - `tests/fixtures/golden_mock_run/promotion.patch`

4. **Minimal audit/approval loop**
   - `scripts/validate_stable_baseline.sh`
   - Checks: clean git status, passing tests, doctor OK

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Startup success rate | 100% | `make start` on clean checkout |
| Smoke test pass rate | 100% | `make smoke-local` |
| Mock AEP success rate | 100% | `make agent-run AEP_AGENT=mock` |
| Runtime artifact exclusion | 100% | Patch file validation |

## Timeline Estimate

- Phase 1 (Safe Startup): 2-3 hours
- Phase 2 (Verified Workflow): 2-3 hours
- Phase 3 (Documentation): 1-2 hours
- Validation & Testing: 1-2 hours

**Total**: 6-10 hours of focused work

## Next Steps

1. Create branch `feat/stable-single-machine-release` ✅
2. Implement Phase 1 changes
3. Add Phase 2 smoke test
4. Update documentation (Phase 3)
5. Run validation checklist
6. Create PR for review
