# Next Steps: Once Business Assets Arrive

**Branch**: `feat/single-machine-aas-ready-for-req4`
**For**: Next developer implementing requirement #4
**When**: After business provides the 4 required assets

> Current execution note:
> For the repository's current requirement-4 source of truth, use
> `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md` and
> `docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md`.
> This note is supplemental context, not the canonical 2-day pilot plan.

---

## Overview

This branch contains a **complete engineering scaffold** for requirement #4 (Excel commission processing). When business provides the required assets, you can start implementing business logic immediately.

**What's Already Done**:
- Commission engine interface (deterministic-only)
- Excel jobs repository (SQLite-backed)
- Excel ops service and router
- Model contracts and validation
- Test scaffold and fixture directories
- Documentation and validation scripts

**What You Need to Do**:
1. Accept business assets into fixture directories
2. Map sample files to input roles
3. Encode ambiguity decisions
4. Implement business rules
5. Validate against golden outputs

---

## Step 1: Accept Business Assets

### 1.1 Receive Assets from Business

You should receive:
1. **Input/output Excel contracts** - File schemas, column mappings, validation rules
2. **Ambiguity checklist** - Decisions for 7 categories of edge cases
3. **1-3 Excel sample files** - Real input data
4. **Golden outputs** - Expected calculation results

### 1.2 Place Assets in Fixture Directories

```bash
# Copy sample files
cp /path/to/sample_input_1.xlsx tests/fixtures/requirement4_samples/
cp /path/to/sample_input_2.xlsx tests/fixtures/requirement4_samples/  # if provided

# Create samples metadata
cat > tests/fixtures/requirement4_samples/samples_metadata.json << 'EOF'
{
  "samples": [
    {
      "filename": "sample_input_1.xlsx",
      "role": "source_data",
      "description": "Transaction data",
      "sheets": {},
      "provided_by": "Business Team",
      "provided_date": "2026-04-09"
    }
  ]
}
EOF

# Copy golden outputs
cp /path/to/golden_commission_report.xlsx tests/fixtures/requirement4_golden/
cp /path/to/golden_validation_report.xlsx tests/fixtures/requirement4_golden/  # if provided

# Create golden metadata
cat > tests/fixtures/requirement4_golden/golden_metadata.json << 'EOF'
{
  "outputs": [
    {
      "filename": "golden_commission_report.xlsx",
      "description": "Expected commission results",
      "derived_from": "sample_input_1.xlsx",
      "verified_by": "Business Team",
      "verified_date": "2026-04-09"
    }
  ],
  "tolerances": {
    "absolute": 0.01,
    "percentage": 0.001,
    "rounding": "nearest_cent"
  }
}
EOF

# Create contracts
cat > tests/fixtures/requirement4_contracts/excel_contracts.json << 'EOF'
# Business will provide JSON schema defining:
# - Input file roles and sheets
# - Column schemas and data types
# - Validation rules
# See README.md for template
EOF

# Create ambiguity checklist
cp /path/to/ambiguity_checklist.md tests/fixtures/requirement4_contracts/
```

### 1.3 Verify Assets

Run validation script:
```bash
make validate-req4  # or bash scripts/validate_stable_baseline.sh
```

---

## Step 2: Map Sample Files to Input Roles

### 2.1 Analyze Sample Structure

Open each sample file and document:

```python
# Use Python to inspect Excel structure
import pandas as pd

# Read sample
df = pd.read_excel("tests/fixtures/requirement4_samples/sample_input_1.xlsx", sheet_name=None)

# Document sheets
for sheet_name, sheet_df in df.items():
    print(f"Sheet: {sheet_name}")
    print(f"Columns: {sheet_df.columns.tolist()}")
    print(f"Rows: {len(sheet_df)}")
    print(f"Sample data:\n{sheet_df.head()}")
```

### 2.2 Define Input Roles

Update `excel_contracts.json` with discovered schemas:

