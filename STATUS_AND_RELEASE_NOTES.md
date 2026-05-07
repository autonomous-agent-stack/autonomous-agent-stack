# Status & Release Notes

[Simplified Chinese](STATUS_AND_RELEASE_NOTES.zh-CN.md)

## Evergreen OS GA v1.0 achieved

**Status:** achieved  
**Release tag:** `v1.0.0-evergreen-ga`  
**Date:** 2026-05-07

Autonomous Agent Stack has achieved the Evergreen OS GA v1.0 evidence gate in this checkout. The GA result is backed by committed reports for the gap analysis, adapter certification, stable adapter lock, bypass validation, furniture E2E workflow, and blocking release gate.

### GA Evidence

- `ga_gap_report.json` and `ga_gap_report.md`
- `adapter_certification_report.json`
- `stable_adapters.lock`
- `docs/certification/adapter-certification-matrix.md`
- `bypass_ga_report.json`
- `furniture_e2e_report.json`
- `ga_release_gate_report.json`

### Release Guardrails

- `make ga-release-gate` remains the blocking GA release gate.
- External writes remain dry-run by default unless live-write preconditions are explicitly satisfied.
- Adapter stability is derived from certification evidence, not configuration intent alone.

### Post-GA Backlog

- real staging credentials validation
- furniture pilot deployment
- adapter drift monitoring
- CI evidence retention
