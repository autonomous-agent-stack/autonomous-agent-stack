from __future__ import annotations

from collections import Counter
import re
from urllib.parse import urlparse

from autoresearch.shared.models import utc_now
from autoresearch.shared.youtube_subtitle_summary_contract import (
    YouTubeSubtitleSummaryRequest,
    YouTubeSubtitleSummaryResult,
    YouTubeSubtitleSummaryStatus,
)

_TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}[\.,]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[\.,]\d{3})(?:\s+.*)?$"
)
_YOUTUBE_ALLOWED_DOMAINS = {"youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"}


class YouTubeSubtitleSummaryService:
    """YouTube-only summary agent that works from already fetched subtitle text."""

    def __init__(self, *, allowed_domains: set[str] | None = None) -> None:
        self._allowed_domains = {
            item.lower().strip()
            for item in (allowed_domains or _YOUTUBE_ALLOWED_DOMAINS)
            if item.strip()
        }

    def summarize(self, request: YouTubeSubtitleSummaryRequest) -> YouTubeSubtitleSummaryResult:
        created_at = utc_now()
        normalized_url = request.youtube_url.strip()
        title = request.title or "unknown"
        base_metadata = {
            **dict(request.metadata),
            "summary_style": request.summary_style,
            "summary_source": "subtitle_text",
        }
        if not self.is_supported_url(normalized_url):
            return self._failed_result(
                youtube_url=normalized_url,
                title=title,
                error_kind="unsupported_url",
                error="youtube subtitle summary only supports YouTube URLs",
                created_at=created_at,
                metadata={**base_metadata, "summary_reason": "unsupported_url"},
            )

        if not request.subtitle_text:
            return self._failed_result(
                youtube_url=normalized_url,
                title=title,
                error_kind="subtitle_text_required",
                error="subtitle_text is required for this local summary path",
                created_at=created_at,
                metadata={**base_metadata, "summary_reason": "subtitle_text_required"},
            )

        segments = self._extract_segments(request.subtitle_text)
        if not segments:
            return self._failed_result(
                youtube_url=normalized_url,
                title=title,
                error_kind="empty_subtitle_text",
                error="subtitle text did not contain usable caption text",
                created_at=created_at,
                metadata={**base_metadata, "summary_reason": "empty_subtitle_text"},
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
                title=title,
                error_kind="summary_generation_failed",
                error="failed to derive a summary from subtitle text",
                created_at=created_at,
                metadata={**base_metadata, "summary_reason": "summary_generation_failed"},
            )

        updated_at = utc_now()
        return YouTubeSubtitleSummaryResult(
            source_url=normalized_url,
            title=title,
            summary_status=YouTubeSubtitleSummaryStatus.DONE,
            summary=summary,
            key_points=key_points,
            error_kind=None,
            error=None,
            metadata={
                **base_metadata,
                "summary_reason": "subtitle_ok",
                "caption_segments": len(segments),
                "summary_key_points": len(key_points),
                "summary_characters": len(summary),
            },
            created_at=created_at,
            updated_at=updated_at,
        )

    def render_telegram_message(self, result: YouTubeSubtitleSummaryResult) -> str:
        lines = [
            "[YouTube Subtitle Summary]",
            f"title: {result.title}",
            f"source: {result.source_url}",
            f"summary_status: {result.summary_status.value}",
        ]
        if result.summary_status is YouTubeSubtitleSummaryStatus.DONE and result.summary:
            lines.extend(["", "summary:", result.summary])
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
                for keyword in ("因为", "但是", "所以", "同时", "首先", "其次", "最后", "AI", "模型", "学习", "总结")
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

    def _extract_segments(self, subtitle_text: str) -> list[str]:
        segments: list[str] = []
        seen: set[str] = set()
        for raw_line in subtitle_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.upper() == "WEBVTT":
                continue
            if stripped.startswith(("NOTE", "STYLE", "REGION", "Kind:", "Language:")):
                continue
            if stripped.isdigit() or _TIMESTAMP_RE.match(stripped):
                continue
            for piece in re.split(r"(?<=[。！？!?\.])\s+|[；;]\s*", stripped):
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
        return re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9']+", text.lower())

    @staticmethod
    def _trim_segment(segment: str, limit: int = 180) -> str:
        normalized = re.sub(r"\s+", " ", segment).strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16].rstrip() + "\n...[truncated]"

    def _failed_result(
        self,
        *,
        youtube_url: str,
        title: str,
        error_kind: str,
        error: str,
        created_at,
        metadata: dict[str, object],
    ) -> YouTubeSubtitleSummaryResult:
        updated_at = utc_now()
        return YouTubeSubtitleSummaryResult(
            source_url=youtube_url,
            title=title,
            summary_status=YouTubeSubtitleSummaryStatus.FAILED,
            summary=None,
            key_points=[],
            error_kind=error_kind,
            error=error,
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _truncate(text: str, limit: int = 3900) -> str:
        normalized = text.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16].rstrip() + "\n...[truncated]"
