# Requirement #4 Implementation Ready Checklist

**Branch**: `feat/single-machine-aas-ready-for-req4`
**Last Updated**: 2026-04-09
**Status**: ✅ Engineering Scaffold Complete

This checklist separates what engineering has prepared from what business still needs to provide.

---

## ✅ Engineering Preparation (COMPLETE)

### Core Scaffold
- [x] Commission engine interface (`src/autoresearch/core/services/commission_engine.py`)
- [x] Excel jobs repository (`src/autoresearch/core/repositories/excel_jobs.py`)
- [x] Excel ops service (`src/autoresearch/core/services/excel_ops.py`)
- [x] Excel ops router (`src/autoresearch/api/routers/excel_ops.py`)
- [x] Excel ops models (`src/autoresearch/shared/excel_ops_models.py`)

### Key Features
- [x] Deterministic-only commission calculation interface
- [x] Explicit blocking when business contracts missing
- [x] SQLite-backed job persistence
- [x] Audit trail support (validation, review, approval markers)
- [x] Runtime artifact exclusion from patches

### Testing
- [x] Contract-first tests for service/engine/repository
- [x] Tests verify explicit blocking (no silent failures)
- [x] Fixture directory structure with README placeholders

### Documentation
- [x] Engineering preparation plan
- [x] Fixture READMEs (samples, golden, contracts)
- [x] Implementation ready checklist (this file)
- [x] Next steps handoff document

### Validation
- [x] Validation script (`scripts/validate_stable_baseline.sh`)
- [x] Checks environment, imports, scaffold presence
- [x] No accidental runtime-artifact promotion

---

## ⏳ Business Assets Required (NOT YET PROVIDED)

### 1. Input/Output Excel Contracts

**Status**: ❌ Not provided

**Needed**:
- File role specifications (source_data, configuration, reference, rate_table, agent_list)
- Column schemas and data types for each role
- Validation rules per column
- Required vs optional fields

**Location**: `tests/fixtures/requirement4_contracts/excel_contracts.json`

**Template**: See `tests/fixtures/requirement4_contracts/README.md`

---

### 2. Ambiguity Checklist (7 Categories)

**Status**: ❌ Not provided

**Needed**:
Decisions documented for each of 7 categories:

1. **Data Completeness** - Missing/null values, empty rows
2. **Data Validation** - Out-of-range values, invalid formats
3. **Calculation Rules** - Edge cases in formulas, rounding
4. **Agent Mapping** - Unmapped agents, split commissions
5. **Time Periods** - Partial periods, cutoff times
6. **Rate Tiers** - Boundary conditions, tier transitions
7. **Adjustments** - Manual adjustments, corrections

**Location**: `tests/fixtures/requirement4_contracts/ambiguity_checklist.md`

---

### 3. Real Excel Samples (1-3 files)

**Status**: ❌ Not provided

**Needed**:
- `sample_input_1.xlsx` - Primary input file
- `sample_input_2.xlsx` - Secondary input (if applicable)
- `sample_configuration.xlsx` - Configuration/rate table (if applicable)
- `samples_metadata.json` - File descriptions and mappings

**Requirements**:
- Real or realistic data matching production use cases
- Clear sheet structure with named columns
- Representative row count and complexity

**Location**: `tests/fixtures/requirement4_samples/`

---

### 4. Golden Outputs + Audit/Approval Loop

**Status**: ❌ Not provided

**Needed**:
- `golden_commission_report.xlsx` - Expected calculation results
- `golden_validation_report.xlsx` - Expected validation findings
- `golden_audit_trail.json` - Expected audit trail
- `golden_metadata.json` - Verification details and tolerances

**Audit/Approval Loop**:
- Define approval criteria
- Specify acceptable tolerances
- Document approvers and sign-off process

**Location**: `tests/fixtures/requirement4_golden/`

---

## 🚀 Ready-to-Start Trigger

Once the 4 business assets are provided:

### Immediate (Day 1)
1. Review sample files → document schemas
2. Review golden outputs → document expected results
3. Load contracts into `CommissionEngine`
4. Wire up `excel_ops` router in dependencies.py

### Short-term (Week 1)
5. Implement rule execution logic in `CommissionEngine`
6. Add data normalization for sample file format
7. Create comparison tests against golden outputs
8. Implement approval workflow markers

### Validation (Week 2)
9. Run fixture-vs-golden tests
10. Verify tolerances and edge cases
11. Document any deviations from golden outputs
12. Business sign-off on calculation correctness

### Go-Live
13. Enable pilot workflow
14. Monitor first real runs
15. Iterate on edge cases

---

## 📋 Implementation Sequence

When assets arrive, follow this sequence:

**Phase 1: Contract Integration** (1-2 days)
1. Drop sample files into `tests/fixtures/requirement4_samples/`
2. Add golden outputs to `tests/fixtures/requirement4_golden/`
3. Create `excel_contracts.json` based on sample schemas
4. Create `ambiguity_checklist.md` with 7 categories
5. Load contracts in `CommissionEngine.load_contracts()`

**Phase 2: Rule Implementation** (3-5 days)
6. Implement rule parsing from contracts
7. Add data normalization for input format
8. Implement calculation rules deterministically
9. Add intermediate result tracking for audit trail

**Phase 3: Testing & Validation** (2-3 days)
10. Create tests comparing outputs to golden
11. Test all ambiguity checklist decisions
12. Verify tolerances are met
13. Document any edge cases

**Phase 4: Integration & Go-Live** (1-2 days)
14. Wire up excel_ops router in dependencies.py
15. Add API endpoint tests
16. Business sign-off on results
17. Enable pilot workflow

**Total Estimated Time**: 7-12 days once assets arrive

---

## 🔒 Safety Guarantees

This branch maintains these safety guarantees:

1. **No Silent Calculations**
   - All calculations blocked without valid contracts
   - Explicit error messages explain what's missing
   - No fallback or guessing behavior

2. **Deterministic Only**
   - No LLM/freeform reasoning in production path
   - All rules must be explicitly defined
   - Calculation results are reproducible

3. **Audit Trail**
   - All jobs tracked with status markers
   - Validation/approval state persisted
   - Runtime artifacts excluded from patches

4. **Graceful Degradation**
   - Missing contracts → blocked status, not crash
   - Invalid data → validation error, not silent skip
   - Clear error messages guide next steps

---

## 📞 Handoff Point

**When business assets arrive, the next developer should:**

1. Read `NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md`
2. Place assets in appropriate fixture directories
3. Follow implementation sequence above
4. Update this checklist as items are completed

**Current blocker**: Awaiting 4 business assets (see above)

**Engineering readiness**: ✅ Complete - ready to implement immediately when assets arrive

---

## 📚 Related Documentation

- [ENGINEERING_PREP_PLAN.md](ENGINEERING_PREP_PLAN.md) - Detailed preparation plan
- [NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md](NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md) - Handoff instructions
- [../../README.md](../../README.md) - Project README
- [../../STATUS_AND_RELEASE_NOTES.md](../../STATUS_AND_RELEASE_NOTES.md) - Release notes

---

**Last verified**: 2026-04-09
**Verified by**: Engineering baseline validation script
**Next review**: When business assets arrive
