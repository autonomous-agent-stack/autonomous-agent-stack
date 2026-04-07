from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from autoresearch.core.services.youtube_errors import (
    YouTubeFetchError,
    classify_yt_dlp_failure,
)
from autoresearch.shared.models import (
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeResultKind,
    YouTubeTargetKind,
    YouTubeTranscriptSource,
)


@dataclass(frozen=True)
class YouTubeSourceDescriptor:
    normalized_url: str
    target_kind: YouTubeTargetKind
    external_id: str | None = None
    title: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class YouTubeVideoSnapshot:
    video_id: str
    source_url: str
    title: str | None = None
    channel_id: str | None = None
    channel_title: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class YouTubeTranscriptPayload:
    language: str
    source: YouTubeTranscriptSource
    content: str
    result_kind: YouTubeResultKind = YouTubeResultKind.SUCCESS
    failure_kind: YouTubeFailureKind | None = None
    reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class YouTubeCaptionInventory:
    manual_languages: tuple[str, ...] = ()
    automatic_languages: tuple[str, ...] = ()


class YouTubeFetcher:
    """Thin shell around yt-dlp plus URL normalization helpers."""

    _VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,}$")

    def __init__(
        self,
        *,
        command_timeout_seconds: float = 120.0,
        command_extra_args: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self._command_timeout_seconds = command_timeout_seconds
        self._command_extra_args = tuple(command_extra_args or ())

    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        normalized = url.strip()
        parsed = urlparse(normalized)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        normalized_path = path.rstrip("/") or path or "/"
        query = parse_qs(parsed.query or "")

        if "youtu.be" in host:
            video_id = path.lstrip("/")
            if not video_id:
                raise YouTubeFetchError(
                    YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                    "short YouTube URL is missing video id",
                    failed_stage=YouTubeFailedStage.DISCOVERY,
                )
            return YouTubeSourceDescriptor(
                normalized_url=f"https://www.youtube.com/watch?v={video_id}",
                target_kind=YouTubeTargetKind.VIDEO,
                external_id=video_id,
            )

        if "youtube.com" in host:
            if normalized_path == "/playlist" and "list" in query:
                playlist_id = query["list"][0].strip()
                if not playlist_id:
                    raise YouTubeFetchError(
                        YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                        "playlist URL is missing list id",
                        failed_stage=YouTubeFailedStage.DISCOVERY,
                    )
                return YouTubeSourceDescriptor(
                    normalized_url=f"https://www.youtube.com/playlist?list={playlist_id}",
                    target_kind=YouTubeTargetKind.PLAYLIST,
                    external_id=playlist_id,
                )
            if normalized_path == "/watch" and "v" in query:
                video_id = query["v"][0].strip()
                if not video_id:
                    raise YouTubeFetchError(
                        YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                        "video URL is missing v parameter",
                        failed_stage=YouTubeFailedStage.DISCOVERY,
                    )
                return YouTubeSourceDescriptor(
                    normalized_url=f"https://www.youtube.com/watch?v={video_id}",
                    target_kind=YouTubeTargetKind.VIDEO,
                    external_id=video_id,
                )
            for prefix in ("/@", "/channel/", "/c/", "/user/"):
                if normalized_path.startswith(prefix):
                    external_id = normalized_path.removeprefix(prefix).split("/", 1)[0].strip()
                    if not external_id:
                        raise YouTubeFetchError(
                            YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                            "channel URL is missing channel handle or id",
                            failed_stage=YouTubeFailedStage.DISCOVERY,
                        )
                    return YouTubeSourceDescriptor(
                        normalized_url=f"https://www.youtube.com{normalized_path}",
                        target_kind=YouTubeTargetKind.CHANNEL,
                        external_id=external_id,
                    )

        fallback = normalized.rstrip("/")
        if self._VIDEO_ID_RE.match(fallback):
            return YouTubeSourceDescriptor(
                normalized_url=f"https://www.youtube.com/watch?v={fallback}",
                target_kind=YouTubeTargetKind.VIDEO,
                external_id=fallback,
            )

        raise YouTubeFetchError(
            YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
            f"unsupported or unparseable YouTube source: {url}",
            failed_stage=YouTubeFailedStage.DISCOVERY,
        )

    def discover_videos(
        self,
        source_url: str,
        target_kind: YouTubeTargetKind,
        *,
        limit: int = 5,
    ) -> list[YouTubeVideoSnapshot]:
        if target_kind == YouTubeTargetKind.VIDEO:
            return [self.fetch_video_metadata(source_url)]

        payload = self._fetch_video_payload(
            [
                "yt-dlp",
                "--dump-single-json",
                "--flat-playlist",
                "--playlist-end",
                str(limit),
                source_url,
            ],
            failed_stage=YouTubeFailedStage.DISCOVERY,
        )
        entries = payload.get("entries") or []
        snapshots: list[YouTubeVideoSnapshot] = []
        for entry in entries[:limit]:
            if not isinstance(entry, dict):
                continue
            snapshot = self._snapshot_from_payload(entry)
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        payload = self._fetch_video_payload(
            [
                "yt-dlp",
                "--dump-single-json",
                "--no-warnings",
                "--skip-download",
                source_url,
            ],
            failed_stage=YouTubeFailedStage.METADATA_FETCH,
        )
        snapshot = self._snapshot_from_payload(payload)
        if snapshot is None:
            raise YouTubeFetchError(
                YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
                f"unable to parse video metadata for {source_url}",
                failed_stage=YouTubeFailedStage.METADATA_FETCH,
            )
        return snapshot

    def fetch_transcript(
        self,
        source_url: str,
        *,
        preferred_languages: list[str],
        include_auto_generated: bool,
    ) -> YouTubeTranscriptPayload:
        if not preferred_languages:
            preferred_languages = ["en"]

        payload = self._fetch_video_payload(
            [
                "yt-dlp",
                "--dump-single-json",
                "--no-warnings",
                "--skip-download",
                source_url,
            ],
            failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
        )
        inventory = self._extract_caption_inventory(payload)

        selected_manual = self._match_language(preferred_languages, inventory.manual_languages)
        selected_auto = self._match_language(preferred_languages, inventory.automatic_languages)

        result_kind = YouTubeResultKind.SUCCESS
        failure_kind: YouTubeFailureKind | None = None
        reason: str | None = None

        if selected_manual:
            selected_language = selected_manual
            selected_source = YouTubeTranscriptSource.MANUAL
            write_auto_sub = False
        elif selected_auto:
            selected_language = selected_auto
            selected_source = YouTubeTranscriptSource.AUTOMATIC
            if not include_auto_generated:
                raise YouTubeFetchError(
                    YouTubeFailureKind.AUTO_CAPTIONS_ONLY,
                    "only auto captions are available for the requested languages",
                    failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
                    details={
                        "preferred_languages": preferred_languages,
                        "automatic_languages": list(inventory.automatic_languages),
                    },
                )
            result_kind = YouTubeResultKind.WARNING
            failure_kind = YouTubeFailureKind.AUTO_CAPTIONS_ONLY
            reason = "manual subtitles unavailable; using auto captions"
            write_auto_sub = True
        elif inventory.manual_languages or inventory.automatic_languages:
                raise YouTubeFetchError(
                    YouTubeFailureKind.SUBTITLE_LANGUAGE_MISMATCH,
                    "requested subtitle languages are not available",
                    failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
                    details={
                        "preferred_languages": preferred_languages,
                        "manual_languages": list(inventory.manual_languages),
                        "automatic_languages": list(inventory.automatic_languages),
                    },
            )
        else:
            raise YouTubeFetchError(
                YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
                "no subtitles or auto captions are available for this video",
                failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
            )

        with tempfile.TemporaryDirectory(prefix="youtube-transcript-") as temp_dir:
            base_dir = Path(temp_dir)
            output_template = str(base_dir / "%(id)s.%(language)s.%(ext)s")
            command = [
                "yt-dlp",
                "--skip-download",
                "--no-warnings",
                "--sub-format",
                "vtt",
                "--sub-langs",
                selected_language,
            ]
            if write_auto_sub:
                command.append("--write-auto-sub")
            else:
                command.append("--write-sub")
            command.extend(["--output", output_template, source_url])
            self._run_command(command, failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH)

            candidates = sorted(base_dir.glob("*.vtt")) + sorted(base_dir.glob("*.srt")) + sorted(base_dir.glob("*.ttml"))
            if not candidates:
                raise YouTubeFetchError(
                    YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
                    "caption inventory exists but yt-dlp did not produce subtitle files",
                    failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
                    details={"selected_language": selected_language},
                )

            transcript_file = candidates[0]
            content = self._normalize_subtitle(transcript_file.read_text(encoding="utf-8", errors="ignore"))
            if not content.strip():
                raise YouTubeFetchError(
                    YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
                    "subtitle file was downloaded but contained no usable text",
                    failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
                    details={"selected_language": selected_language},
                )

            return YouTubeTranscriptPayload(
                language=selected_language,
                source=selected_source,
                content=content,
                result_kind=result_kind,
                failure_kind=failure_kind,
                reason=reason,
                metadata={
                    "subtitle_path": str(transcript_file),
                    "manual_languages": list(inventory.manual_languages),
                    "automatic_languages": list(inventory.automatic_languages),
                },
            )

    def _fetch_video_payload(
        self,
        command: list[str],
        *,
        failed_stage: YouTubeFailedStage,
    ) -> dict[str, object]:
        completed = self._run_command(command, failed_stage=failed_stage)
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise YouTubeFetchError(
                YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
                f"empty yt-dlp output for command: {' '.join(command)}",
                failed_stage=failed_stage,
            )
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise YouTubeFetchError(
                YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
                f"invalid yt-dlp json output: {exc}",
                failed_stage=failed_stage,
            ) from exc

    def _run_command(
        self,
        command: list[str],
        *,
        failed_stage: YouTubeFailedStage,
    ) -> subprocess.CompletedProcess[str]:
        effective_command = [command[0], *self._command_extra_args, *command[1:]]
        if shutil.which(effective_command[0]) is None:
            raise YouTubeFetchError(
                YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
                f"{effective_command[0]} is not installed",
                failed_stage=failed_stage,
            )
        try:
            completed = subprocess.run(
                effective_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._command_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise YouTubeFetchError(
                YouTubeFailureKind.TIMEOUT_FAILURE,
                f"{effective_command[0]} timed out after {exc.timeout} seconds",
                retryable=True,
                failed_stage=failed_stage,
                details={"command": effective_command},
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            classification = classify_yt_dlp_failure(stderr)
            raise YouTubeFetchError(
                classification.failure_kind,
                stderr or f"{effective_command[0]} failed with exit code {completed.returncode}",
                retryable=classification.retryable,
                failed_stage=failed_stage,
                details={"command": effective_command},
            )
        return completed

    def _extract_caption_inventory(self, payload: dict[str, object]) -> YouTubeCaptionInventory:
        subtitles = payload.get("subtitles")
        automatic_captions = payload.get("automatic_captions")
        manual_languages = tuple(sorted(subtitles.keys())) if isinstance(subtitles, dict) else ()
        automatic_languages = tuple(sorted(automatic_captions.keys())) if isinstance(automatic_captions, dict) else ()
        return YouTubeCaptionInventory(
            manual_languages=manual_languages,
            automatic_languages=automatic_languages,
        )

    def _snapshot_from_payload(self, payload: object) -> YouTubeVideoSnapshot | None:
        if not isinstance(payload, dict):
            return None

        video_id = str(payload.get("id") or payload.get("url") or "").strip()
        if not video_id:
            return None
        source_url = str(payload.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}")
        inventory = self._extract_caption_inventory(payload)

        return YouTubeVideoSnapshot(
            video_id=video_id,
            source_url=source_url,
            title=self._optional_text(payload.get("title")),
            channel_id=self._optional_text(payload.get("channel_id")),
            channel_title=self._optional_text(payload.get("channel") or payload.get("uploader")),
            description=self._optional_text(payload.get("description")),
            published_at=self._parse_datetime(payload),
            duration_seconds=self._parse_int(payload.get("duration")),
            metadata={
                "extractor": payload.get("extractor"),
                "playlist_id": payload.get("playlist_id"),
                "manual_languages": list(inventory.manual_languages),
                "automatic_languages": list(inventory.automatic_languages),
            },
        )

    def _parse_datetime(self, payload: dict[str, object]) -> datetime | None:
        timestamp = payload.get("timestamp")
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)

        upload_date = self._optional_text(payload.get("upload_date"))
        if upload_date and len(upload_date) == 8 and upload_date.isdigit():
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        return None

    def _normalize_subtitle(self, content: str) -> str:
        cleaned_lines: list[str] = []
        seen: set[str] = set()
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line == "WEBVTT" or line.startswith("NOTE"):
                continue
            if line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            line = re.sub(r"<[^>]+>", "", line)
            if not line or line in seen:
                continue
            seen.add(line)
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _parse_int(self, value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _match_language(self, preferred_languages: list[str], available_languages: tuple[str, ...]) -> str | None:
        if not preferred_languages or not available_languages:
            return None

        normalized_available = {
            self._normalize_language_tag(language): language
            for language in available_languages
        }

        for preferred in preferred_languages:
            if preferred in available_languages:
                return preferred

        for preferred in preferred_languages:
            normalized = self._normalize_language_tag(preferred)
            if normalized in normalized_available:
                return normalized_available[normalized]
        return None

    def _normalize_language_tag(self, language: str) -> str:
        normalized = language.strip().lower()
        if not normalized:
            return normalized
        if normalized.startswith("zh-"):
            return normalized
        return normalized.split("-", 1)[0]
