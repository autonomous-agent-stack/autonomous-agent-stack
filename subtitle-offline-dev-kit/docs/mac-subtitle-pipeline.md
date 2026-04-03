# Subtitle Offline Dev Kit, Mac Pipeline

## Purpose

This document is the handoff guide for the offline subtitle validation flow inside
`subtitle-offline-dev-kit/`.

This kit is intentionally narrow. It validates subtitle files offline, normalizes
them into a small shared contract, and reports basic anomalies. It does not do
network download, routing, fallback orchestration, or live pipeline control.

## Dependencies

- Python 3.10+
- No extra package install is required for the current dev kit workflow

## Working Directory

You can run the smoke check in either of these ways:

### From `subtitle-offline-dev-kit/`

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit
python scripts/check_subtitle_contract.py
```

### From the repository root

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack
python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

## Input Contract

The smoke check accepts either a directory or a single file.

- Supported file formats: `.vtt`, `.srt`
- Expected text encoding: UTF-8
- File naming is flexible, but suffix-based detection is strict
- Non-supported files are skipped when scanning a directory
- Passing a non-supported single file will fail with a non-zero exit code

## Normalized Output Contract

`clean_subtitle_file(...)` returns a dictionary with this shape:

```python
{
  "filename": str,
  "lines": [
    {
      "start": float,
      "end": float,
      "text": str,
      "language": str | None,
      "speaker": str | None,
      "note": str | None,
    }
  ],
  "total_duration": float,
  "language": str | None,
}
```

`note` is where anomaly markers are stored. The stage-3 smoke check currently
summarizes these markers:

- `missing_text`
- `end_before_start`
- `out_of_order`

## CLI Output

The script writes one summary line per subtitle file to stdout.

Current output format:

```text
sample_01_en.vtt: total_lines=1, missing_text=0, end_before_start=0, out_of_order=0
sample_05_missing_fields.srt: total_lines=2, missing_text=1, end_before_start=0, out_of_order=0
sample_07_exception.srt: total_lines=2, missing_text=0, end_before_start=1, out_of_order=1
```

Field meanings:

- `total_lines`: normalized subtitle cue count
- `missing_text`: count of lines whose normalized text is empty
- `end_before_start`: count of lines whose end timestamp is earlier than start
- `out_of_order`: count of lines whose start timestamp moves backward relative to
  the previous line

## Exit Codes

- `0`: all processed subtitle files completed with no summarized anomalies
- `1`: at least one processed subtitle file contains anomalies, or the script
  encountered a file/path error

For the current fixture set, `sample_05_missing_fields.srt` and
`sample_07_exception.srt` intentionally trigger `exit 1`.

## Usage

### Check the default fixtures

From `subtitle-offline-dev-kit/`:

```bash
python scripts/check_subtitle_contract.py
```

From the repository root:

```bash
python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

### Check a specific directory

```bash
python scripts/check_subtitle_contract.py /path/to/subtitle_dir
```

### Check a single file

```bash
python scripts/check_subtitle_contract.py /path/to/subtitle_dir/sample_01_en.vtt
```

### Show help

```bash
python scripts/check_subtitle_contract.py -h
```

### Scan a larger subtitle corpus for anomaly candidates

```bash
python scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitle_corpus \
  --issues-only \
  --json scan-report.json \
  --markdown scan-report.md
```

Useful filters:

- `--language en` or `--language zh`
- `--min-lines 50`
- `--issues-only`

### Regenerate harvested fixtures from the real subtitle corpus

```bash
python scripts/harvest_real_fixtures.py
```

The harvest plan lives in `fixtures/manifest.json`. It records where each
fixture came from and which transformation was applied.

### Write a JSON report

```bash
python scripts/check_subtitle_contract.py /path/to/subtitle_dir --json report.json
```

### Write a Markdown report

```bash
python scripts/check_subtitle_contract.py /path/to/subtitle_dir --markdown report.md
```

## Common Failures

| Problem | Likely Cause | What To Do |
|---|---|---|
| `Unsupported subtitle format` | File suffix is not `.vtt` or `.srt` | Rename to a supported format if the content is valid, or skip the file |
| Script exits with `1` | One or more files contain `missing_text`, `end_before_start`, or `out_of_order` | Read the stdout summary, then inspect the affected `note` markers in the normalized contract |
| `No supported subtitle files found` | The target directory is empty or contains only unsupported files | Point the script at a directory with `.vtt` or `.srt` files |
| Output text looks garbled | File is not UTF-8 clean | Re-encode the subtitle file to UTF-8 and re-run |
| `Path does not exist` | Wrong file or directory path | Re-run with an existing absolute or relative path |

## Suggested Workflow

1. Run the fixture smoke check first to confirm the dev kit still behaves as expected.
2. Run the same script against a real subtitle directory.
3. Use `scan_subtitle_anomalies.py` when you need a broader candidate list across
   a recursive corpus, especially before choosing new harvested fixtures.
4. Investigate any files that produce non-zero anomaly counts.
5. If a new edge case matters, add a minimized reproduction into `fixtures/`.
6. Run the isolated test suite to keep parser behavior stable:

```bash
pytest -q /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/tests
```

## Handoff Checklist

This kit does not require a separate git worktree. It already lives inside the
main repository.

1. Confirm Python is available:

```bash
python3 --version
```

2. Run the isolated regression suite:

```bash
pytest -q /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/tests
```

3. Run the fixture smoke check:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

4. Run the same check against a real subtitle directory and save a report:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/check_subtitle_contract.py \
  /path/to/subtitle_dir \
  --json /path/to/report.json \
  --markdown /path/to/report.md
```

5. If new anomalies matter, add a minimized reproduction into `fixtures/` and
rerun both pytest and the smoke check.

7. If you need to refresh the canonical fixture set from the local subtitle
corpus, rerun:

```bash
python /Volumes/AI_LAB/Github/autonomous-agent-stack/subtitle-offline-dev-kit/scripts/harvest_real_fixtures.py
```

## Linux Boundary

This dev kit is safe to use as an offline validation sidecar on Linux, but only
for local parsing and contract checks.

Out of scope for this kit:

- subtitle downloading
- network-dependent pipeline steps
- routing or fallback policy changes
- live orchestration or agent execution

## Tool Split

Use `check_subtitle_contract.py` when you already know which file or directory
you want to validate and you care about pass/fail semantics.

Use `scan_subtitle_anomalies.py` when you want to search a larger recursive
corpus for candidates worth harvesting into fixtures or reviewing manually.
