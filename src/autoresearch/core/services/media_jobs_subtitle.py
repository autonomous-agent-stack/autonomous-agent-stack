from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable
from urllib.parse import urlparse

from autoresearch.shared.media_job_contract_subtitle import (
    MediaJobContractSubtitle,
    MediaJobSubtitleRequest,
    SubtitleJobStatus,
    SubtitleOutputFormat,
)
from autoresearch.shared.models import utc_now

_TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)


def clean_subtitle_file(raw_path: Path, out_path: Path, *, output_format: SubtitleOutputFormat) -> Path:
    """Normalize a local subtitle file into either clean SRT or plain text."""
    source = raw_path.read_text(encoding="utf-8")
    if output_format is SubtitleOutputFormat.TXT:
        cleaned = _normalize_txt(source)
    else:
        cleaned = _normalize_srt(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned, encoding="utf-8")
    return out_path


def run_subtitle_job(
    raw_path: Path,
    output_dir: Path,
    *,
    output_format: SubtitleOutputFormat | str = SubtitleOutputFormat.SRT,
    url: str = "offline-fixture",
) -> MediaJobContractSubtitle:
    """Offline pipeline for fixture-driven validation on Mac."""
    started_at = utc_now()
    format_enum = SubtitleOutputFormat(output_format)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{raw_path.stem}_clean.{format_enum.value}"
    try:
        clean_subtitle_file(raw_path, output_path, output_format=format_enum)
        return MediaJobContractSubtitle(
            url=url,
            title=raw_path.stem,
            output_path=output_path.as_posix(),
            output_format=format_enum,
            status=SubtitleJobStatus.DONE,
            metadata={
                "source_kind": "offline-fixture",
                "fixture_name": raw_path.name,
                "duration_seconds": None,
                "language": None,
                "lang_tracks": [],
            },
            raw_subtitle_path=raw_path.as_posix(),
            created_at=started_at,
            updated_at=utc_now(),
        )
    except Exception as exc:
        return MediaJobContractSubtitle(
            url=url,
            title=raw_path.stem,
            output_path=output_path.as_posix(),
            output_format=format_enum,
            status=SubtitleJobStatus.FAILED,
            metadata={
                "source_kind": "offline-fixture",
                "fixture_name": raw_path.name,
                "duration_seconds": None,
                "language": None,
                "lang_tracks": [],
            },
            raw_subtitle_path=raw_path.as_posix(),
            created_at=started_at,
            updated_at=utc_now(),
            error=str(exc),
        )


