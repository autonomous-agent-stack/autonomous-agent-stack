from __future__ import annotations

"""Manual lease-based standby worker helpers.

This module is intentionally small in scope:
- file-backed lease
- file-backed pending/running/completed/failed inbox
- single-active worker that only consumes when `lease.owner == host_id`

Non-goals:
- automatic failover
- scheduler semantics
- heartbeat-based lease transfer
- fencing / split-brain guarantees
- shared queue or control-plane orchestration
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import socket
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import Field

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.shared.models import StrictModel


_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_STANDBY_ROOT = (_REPO_ROOT / "artifacts" / "runtime" / "standby").resolve()
_SUCCESS_FINAL_STATUSES = {"ready_for_promotion", "promoted"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_host_id() -> str:
    return socket.gethostname().strip().lower() or "unknown-host"


def _safe_file_component(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    normalized = normalized.rsplit("/", 1)[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)
    safe = safe.strip("._")
    return safe or "job"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


class HostStandbyLease(StrictModel):
    owner: str | None = None
    version: int = Field(default=0, ge=0)


class HostStandbyJobEnvelope(StrictModel):
    job: JobSpec
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    enqueued_at: str = Field(default_factory=utc_now_iso)
    claimed_by: str | None = None
    claimed_at: str | None = None
    claimed_lease_owner: str | None = None
    claimed_lease_version: int | None = None
    finished_at: str | None = None
    run_summary: RunSummary | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HostStandbyIterationResult(StrictModel):
    action: Literal["standby", "idle", "completed", "failed"]
    host_id: str
    lease_owner: str | None = None
    lease_version: int = 0
    run_id: str | None = None
    detail: str = ""


@dataclass(slots=True)
class ClaimedStandbyJob:
    path: Path
    envelope: HostStandbyJobEnvelope


class HostStandbyLeaseStore:
    """Minimal file-backed lease for manual host takeover."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = (path or (_DEFAULT_STANDBY_ROOT / "lease.json")).expanduser().resolve()

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> HostStandbyLease:
        if not self._path.is_file():
            return HostStandbyLease()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return HostStandbyLease()
        if not isinstance(payload, dict):
            return HostStandbyLease()
        return HostStandbyLease.model_validate(payload)

    def write(self, lease: HostStandbyLease) -> HostStandbyLease:
        _write_json_atomic(self._path, lease.model_dump(mode="json"))
        return lease

    def is_owner(self, host_id: str) -> bool:
        normalized = host_id.strip()
        if not normalized:
            return False
        return self.read().owner == normalized


