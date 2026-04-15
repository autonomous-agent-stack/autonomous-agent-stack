# Requirement #4 Engineering Preparation Plan

**Branch**: `feat/single-machine-aas-ready-for-req4`
**Status**: In Progress
**Date**: 2026-04-09

## Objective

Prepare a **stable single-machine engineering baseline** so that when business provides the 4 required assets, implementation of requirement #4 can start immediately.

**This branch is NOT production complete.** It is "requirement-4 ready" - meaning the engineering scaffolding exists but business logic is blocked until assets arrive.

## Business Assets Required (Not Yet Provided)

1. **Input/Output Excel contracts** - File role specifications, column schemas, validation rules
2. **Ambiguity checklist** - Decisions covering 7 categories of edge cases
3. **1-3 real Excel samples** - Actual input files for testing
4. **Golden outputs + audit/approval loop** - Expected results and validation process

**Engineering does NOT invent these.** We provide the scaffold; business provides the rules.

## Current Repo State

### What Already Exists ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Excel audit router | ✅ Found | `src/autoresearch/api/routers/excel_audit.py` |
| Excel audit service | ✅ Found | `src/autoresearch/core/services/excel_audit.py` |
| Excel audit contracts | ✅ Found | `src/autoresearch/shared/excel_audit_contract.py` |
| Job status enum | ✅ Found | In `src/autoresearch/shared/models.py` |
| SQLite repository pattern | ✅ Found | `src/autoresearch/shared/store.py` |
| Minimal mode startup | ✅ Found | From previous stable baseline work |
| Runtime artifact exclusion | ✅ Found | In `AgentExecutionRunner` |

### What Needs to Be Created 🔨

| Component | Path | Priority |
|-----------|------|----------|
| Commission engine interface | `src/autoresearch/core/services/commission_engine.py` | HIGH |
| Excel jobs repository | `src/autoresearch/core/repositories/excel_jobs.py` | HIGH |
| Excel ops router | `src/autoresearch/api/routers/excel_ops.py` | MEDIUM |
| Excel ops service | `src/autoresearch/core/services/excel_ops.py` | MEDIUM |
| Expanded models | `src/autoresearch/shared/excel_ops_models.py` | MEDIUM |
| Fixture directories | `tests/fixtures/requirement4_*` | MEDIUM |
| Requirement-4 docs | `docs/requirement4/` | MEDIUM |
| Contract tests | `tests/test_excel_ops_*.py` | LOW |
| Smoke validation | `scripts/validate_stable_baseline.sh` | LOW |

## Implementation Order

### Phase 1: Core Scaffold (High Priority)
1. Create commission engine interface with deterministic behavior
2. Create excel jobs repository (SQLite-backed)
3. Create excel ops models and contracts
4. Add "blocked: awaiting business assets" responses

### Phase 2: Router/Service Layer (Medium Priority)
5. Create excel ops router with upload/register endpoints
6. Create excel ops service for orchestration
7. Wire up dependencies in `src/autoresearch/api/dependencies.py`

### Phase 3: Testing & Fixtures (Medium Priority)
8. Create fixture directories with README placeholders
9. Create requirement-4 doc structure
10. Add contract-first tests for router/service/engine

### Phase 4: Validation & Docs (Low Priority)
11. Create smoke validation script
12. Update README, QUICK_START, STATUS_NOTES
13. Create implementation ready checklist
14. Create handoff document

## Non-Goals (Explicitly Out of Scope)

- ❌ Distributeed system components
- ❌ Cloud service dependencies
- ❌ AI runtime decisions for commission calculation
- ❌ Speculative business logic implementation
- ❌ Fake commission formulas
- ❌ Production completeness claims

## Hard Constraints

1. **Deterministic Only** - Runtime commission calculation must be deterministic
2. **Explicit Blocking** - Missing contracts/rules → explicit blocked status
3. **No LLM Money Math** - No LLM should compute money in production path
4. **Useful Immediately** - Branch useful for engineering prep even before business assets

## Success Criteria

A. Single-machine mode starts reliably on clean Mac
B. Default mode is stable and minimal-first
C. `/health`, `/docs`, `/panel` work or degrade gracefully
D. SQLite control-plane storage works locally
E. Runtime artifacts excluded from promotion patches
F. Clear requirement-4 scaffold exists in repo
G. README/release notes explain "requirement-4 ready baseline"
H. Documented handoff point for next implementation PR

## File Changes Summary

### New Files (Estimated 15-20)
- 4 service/engine modules
- 2 router modules
- 2 repository modules
- 2 model/contract modules
- 4 test files
- 3 doc files
- 2 fixture directories with README

### Modified Files (Estimated 5-8)
- `src/autoresearch/api/main.py` (add excel_ops router)
- `src/autoresearch/api/dependencies.py` (add deps)
- `Makefile` (add validation target)
- `README.md` (update)
- `docs/QUICK_START.md` (update)
- `STATUS_AND_RELEASE_NOTES.md` (update)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Scope creep | Strict adherence to scaffold-only implementation |
| Business logic leakage | All placeholders return explicit "not ready" errors |
| Test flakiness | Use deterministic fixtures, mock external deps |
| Dependency drift | Pin core routers, allow optional to fail |

## Handoff Criteria

When business assets arrive, the next developer should be able to:
1. Drop sample files into `tests/fixtures/requirement4_samples/`
2. Add golden outputs to `tests/fixtures/requirement4_golden/`
3. Implement business rules in `commission_engine.py`
4. Run contract tests to verify behavior
5. Enable pilot workflow

All scaffolding for this workflow must exist in this branch.