class MacSubtitleJobService:
    def __init__(
        self,
        *,
        yt_dlp_bin: str = "yt-dlp",
        allowed_domains: set[str] | None = None,
        command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self._yt_dlp_bin = yt_dlp_bin
        self._allowed_domains = {
            item.lower().strip()
            for item in (allowed_domains or {"youtube.com", "youtu.be", "www.youtube.com"})
            if item.strip()
        }
        self._command_runner = command_runner or _run_command

    def fetch_subtitle(
        self,
        youtube_url: str,
        output_dir: str | Path,
        *,
        output_format: SubtitleOutputFormat = SubtitleOutputFormat.SRT,
    ) -> MediaJobContractSubtitle:
        request = MediaJobSubtitleRequest(url=youtube_url, output_format=output_format)
        return self.fetch(request, output_dir=output_dir)

    def fetch(self, request: MediaJobSubtitleRequest, *, output_dir: str | Path) -> MediaJobContractSubtitle:
        created_at = utc_now()
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        output_path = output_dir_path / f"subtitle_clean.{request.output_format.value}"
        title = "unknown"
        raw_subtitle_path: str | None = None

        try:
            if not self.is_supported_url(request.url):
                raise ValueError("subtitle url host is not in the Mac-only allowlist")

            existing_files = {path.resolve() for path in output_dir_path.rglob("*") if path.is_file()}
            raw_metadata = self._probe_metadata(request.url)
            title = _coerce_str(raw_metadata.get("title")) or title

            command = [
                self._yt_dlp_bin,
                "--skip-download",
                "--write-auto-sub",
                "--write-sub",
                "--sub-format",
                "srt",
                "--sub-langs",
                "all",
                "-o",
                str(output_dir_path / "%(title)s-%(id)s.%(ext)s"),
                request.url,
            ]
            result = self._command_runner(command)
            raw_path = self._find_downloaded_subtitle(output_dir_path, existing_files, allow_missing=result.returncode != 0)
            if result.returncode != 0 and raw_path is None:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "subtitle download failed")
            download_warning = None
            if result.returncode != 0:
                download_warning = result.stderr.strip() or result.stdout.strip() or "subtitle download partially succeeded"
            assert raw_path is not None
            raw_subtitle_path = raw_path.as_posix()
            output_path = raw_path.with_name(f"{raw_path.stem}_clean.{request.output_format.value}")
            clean_subtitle_file(raw_path, output_path, output_format=request.output_format)

            return MediaJobContractSubtitle(
                url=request.url,
                title=title,
                output_path=output_path.as_posix(),
                output_format=request.output_format,
                status=SubtitleJobStatus.DONE,
                metadata=_build_contract_metadata(
                    source_kind="yt-dlp",
                    raw_metadata=raw_metadata,
                    raw_subtitle_path=raw_path,
                    download_warning=download_warning,
                ),
                raw_subtitle_path=raw_subtitle_path,
                created_at=created_at,
                updated_at=utc_now(),
            )
        except Exception as exc:
            return MediaJobContractSubtitle(
                url=request.url,
                title=title,
                output_path=output_path.as_posix(),
                output_format=request.output_format,
                status=SubtitleJobStatus.FAILED,
                metadata=request.metadata,
                raw_subtitle_path=raw_subtitle_path,
                created_at=created_at,
                updated_at=utc_now(),
                error=str(exc),
            )

    def is_supported_url(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self._allowed_domains)

    def _probe_metadata(self, url: str) -> dict[str, Any]:
        result = self._command_runner([self._yt_dlp_bin, "--dump-single-json", "--skip-download", url])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "failed to probe subtitle metadata")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid subtitle metadata payload") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("invalid subtitle metadata payload")
        return payload

    @staticmethod
    def _find_downloaded_subtitle(
        output_dir: Path,
        existing_files: set[Path],
        *,
        allow_missing: bool = False,
    ) -> Path | None:
        candidates = [
            path
            for path in output_dir.rglob("*.srt")
            if path.is_file() and path.resolve() not in existing_files and not path.name.endswith("_clean.srt")
        ]
        if not candidates:
            if allow_missing:
                return None
            raise FileNotFoundError("subtitle download did not produce an .srt file")
        candidates.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
        return candidates[0]


def _normalize_srt(source: str) -> str:
    cues = _extract_cues(source)
    if cues:
        blocks: list[str] = []
        for index, cue in enumerate(cues, start=1):
            if cue["start"] is None or cue["end"] is None:
                blocks.append("\n".join(cue["text_lines"]))
                continue
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{cue['start']} --> {cue['end']}",
                        *cue["text_lines"],
                    ]
                )
            )
        return "\n\n".join(blocks) + "\n"
    cleaned = _fallback_clean_lines(source)
    if not cleaned:
        raise ValueError("subtitle source is empty after normalization")
    return "\n".join(cleaned) + "\n"


def _normalize_txt(source: str) -> str:
    cues = _extract_cues(source)
    if cues:
        text_lines = [line for cue in cues for line in cue["text_lines"]]
        if text_lines:
            return "\n".join(text_lines) + "\n"
    cleaned = [line for line in _fallback_clean_lines(source) if not _TIMESTAMP_RE.match(line)]
    if not cleaned:
        raise ValueError("subtitle source does not contain caption text")
    return "\n".join(cleaned) + "\n"


