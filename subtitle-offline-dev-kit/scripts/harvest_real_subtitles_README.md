# Harvest Real Subtitles

## Purpose

Harvest representative subtitle fixtures from an external local subtitle corpus.
Use the harvested copies and manifest reports to expand offline regression coverage
without committing the full raw corpus into this repo.

## Minimal Run

```bash
python subtitle-offline-dev-kit/scripts/harvest_real_subtitles.py \
  --input-dir /path/to/external/subtitles \
  --output-dir subtitle-offline-dev-kit/fixtures/harvested
```

## Outputs

- `subtitle-offline-dev-kit/fixtures/harvested/`
- `subtitle-offline-dev-kit/reports/harvested-manifest.json`
- `subtitle-offline-dev-kit/reports/harvested-manifest.md`

## Test

```bash
pytest -q subtitle-offline-dev-kit/tests/test_harvest_real_subtitles.py
```
