from __future__ import annotations

import argparse
import json
from pathlib import Path

from subtitle_offline.contract import SubtitleOutputFormat
from subtitle_offline.service import run_subtitle_job


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Mac-only offline subtitle contract check.")
    parser.add_argument("raw_path", help="Path to a local .srt/.vtt fixture")
    parser.add_argument("--output-dir", default="artifacts/subtitles-check", help="Directory for clean outputs")
    parser.add_argument("--format", choices=["srt", "txt"], default="srt", help="Desired clean output format")
    args = parser.parse_args()

    job = run_subtitle_job(
        Path(args.raw_path),
        Path(args.output_dir),
        output_format=SubtitleOutputFormat(args.format),
    )
    print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2))
    return 0 if job.status.value == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
