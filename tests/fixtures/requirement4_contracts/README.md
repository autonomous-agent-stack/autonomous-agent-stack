# Requirement #4 Contracts

**Status**: Awaiting business assets

This directory will contain **input/output Excel contracts** and the **ambiguity checklist covering 7 categories**.

## What Should Be Placed Here

When business assets arrive, place contract definitions in this directory:

### 1. Excel Input/Output Contracts (`excel_contracts.json`)

Defines:
- Input file roles and schemas
- Output file roles and schemas
- Column mappings and data types
- Validation rules per column
- Required vs optional fields

```json
{
  "input_roles": {
    "source_data": {
      "required_sheets": ["Transactions"],
      "schema": {
        "Transactions": {
          "agent_id": {"type": "string", "required": true},
          "transaction_amount": {"type": "decimal", "required": true},
          "transaction_date": {"type": "date", "required": true}
        }
      }
    }
  },
  "output_roles": {
    "commission_report": {
      "required_sheets": ["Commissions"],
      "schema": {
        "Commissions": {
          "agent_id": {"type": "string"},
          "commission_amount": {"type": "decimal", "precision": 2}
        }
      }
    }
  }
}
```

### 2. Ambiguity Checklist (`ambiguity_checklist.md`)

Documents decisions covering 7 categories of edge cases:

1. **Data Completeness** - How to handle missing/null values
2. **Data Validation** - Out-of-range values, invalid formats
3. **Calculation Rules** - Edge cases in formulas, rounding
4. **Agent Mapping** - Unmapped agents, split commissions
5. **Time Periods** - Partial periods, cutoff times
6. **Rate Tiers** - Boundary conditions, tier transitions
7. **Adjustments** - Manual adjustments, corrections

Example format:
```markdown
## Category 1: Data Completeness

### Decision: Missing Agent IDs
- **Rule**: Reject transaction with missing agent_id
- **Reason**: Cannot calculate commission without agent assignment
- **Implementation**: `if agent_id is null: reject_row()`

### Decision: Zero Transaction Amount
- **Rule**: Include zero-amount transactions with $0 commission
- **Reason**: May be intentional (promo, correction)
- **Implementation**: `if amount == 0: commission = 0`
```

### 3. Rule Definitions (`commission_rules.json`)

Defines deterministic calculation rules:

```json
{
  "rules": [
    {
      "rule_id": "rule_001",
      "name": "Standard Commission",
      "formula": "transaction_amount * 0.05",
      "conditions": {
        "transaction_type": "sale",
        "agent_tier": "standard"
      },
      "priority": 1
    }
  ]
}
```

## Contract Validation

Contracts will be validated:

1. **Schema Validation** - JSON structure validation
2. **Reference Integrity** - All referenced entities exist
3. **Rule Completeness** - All required rules defined
4. **Ambiguity Coverage** - All 7 categories addressed

## Current State

**Empty** - Awaiting business to provide:
1. Input/output Excel contracts
2. Ambiguity checklist decisions
3. Commission calculation rules

## Next Steps

Once contracts arrive:
1. Validate contract schemas
2. Load contracts into `CommissionEngine`
3. Implement rule execution logic
4. Create tests for each rule
5. Verify against golden outputs

---

**See Also**:
- `../requirement4_samples/` - Input files to define contracts for
- `../requirement4_golden/` - Expected outputs from rules
- `../../../docs/requirement4/` - Complete requirement #4 documentation
