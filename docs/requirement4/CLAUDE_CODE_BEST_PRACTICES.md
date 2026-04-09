# Using Claude Code CLI for Requirement #4 Implementation

## Overview

This guide explains how to use **Claude Code CLI** to implement requirement #4 (Excel commission processing) once business assets are provided.

## Prerequisites

1. **Claude Code CLI Installed**
   ```bash
   # Install via npm
   npm install -g @anthropic-ai/claude-code

   # Or via homebrew (macOS)
   brew install claude-code
   ```

2. **Branch Checked Out**
   ```bash
   git checkout feat/single-machine-aas-ready-for-req4
   git pull origin feat/single-machine-aas-ready-for-req4
   ```

3. **Environment Setup**
   ```bash
   make setup
   make doctor
   ```

## Step 1: Verify Baseline

Before starting implementation, verify the scaffold is ready:

```bash
make validate-req4
```

Expected output: All checks should pass with ✅ indicators.

## Step 2: Accept Business Assets

When business provides the 4 required assets:

```bash
# Place assets in fixture directories
tests/fixtures/requirement4_contracts/
├── excel_contracts.json          # Business provides
└── ambiguity_checklist.md        # Business provides

tests/fixtures/requirement4_samples/
└── *.xlsx                        # Business provides (1-3 files)

tests/fixtures/requirement4_golden/
├── *.xlsx                        # Business provides
└── golden_metadata.json          # Business provides
```

## Step 3: Initialize Claude Code Session

Start a Claude Code session in the repository:

```bash
cd /path/to/autonomous-agent-stack
claude
```

## Step 4: Context Loading Strategy

Load context incrementally to avoid overwhelming Claude:

### Phase 1: Load Architecture (First Session)
```
Please read the following files to understand the architecture:
1. docs/requirement4/ENGINEERING_PREP_PLAN.md
2. docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md
3. src/autoresearch/core/services/commission_engine.py
4. src/autoresearch/core/repositories/excel_jobs.py
5. src/autoresearch/core/services/excel_ops.py
```

### Phase 2: Load Contracts (Second Session)
```
Now read the business contracts:
1. tests/fixtures/requirement4_contracts/excel_contracts.json
2. tests/fixtures/requirement4_contracts/ambiguity_checklist.md
3. tests/fixtures/requirement4_golden/golden_metadata.json
```

### Phase 3: Load Samples (Third Session)
```
Now examine the sample Excel files:
1. tests/fixtures/requirement4_samples/*.xlsx
2. tests/fixtures/requirement4_golden/*.xlsx
```

## Step 5: Implementation Prompts

### 5.1 Understand Contracts
```
Based on the contracts in tests/fixtures/requirement4_contracts/:

1. What are the input file roles? (e.g., source_data, rate_table, agent_list)
2. What columns are expected in each input file?
3. What calculation rules are defined?
4. What validation rules apply?

Create a summary document: docs/requirement4/CONTRACT_SUMMARY.md
```

### 5.2 Implement Commission Engine
```
Implement the commission calculation logic in src/autoresearch/core/services/commission_engine.py:

Requirements:
1. Load contracts from tests/fixtures/requirement4_contracts/excel_contracts.json
2. Parse Excel files from tests/fixtures/requirement4_samples/
3. Apply calculation rules per the ambiguity checklist
4. Return results in CommissionCalculationResult format
5. No LLM calls in the calculation path (deterministic only)

Use openpyxl for Excel parsing. Implement validation per contracts.
```

### 5.3 Implement Excel Parsing
```
Add Excel file parsing to src/autoresearch/core/services/excel_ops.py:

1. Read input files from job.input_files
2. Map columns per excel_contracts.json
3. Validate data per ambiguity_checklist.md
4. Normalize to CommissionCalculationRequest format
5. Handle missing/invalid data with explicit errors
```

### 5.4 Implement Validation
```
Implement validation in src/autoresearch/core/services/excel_ops.py:

1. Add validate_job() method
2. Check results against golden outputs
3. Verify within tolerances from golden_metadata.json
4. Return ExcelValidationResult with findings
```

