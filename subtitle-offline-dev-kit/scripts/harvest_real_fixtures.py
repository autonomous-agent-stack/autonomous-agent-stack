#!/usr/bin/env python3
"""Regenerate dev-kit fixtures from real subtitle sources."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]

if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from subtitle_offline.utils import split_subtitle_blocks

TAG_RE = re.compile(r"<[^>]+>")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Regenerate real-derived fixture files from the harvest manifest.")
    parser.add_argument(
        "--manifest",
        default=str(KIT_ROOT / "fixtures" / "manifest.json"),
        help="Path to the harvest manifest JSON.",
    )
    return parser


def load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vtt_cues(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    cues: list[dict[str, object]] = []
    for block in split_subtitle_blocks(text):
        lines = block.splitlines()
        timestamp_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timestamp_index is None:
            continue
        cues.append(
            {
                "time_line": lines[timestamp_index].rstrip(),
                "text_lines": [line.rstrip() for line in lines[timestamp_index + 1 :]],
            }
        )
    return cues


def extract_cues(path: Path, cue_indices: list[int]) -> list[dict[str, object]]:
    cues = load_vtt_cues(path)
    return [cues[index] for index in cue_indices]


def strip_vtt_tags(text: str) -> str:
    return TAG_RE.sub("", text)


def normalize_srt_lines(text_lines: list[str]) -> list[str]:
    cleaned = [strip_vtt_tags(line).strip() for line in text_lines]
    return [line for line in cleaned if line]


def vtt_timestamp_to_srt_token(token: str) -> str:
    return token.replace(".", ",")


def convert_time_line_to_srt(time_line: str) -> str:
    start_text, end_text = time_line.split("-->", 1)
    start_token = start_text.strip().split()[0]
    end_token = end_text.strip().split()[0]
    return f"{vtt_timestamp_to_srt_token(start_token)} --> {vtt_timestamp_to_srt_token(end_token)}"


def render_vtt(cues: list[dict[str, object]]) -> str:
    blocks = ["WEBVTT"]
    for cue in cues:
        text_lines = list(cue["text_lines"])
        block_lines = [str(cue["time_line"]), *[str(line) for line in text_lines]]
        blocks.append("\n".join(block_lines).rstrip())
    return "\n\n".join(blocks).rstrip() + "\n"


def render_srt(
    cues: list[dict[str, object]],
    *,
    dirty_arrow_indices: list[int] | None = None,
    blank_text_indices: list[int] | None = None,
    time_overrides: dict[str, dict[str, str]] | None = None,
) -> str:
    dirty_arrow_indices = dirty_arrow_indices or []
    blank_text_indices = blank_text_indices or []
    time_overrides = time_overrides or {}
    blocks: list[str] = []

    for index, cue in enumerate(cues, start=1):
        cue_key = str(index - 1)
        time_line = convert_time_line_to_srt(str(cue["time_line"]))
        if cue_key in time_overrides:
            override = time_overrides[cue_key]
            time_line = f"{override['start']} --> {override['end']}"
        if (index - 1) in dirty_arrow_indices:
            time_line = time_line.replace(" --> ", "  --> ")

        if (index - 1) in blank_text_indices:
            text_lines: list[str] = []
        else:
            text_lines = normalize_srt_lines(list(cue["text_lines"]))

        blocks.append("\n".join([str(index), time_line, *text_lines]).rstrip())

    return "\n\n".join(blocks).rstrip() + "\n"


def materialize_fixture(fixtures_dir: Path, item: dict[str, object]) -> Path:
    output_path = fixtures_dir / str(item["output"])
    recipe = str(item["recipe"])

    if recipe == "vtt_slice":
        source = Path(str(item["source"]))
        cues = extract_cues(source, list(item["cue_indices"]))
        output = render_vtt(cues)
    elif recipe == "srt_from_vtt_slice":
        source = Path(str(item["source"]))
        cues = extract_cues(source, list(item["cue_indices"]))
        output = render_srt(
            cues,
            dirty_arrow_indices=list(item.get("dirty_arrow_indices", [])),
            blank_text_indices=list(item.get("blank_text_indices", [])),
            time_overrides=dict(item.get("time_overrides", {})),
        )
    elif recipe == "mixed_vtt":
        cues: list[dict[str, object]] = []
        for source_spec in list(item["sources"]):
            spec = dict(source_spec)
            source = Path(str(spec["source"]))
            cues.extend(extract_cues(source, list(spec["cue_indices"])))
        output = render_vtt(cues)
    else:
        raise ValueError(f"Unsupported recipe: {recipe}")

    output_path.write_text(output, encoding="utf-8")
    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    fixtures_dir = manifest_path.parent

    generated_paths: list[Path] = []
    for item in list(manifest["fixtures"]):
        generated_paths.append(materialize_fixture(fixtures_dir, dict(item)))

    for path in generated_paths:
        print(f"generated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
