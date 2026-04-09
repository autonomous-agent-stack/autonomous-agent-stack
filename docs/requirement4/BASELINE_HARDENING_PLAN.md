# Baseline Hardening Plan

**Branch**: `feat/single-machine-aas-ready-for-req4`
**Goal**: Harden and verify the requirement-4 ready baseline
**Date**: 2026-04-09

## Current State Assessment

### What Exists ✅
- Commission engine interface (deterministic-only)
- Excel jobs repository (SQLite-backed)
- Excel ops service and router (scaffold)
- Model contracts defined
- Fixture directories with README placeholders
- Contract tests for blocking behavior
- Validation script skeleton

### What Needs Hardening 🔧
1. **End-to-end startup verification** - Need to verify app actually starts with excel_ops router
2. **API-level tests** - Need actual router tests, not just service tests
3. **Stronger blocked-state model** - Need granular blocked statuses
4. **Mock e2e verification** - Need to prove pipeline works end-to-end
5. **Validation improvements** - Need more comprehensive checks
6. **Release wording** - Remove any "production-quality" claims

## Implementation Plan

### Priority 1: End-to-End Startup Verification
- [x] Test app startup with default minimal mode
- [x] Verify excel_ops router is registered
- [x] Add smoke test for running app
- [x] Verify `/health`, `/docs`, `/panel` endpoints

### Priority 2: API-Level Verification
- [x] Create `tests/test_excel_ops_router.py`
- [x] Test job registration endpoint
- [x] Test job retrieval endpoint
- [x] Test blocked status responses
- [x] Test requirement-4 status endpoint

### Priority 3: Stronger Blocked-State Model
- [x] Define granular blocked status enum
- [x] Update models to use specific blocked statuses
- [x] Document each blocked state clearly
- [x] Test each blocked state explicitly

### Priority 4: Mock E2E Fixture Verification
- [x] Create minimal synthetic fixture
- [x] Test job creation → artifact generation → SQLite persistence
- [x] Verify runtime artifact exclusion
- [x] Add promotion patch hygiene test

### Priority 5: Validation Improvements
- [x] Enhance `validate_stable_baseline.sh`
- [x] Add router registration check
- [x] Add blocked-state test verification
- [x] Add runtime artifact hygiene check
- [x] Make validation fail clearly on issues

### Priority 6: Release Wording Tightening
- [x] Remove "production-quality" language
- [x] Use "engineering scaffold complete"
- [x] Add "not production complete" disclaimers
- [x] Update all README and notes

## Success Criteria

After hardening:
1. App starts reliably in minimal mode
2. Excel ops router is registered and reachable
3. All blocked states are explicit and tested
4. Mock e2e flow works end-to-end
5. Validation script fails clearly on missing pieces
6. No "production complete" claims
7. Next developer has clear handoff documentation

## File Changes Expected

### New Files
- `tests/test_excel_ops_router.py` - Router API tests
- `tests/test_e2e_pipeline_verification.py` - Mock e2e test

### Modified Files
- `src/autoresearch/shared/excel_ops_models.py` - Add blocked status enum
- `src/autoresearch/core/services/commission_engine.py` - Use specific blocked statuses
- `src/autoresearch/core/services/excel_ops.py` - Return granular blocked statuses
- `scripts/validate_stable_baseline.sh` - Enhance validation
- `STATUS_AND_RELEASE_NOTES.md` - Tighten wording
- `README.md` - Update descriptions

## Non-Goals (Explicitly Out of Scope)

- ❌ Implement real business logic
- ❌ Add distributed components
- ❌ Fake commission formulas
- ❌ Expand beyond requirement #4 scope
- ❌ Make calculations work without contracts
