# Legacy Memory Import - Migration Guide

> **For codex-2 implementation reference**  
> Created by: glm-5-2  
> Date: 2026-03-26

## Quick Start

This directory contains the legacy memory import specification and validation tools.

### Files

- `../docs/legacy-memory-import-spec.md` - Complete migration specification
- `validate_import.py` - Validation script for imported sessions
- `import_legacy_sample.py` - Sample import script (to be created by codex-2)

### Validation

To validate imported sessions:

```bash
# Validate and generate report
python3 migration/validate_import.py ~/.openclaw/agents/agent/sessions ./imported_sessions --report validation_report.json

# Verbose output
python3 migration/validate_import.py ~/.openclaw/agents/agent/sessions ./imported_sessions --verbose
```

### What's Validated

1. **Event Count**: Source events should match target events
2. **Role Distribution**: User/assistant/toolResult counts should match
3. **Event Types**: Type distribution should be preserved
4. **Timestamp Order**: Events should remain in chronological order
5. **Parent Chain**: All parentIds should reference valid events
6. **Time Range**: First and last timestamps should match
7. **Content Integrity**: Spot check of 10 random events
8. **External IDs**: All events should have valid `external_id` fields
9. **Metadata**: Import metadata should be present and valid

### Sample Validation Report

```json
{
  "generated_at": "2026-03-26T00:00:00Z",
  "summary": {
    "total_sessions": 10,
    "valid_sessions": 9,
    "invalid_sessions": 1,
    "total_errors": 3,
    "check_summary": {
      "event_count_match": {"passed": 10, "failed": 0},
      "role_distribution": {"passed": 10, "failed": 0},
      "external_ids": {"passed": 10, "failed": 0},
      "metadata": {"passed": 10, "failed": 0}
    }
  }
}
```

### Next Steps for codex-2

1. Read `../docs/legacy-memory-import-spec.md` for full specification
2. Implement import script based on sample code in spec
3. Use `validate_import.py` to verify imports
4. Add dry-run mode
5. Add batch progress reporting
6. Handle edge cases (malformed JSONL, missing fields)

### Constraints

- DO NOT modify `claude_agents.py` or `openclaw.py`
- DO NOT touch Telegram channel code
- Batch import only (no real-time sync)
- Log errors and continue (don't fail on individual sessions)

### Support

For questions about the specification, refer to:

- Field mapping: Section 3 in spec
- Idempotency: Section 4 in spec
- Timestamp handling: Section 5 in spec
- Validation strategy: Section 8 in spec