## Step 6: Testing Strategy

### 6.1 Run Contract Tests
```bash
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v
```

### 6.2 Run E2E Tests
```bash
PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v
```

### 6.3 Golden Output Comparison
```
Create a test to verify:
1. Load sample files from tests/fixtures/requirement4_samples/
2. Run calculation via CommissionEngine
3. Compare output with tests/fixtures/requirement4_golden/*.xlsx
4. Verify within tolerances from golden_metadata.json

Add to tests/test_excel_ops_service.py as test_golden_output_match()
```

## Step 7: Wire Service (After Validation)

Once tests pass against golden outputs:

```
Wire the excel_ops service in src/autoresearch/api/dependencies.py:

1. Import ExcelOpsService, ExcelJobsRepository, CommissionEngine
2. Create database path: artifacts/api/excel_jobs.db
3. Initialize service instance
4. Wire to get_excel_ops_service dependency
5. Remove HTTPException 501 from router
```

## Step 8: Final Validation

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/test_excel_ops_*.py tests/test_e2e_pipeline_verification.py -v

# Validate baseline
make validate-req4

# Smoke test
make smoke-local
```

## Best Practices

### DO ✅
- Load context in phases, not all at once
- Use specific file paths in prompts
- Ask Claude to create summary documents before coding
- Run tests after each implementation step
- Verify against golden outputs before wiring service
- Keep calculations deterministic (no LLM in production path)

### DON'T ❌
- Don't ask Claude to "read the entire codebase"
- Don't skip contract review before implementation
- Don't wire service before validation passes
- Don't use LLM for calculations (use Python/openpyxl)
- Don't modify core architecture without understanding it
- Don't skip tests against golden outputs

## Example Session Flow

```
# Session 1: Architecture review
claude
> Read docs/requirement4/ENGINEERING_PREP_PLAN.md
> Read src/autoresearch/core/services/commission_engine.py
> Summarize the blocked states and why they exist

# Session 2: Contract review
claude
> Read tests/fixtures/requirement4_contracts/excel_contracts.json
> Create docs/requirement4/CONTRACT_SUMMARY.md with:
>   - Input file roles and schemas
>   - Calculation rules
>   - Validation requirements

# Session 3: Implementation
claude
> Read src/autoresearch/core/services/commission_engine.py
> Read docs/requirement4/CONTRACT_SUMMARY.md
> Implement calculate() method to:
>   1. Parse sample Excel files
>   2. Apply commission rules
>   3. Return CommissionCalculationResult
>   4. No LLM calls

# Session 4: Testing
claude
> Run: PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v
> If tests fail, fix implementation
> Create golden output comparison test

# Session 5: Integration
claude
> Read src/autoresearch/api/dependencies.py
> Wire excel_ops service
> Run smoke test
```

## Troubleshooting

### Issue: Tests fail after implementation
**Solution**:
```bash
# Check test output for specific failures
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v --tb=short

# Compare with golden outputs manually
python -c "
import pandas as pd
expected = pd.read_excel('tests/fixtures/requirement4_golden/output.xlsx')
actual = pd.read_excel('artifacts/test_output.xlsx')
print(expected.compare(actual))
"
```

### Issue: Commission engine blocked
**Solution**: Ensure contract files are in place:
```bash
ls -la tests/fixtures/requirement4_contracts/
# Should see excel_contracts.json and ambiguity_checklist.md
```

### Issue: Service returns 501
**Solution**: Wire service in dependencies.py and remove HTTPException from router.

## Next Steps After Implementation

1. **Business Review**: Share results with business for approval
2. **Pilot Deployment**: Deploy in minimal mode for pilot testing
3. **Monitor**: Track calculation accuracy and performance
4. **Iterate**: Fix issues found during pilot

## References

- **Preparation Plan**: `docs/requirement4/ENGINEERING_PREP_PLAN.md`
- **Next Steps**: `docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md`
- **Checklist**: `docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md`
- **Hardening**: `docs/requirement4/BASELINE_HARDENING_PLAN.md`
