from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a minimal online smoke test for subtitle_offline.")
    parser.add_argument("--url", required=True, help="YouTube video URL with available subtitles")
    parser.add_argument(
        "--output-dir",
        default="artifacts/subtitles-smoke",
        help="Directory for smoke-test subtitle outputs",
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
        help="yt-dlp binary to use for the smoke test",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path to also write the result JSON payload",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    job = fetch_subtitle(
        youtube_url=args.url,
        output_dir=Path(args.output_dir),
        output_format=SubtitleOutputFormat(args.format),
        yt_dlp_bin=args.yt_dlp_bin,
    )
    job = _classify_result(job)
    _validate_smoke_result(job)
    payload = json.dumps(job.to_dict(), ensure_ascii=False, indent=2)
    if args.json_out:
        json_out_path = Path(args.json_out)
        json_out_path.parent.mkdir(parents=True, exist_ok=True)
        json_out_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if job.status.value == "done" else 1


def _validate_smoke_result(job: MediaJobContractSubtitle) -> None:
    required_text_fields = {
        "url": job.url,
        "title": job.title,
        "output_path": job.output_path,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise RuntimeError(f"smoke test result missing required field: {field_name}")

    if job.status.value != "done":
        raise RuntimeError(job.error or f"online smoke failed with status={job.status.value}")

    output_path = Path(job.output_path)
    if not output_path.exists():
        raise RuntimeError(f"smoke test output file was not created: {output_path}")
    if output_path.read_text(encoding="utf-8").strip() == "":
        raise RuntimeError(f"smoke test output file is empty: {output_path}")


def _classify_result(job: MediaJobContractSubtitle) -> MediaJobContractSubtitle:
    metadata = dict(job.metadata)
    error_text = " ".join(
        part for part in [metadata.get("download_warning"), job.error] if isinstance(part, str) and part.strip()
    ).strip()

    if job.status.value == "done":
        error_kind = _classify_error_kind(error_text)
        if error_kind is not None:
            metadata["error_kind"] = error_kind
        return job.model_copy(update={"metadata": metadata})

    error_kind = _classify_error_kind(error_text)
    if error_kind is None:
        error_kind = "unknown_download_error"
    metadata["error_kind"] = error_kind
    if error_text:
        metadata["download_warning"] = _summarize_warning(error_kind=error_kind, raw_message=error_text)
    return job.model_copy(update={"metadata": metadata})


def _classify_error_kind(message: str) -> str | None:
    normalized = message.lower()
    if not normalized:
        return None
    if "http error 429" in normalized or "too many requests" in normalized:
        return "rate_limited"
    if "ssl:" in normalized or "unexpected_eof_while_reading" in normalized:
        return "network_ssl"
    if "did not produce an .srt file" in normalized or "no subtitle" in normalized:
        return "no_subtitle_output"
    return "unknown_download_error"


def _summarize_warning(*, error_kind: str, raw_message: str) -> str:
    if error_kind == "rate_limited":
        return "yt-dlp hit rate limiting while fetching one or more subtitle tracks"
    if error_kind == "network_ssl":
        return "yt-dlp failed with an SSL/network transport error"
    if error_kind == "no_subtitle_output":
        return "yt-dlp completed without producing a subtitle file"
    return raw_message.strip()


if __name__ == "__main__":
    raise SystemExit(main())