def _extract_cues(source: str) -> list[dict[str, object]]:
    lines = [line.rstrip("\r") for line in source.splitlines()]
    if lines:
        lines[0] = lines[0].lstrip("\ufeff")

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(stripped)
    if current:
        blocks.append(current)

    cues: list[dict[str, object]] = []
    for block in blocks:
        if not block:
            continue
        head = block[0].upper()
        if head == "WEBVTT" or head.startswith("NOTE") or head.startswith("STYLE") or head.startswith("REGION"):
            continue
        filtered_block = [line for line in block if line not in {"WEBVTT"} and not line.startswith(("Kind:", "Language:"))]
        timestamp_index = next((index for index, line in enumerate(filtered_block) if _TIMESTAMP_RE.match(line)), None)
        if timestamp_index is None:
            text_lines = [_normalize_caption_text(line) for line in filtered_block if _normalize_caption_text(line)]
            if text_lines:
                cues.append({"start": None, "end": None, "text_lines": text_lines})
            continue

        match = _TIMESTAMP_RE.match(filtered_block[timestamp_index])
        assert match is not None
        text_lines = [
            normalized
            for line in filtered_block[timestamp_index + 1 :]
            if (normalized := _normalize_caption_text(line))
        ]
        if not text_lines:
            continue
        cues.append(
            {
                "start": _normalize_timestamp(match.group("start")),
                "end": _normalize_timestamp(match.group("end")),
                "text_lines": text_lines,
            }
        )
    return cues


def _fallback_clean_lines(source: str) -> list[str]:
    cleaned_lines: list[str] = []
    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.upper() == "WEBVTT":
            continue
        if stripped.startswith(("NOTE", "STYLE", "REGION", "Kind:", "Language:")):
            continue
        cleaned = _normalize_caption_text(stripped)
        if cleaned:
            cleaned_lines.append(cleaned)
    return cleaned_lines


def _normalize_caption_text(line: str) -> str:
    if _TIMESTAMP_RE.match(line):
        return ""
    if line.isdigit():
        return ""
    return re.sub(r"\s+", " ", line).strip()


def _normalize_timestamp(value: str) -> str:
    return value.replace(".", ",")


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_contract_metadata(
    *,
    source_kind: str,
    raw_metadata: dict[str, Any],
    raw_subtitle_path: Path | None,
    download_warning: str | None = None,
) -> dict[str, Any]:
    language = _infer_language_from_subtitle_path(raw_subtitle_path) if raw_subtitle_path is not None else None
    if language is None:
        language = _coerce_str(raw_metadata.get("language"))

    lang_tracks = _extract_lang_tracks(raw_metadata)
    if not lang_tracks and language:
        lang_tracks = [language]

    metadata: dict[str, Any] = {
        "source_kind": source_kind,
        "video_id": _coerce_str(raw_metadata.get("id")),
        "duration_seconds": _coerce_int(raw_metadata.get("duration")),
        "language": language,
        "lang_tracks": lang_tracks,
    }
    if download_warning:
        metadata["download_warning"] = download_warning
    return metadata


def _infer_language_from_subtitle_path(path: Path) -> str | None:
    suffixes = path.name.split(".")
    if len(suffixes) < 3:
        return None
    candidate = suffixes[-2].strip()
    if not candidate or candidate == path.stem or candidate == "clean":
        return None
    return candidate


def _extract_lang_tracks(raw_metadata: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    subtitles = raw_metadata.get("subtitles")
    if isinstance(subtitles, dict):
        candidates.extend(_normalize_lang_track_keys(subtitles.keys()))
    automatic_captions = raw_metadata.get("automatic_captions")
    if isinstance(automatic_captions, dict):
        candidates.extend(_normalize_lang_track_keys(automatic_captions.keys()))
    return sorted(dict.fromkeys(candidates))


def _normalize_lang_track_keys(keys: Any) -> list[str]:
    tracks: list[str] = []
    for key in keys:
        normalized = _coerce_str(key)
        if normalized:
            tracks.append(normalized)
    return tracks


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)
