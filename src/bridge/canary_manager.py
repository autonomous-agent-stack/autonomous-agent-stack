from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CanaryMetrics(BaseModel):
    total_samples: int = 0
    candidate_samples: int = 0
    candidate_failures: int = 0
    candidate_latencies_ms: list[float] = Field(default_factory=list)


class CanaryRelease(BaseModel):
    release_id: str
    baseline_version: str
    candidate_version: str
    traffic_ratio: float = 0.1
    error_rate_threshold: float = 0.05
    p95_latency_ms_threshold: float = 2500.0
    min_samples: int = 20
    status: str = "active"  # active | rolled_back | promoted
    rollback_reason: str | None = None
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)
    metrics: CanaryMetrics = Field(default_factory=CanaryMetrics)


class CanaryState(BaseModel):
    active_release_id: str | None = None
    releases: dict[str, CanaryRelease] = Field(default_factory=dict)


class CanaryReleaseManager:
    def __init__(self, state_path: str = "data/canary_state.json") -> None:
        self._path = Path(state_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._state = self._load_state()

    def _load_state(self) -> CanaryState:
        if not self._path.exists():
            return CanaryState()
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return CanaryState.model_validate(payload)

    def _save_state(self) -> None:
        self._path.write_text(
            self._state.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def start_release(
        self,
        *,
        baseline_version: str,
        candidate_version: str,
        traffic_ratio: float,
        error_rate_threshold: float,
        p95_latency_ms_threshold: float,
        min_samples: int,
    ) -> CanaryRelease:
        with self._lock:
            release_id = f"canary_{int(datetime.now(timezone.utc).timestamp())}"
            release = CanaryRelease(
                release_id=release_id,
                baseline_version=baseline_version,
                candidate_version=candidate_version,
                traffic_ratio=max(0.01, min(traffic_ratio, 0.9)),
                error_rate_threshold=max(0.001, min(error_rate_threshold, 0.5)),
                p95_latency_ms_threshold=max(100.0, p95_latency_ms_threshold),
                min_samples=max(1, min_samples),
            )
            self._state.releases[release_id] = release
            self._state.active_release_id = release_id
            self._save_state()
            return release

    def get_active_release(self) -> CanaryRelease | None:
        rid = self._state.active_release_id
        if rid is None:
            return None
        return self._state.releases.get(rid)

    def get_release(self, release_id: str) -> CanaryRelease | None:
        return self._state.releases.get(release_id)

    def choose_channel(self, release: CanaryRelease, sticky_key: str) -> str:
        digest = hashlib.sha256(sticky_key.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        return "candidate" if bucket < release.traffic_ratio else "baseline"

    def record_result(
        self,
        *,
        release_id: str,
        channel: str,
        success: bool,
        latency_ms: float,
    ) -> CanaryRelease:
        with self._lock:
            release = self._state.releases[release_id]
            release.metrics.total_samples += 1
            if channel == "candidate":
                release.metrics.candidate_samples += 1
                if not success:
                    release.metrics.candidate_failures += 1
                release.metrics.candidate_latencies_ms.append(max(0.0, latency_ms))
            release.updated_at = _utc_now()
            self._save_state()
            return release

    def evaluate(self, release_id: str) -> dict[str, Any]:
        with self._lock:
            release = self._state.releases[release_id]
            metrics = release.metrics

            candidate_samples = max(metrics.candidate_samples, 0)
            error_rate = (
                metrics.candidate_failures / candidate_samples if candidate_samples else 0.0
            )

            p95 = 0.0
            if metrics.candidate_latencies_ms:
                sorted_latency = sorted(metrics.candidate_latencies_ms)
                idx = int(0.95 * (len(sorted_latency) - 1))
                p95 = sorted_latency[idx]

            action = "hold"
            reason = "insufficient samples"

            if candidate_samples >= release.min_samples:
                if error_rate > release.error_rate_threshold:
                    release.status = "rolled_back"
                    release.rollback_reason = (
                        f"error_rate {error_rate:.3f} > {release.error_rate_threshold:.3f}"
                    )
                    self._state.active_release_id = None
                    action = "rollback"
                    reason = release.rollback_reason
                elif p95 > release.p95_latency_ms_threshold:
                    release.status = "rolled_back"
                    release.rollback_reason = (
                        f"p95_latency {p95:.1f}ms > {release.p95_latency_ms_threshold:.1f}ms"
                    )
                    self._state.active_release_id = None
                    action = "rollback"
                    reason = release.rollback_reason
                else:
                    release.status = "promoted"
                    self._state.active_release_id = None
                    action = "promote"
                    reason = "candidate passed canary thresholds"

            release.updated_at = _utc_now()
            self._save_state()

            return {
                "release_id": release.release_id,
                "status": release.status,
                "action": action,
                "reason": reason,
                "candidate_samples": candidate_samples,
                "error_rate": round(error_rate, 6),
                "p95_latency_ms": round(p95, 3),
                "thresholds": {
                    "error_rate": release.error_rate_threshold,
                    "p95_latency_ms": release.p95_latency_ms_threshold,
                    "min_samples": release.min_samples,
                },
            }

    def rollback(self, *, release_id: str, reason: str) -> CanaryRelease:
        with self._lock:
            release = self._state.releases[release_id]
            release.status = "rolled_back"
            release.rollback_reason = reason
            release.updated_at = _utc_now()
            if self._state.active_release_id == release_id:
                self._state.active_release_id = None
            self._save_state()
            return release
