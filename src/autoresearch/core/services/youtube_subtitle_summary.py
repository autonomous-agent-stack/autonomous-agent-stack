from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import urlparse

from autoresearch.shared.media_job_contract_subtitle import (
    MediaJobContractSubtitle,
    SubtitleJobStatus,
    SubtitleOutputFormat,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.youtube_subtitle_summary_contract import (
    YoutubeSubtitleSummaryRequest,
    YoutubeSubtitleSummaryResult,
    YoutubeSubtitleSummaryStatus,
)
from subtitle_offline.service import fetch_subtitle

_TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)
_YOUTUBE_ALLOWED_DOMAINS = {"youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"}


class YoutubeSubtitleSummaryService:
    """YouTube-only special agent built on the PR #33 subtitle pipeline."""

    def __init__(
        self,
        *,
        yt_dlp_bin: str = "yt-dlp",
        allowed_domains: set[str] | None = None,
        subtitle_fetcher: Callable[..., MediaJobContractSubtitle] | None = None,
    ) -> None:
        self._yt_dlp_bin = yt_dlp_bin
        self._allowed_domains = {
            item.lower().strip()
            for item in (allowed_domains or _YOUTUBE_ALLOWED_DOMAINS)
            if item.strip()
        }
        self._subtitle_fetcher = subtitle_fetcher or fetch_subtitle

    def summarize(self, request: YoutubeSubtitleSummaryRequest) -> YoutubeSubtitleSummaryResult:
        created_at = utc_now()
        normalized_url = request.youtube_url.strip()
        if not self.is_supported_url(normalized_url):
            return self._failed_result(
                youtube_url=normalized_url,
                title="unknown",
                subtitle_status=SubtitleJobStatus.FAILED,
                summary_status=YoutubeSubtitleSummaryStatus.FAILED,
                error_kind="unsupported_url",
                error="youtube subtitle summary only supports YouTube URLs",
                created_at=created_at,
                metadata={
                    **dict(request.metadata),
                    "summary_style": request.summary_style,
                    "summary_reason": "unsupported_url",
                },
            )

        subtitle_result = self._subtitle_fetcher(
            normalized_url,
            request.output_dir,
            output_format=SubtitleOutputFormat(request.output_format),
            yt_dlp_bin=request.yt_dlp_bin or self._yt_dlp_bin,
            allowed_domains=self._allowed_domains,
        )
        base_metadata = {
            **dict(request.metadata),
            "summary_style": request.summary_style,
            "requested_output_format": SubtitleOutputFormat(request.output_format).value,
            "subtitle_metadata": dict(subtitle_result.metadata),
        }
        clean_subtitle_path = subtitle_result.output_path or None
        raw_subtitle_path = subtitle_result.raw_subtitle_path
        if subtitle_result.status is not SubtitleJobStatus.DONE:
            error_kind = self._classify_subtitle_failure(subtitle_result)
            return self._failed_result(
                youtube_url=normalized_url,
                title=subtitle_result.title or "unknown",
                subtitle_status=subtitle_result.status,
                summary_status=YoutubeSubtitleSummaryStatus.FAILED,
                error_kind=error_kind,
                error=subtitle_result.error or subtitle_result.metadata.get("download_warning") or error_kind,
                subtitle_result=subtitle_result,
                raw_subtitle_path=raw_subtitle_path,
                clean_subtitle_path=clean_subtitle_path,
                created_at=created_at,
                metadata={
                    **base_metadata,
                    "summary_reason": "subtitle_failed",
                },
            )

        clean_path = Path(subtitle_result.output_path)
        try:
            caption_text = clean_path.read_text(encoding="utf-8")
        except OSError as exc:
            return self._failed_result(
                youtube_url=normalized_url,
                title=subtitle_result.title or clean_path.stem,
                subtitle_status=SubtitleJobStatus.DONE,
                summary_status=YoutubeSubtitleSummaryStatus.FAILED,
                error_kind="no_subtitle_output",
                error=str(exc),
                subtitle_result=subtitle_result,
                raw_subtitle_path=raw_subtitle_path,
                clean_subtitle_path=clean_subtitle_path,
                created_at=created_at,
                metadata={
                    **base_metadata,
                    "summary_reason": "clean_subtitle_missing",
                },
            )

        segments = self._extract_segments(caption_text)
        if not segments:
            return self._failed_result(
                youtube_url=normalized_url,
                title=subtitle_result.title or clean_path.stem,
                subtitle_status=SubtitleJobStatus.DONE,
                summary_status=YoutubeSubtitleSummaryStatus.FAILED,
                error_kind="empty_subtitle_text",
                error="subtitle output did not contain usable caption text",
                subtitle_result=subtitle_result,
                raw_subtitle_path=raw_subtitle_path,
                clean_subtitle_path=clean_subtitle_path,
                created_at=created_at,
                metadata={
                    **base_metadata,
                    "summary_reason": "empty_caption_text",
                },
            )

        summary, key_points = self._build_summary(
            segments=segments,
            max_key_points=request.max_key_points,
            max_summary_chars=request.max_summary_chars,
            summary_style=request.summary_style,
        )
        if not summary:
            return self._failed_result(
                youtube_url=normalized_url,
                title=subtitle_result.title or clean_path.stem,
                subtitle_status=SubtitleJobStatus.DONE,
                summary_status=YoutubeSubtitleSummaryStatus.FAILED,
                error_kind="summary_generation_failed",
                error="failed to derive a summary from the subtitle text",
                subtitle_result=subtitle_result,
                raw_subtitle_path=raw_subtitle_path,
                clean_subtitle_path=clean_subtitle_path,
                created_at=created_at,
                metadata={
                    **base_metadata,
                    "summary_reason": "summary_generation_failed",
                },
            )

        title = subtitle_result.title or clean_path.stem
        updated_at = utc_now()
        return YoutubeSubtitleSummaryResult(
            source_url=normalized_url,
            title=title,
            subtitle_status=SubtitleJobStatus.DONE,
            summary_status=YoutubeSubtitleSummaryStatus.DONE,
            error_kind=None,
            subtitle_result=subtitle_result,
            summary=summary,
            key_points=key_points,
            metadata={
                **base_metadata,
                "summary_reason": "subtitle_ok",
                "captions_segments": len(segments),
                "summary_key_points": len(key_points),
                "summary_characters": len(summary),
            },
            raw_subtitle_path=raw_subtitle_path,
            clean_subtitle_path=clean_subtitle_path,
            created_at=created_at,
            updated_at=updated_at,
            error=None,
        )

    def render_telegram_message(self, result: YoutubeSubtitleSummaryResult) -> str:
        lines = [
            "[YouTube Subtitle Summary]",
            f"title: {result.title}",
            f"source: {result.source_url}",
            f"subtitle_status: {result.subtitle_status.value}",
            f"summary_status: {result.summary_status.value}",
        ]
        if result.summary_status is YoutubeSubtitleSummaryStatus.DONE and result.summary:
            lines.extend(["", "summary:"])
            lines.append(result.summary)
            if result.key_points:
                lines.extend(["", "key_points:"])
                lines.extend(f"- {item}" for item in result.key_points)
        else:
            lines.extend(
                [
                    "",
                    f"error_kind: {result.error_kind or 'unknown'}",
                    f"error: {result.error or 'subtitle summary failed closed'}",
                ]
            )
        if result.raw_subtitle_path:
            lines.append(f"raw_subtitle_path: {result.raw_subtitle_path}")
        if result.clean_subtitle_path:
            lines.append(f"clean_subtitle_path: {result.clean_subtitle_path}")
        return self._truncate("\n".join(lines))

    def is_supported_url(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self._allowed_domains)

    def _build_summary(
        self,
        *,
        segments: list[str],
        max_key_points: int,
        max_summary_chars: int,
        summary_style: str,
    ) -> tuple[str, list[str]]:
        scored_segments: list[tuple[int, int, str]] = []
        token_counts = Counter()
        tokenized_segments: list[tuple[int, str, list[str]]] = []
        for index, segment in enumerate(segments):
            tokens = self._tokenize(segment)
            tokenized_segments.append((index, segment, tokens))
            token_counts.update(set(tokens))

        for index, segment, tokens in tokenized_segments:
            if not segment.strip():
                continue
            richness = len(set(tokens))
            keyword_bonus = sum(
                6
                for keyword in ("因为", "但是", "所以", "同时", "首先", "其次", "最后", "AI", "模型", "字幕", "总结")
                if keyword.lower() in segment.lower()
            )
            score = len(segment) + richness * 4 + keyword_bonus
            score += sum(token_counts[token] for token in set(tokens))
            scored_segments.append((score, index, segment))

        if not scored_segments:
            return "", []

        scored_segments.sort(key=lambda item: (-item[0], item[1]))
        chosen = sorted(scored_segments[:max_key_points], key=lambda item: item[1])
        key_points = [self._trim_segment(item[2]) for item in chosen if self._trim_segment(item[2])]
        if not key_points:
            return "", []

        if summary_style.strip().lower() == "narrative":
            summary = " ".join(key_points)
        else:
            summary = "\n".join(f"- {point}" for point in key_points)

        if len(summary) > max_summary_chars:
            summary = summary[: max_summary_chars - 16].rstrip() + "\n...[truncated]"
        return summary, key_points

    def _extract_segments(self, caption_text: str) -> list[str]:
        segments: list[str] = []
        seen: set[str] = set()
        for raw_line in caption_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.upper() == "WEBVTT":
                continue
            if stripped.startswith(("NOTE", "STYLE", "REGION", "Kind:", "Language:")):
                continue
            if stripped.isdigit() or _TIMESTAMP_RE.match(stripped):
                continue
            for piece in re.split(r"(?<=[。！？!?\.])\s+|[;；]\s*", stripped):
                normalized = re.sub(r"\s+", " ", piece).strip()
                if not normalized:
                    continue
                lowered = normalized.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                segments.append(normalized)
        return segments

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9']+", text.lower())
        return tokens

    @staticmethod
    def _trim_segment(segment: str, limit: int = 180) -> str:
        normalized = re.sub(r"\s+", " ", segment).strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16].rstrip() + "\n...[truncated]"

    def _classify_subtitle_failure(self, subtitle_result: MediaJobContractSubtitle) -> str:
        error_text = " ".join(
            part
            for part in [
                subtitle_result.error,
                subtitle_result.metadata.get("download_warning"),
            ]
            if isinstance(part, str) and part.strip()
        ).strip()
        normalized = error_text.lower()
        if not normalized:
            return "unknown_download_error"
        if "http error 429" in normalized or "too many requests" in normalized:
            return "rate_limited"
        if "ssl:" in normalized or "unexpected_eof_while_reading" in normalized:
            return "network_ssl"
        if "did not produce an .srt file" in normalized or "no subtitle" in normalized:
            return "no_subtitle_output"
        return "unknown_download_error"

    def _failed_result(
        self,
        *,
        youtube_url: str,
        title: str,
        subtitle_status: SubtitleJobStatus,
        summary_status: YoutubeSubtitleSummaryStatus,
        error_kind: str,
        error: str | None,
        created_at,
        metadata: dict[str, Any],
        subtitle_result: MediaJobContractSubtitle | None = None,
        raw_subtitle_path: str | None = None,
        clean_subtitle_path: str | None = None,
    ) -> YoutubeSubtitleSummaryResult:
        updated_at = utc_now()
        return YoutubeSubtitleSummaryResult(
            source_url=youtube_url,
            title=title,
            subtitle_status=subtitle_status,
            summary_status=summary_status,
            error_kind=error_kind,
            subtitle_result=subtitle_result,
            summary=None,
            key_points=[],
            metadata=metadata,
            raw_subtitle_path=raw_subtitle_path,
            clean_subtitle_path=clean_subtitle_path,
            created_at=created_at,
            updated_at=updated_at,
            error=error,
        )

    @staticmethod
    def _truncate(text: str, limit: int = 3900) -> str:
        normalized = text.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16].rstrip() + "\n...[truncated]"

