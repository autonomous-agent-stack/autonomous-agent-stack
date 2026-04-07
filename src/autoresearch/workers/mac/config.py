from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import socket

from autoresearch.core.runtime_identity import get_runtime_identity
from autoresearch.shared.models import WorkerMode, WorkerQueueName, WorkerRegisterRequest, WorkerType


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _sanitize_worker_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return normalized or "mac-standby-worker"


@dataclass(slots=True)
class MacWorkerConfig:
    worker_id: str
    control_plane_base_url: str
    worker_name: str | None
    host: str
    heartbeat_seconds: float = 15.0
    claim_poll_seconds: float = 5.0
    lease_ttl_seconds: int = 60
    housekeeping_root: Path = field(default_factory=lambda: Path.cwd().resolve())
    dry_run: bool = True
    role: str = "housekeeper"
    capabilities: tuple[str, ...] = (
        "housekeeping",
        "cleanup_appledouble",
        "cleanup_tmp",
        "youtube_action",
        "youtube_autoflow",
    )
    queue_name: WorkerQueueName = WorkerQueueName.HOUSEKEEPING
    worker_type: WorkerType = WorkerType.MAC
    mode: WorkerMode = WorkerMode.STANDBY

    @classmethod
    def from_env(cls) -> MacWorkerConfig:
        host = os.getenv("WORKER_HOST", socket.gethostname())
        default_worker_id = _sanitize_worker_id(f"mac-{host.split('.')[0]}")
        base_url = os.getenv("CONTROL_PLANE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
        housekeeping_root = Path(os.getenv("HOUSEKEEPING_ROOT", str(Path.cwd()))).expanduser().resolve()
        return cls(
            worker_id=_sanitize_worker_id(os.getenv("WORKER_ID", default_worker_id)),
            control_plane_base_url=base_url,
            worker_name=os.getenv("WORKER_NAME") or None,
            host=host,
            heartbeat_seconds=max(1.0, float(os.getenv("WORKER_HEARTBEAT_SEC", "15"))),
            claim_poll_seconds=max(1.0, float(os.getenv("WORKER_CLAIM_POLL_SEC", "5"))),
            lease_ttl_seconds=max(1, int(os.getenv("WORKER_LEASE_TTL_SEC", "60"))),
            housekeeping_root=housekeeping_root,
            dry_run=_parse_bool(os.getenv("WORKER_DRY_RUN"), default=True),
            role=os.getenv("WORKER_ROLE", "housekeeper").strip() or "housekeeper",
        )

    def build_register_request(self) -> WorkerRegisterRequest:
        runtime_identity = get_runtime_identity()
        return WorkerRegisterRequest(
            worker_id=self.worker_id,
            worker_type=self.worker_type,
            name=self.worker_name,
            host=self.host,
            mode=self.mode,
            role=self.role,
            capabilities=list(self.capabilities),
            metadata={
                **runtime_identity,
                "configured_host": self.host,
                "lease_ttl_seconds": self.lease_ttl_seconds,
                "housekeeping_root": str(self.housekeeping_root),
                "dry_run": self.dry_run,
            },
        )