```json
{
  "input_roles": {
    "source_data": {
      "filename_pattern": "sample_input_*.xlsx",
      "required_sheets": ["Transactions"],
      "schema": {
        "Transactions": {
          "agent_id": {"type": "string", "required": true},
          "transaction_amount": {"type": "decimal", "required": true},
          "transaction_date": {"type": "date", "required": true}
        }
      }
    }
  }
}
```

---

## Step 3: Encode Ambiguity Decisions

### 3.1 Review Ambiguity Checklist

Business should provide decisions for 7 categories. Review `ambiguity_checklist.md`.

### 3.2 Implement Decisions as Rules

For each decision, implement in `CommissionEngine`:

```python
# Example: Missing Agent IDs
if row["agent_id"] is None:
    # Business decision: reject transaction
    raise ValidationError("Missing agent_id")

# Example: Zero Amount Transactions
if row["transaction_amount"] == 0:
    # Business decision: include with $0 commission
    commission = 0
```

---

## Step 4: Implement Business Rules

### 4.1 Load Contracts in CommissionEngine

Update `src/autoresearch/core/services/commission_engine.py`:

```python
def load_contracts(self) -> CommissionEngineStatus:
    """Load business rule contracts."""
    contracts_file = self._contracts_dir / "excel_contracts.json"

    if not contracts_file.exists():
        return CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS

    # Load and parse contracts
    import json
    with contracts_file.open() as f:
        contracts = json.load(f)

    # Validate contracts
    self._rules = self._parse_contracts(contracts)
    self._contracts_loaded = True

    return CommissionEngineStatus.READY
```

### 4.2 Implement Calculation Logic

```python
def calculate(self, request: CommissionCalculationRequest) -> CommissionCalculationResult:
    """Calculate commissions using business rules."""
    if not self._contracts_loaded:
        self.load_contracts()

    if self._contracts_loaded != CommissionEngineStatus.READY:
        return self._blocked_result(request.job_id)

    # Execute rules deterministically
    results = {}
    applied_rules = []
    steps = []

    for rule in self._rules.values():
        # Apply rule to input data
        rule_result = self._apply_rule(rule, request.input_data)
        results[rule.rule_id] = rule_result
        applied_rules.append(rule.rule_id)
        steps.append({
            "rule_id": rule.rule_id,
            "input": request.input_data,
            "output": rule_result,
        })

    return CommissionCalculationResult(
        job_id=request.job_id,
        status=CommissionEngineStatus.READY,
        calculated_values=results,
        applied_rules=applied_rules,
        intermediate_steps=steps,
    )
```

### 4.3 Add Rule Parsing

```python
def _parse_contracts(self, contracts: dict) -> dict[str, CommissionRuleContract]:
    """Parse contracts into rule objects."""
    rules = {}

    for role, spec in contracts.get("input_roles", {}).items():
        # Create validation rules from schema
        for field, field_spec in spec.get("schema", {}).items():
            # Parse and store rule
            pass

    # Load calculation rules if provided
    for rule_spec in contracts.get("calculation_rules", []):
        rule = CommissionRuleContract(
            rule_id=rule_spec["rule_id"],
            name=rule_spec["name"],
            formula=rule_spec["formula"],
            conditions=rule_spec["conditions"],
            priority=rule_spec["priority"],
        )
        rules[rule.rule_id] = rule

    return rules
```

---

## Step 5: Validate Against Golden Outputs

### 5.1 Run Sample Through Pipeline

```python
# Test calculation with sample data
job = service.create_job(ExcelJobCreateRequest(
    task_name="Golden validation",
    input_files=["tests/fixtures/requirement4_samples/sample_input_1.xlsx"],
))

# Request calculation
result = service.calculate_commission(job.job_id, CommissionCalculationRequest(
    job_id=job.job_id,
    input_data=load_sample_data("sample_input_1.xlsx"),
))
```

### 5.2 Compare to Golden Output

```python
# Load golden output
golden = load_golden_output("golden_commission_report.xlsx")

# Compare
tolerance = 0.01  # From golden_metadata.json
for agent_id, calculated_value in result.calculated_values.items():
    golden_value = golden[agent_id]
    diff = abs(calculated_value - golden_value)

    if diff > tolerance:
        raise AssertionError(
            f"Agent {agent_id}: calculated {calculated_value}, "
            f"golden {golden_value}, diff {diff} exceeds tolerance {tolerance}"
        )
```

