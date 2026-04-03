#!/usr/bin/env python3
"""Scan a subtitle corpus and surface anomaly candidates for fixture harvest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.service import clean_subtitle_file
from subtitle_offline.utils import merge_note

SUPPORTED_SUFFIXES = {".srt", ".vtt"}
CHECK_KEYS = ("missing_text", "end_before_start", "out_of_order", "mixed_language")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan subtitle files recursively and report anomaly candidates."
    )
    parser.add_argument("--input-dir", required=True, help="Directory or subtitle file to scan.")
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
    return parser


def iter_subtitle_files(target: Path) -> list[Path]:
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_SUFFIXES else []
    return sorted(path for path in target.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)


def summarize_notes(lines: list[dict[str, object]]) -> dict[str, int]:
    summary = {key: 0 for key in CHECK_KEYS}
    line_languages = {line.get("language") for line in lines if line.get("language")}
    if len(line_languages) > 1:
        summary["mixed_language"] = 1
        for line in lines:
            note = line.get("note")
            line["note"] = merge_note(note if isinstance(note, str) else None, "mixed_language")

    for line in lines:
        note = line.get("note")
        if not isinstance(note, str) or not note:
            continue
        flags = {part.strip() for part in note.split(";") if part.strip()}
        for key in CHECK_KEYS:
            if key in flags:
                summary[key] += 1
    return summary


def has_issues(summary: dict[str, int]) -> bool:
    return any(summary[key] > 0 for key in CHECK_KEYS)


def scan_file(path: Path) -> dict[str, object]:
    try:
        contract = clean_subtitle_file(path)
    except Exception as exc:
        return {
            "filename": path.name,
            "source_file": str(path),
            "status": "error",
            "error": str(exc),
            "language": None,
            "summary": None,
        }

    summary = {"total_lines": len(contract["lines"]), **summarize_notes(contract["lines"])}
    issue_line_indices = [
        index
        for index, line in enumerate(contract["lines"], start=1)
        if isinstance(line.get("note"), str) and line["note"]
    ]
    return {
        "filename": path.name,
        "source_file": str(path),
        "status": "ok",
        "error": None,
        "language": contract["language"],
        "summary": summary,
        "issue_line_indices": issue_line_indices,
        "total_duration": contract["total_duration"],
    }


def filter_record(record: dict[str, object], *, languages: set[str] | None, min_lines: int, issues_only: bool) -> bool:
    if record["status"] != "ok":
        return True

    summary = record["summary"]
    assert isinstance(summary, dict)
    if summary["total_lines"] < min_lines:
        return False
    if languages and record["language"] not in languages:
        return False
    if issues_only and not has_issues(summary):
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
        f"- Parser errors: `{summary['error_files']}`",
        "",
        "## Issue Totals",
        "",
        f"- `missing_text`: {issue_totals['missing_text']}",
        f"- `end_before_start`: {issue_totals['end_before_start']}",
        f"- `out_of_order`: {issue_totals['out_of_order']}",
        f"- `mixed_language`: {issue_totals['mixed_language']}",
        "",
        "## Candidates",
        "",
        "| File | Language | total_lines | missing_text | end_before_start | out_of_order | mixed_language | Issue lines | Error |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]

    for record in payload["records"]:
        if record["status"] != "ok":
            lines.append(
                f"| {record['filename']} | - | - | - | - | - | - | - | {record['error']} |"
            )
            continue
        item_summary = record["summary"]
        assert isinstance(item_summary, dict)
        issue_lines = ",".join(str(i) for i in record["issue_line_indices"]) or "-"
        lines.append(
            f"| {record['filename']} | {record['language'] or '-'} | {item_summary['total_lines']} | "
            f"{item_summary['missing_text']} | {item_summary['end_before_start']} | "
            f"{item_summary['out_of_order']} | {item_summary['mixed_language']} | {issue_lines} |  |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_subtitle_anomalies(
    input_dir: str | Path,
    *,
    languages: list[str] | None = None,
    min_lines: int = 0,
    issues_only: bool = False,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    source_root = Path(input_dir).resolve()
    files = iter_subtitle_files(source_root)
    if not files:
        raise FileNotFoundError(f"No supported subtitle files found in {source_root}")

    language_filter = set(languages or [])
    scanned = [scan_file(path) for path in files]
    filtered = [
        record
        for record in scanned
        if filter_record(record, languages=language_filter or None, min_lines=min_lines, issues_only=issues_only)
    ]
    payload = build_report(
        source_root,
        filtered,
        {
            "languages": sorted(language_filter),
            "min_lines": min_lines,
            "issues_only": issues_only,
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
    try:
        payload = scan_subtitle_anomalies(
            args.input_dir,
            languages=args.languages,
            min_lines=args.min_lines,
            issues_only=args.issues_only,
            json_path=args.json_path,
            markdown_path=args.markdown_path,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Scanned {payload['summary']['total_files']} subtitle files, "
        f"flagged {payload['summary']['files_with_issues']} candidate files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
