#!/usr/bin/env python3
"""Convert normalized subtitles into notes-ready JSONL chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.service import clean_subtitle_file

SUPPORTED_SUFFIXES = {".srt", ".vtt"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chunk subtitle files into notes-ready JSONL artifacts."
    )
    parser.add_argument("--input-dir", required=True, help="Directory or subtitle file to chunk.")
    parser.add_argument("--output-dir", required=True, help="Output directory for notes-ready artifacts.")
    parser.add_argument(
        "--output-file",
        help="Optional JSONL output path. Defaults to <output-dir>/chunks.jsonl.",
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


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_chunk_records(source: Path, contract: dict[str, Any], source_checksum: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_index, line in enumerate(contract["lines"], start=1):
        text = str(line["text"]).strip()
        if not text:
            continue
        chunk = {
            "source_file": source.name,
            "source_language": contract["language"],
            "line_language": line["language"],
            "line_index": line_index,
            "start": line["start"],
            "end": line["end"],
            "text": text,
            "source_checksum": source_checksum,
        }
        chunk["chunk_checksum"] = sha256_text(
            json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        )
        records.append(chunk)
    return records


def chunk_subtitles(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    output_file: str | Path | None = None,
) -> dict[str, Any]:
    source_root = Path(input_dir).resolve()
    destination_root = Path(output_dir).resolve()
    files = iter_subtitle_files(source_root)
    if not files:
        raise FileNotFoundError(f"No supported subtitle files found in {source_root}")

    destination_root.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_file).resolve() if output_file else destination_root / "chunks.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chunk_count = 0
    file_count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for source in files:
            contract = clean_subtitle_file(source)
            source_checksum = sha256_file(source)
            records = build_chunk_records(source, contract, source_checksum)
            file_count += 1
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                chunk_count += 1

    return {
        "input_dir": str(source_root),
        "output_dir": str(destination_root),
        "output_file": str(output_path),
        "file_count": file_count,
        "chunk_count": chunk_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = chunk_subtitles(args.input_dir, args.output_dir, output_file=args.output_file)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {payload['chunk_count']} notes-ready chunks "
        f"from {payload['file_count']} subtitle files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
