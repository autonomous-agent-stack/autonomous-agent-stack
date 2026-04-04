from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from subtitle_offline.contract import SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle, run_subtitle_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mac-only subtitle pipeline entrypoint.")
    parser.add_argument("--input", required=True, help="Local subtitle fixture path or video URL")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force offline mode and treat --input as a local subtitle file",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/subtitles-cli",
        help="Directory to write clean subtitle outputs",
    )
    parser.add_argument(
        "--format",
        choices=["srt", "txt"],
        default="srt",
        help="Desired clean output format",
    )
    parser.add_argument(
        "--yt-dlp-bin",
        default="yt-dlp",
        help="yt-dlp binary to use for online fetch mode",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_format = SubtitleOutputFormat(args.format)
    output_dir = Path(args.output_dir)

    if args.offline or _should_run_offline(args.input):
        job = run_subtitle_job(
            Path(args.input),
            output_dir,
            output_format=output_format,
        )
    else:
        job = fetch_subtitle(
            args.input,
            output_dir,
            output_format=output_format,
            yt_dlp_bin=args.yt_dlp_bin,
        )

    print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2))
    return 0 if job.status.value == "done" else 1


def _should_run_offline(input_value: str) -> bool:
    normalized = input_value.strip()
    return not normalized.startswith(("http://", "https://"))


if __name__ == "__main__":
    raise SystemExit(main())
