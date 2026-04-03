# Subtitle Offline Dev Kit

Offline-first scaffold for validating a Mac-only subtitle pipeline without touching
live routing, fallback, or network-dependent execution paths.

## Status

Phase 5. The dev kit now has:

- typed subtitle contracts
- offline VTT/SRT parsing and cleaning
- anomaly tagging for `missing_text`, `end_before_start`, and `out_of_order`
- a smoke-check CLI with stdout, JSON, and Markdown output
- isolated regression tests

## Goals

- Make the subtitle sidecar workstream easy to resume and hand off.
- Keep validation fully offline.
- Lock the expected directory layout before implementation starts.

## Layout

```text
subtitle-offline-dev-kit/
├── README.md
├── docs/
├── fixtures/
├── scripts/
├── subtitle_offline/
└── tests/
```

## Current Commands

Run the isolated tests:

```bash
pytest -q /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/tests
```

Run the smoke check:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

Scan a larger subtitle corpus for anomaly candidates:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitle_corpus \
  --issues-only \
  --json /path/to/scan-report.json \
  --markdown /path/to/scan-report.md
```

Regenerate real-derived fixtures:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/harvest_real_fixtures.py
```

Write machine-readable reports:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py \
  /path/to/subtitle_dir \
  --json /path/to/report.json \
  --markdown /path/to/report.md
```

## Remaining TODO

- Expand the harvested fixture set when new edge cases are discovered.
- Expand anomaly coverage beyond the three stage-3 markers.
- Add richer contract fields only after the real pipeline contract is stable.

## Suggested Next Command

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```
