#!/usr/bin/env python3
"""Offline smoke checker for subtitle contract validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.service import clean_subtitle_file

SUPPORTED_SUFFIXES = {".vtt", ".srt"}
CHECK_KEYS = ("missing_text", "end_before_start", "out_of_order")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Subtitle contract checker. Run an offline smoke check over one "
            "subtitle file or a directory of fixtures and summarize contract anomalies."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(KIT_ROOT / "fixtures"),
        help="Subtitle file or directory to inspect. Defaults to the kit fixtures.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Write the full check report to a JSON file.",
    )
    parser.add_argument(
        "--report-json",
        dest="json_path",
        help="Alias for --json.",
    )
    parser.add_argument(
        "--markdown",
        dest="markdown_path",
        help="Write the full check report to a Markdown file.",
    )
    parser.add_argument(
        "--report-md",
        dest="markdown_path",
        help="Alias for --markdown.",
    )
    parser.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="Exit non-zero when any contract anomaly is detected. Default: enabled.",
    )
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Always emit reports, but only fail on file-level processing errors.",
    )
    parser.set_defaults(strict=True)
    return parser


def iter_subtitle_files(target: Path) -> list[Path]:
    """Resolve the CLI path into supported subtitle files."""

    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_SUFFIXES else []
    return sorted(
        path for path in target.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def summarize_notes(lines: Iterable[dict[str, object]]) -> dict[str, int]:
    """Count each supported anomaly flag from the line notes."""

    summary = {key: 0 for key in CHECK_KEYS}
    for line in lines:
        note = line.get("note")
        if not isinstance(note, str) or not note:
            continue
        flags = {part.strip() for part in note.split(";") if part.strip()}
        for key in CHECK_KEYS:
            if key in flags:
                summary[key] += 1
    return summary


def check_file(filepath: Path) -> dict[str, object]:
    """Run the contract check on one subtitle file."""

    try:
        result = clean_subtitle_file(filepath)
    except Exception as exc:
        return {
            "filename": filepath.name,
            "status": "error",
            "error": str(exc),
            "summary": None,
        }

    summary = {"total_lines": len(result["lines"]), **summarize_notes(result["lines"])}
    return {
        "filename": filepath.name,
        "status": "ok",
        "error": None,
        "summary": summary,
    }


def has_contract_issues(summary: dict[str, int] | None) -> bool:
    """Return whether one summary contains actionable anomalies."""

    if summary is None:
        return True
    return any(summary[key] > 0 for key in CHECK_KEYS)


def aggregate_results(results: list[dict[str, object]]) -> dict[str, Any]:
    """Build a top-level summary across all checked files."""

    issue_totals = {key: 0 for key in CHECK_KEYS}
    ok_files = 0
    error_files = 0
    files_with_issues = 0

    for result in results:
        if result["status"] != "ok":
            error_files += 1
            continue

        ok_files += 1
        summary = result["summary"]
        assert isinstance(summary, dict)
        if has_contract_issues(summary):
            files_with_issues += 1
        for key in CHECK_KEYS:
            issue_totals[key] += int(summary[key])

    return {
        "checked_files": len(results),
        "ok_files": ok_files,
        "error_files": error_files,
        "files_with_issues": files_with_issues,
        "issue_totals": issue_totals,
    }


def compute_exit_code(results: list[dict[str, object]], *, strict: bool) -> int:
    """Translate check results into the CLI exit code."""

    if strict:
        return (
            1
            if any(result["status"] != "ok" or has_contract_issues(result["summary"]) for result in results)
            else 0
        )
    return 1 if any(result["status"] != "ok" for result in results) else 0


def build_report(target: Path, results: list[dict[str, object]], exit_code: int) -> dict[str, Any]:
    """Create a serializable report payload."""

    aggregate = aggregate_results(results)
    return {
        "target": str(target),
        "status": "issues" if exit_code else "ok",
        "exit_code": exit_code,
        "summary": aggregate,
        "results": results,
    }


def write_json_report(path: Path, report: dict[str, Any]) -> None:
    """Persist a machine-readable JSON report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    """Persist a human-readable Markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    assert isinstance(summary, dict)
    issue_totals = summary["issue_totals"]
    assert isinstance(issue_totals, dict)

    lines = [
        "# Subtitle Contract Report",
        "",
        f"- Target: `{report['target']}`",
        f"- Status: `{report['status']}`",
        f"- Exit code: `{report['exit_code']}`",
        f"- Checked files: `{summary['checked_files']}`",
        f"- Files with issues: `{summary['files_with_issues']}`",
        f"- Parser errors: `{summary['error_files']}`",
        "",
        "## Issue Totals",
        "",
        f"- `missing_text`: {issue_totals['missing_text']}",
        f"- `end_before_start`: {issue_totals['end_before_start']}",
        f"- `out_of_order`: {issue_totals['out_of_order']}",
        "",
        "## Results",
        "",
        "| File | Status | total_lines | missing_text | end_before_start | out_of_order | Error |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for result in report["results"]:
        assert isinstance(result, dict)
        if result["status"] != "ok":
            lines.append(
                f"| {result['filename']} | error | - | - | - | - | {result['error']} |"
            )
            continue

        item_summary = result["summary"]
        assert isinstance(item_summary, dict)
        lines.append(
            f"| {result['filename']} | ok | {item_summary['total_lines']} | "
            f"{item_summary['missing_text']} | {item_summary['end_before_start']} | "
            f"{item_summary['out_of_order']} |  |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    target = Path(args.path).resolve()

    try:
        files = iter_subtitle_files(target)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not files:
        print(f"No supported subtitle files found in {target}", file=sys.stderr)
        return 1

    print(f"Checking subtitle contract in {target}")

    results = [check_file(path) for path in files]
    for result in results:
        if result["status"] != "ok":
            print(f"{result['filename']}: ERROR -> {result['error']}")
            continue

        summary = result["summary"]
        assert isinstance(summary, dict)
        print(
            f"{result['filename']}: total_lines={summary['total_lines']}, "
            f"missing_text={summary['missing_text']}, "
            f"end_before_start={summary['end_before_start']}, "
            f"out_of_order={summary['out_of_order']}"
        )

    exit_code = compute_exit_code(results, strict=args.strict)
    report = build_report(target, results, exit_code)

    if args.json_path:
        write_json_report(Path(args.json_path).resolve(), report)
    if args.markdown_path:
        write_markdown_report(Path(args.markdown_path).resolve(), report)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
