"""Flight recording helpers for MASFactory demo runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FlightRecorder:
    """Write a concise JSONL trace for a MASFactory flight."""

    enabled: bool = False
    path: Path = Path(".masfactory_runtime/masfactory-flight.jsonl")
    echo: bool = False

    def __post_init__(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def emit(self, stage: str, event: str, *, summary: str | None = None, **payload: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "event": event,
            **payload,
        }
        if self.enabled:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            if self.echo:
                if summary is None:
                    parts = []
                    for key, value in payload.items():
                        if key == "summary":
                            continue
                        parts.append(f"{key}={value}")
                    summary = ", ".join(parts) if parts else ""
                suffix = f" {summary}" if summary else ""
                print(f"[watch] {record['ts']} {stage}.{event}{suffix}")
        return record

