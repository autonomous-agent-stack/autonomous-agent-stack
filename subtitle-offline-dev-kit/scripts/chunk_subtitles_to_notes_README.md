# Chunk Subtitles To Notes

## Purpose

Convert cleaned subtitle files into notes-ready JSONL chunks with stable metadata:
source file, time range, language, source checksum, and chunk checksum.

## Minimal Run

```bash
python subtitle-offline-dev-kit/scripts/chunk_subtitles_to_notes.py \
  --input-dir subtitle-offline-dev-kit/fixtures \
  --output-dir artifacts/subtitle-notes-ready
```

## Outputs

- `artifacts/subtitle-notes-ready/chunks.jsonl`

## Test

```bash
pytest -q subtitle-offline-dev-kit/tests/test_chunk_subtitles_to_notes.py
```
