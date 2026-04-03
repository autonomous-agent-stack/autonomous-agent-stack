#!/usr/bin/env python3
"""Harvest representative subtitle fixtures from a larger local corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.service import clean_subtitle_file

SUPPORTED_SUFFIXES = {".srt", ".vtt"}
LONG_FILE_LINE_THRESHOLD = 100
LONG_FILE_DURATION_THRESHOLD = 1800.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harvest representative subtitle fixtures from a local subtitle corpus."
    )
    parser.add_argument("--input-dir", required=True, help="Corpus directory or one subtitle file.")
    parser.add_argument("--output-dir", required=True, help="Destination directory for copied fixtures.")
    parser.add_argument(
        "--manifest-json",
        help="Optional JSON manifest path. Defaults to a sibling reports directory when available.",
    )
    parser.add_argument(
        "--manifest-md",
        help="Optional Markdown manifest path. Defaults to a sibling reports directory when available.",
    )
    return parser


def iter_subtitle_files(target: Path) -> list[Path]:
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_SUFFIXES else []
    return sorted(
        path for path in target.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 64), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_anomalies(contract: dict[str, Any]) -> list[str]:
    anomalies: set[str] = set()
    for line in contract["lines"]:
        note = line.get("note")
        if isinstance(note, str) and note:
            anomalies.update(part.strip() for part in note.split(";") if part.strip())
    if contract["language"] is None:
        anomalies.add("unknown_language")
    if (
        len(contract["lines"]) >= LONG_FILE_LINE_THRESHOLD
        or float(contract["total_duration"]) >= LONG_FILE_DURATION_THRESHOLD
    ):
        anomalies.add("long")
    return sorted(anomalies)


def choose_harvest_name(source: Path, checksum: str, seen_names: set[str]) -> str:
    candidate = source.name
    if candidate not in seen_names:
        seen_names.add(candidate)
        return candidate

    renamed = f"{source.stem}-{checksum[:8]}{source.suffix.lower()}"
    seen_names.add(renamed)
    return renamed


def default_report_root(output_dir: Path) -> Path:
    if output_dir.parent.name == "fixtures":
        return output_dir.parents[1] / "reports"
    return output_dir


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Harvested Subtitle Fixtures",
        "",
        f"- Input: `{payload['input_dir']}`",
        f"- Output: `{payload['output_dir']}`",
        f"- Total files: `{payload['summary']['total_files']}`",
        f"- Copied files: `{payload['summary']['copied_files']}`",
        f"- Error files: `{payload['summary']['error_files']}`",
        "",
        "| File | Language | Anomalies | Checksum |",
        "|---|---|---|---|",
    ]

    for record in payload["records"]:
        if record["status"] != "ok":
            lines.append(
                f"| {record['filename']} | - | error | {record.get('checksum', '-') or '-'} |"
            )
            continue
        anomalies = ",".join(record["anomalies"]) if record["anomalies"] else "clean"
        lines.append(
            f"| {record['filename']} | {record['language'] or '-'} | {anomalies} | "
            f"{record['checksum'][:12]} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def harvest_subtitles(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    manifest_json: str | Path | None = None,
    manifest_md: str | Path | None = None,
) -> dict[str, Any]:
    source_root = Path(input_dir).resolve()
    destination_root = Path(output_dir).resolve()
    files = iter_subtitle_files(source_root)
    if not files:
        raise FileNotFoundError(f"No supported subtitle files found in {source_root}")

    destination_root.mkdir(parents=True, exist_ok=True)
    seen_names: set[str] = set()
    records: list[dict[str, Any]] = []

    for source in files:
        checksum = sha256_file(source)
        try:
            contract = clean_subtitle_file(source)
        except Exception as exc:
            records.append(
                {
                    "filename": source.name,
                    "source_file": str(source),
                    "status": "error",
                    "error": str(exc),
                    "checksum": checksum,
                }
            )
            continue

        harvested_name = choose_harvest_name(source, checksum, seen_names)
        copied_path = destination_root / harvested_name
        shutil.copy2(source, copied_path)
        records.append(
            {
                "filename": source.name,
                "source_file": str(source),
                "harvested_file": str(copied_path),
                "status": "ok",
                "language": contract["language"],
                "line_count": len(contract["lines"]),
                "total_duration": contract["total_duration"],
                "size_bytes": source.stat().st_size,
                "checksum": checksum,
                "anomalies": summarize_anomalies(contract),
            }
        )

    summary = {
        "total_files": len(records),
        "copied_files": sum(1 for item in records if item["status"] == "ok"),
        "error_files": sum(1 for item in records if item["status"] != "ok"),
    }
    payload = {
        "input_dir": str(source_root),
        "output_dir": str(destination_root),
        "summary": summary,
        "records": records,
    }

    report_root = default_report_root(destination_root)
    json_path = Path(manifest_json).resolve() if manifest_json else report_root / "harvested-manifest.json"
    md_path = Path(manifest_md).resolve() if manifest_md else report_root / "harvested-manifest.md"
    write_json(json_path, payload)
    write_markdown(md_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = harvest_subtitles(
            args.input_dir,
            args.output_dir,
            manifest_json=args.manifest_json,
            manifest_md=args.manifest_md,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Harvested {payload['summary']['copied_files']} subtitle fixtures "
        f"from {payload['summary']['total_files']} discovered files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
