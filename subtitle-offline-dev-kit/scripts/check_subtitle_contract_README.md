# Subtitle Contract Batch Checker

## Purpose

Run offline subtitle contract checks against fixture files or a larger local
subtitle directory, then emit summary reports for anomalies and parser errors.

## Minimal Run

```bash
python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py \
  subtitle-offline-dev-kit/fixtures \
  --report-json subtitle-offline-dev-kit/reports/batch_check_report.json \
  --report-md subtitle-offline-dev-kit/reports/batch_check_report.md \
  --strict
```

## Outputs

- `subtitle-offline-dev-kit/reports/batch_check_report.json`
- `subtitle-offline-dev-kit/reports/batch_check_report.md`

## Test

```bash
pytest -q subtitle-offline-dev-kit/tests/test_scripts.py
```
