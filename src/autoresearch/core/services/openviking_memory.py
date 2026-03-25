from __future__ import annotations

from collections import Counter
import json
import math
from typing import Any

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    OpenClawSessionRead,
    OpenVikingCompactRequest,
    OpenVikingMemoryProfileRead,
    utc_now,
)
from autoresearch.shared.store import create_resource_id


class OpenVikingMemoryService:
    """
    OpenViking-style memory adapter:
    compress long session history into hierarchical summary + recent window.
    """

    def __init__(self, openclaw_service: OpenClawCompatService) -> None:
        self._openclaw_service = openclaw_service

    def compact_session(
        self,
        session_id: str,
        request: OpenVikingCompactRequest,
    ) -> tuple[OpenClawSessionRead, OpenVikingMemoryProfileRead]:
        session = self._openclaw_service.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")

        original_events = list(session.events)
        keep_recent = request.keep_recent_events
        compressed_events = original_events[:-keep_recent] if len(original_events) > keep_recent else []
        retained_events = original_events[-keep_recent:] if original_events else []

        summary = self._summarize_events(compressed_events, max_chars=request.summary_max_chars)
        events_after = list(retained_events)
        if compressed_events:
            events_after.insert(
                0,
                {
                    "event_id": create_resource_id("evt"),
                    "role": "system",
                    "content": f"[OpenViking Summary]\n{summary}",
                    "metadata": {
                        "source": "openviking",
                        "compressed_events": len(compressed_events),
                    },
                    "created_at": utc_now().isoformat(),
                },
            )

        before_tokens = self._estimate_tokens(original_events)
        after_tokens = self._estimate_tokens(events_after)
        ratio = self._compression_ratio(before_tokens, after_tokens)

        profile = OpenVikingMemoryProfileRead(
            session_id=session.session_id,
            original_event_count=len(original_events),
            retained_event_count=len(events_after),
            compressed_event_count=len(compressed_events),
            estimated_tokens_before=before_tokens,
            estimated_tokens_after=after_tokens,
            compression_ratio=ratio,
            summary=summary,
            updated_at=utc_now(),
        )

        metadata = dict(session.metadata)
        metadata["openviking"] = {
            "compression_ratio": ratio,
            "compressed_events": len(compressed_events),
            "retained_events": len(events_after),
            "estimated_tokens_before": before_tokens,
            "estimated_tokens_after": after_tokens,
            "updated_at": profile.updated_at.isoformat(),
        }
        updated = session.model_copy(
            update={
                "events": events_after,
                "metadata": metadata,
                "updated_at": profile.updated_at,
            }
        )
        saved = self._openclaw_service.save_session(updated)
        return saved, profile

    def memory_profile(self, session_id: str) -> OpenVikingMemoryProfileRead:
        session = self._openclaw_service.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        events = list(session.events)
        tokens = self._estimate_tokens(events)
        summary = ""
        openviking_meta = session.metadata.get("openviking")
        if isinstance(openviking_meta, dict):
            summary = str(openviking_meta.get("summary", ""))
        return OpenVikingMemoryProfileRead(
            session_id=session_id,
            original_event_count=len(events),
            retained_event_count=len(events),
            compressed_event_count=0,
            estimated_tokens_before=tokens,
            estimated_tokens_after=tokens,
            compression_ratio=0.0,
            summary=summary,
            updated_at=session.updated_at,
        )

    def _summarize_events(self, events: list[dict[str, Any]], max_chars: int) -> str:
        if not events:
            return "No historical events to compress."

        role_counter = Counter(str(event.get("role", "unknown")) for event in events)
        highlights: list[str] = []
        for event in events[-12:]:
            role = str(event.get("role", "unknown"))
            content = " ".join(str(event.get("content", "")).strip().split())
            if content:
                highlights.append(f"[{role}] {content[:140]}")

        head = ", ".join(f"{role}:{count}" for role, count in role_counter.items())
        summary = f"Role distribution: {head}\nRecent highlights:\n" + "\n".join(highlights)
        if len(summary) <= max_chars:
            return summary
        return summary[: max_chars - 16] + "\n...[truncated]"

    def _estimate_tokens(self, events: list[dict[str, Any]]) -> int:
        payload = json.dumps(events, ensure_ascii=False, sort_keys=True)
        # pragmatic approximation: 1 token ~= 4 chars for mixed zh/en text
        return max(1, math.ceil(len(payload) / 4))

    def _compression_ratio(self, before_tokens: int, after_tokens: int) -> float:
        if before_tokens <= 0:
            return 0.0
        ratio = 1.0 - (after_tokens / before_tokens)
        return max(0.0, round(ratio, 4))
