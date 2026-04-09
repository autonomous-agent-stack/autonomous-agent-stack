# Requirement #4 Sample Files

**Status**: Awaiting business assets

This directory will contain **1-3 real Excel sample files** provided by the business.

## What Should Be Placed Here

When business assets arrive, place sample Excel files in this directory:

- `sample_input_1.xlsx` - Primary input file with transaction data
- `sample_input_2.xlsx` - Secondary input file (if applicable)
- `sample_configuration.xlsx` - Configuration/rate table file (if applicable)

## File Requirements

Each sample file should include:

1. **Clear sheet structure** - Named sheets with consistent column headers
2. **Real data** - Actual or realistic data matching production use cases
3. **Role identification** - Which input role this file serves (source data, config, reference, etc.)
4. **Expected volume** - Representative row count and complexity

## Metadata File

Along with sample files, create a `samples_metadata.json` file:

```json
{
  "samples": [
    {
      "filename": "sample_input_1.xlsx",
      "role": "source_data",
      "description": "Transaction data from January 2026",
      "sheets": {
        "Transactions": "Main transaction records",
        "Agents": "Agent reference data"
      },
      "row_count": 1500,
      "provided_by": "Business Team",
      "provided_date": "2026-04-09"
    }
  ],
  "notes": "Include any special handling instructions or known edge cases"
}
```

## Purpose

These sample files will be used to:

1. Define input file schemas and column mappings
2. Test data ingestion and normalization
3. Validate calculation rules
4. Generate expected outputs for comparison

## Current State

**Empty** - Awaiting business to provide sample Excel files.

## Next Steps

Once samples arrive:
1. Review file structure and document schemas
2. Create input/output contracts based on samples
3. Add sample metadata to `samples_metadata.json`
4. Update `CommissionEngine` to handle sample data format
5. Create test cases using these samples

---

**See Also**:
- `../requirement4_golden/` - Expected output files
- `../requirement4_contracts/` - Rule and schema definitions
- `../../../docs/requirement4/` - Complete requirement #4 documentation