class HostStandbyJobInbox:
    """File-backed inbox used by the manual standby worker."""

    def __init__(self, root: Path | None = None) -> None:
        resolved_root = (root or (_DEFAULT_STANDBY_ROOT / "jobs")).expanduser().resolve()
        self._root = resolved_root
        self._pending_dir = resolved_root / "pending"
        self._running_dir = resolved_root / "running"
        self._completed_dir = resolved_root / "completed"
        self._failed_dir = resolved_root / "failed"
        for path in (
            self._pending_dir,
            self._running_dir,
            self._completed_dir,
            self._failed_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def enqueue(self, job: JobSpec, *, metadata: dict[str, Any] | None = None) -> Path:
        envelope = HostStandbyJobEnvelope(job=job, metadata=dict(metadata or {}))
        target = self._pending_dir / f"{_safe_file_component(job.run_id)}.json"
        if target.exists():
            raise FileExistsError(f"standby job already exists: {target.name}")
        _write_json_atomic(target, envelope.model_dump(mode="json"))
        return target

    def claim_next(self, host_id: str, *, lease: HostStandbyLease | None = None) -> ClaimedStandbyJob | None:
        normalized_host = host_id.strip()
        if not normalized_host:
            raise ValueError("host_id is required")

        for pending_path in sorted(self._pending_dir.glob("*.json")):
            claimed_path = self._running_dir / f"{pending_path.stem}.{_safe_file_component(normalized_host)}.json"
            try:
                pending_path.replace(claimed_path)
            except FileNotFoundError:
                continue

            envelope = HostStandbyJobEnvelope.model_validate_json(
                claimed_path.read_text(encoding="utf-8")
            )
            envelope = envelope.model_copy(
                update={
                    "status": "running",
                    "claimed_by": normalized_host,
                    "claimed_at": utc_now_iso(),
                    "claimed_lease_owner": lease.owner if lease is not None else None,
                    "claimed_lease_version": lease.version if lease is not None else None,
                    "finished_at": None,
                    "run_summary": None,
                    "error": None,
                }
            )
            _write_json_atomic(claimed_path, envelope.model_dump(mode="json"))
            return ClaimedStandbyJob(path=claimed_path, envelope=envelope)
        return None

    def finish(
        self,
        claimed: ClaimedStandbyJob,
        *,
        status: Literal["completed", "failed"],
        run_summary: RunSummary | None = None,
        error: str | None = None,
    ) -> Path:
        updated = claimed.envelope.model_copy(
            update={
                "status": status,
                "finished_at": utc_now_iso(),
                "run_summary": run_summary,
                "error": error,
            }
        )
        _write_json_atomic(claimed.path, updated.model_dump(mode="json"))
        destination_dir = self._completed_dir if status == "completed" else self._failed_dir
        destination = destination_dir / claimed.path.name
        claimed.path.replace(destination)
        return destination


class HostStandbyWorker:
    """Single-active execution helper guarded by a manual lease."""

    def __init__(
        self,
        *,
        host_id: str | None = None,
        repo_root: Path | None = None,
        lease_store: HostStandbyLeaseStore | None = None,
        inbox: HostStandbyJobInbox | None = None,
        dispatch_runner: Callable[[JobSpec], RunSummary] | None = None,
    ) -> None:
        self._host_id = (host_id or default_host_id()).strip()
        if not self._host_id:
            raise ValueError("host_id is required")
        self._repo_root = (repo_root or _REPO_ROOT).resolve()
        self._lease_store = lease_store or HostStandbyLeaseStore()
        self._inbox = inbox or HostStandbyJobInbox()
        self._dispatch_runner = dispatch_runner or self._default_dispatch_runner

    @property
    def host_id(self) -> str:
        return self._host_id

    def run_once(self) -> HostStandbyIterationResult:
        lease = self._lease_store.read()
        if lease.owner != self._host_id:
            return HostStandbyIterationResult(
                action="standby",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                detail="host does not own the standby lease",
            )

        claimed = self._inbox.claim_next(self._host_id, lease=lease)
        if claimed is None:
            return HostStandbyIterationResult(
                action="idle",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                detail="no pending standby jobs",
            )

        fencing_error = self._fencing_error(claimed)
        if fencing_error is not None:
            self._inbox.finish(claimed, status="failed", error=fencing_error)
            return HostStandbyIterationResult(
                action="failed",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                run_id=claimed.envelope.job.run_id,
                detail=fencing_error,
            )

        try:
            summary = self._dispatch_runner(claimed.envelope.job)
        except Exception as exc:
            self._inbox.finish(claimed, status="failed", error=str(exc))
            return HostStandbyIterationResult(
                action="failed",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                run_id=claimed.envelope.job.run_id,
                detail=str(exc),
            )

        fencing_error = self._fencing_error(claimed)
        if fencing_error is not None:
            self._inbox.finish(
                claimed,
                status="failed",
                run_summary=summary,
                error=fencing_error,
            )
            return HostStandbyIterationResult(
                action="failed",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                run_id=claimed.envelope.job.run_id,
                detail=fencing_error,
            )

        if summary.final_status in _SUCCESS_FINAL_STATUSES:
            self._inbox.finish(claimed, status="completed", run_summary=summary)
            return HostStandbyIterationResult(
                action="completed",
                host_id=self._host_id,
                lease_owner=lease.owner,
                lease_version=lease.version,
                run_id=claimed.envelope.job.run_id,
                detail=summary.final_status,
            )

        error = summary.driver_result.error or summary.final_status
        self._inbox.finish(
            claimed,
            status="failed",
            run_summary=summary,
            error=error,
        )
        return HostStandbyIterationResult(
            action="failed",
            host_id=self._host_id,
            lease_owner=lease.owner,
            lease_version=lease.version,
            run_id=claimed.envelope.job.run_id,
            detail=error,
        )

    def _default_dispatch_runner(self, job: JobSpec) -> RunSummary:
        runner = AgentExecutionRunner(repo_root=self._repo_root)
        return runner.run_job(job)

    def _fencing_error(self, claimed: ClaimedStandbyJob) -> str | None:
        expected_owner = claimed.envelope.claimed_lease_owner
        expected_version = claimed.envelope.claimed_lease_version
        current = self._lease_store.read()

        if expected_owner != self._host_id or expected_version is None:
            return (
                "lease fencing mismatch: "
                f"expected owner={self._host_id!r} version=<recorded>, "
                f"claimed owner={expected_owner!r} version={expected_version!r}"
            )

        if current.owner == expected_owner and current.version == expected_version:
            return None

        return (
            "lease fencing mismatch: "
            f"expected owner={expected_owner!r} version={expected_version}, "
            f"got owner={current.owner!r} version={current.version}"
        )
