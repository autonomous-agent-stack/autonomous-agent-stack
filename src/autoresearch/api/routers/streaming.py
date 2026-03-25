from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from autoresearch.shared.models import utc_now


router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])


def _format_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/health")
async def stream_health(
    interval_seconds: float = 1.0,
    limit: int = 5,
) -> StreamingResponse:
    """
    Emit heartbeat events to validate SSE connectivity and reconnection behavior.
    """

    async def event_generator() -> AsyncIterator[str]:
        yield _format_event(
            "ready",
            {
                "status": "ok",
                "timestamp": utc_now().isoformat(),
            },
        )
        for sequence in range(limit):
            await asyncio.sleep(max(0.1, interval_seconds))
            yield _format_event(
                "heartbeat",
                {
                    "sequence": sequence + 1,
                    "timestamp": utc_now().isoformat(),
                },
            )
        yield _format_event(
            "complete",
            {
                "status": "ok",
                "heartbeats": limit,
                "timestamp": utc_now().isoformat(),
            },
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
