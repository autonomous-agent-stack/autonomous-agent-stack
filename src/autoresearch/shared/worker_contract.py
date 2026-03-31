"""Unified worker registration contract for the control plane.

Canonical Python runtime equivalent of the TypeScript spec in
agent-control-plane/packages/core/src/types/worker.ts.

Every worker that registers with the control plane must conform to this
schema.  Backend-specific adapters (LinuxSupervisor, Yingdao, OpenClaw)
translate their native heartbeat/status shapes into this unified model.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import StrictModel, utc_now

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkerType(str, Enum):
    """Worker platform type.  Mirrors TS WorkerType."""

    LINUX = "linux"
    MAC = "mac"
    WIN_YINGDAO = "win_yingdao"
    OPENCLAW = "openclaw"


class WorkerStatus(str, Enum):
    """Worker availability status.  Mirrors TS WorkerStatus."""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    DEGRADED = "degraded"


class AllowedAction(str, Enum):
    """Actions a worker is authorised to perform."""

    EXECUTE_TASK = "execute_task"
    READ_MEMORY = "read_memory"
    WRITE_FILE = "write_file"
    RUN_SCRIPT = "run_script"
    COLLECT_LOGS = "collect_logs"
    RUN_FLOW = "run_flow"
    CAPTURE_SCREENSHOT = "capture_screenshot"
    FILL_FORM = "fill_form"
    SEND_MESSAGE = "send_message"


# ---------------------------------------------------------------------------
# Timeout defaults (centralised, overridable per registration)
# ---------------------------------------------------------------------------


class WorkerTimeoutDefaults(StrictModel):
    """Default timeout policy for a worker.

    Values are in seconds.  Individual tasks may override via ExecutionPolicy.
    """

    task_timeout_sec: int = 900  # 15 min
    heartbeat_interval_sec: int = 30
    heartbeat_stale_sec: int = 120  # marks DEGRADED
    heartbeat_dead_sec: int = 300  # marks OFFLINE
    stall_timeout_sec: int = 600  # no-progress stall
    cleanup_grace_sec: int = 60


# ---------------------------------------------------------------------------
# Worker metrics (from heartbeat)
# ---------------------------------------------------------------------------


class WorkerMetrics(StrictModel):
    """Lightweight resource metrics reported by heartbeat."""

    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    active_tasks: int = 0
    total_tasks_completed: int = 0
    avg_task_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class WorkerRegistration(StrictModel):
    """Canonical worker registration record in the control plane.

    Mirrors TS WorkerRegistration + WorkerConfig.  Created once when a worker
    registers; updated on every heartbeat.
    """

    # Identity
    worker_id: str
    name: str
    worker_type: WorkerType

    # Capabilities and authorisation
    capabilities: list[str] = Field(default_factory=list)
    allowed_actions: list[AllowedAction] = Field(default_factory=list)

    # Lifecycle
    status: WorkerStatus = WorkerStatus.OFFLINE
    registered_at: datetime = Field(default_factory=utc_now)
    last_heartbeat: datetime | None = None

    # Metrics
    metrics: WorkerMetrics = Field(default_factory=WorkerMetrics)

    # Timeouts
    timeout_defaults: WorkerTimeoutDefaults = Field(default_factory=WorkerTimeoutDefaults)

    # Concurrency
    max_concurrent_tasks: int = 1

    # Backend mapping (Python-specific: links worker to execution backend)
    backend_kind: str | None = None

    # Errors / diagnostics
    errors: list[str] = Field(default_factory=list)

    # Free-form
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeat(StrictModel):
    """Payload a worker sends to the control plane on each heartbeat tick."""

    worker_id: str
    status: WorkerStatus = WorkerStatus.ONLINE
    metrics: WorkerMetrics = Field(default_factory=WorkerMetrics)
    active_task_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Query / response helpers
# ---------------------------------------------------------------------------


class WorkerQuery(BaseModel):
    """Filter parameters for listing workers."""

    model_config = ConfigDict(extra="ignore")

    worker_type: WorkerType | None = None
    status: WorkerStatus | None = None
    capability: str | None = None
    backend_kind: str | None = None
    limit: int = 100
    offset: int = 0


# ---------------------------------------------------------------------------
# Status ranking for worker selection
# ---------------------------------------------------------------------------

_STATUS_RANK: dict[WorkerStatus, int] = {
    WorkerStatus.ONLINE: 0,
    WorkerStatus.BUSY: 1,
    WorkerStatus.DEGRADED: 2,
    WorkerStatus.OFFLINE: 3,
}


def worker_status_rank(status: WorkerStatus) -> int:
    """Return a numeric rank for *status* (lower = more available)."""
    return _STATUS_RANK[status]


# ---------------------------------------------------------------------------
# Legacy mapping
# ---------------------------------------------------------------------------

from .housekeeper_contract import (  # noqa: E402
    WorkerAvailabilityStatus as _LegacyWorkerStatus,
)

_LEGACY_TO_UNIFIED: dict[_LegacyWorkerStatus, WorkerStatus] = {
    _LegacyWorkerStatus.ONLINE: WorkerStatus.ONLINE,
    _LegacyWorkerStatus.OFFLINE: WorkerStatus.OFFLINE,
    _LegacyWorkerStatus.BUSY: WorkerStatus.BUSY,
    _LegacyWorkerStatus.DEGRADED: WorkerStatus.DEGRADED,
}


def legacy_worker_status_to_unified(s: _LegacyWorkerStatus) -> WorkerStatus:
    return _LEGACY_TO_UNIFIED[s]
