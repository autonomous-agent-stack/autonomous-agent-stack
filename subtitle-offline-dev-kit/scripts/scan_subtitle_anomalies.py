#!/usr/bin/env python3
"""Scan a subtitle corpus and surface anomaly candidates for fixture harvest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.service import clean_subtitle_file
from subtitle_offline.utils import merge_note

SUPPORTED_SUFFIXES = {".srt", ".vtt"}
CHECK_KEYS = (
    "missing_text",
    "end_before_start",
    "out_of_order",
    "mixed_language",
    "duplicate_cue",
    "rapid_repeat",
    "long_cue",
    "large_gap",
)
VISIBLE_TAG_RE = re.compile(r"<[^>]+>")
DEFAULT_DUPLICATE_CUE_MIN_CHARS = 24
DEFAULT_RAPID_REPEAT_GAP_SECONDS = 0.1
DEFAULT_LONG_CUE_CHAR_THRESHOLD = 240
DEFAULT_LARGE_GAP_SECONDS = 30.0
MODE_PRESETS: dict[str, dict[str, object]] = {
    "harvest": {
        "issues_only": True,
        "ignore_empty_auto_caption": True,
        "languages": ["en"],
        "candidate_issues": ["duplicate_cue"],
        "duplicate_min_text_len": 80,
    },
    "audit": {
        "issues_only": True,
        "ignore_empty_auto_caption": True,
        "candidate_issues": ["duplicate_cue", "rapid_repeat", "long_cue", "large_gap"],
        "duplicate_min_text_len": 60,
        "rapid_repeat_window_seconds": DEFAULT_RAPID_REPEAT_GAP_SECONDS,
        "large_gap_seconds": DEFAULT_LARGE_GAP_SECONDS,
        "long_cue_chars": DEFAULT_LONG_CUE_CHAR_THRESHOLD,
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan subtitle files recursively and report anomaly candidates."
    )
    parser.add_argument("--input-dir", required=True, help="Directory or subtitle file to scan.")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_PRESETS),
        help=(
            "Apply a preset scan profile. "
            "Explicit flags such as --language or --duplicate-min-text-len override preset values."
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--markdown",
        dest="markdown_path",
        help="Optional Markdown report path.",
    )
    parser.add_argument(
        "--language",
        action="append",
        dest="languages",
        help="Only include files whose inferred source language matches one of these values. Repeatable.",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=0,
        help="Only include files with at least this many normalized subtitle lines.",
    )
    parser.add_argument(
        "--issues-only",
        action="store_true",
        help="Only include files that contain one or more anomaly flags.",
    )
    parser.add_argument(
        "--candidate-issue",
        action="append",
        dest="candidate_issues",
        choices=CHECK_KEYS,
        help=(
            "Only keep candidate files that include at least one of these issue types. "
            "Repeatable. Example: --candidate-issue end_before_start"
        ),
    )
    parser.add_argument(
        "--ignore-empty-auto-caption",
        action="store_true",
        help=(
            "Downgrade pure empty auto-caption VTT cues from candidate anomalies to noise. "
            "This reduces false positives from auto-generated placeholder blocks."
        ),
    )
    parser.add_argument(
        "--duplicate-min-text-len",
        type=int,
        default=None,
        help=(
            "Minimum visible-text length before repeated cues count toward duplicate detection. "
            f"Default: {DEFAULT_DUPLICATE_CUE_MIN_CHARS}, or the active --mode preset."
        ),
    )
    parser.add_argument(
        "--rapid-repeat-window-seconds",
        type=float,
        default=None,
        help=(
            "Maximum gap between identical adjacent cues before they count as a rapid repeat. "
            f"Default: {DEFAULT_RAPID_REPEAT_GAP_SECONDS}, or the active --mode preset."
        ),
    )
    parser.add_argument(
        "--large-gap-seconds",
        type=float,
        default=None,
        help=(
            "Minimum cue-to-cue gap that should be flagged as a large gap. "
            f"Default: {DEFAULT_LARGE_GAP_SECONDS}, or the active --mode preset."
        ),
    )
    parser.add_argument(
        "--long-cue-chars",
        type=int,
        default=None,
        help=(
            "Minimum visible-text length for a single cue to count as long. "
            f"Default: {DEFAULT_LONG_CUE_CHAR_THRESHOLD}, or the active --mode preset."
        ),
    )
    return parser


def resolve_cli_options(args: argparse.Namespace) -> dict[str, object]:
    preset = MODE_PRESETS.get(args.mode, {})

    languages = list(args.languages) if args.languages is not None else list(preset.get("languages", []))
    candidate_issues = (
        list(args.candidate_issues)
        if args.candidate_issues is not None
        else list(preset.get("candidate_issues", []))
    )

    return {
        "mode": args.mode,
        "languages": languages,
        "min_lines": args.min_lines,
        "issues_only": args.issues_only or bool(preset.get("issues_only", False)),
        "ignore_empty_auto_caption": (
            args.ignore_empty_auto_caption or bool(preset.get("ignore_empty_auto_caption", False))
        ),
        "candidate_issues": candidate_issues,
        "duplicate_min_text_len": (
            args.duplicate_min_text_len
            if args.duplicate_min_text_len is not None
            else int(preset.get("duplicate_min_text_len", DEFAULT_DUPLICATE_CUE_MIN_CHARS))
        ),
        "rapid_repeat_window_seconds": (
            args.rapid_repeat_window_seconds
            if args.rapid_repeat_window_seconds is not None
            else float(preset.get("rapid_repeat_window_seconds", DEFAULT_RAPID_REPEAT_GAP_SECONDS))
        ),
        "large_gap_seconds": (
            args.large_gap_seconds
            if args.large_gap_seconds is not None
            else float(preset.get("large_gap_seconds", DEFAULT_LARGE_GAP_SECONDS))
        ),
        "long_cue_chars": (
            args.long_cue_chars
            if args.long_cue_chars is not None
            else int(preset.get("long_cue_chars", DEFAULT_LONG_CUE_CHAR_THRESHOLD))
        ),
        "json_path": args.json_path,
        "markdown_path": args.markdown_path,
    }


def iter_subtitle_files(target: Path) -> list[Path]:
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_SUFFIXES else []
    return sorted(path for path in target.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)


def is_auto_caption_vtt(path: Path, raw_text: str) -> bool:
    return path.suffix.lower() == ".vtt" and (
        "align:start position:" in raw_text or "Kind: captions" in raw_text
    )


def normalize_visible_text(text: object) -> str:
    raw = str(text or "")
    without_tags = VISIBLE_TAG_RE.sub("", raw)
    return " ".join(without_tags.split()).strip()


def annotate_structural_issues(
    lines: list[dict[str, object]],
    *,
    duplicate_min_text_len: int,
    rapid_repeat_window_seconds: float,
    long_cue_chars: int,
    large_gap_seconds: float,
) -> None:
    visible_texts = [normalize_visible_text(line.get("text")) for line in lines]
    duplicate_groups: dict[str, list[int]] = defaultdict(list)

    for index, visible_text in enumerate(visible_texts):
        if len(visible_text) >= duplicate_min_text_len:
            duplicate_groups[visible_text.casefold()].append(index)

        if len(visible_text) >= long_cue_chars:
            note = lines[index].get("note")
            lines[index]["note"] = merge_note(note if isinstance(note, str) else None, "long_cue")

        if index == 0:
            continue

        previous_line = lines[index - 1]
        current_line = lines[index]
        gap = float(current_line["start"]) - float(previous_line["end"])
        if gap >= large_gap_seconds:
            note = current_line.get("note")
            current_line["note"] = merge_note(note if isinstance(note, str) else None, "large_gap")

        if (
            visible_text
            and visible_text == visible_texts[index - 1]
            and 0.0 <= gap <= rapid_repeat_window_seconds
        ):
            note = current_line.get("note")
            current_line["note"] = merge_note(note if isinstance(note, str) else None, "rapid_repeat")

    for indices in duplicate_groups.values():
        if len(indices) < 2:
            continue

        has_nonlocal_repeat = False
        for left, right in zip(indices, indices[1:]):
            adjacent = right == left + 1
            gap = float(lines[right]["start"]) - float(lines[left]["end"])
            if not adjacent or gap > rapid_repeat_window_seconds:
                has_nonlocal_repeat = True
                break

        if not has_nonlocal_repeat:
            continue

        for index in indices[1:]:
            note = lines[index].get("note")
            lines[index]["note"] = merge_note(note if isinstance(note, str) else None, "duplicate_cue")


def summarize_notes(
    lines: list[dict[str, object]],
    *,
    path: Path,
    raw_text: str,
    ignore_empty_auto_caption: bool,
    duplicate_min_text_len: int,
    rapid_repeat_window_seconds: float,
    long_cue_chars: int,
    large_gap_seconds: float,
) -> tuple[dict[str, int], list[int], list[int]]:
    summary = {key: 0 for key in CHECK_KEYS}
    candidate_line_indices: list[int] = []
    noise_line_indices: list[int] = []
    annotate_structural_issues(
        lines,
        duplicate_min_text_len=duplicate_min_text_len,
        rapid_repeat_window_seconds=rapid_repeat_window_seconds,
        long_cue_chars=long_cue_chars,
        large_gap_seconds=large_gap_seconds,
    )
    line_languages = {line.get("language") for line in lines if line.get("language")}
    if len(line_languages) > 1:
        summary["mixed_language"] = 1
        for line in lines:
            note = line.get("note")
            line["note"] = merge_note(note if isinstance(note, str) else None, "mixed_language")

    auto_caption_file = ignore_empty_auto_caption and is_auto_caption_vtt(path, raw_text)

    for index, line in enumerate(lines, start=1):
        note = line.get("note")
        if not isinstance(note, str) or not note:
            continue
        flags = {part.strip() for part in note.split(";") if part.strip()}
        downgraded_only_noise = False
        if auto_caption_file and "missing_text" in flags and not str(line.get("text", "")).strip():
            flags.remove("missing_text")
            noise_line_indices.append(index)
            downgraded_only_noise = True
        for key in CHECK_KEYS:
            if key in flags:
                summary[key] += 1
        if flags:
            candidate_line_indices.append(index)
        elif downgraded_only_noise:
            continue

    return summary, candidate_line_indices, noise_line_indices


def has_issues(summary: dict[str, int]) -> bool:
    return any(summary[key] > 0 for key in CHECK_KEYS)


def matches_candidate_issues(summary: dict[str, int], candidate_issues: set[str] | None) -> bool:
    if not candidate_issues:
        return has_issues(summary)
    return any(summary[key] > 0 for key in candidate_issues)


def determine_category(
    *,
    status: str,
    summary: dict[str, int] | None,
    noise_line_indices: list[int] | None = None,
) -> str:
    if status != "ok":
        return "error"
    assert summary is not None
    if has_issues(summary):
        return "candidate"
    if noise_line_indices:
        return "noise"
    return "clean"


def scan_file(
    path: Path,
    *,
    ignore_empty_auto_caption: bool = False,
    duplicate_min_text_len: int = DEFAULT_DUPLICATE_CUE_MIN_CHARS,
    rapid_repeat_window_seconds: float = DEFAULT_RAPID_REPEAT_GAP_SECONDS,
    long_cue_chars: int = DEFAULT_LONG_CUE_CHAR_THRESHOLD,
    large_gap_seconds: float = DEFAULT_LARGE_GAP_SECONDS,
) -> dict[str, object]:
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        contract = clean_subtitle_file(path)
    except Exception as exc:
        return {
            "filename": path.name,
            "source_file": str(path),
            "status": "error",
            "category": "error",
            "error": str(exc),
            "language": None,
            "summary": None,
        }

    note_summary, issue_line_indices, noise_line_indices = summarize_notes(
        contract["lines"],
        path=path,
        raw_text=raw_text,
        ignore_empty_auto_caption=ignore_empty_auto_caption,
        duplicate_min_text_len=duplicate_min_text_len,
        rapid_repeat_window_seconds=rapid_repeat_window_seconds,
        long_cue_chars=long_cue_chars,
        large_gap_seconds=large_gap_seconds,
    )
    summary = {"total_lines": len(contract["lines"]), **note_summary}
    category = determine_category(
        status="ok",
        summary=summary,
        noise_line_indices=noise_line_indices,
    )
    return {
        "filename": path.name,
        "source_file": str(path),
        "status": "ok",
        "category": category,
        "error": None,
        "language": contract["language"],
        "summary": summary,
        "issue_line_indices": issue_line_indices,
        "noise_line_indices": noise_line_indices,
        "total_duration": contract["total_duration"],
    }


def filter_record(
    record: dict[str, object],
    *,
    languages: set[str] | None,
    min_lines: int,
    issues_only: bool,
    candidate_issues: set[str] | None,
) -> bool:
    if record["status"] != "ok":
        return True

    summary = record["summary"]
    assert isinstance(summary, dict)
    if summary["total_lines"] < min_lines:
        return False
    if languages and record["language"] not in languages:
        return False
    if record["category"] == "candidate" and candidate_issues and not matches_candidate_issues(summary, candidate_issues):
        return False
    if issues_only and record["category"] != "candidate":
        return False
    return True


def aggregate(records: list[dict[str, object]]) -> dict[str, Any]:
    issue_totals = {key: 0 for key in CHECK_KEYS}
    ok_files = 0
    error_files = 0
    files_with_issues = 0

    for record in records:
        if record["status"] != "ok":
            error_files += 1
            continue
        ok_files += 1
        summary = record["summary"]
        assert isinstance(summary, dict)
        if has_issues(summary):
            files_with_issues += 1
        for key in CHECK_KEYS:
            issue_totals[key] += int(summary[key])

    return {
        "total_files": len(records),
        "ok_files": ok_files,
        "error_files": error_files,
        "files_with_issues": files_with_issues,
        "candidate_files": sum(1 for record in records if record.get("category") == "candidate"),
        "noise_files": sum(1 for record in records if record.get("category") == "noise"),
        "issue_totals": issue_totals,
    }


def build_report(input_dir: Path, records: list[dict[str, object]], filters: dict[str, object]) -> dict[str, Any]:
    return {
        "input_dir": str(input_dir),
        "filters": filters,
        "summary": aggregate(records),
        "records": records,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload["summary"]
    assert isinstance(summary, dict)
    issue_totals = summary["issue_totals"]
    assert isinstance(issue_totals, dict)
    lines = [
        "# Subtitle Anomaly Scan",
        "",
        f"- Input: `{payload['input_dir']}`",
        f"- Total files: `{summary['total_files']}`",
        f"- Files with issues: `{summary['files_with_issues']}`",
        f"- Candidate files: `{summary['candidate_files']}`",
        f"- Noise-only files: `{summary['noise_files']}`",
        f"- Parser errors: `{summary['error_files']}`",
        "",
        "## Issue Totals",
        "",
        f"- `missing_text`: {issue_totals['missing_text']}",
        f"- `end_before_start`: {issue_totals['end_before_start']}",
        f"- `out_of_order`: {issue_totals['out_of_order']}",
        f"- `mixed_language`: {issue_totals['mixed_language']}",
        f"- `duplicate_cue`: {issue_totals['duplicate_cue']}",
        f"- `rapid_repeat`: {issue_totals['rapid_repeat']}",
        f"- `long_cue`: {issue_totals['long_cue']}",
        f"- `large_gap`: {issue_totals['large_gap']}",
        "",
        "## Candidates",
        "",
        "| File | Category | Language | total_lines | missing_text | end_before_start | out_of_order | mixed_language | duplicate_cue | rapid_repeat | long_cue | large_gap | Issue lines | Noise lines | Error |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]

    for record in payload["records"]:
        if record["status"] != "ok":
            lines.append(
                f"| {record['filename']} | error | - | - | - | - | - | - | - | - | - | - | - | - | {record['error']} |"
            )
            continue
        item_summary = record["summary"]
        assert isinstance(item_summary, dict)
        issue_lines = ",".join(str(i) for i in record["issue_line_indices"]) or "-"
        noise_lines = ",".join(str(i) for i in record.get("noise_line_indices", [])) or "-"
        lines.append(
            f"| {record['filename']} | {record['category']} | {record['language'] or '-'} | {item_summary['total_lines']} | "
            f"{item_summary['missing_text']} | {item_summary['end_before_start']} | "
            f"{item_summary['out_of_order']} | {item_summary['mixed_language']} | {item_summary['duplicate_cue']} | "
            f"{item_summary['rapid_repeat']} | {item_summary['long_cue']} | {item_summary['large_gap']} | "
            f"{issue_lines} | {noise_lines} |  |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_subtitle_anomalies(
    input_dir: str | Path,
    *,
    mode: str | None = None,
    languages: list[str] | None = None,
    min_lines: int = 0,
    issues_only: bool = False,
    candidate_issues: list[str] | None = None,
    ignore_empty_auto_caption: bool = False,
    duplicate_min_text_len: int = DEFAULT_DUPLICATE_CUE_MIN_CHARS,
    rapid_repeat_window_seconds: float = DEFAULT_RAPID_REPEAT_GAP_SECONDS,
    large_gap_seconds: float = DEFAULT_LARGE_GAP_SECONDS,
    long_cue_chars: int = DEFAULT_LONG_CUE_CHAR_THRESHOLD,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    source_root = Path(input_dir).resolve()
    files = iter_subtitle_files(source_root)
    if not files:
        raise FileNotFoundError(f"No supported subtitle files found in {source_root}")

    language_filter = set(languages or [])
    candidate_issue_filter = set(candidate_issues or [])
    scanned = [
        scan_file(
            path,
            ignore_empty_auto_caption=ignore_empty_auto_caption,
            duplicate_min_text_len=duplicate_min_text_len,
            rapid_repeat_window_seconds=rapid_repeat_window_seconds,
            large_gap_seconds=large_gap_seconds,
            long_cue_chars=long_cue_chars,
        )
        for path in files
    ]
    filtered = [
        record
        for record in scanned
        if filter_record(
            record,
            languages=language_filter or None,
            min_lines=min_lines,
            issues_only=issues_only,
            candidate_issues=candidate_issue_filter or None,
        )
    ]
    payload = build_report(
        source_root,
        filtered,
        {
            "mode": mode,
            "languages": sorted(language_filter),
            "min_lines": min_lines,
            "issues_only": issues_only,
            "candidate_issues": sorted(candidate_issue_filter),
            "ignore_empty_auto_caption": ignore_empty_auto_caption,
            "duplicate_min_text_len": duplicate_min_text_len,
            "rapid_repeat_window_seconds": rapid_repeat_window_seconds,
            "large_gap_seconds": large_gap_seconds,
            "long_cue_chars": long_cue_chars,
        },
    )

    if json_path:
        write_json(Path(json_path).resolve(), payload)
    if markdown_path:
        write_markdown(Path(markdown_path).resolve(), payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    options = resolve_cli_options(args)
    try:
        payload = scan_subtitle_anomalies(
            args.input_dir,
            mode=options["mode"],
            languages=options["languages"],
            min_lines=int(options["min_lines"]),
            issues_only=bool(options["issues_only"]),
            candidate_issues=options["candidate_issues"],
            ignore_empty_auto_caption=bool(options["ignore_empty_auto_caption"]),
            duplicate_min_text_len=int(options["duplicate_min_text_len"]),
            rapid_repeat_window_seconds=float(options["rapid_repeat_window_seconds"]),
            large_gap_seconds=float(options["large_gap_seconds"]),
            long_cue_chars=int(options["long_cue_chars"]),
            json_path=options["json_path"],
            markdown_path=options["markdown_path"],
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Scanned {payload['summary']['total_files']} subtitle files, "
        f"flagged {payload['summary']['candidate_files']} candidate files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
