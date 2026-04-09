# Requirement #4 Golden Outputs

**Status**: Awaiting business assets

This directory will contain **golden output files** plus a minimal audit/approval loop specification.

## What Should Be Placed Here

When business assets arrive, place expected output files in this directory:

- `golden_commission_report.xlsx` - Expected commission calculation results
- `golden_validation_report.xlsx` - Expected validation findings
- `golden_audit_trail.json` - Expected audit trail

## Golden Output Requirements

Each golden output must include:

1. **Exact expected values** - No ranges or approximations
2. **Clear derivation** - How each value was calculated
3. **Reference to input** - Which input rows/data produced each output
4. **Edge case coverage** - Include known edge cases and their handling

## Metadata File

Create a `golden_metadata.json` file:

```json
{
  "outputs": [
    {
      "filename": "golden_commission_report.xlsx",
      "description": "Expected commission results for sample_input_1.xlsx",
      "sheets": {
        "Commissions": "Per-agent commission amounts",
        "Summary": "Aggregate statistics"
      },
      "derived_from": "sample_input_1.xlsx",
      "rules_applied": ["rule_001", "rule_002"],
      "verified_by": "Business Team",
      "verified_date": "2026-04-09"
    }
  ],
  "audit_loop": {
    "approvers": ["business_lead@example.com"],
    "approval_criteria": [
      "All calculated values match golden output within 0.01",
      "All edge cases documented and handled",
      "Audit trail complete and reproducible"
    ],
    "test_command": "pytest tests/test_excel_ops_service.py::test_golden_output_match"
  }
}
```

## Audit/Approval Loop Specification

Define the minimal approval process:

1. **Calculation** - System produces commission output
2. **Comparison** - Automated comparison against golden output
3. **Review** - Business team reviews any discrepancies
4. **Approval** - Business approves if within tolerance
5. **Sign-off** - Audit trail records approval

## Tolerance Guidelines

Define acceptable tolerances for comparison:

```json
{
  "tolerances": {
    "absolute": 0.01,
    "percentage": 0.001,
    "rounding": "nearest_cent"
  }
}
```

## Current State

**Empty** - Awaiting business to provide golden outputs and approval criteria.

## Next Steps

Once golden outputs arrive:
1. Verify golden outputs against input samples
2. Document calculation rules applied
3. Define approval tolerances
4. Implement automated comparison tests
5. Create approval workflow

---

**See Also**:
- `../requirement4_samples/` - Input sample files
- `../requirement4_contracts/` - Rule definitions
- `../../../docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md` - Complete checklist
