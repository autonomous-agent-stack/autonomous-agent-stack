# Subtitle Offline Dev Kit

Offline-first scaffold for validating a Mac-only subtitle pipeline without touching
live routing, fallback, or network-dependent execution paths.

## Status

Phase 5. The dev kit now has:

- typed subtitle contracts
- offline VTT/SRT parsing and cleaning
- anomaly tagging for `missing_text`, `end_before_start`, and `out_of_order`
- recursive anomaly scanning with candidate/noise/clean/error categories
- structural anomaly detection for `duplicate_cue`, `rapid_repeat`, `long_cue`, and `large_gap`
- threshold controls for `duplicate_cue`, `rapid_repeat`, `long_cue`, and `large_gap`
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
  --ignore-empty-auto-caption \
  --candidate-issue duplicate_cue \
  --candidate-issue rapid_repeat \
  --candidate-issue long_cue \
  --candidate-issue large_gap \
  --issues-only \
  --json /path/to/scan-report.json \
  --markdown /path/to/scan-report.md
```

High-signal harvest mode for manual fixture selection:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitle_corpus \
  --ignore-empty-auto-caption \
  --issues-only \
  --language en \
  --candidate-issue duplicate_cue \
  --duplicate-min-text-len 80 \
  --json /path/to/harvest-report.json
```

Broader audit mode for structural quality review:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitle_corpus \
  --ignore-empty-auto-caption \
  --issues-only \
  --candidate-issue duplicate_cue \
  --candidate-issue rapid_repeat \
  --candidate-issue long_cue \
  --candidate-issue large_gap \
  --duplicate-min-text-len 60 \
  --rapid-repeat-window-seconds 0.1 \
  --large-gap-seconds 30 \
  --long-cue-chars 240 \
  --json /path/to/audit-report.json \
  --markdown /path/to/audit-report.md
```

Observed sweep results on real corpora:

| Corpus | Recommended mode | Suggested flags | Observed result |
|---|---|---|---|
| `diaryofaceo` | harvest | `--language en --candidate-issue duplicate_cue --duplicate-min-text-len 80` | about 25 candidate files |
| `diaryofaceo` | audit | `--candidate-issue duplicate_cue --candidate-issue rapid_repeat --duplicate-min-text-len 60` | about 339 candidate files |
| `wowinsight` | harvest | `--candidate-issue duplicate_cue --duplicate-min-text-len 70` | about 1 candidate file |
| `wowinsight` | audit | `--candidate-issue duplicate_cue --candidate-issue rapid_repeat --duplicate-min-text-len 60` | about 3 candidate files |

Operational note:

- `rapid_repeat_window_seconds` did not materially change `diaryofaceo` results between `0.005` and `0.8`; those repeats are effectively gap-free, so language and candidate-issue selection are stronger filters than widening the window.

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
- Revisit threshold presets when a new corpus shows materially different repeat behavior.
- Add richer contract fields only after the real pipeline contract is stable.

## Suggested Next Command

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```