### 5.3 Update Tests

Add to `tests/test_excel_ops_service.py`:

```python
def test_golden_output_match():
    """Verify calculations match golden output."""
    # Load sample
    sample = load_fixture("sample_input_1.xlsx")

    # Calculate
    result = commission_engine.calculate(
        CommissionCalculationRequest(
            job_id="test",
            input_data=sample,
        )
    )

    # Load golden
    golden = load_golden("golden_commission_report.xlsx")

    # Compare
    assert_match_within_tolerance(result, golden)
```

---

## Step 6: Wire Up Router and Enable Workflow

### 6.1 Wire Up Dependencies

Update `src/autoresearch/api/dependencies.py`:

```python
def get_excel_ops_service() -> ExcelOpsService:
    """Get Excel ops service instance."""
    # Get SQLite repository
    settings = get_runtime_settings()
    db_path = settings.api_db_path.parent / "excel_jobs.db"

    repository = ExcelJobsRepository(db_path)
    engine = CommissionEngine()

    return ExcelOpsService(
        repository=repository,
        commission_engine=engine,
        repo_root=Path(__file__).parents[3],
    )
```

### 6.2 Add Router to Main App

Update `src/autoresearch/api/main.py`:

```python
# In optional_routers list:
("autoresearch.api.routers.excel_ops", "router", "excel ops"),
```

### 6.3 Test API Endpoints

```bash
# Start API
make start

# Test endpoints
curl http://127.0.0.1:8001/api/v1/excel-ops/status/requirement4
curl -X POST http://127.0.0.1:8001/api/v1/excel-ops/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "Test", "input_files": []}'
```

---

## Step 7: Enable Pilot Workflow

### 7.1 Run Validation

```bash
# Run full validation
bash scripts/validate_stable_baseline.sh

# Run contract tests
pytest tests/test_excel_ops_service.py -v
```

### 7.2 Business Sign-Off

- Share results with business team
- Verify calculations match golden outputs
- Document any deviations
- Get approval for pilot

### 7.3 Monitor First Runs

- Enable for limited pilot users
- Monitor calculation accuracy
- Track performance metrics
- Iterate on edge cases

---

## Troubleshooting

### Contracts Not Loading

**Issue**: `CommissionEngine.load_contracts()` returns `BLOCKED_AWAITING_CONTRACTS`

**Check**:
1. Contracts file exists in `tests/fixtures/requirement4_contracts/`
2. JSON is valid
3. All required fields present

### Calculation Results Differ from Golden

**Issue**: Test failures due to value differences

**Check**:
1. Tolerance settings in `golden_metadata.json`
2. Rounding method matches (nearest_cent, round_half_up, etc.)
3. All rules applied in correct order
4. Input data normalized correctly

### Router Returns 501 Not Implemented

**Issue**: `/api/v1/excel-ops/*` endpoints return 501

**Fix**:
1. Wire up dependencies in `dependencies.py`
2. Add router to main app
3. Restart API

---

## Summary

**Current Pilot Estimate**: 2 days for the compressed pilot path defined in `ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md`

**Later Productionization**: longer follow-up phase outside the current pilot scope

**Critical Path**:
1. Assets → Readiness Review → Deterministic CLI → AAS/Telegram Manual Trigger → Manual Review

**Success Criteria**:
- At least one real sample runs deterministically
- At least one golden comparison is executed
- AAS can invoke the CLI
- Telegram can manually trigger one pilot run
- Outputs remain auditable and manually reviewable

**Next Review**: After business assets provided

---

**See Also**:
- [IMPLEMENTATION_READY_CHECKLIST.md](IMPLEMENTATION_READY_CHECKLIST.md) - Detailed checklist
- [ENGINEERING_PREP_PLAN.md](ENGINEERING_PREP_PLAN.md) - Preparation plan
- [../../STATUS_AND_RELEASE_NOTES.md](../../STATUS_AND_RELEASE_NOTES.md) - Release notes
