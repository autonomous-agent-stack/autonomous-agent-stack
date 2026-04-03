from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.core.services.host_standby import (
    HostStandbyJobInbox,
    HostStandbyLease,
    HostStandbyLeaseStore,
    HostStandbyWorker,
)


def _job(run_id: str = "run-1") -> JobSpec:
    return JobSpec(
        run_id=run_id,
        agent_id="mock",
        task="demo task",
    )


def _summary(job: JobSpec, *, final_status: str = "ready_for_promotion", error: str | None = None) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status=final_status,
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded" if error is None and final_status == "ready_for_promotion" else "failed",
            summary="standby worker test summary",
            error=error,
        ),
        validation=ValidationReport(run_id=job.run_id, passed=error is None),
        promotion_patch_uri=None,
    )


def test_host_standby_lease_store_roundtrip(tmp_path: Path) -> None:
    store = HostStandbyLeaseStore(tmp_path / "lease.json")
    assert store.read().owner is None

    store.write(HostStandbyLease(owner="mac-1", version=2))

    stored = store.read()
    assert stored.owner == "mac-1"
    assert stored.version == 2
    assert store.is_owner("mac-1") is True
    assert store.is_owner("linux-1") is False


def test_job_inbox_claim_moves_job_into_running_with_claim_metadata(tmp_path: Path) -> None:
    inbox = HostStandbyJobInbox(tmp_path / "jobs")
    queued_path = inbox.enqueue(_job("run-claim"))
    assert queued_path.exists()

    claimed = inbox.claim_next("mac-1")

    assert claimed is not None
    assert claimed.envelope.job.run_id == "run-claim"
    assert claimed.envelope.status == "running"
    assert claimed.envelope.claimed_by == "mac-1"
    assert not queued_path.exists()
    assert claimed.path.parent.name == "running"

    payload = json.loads(claimed.path.read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["claimed_by"] == "mac-1"


def test_host_standby_worker_stays_idle_when_lease_owner_is_another_host(tmp_path: Path) -> None:
    lease_store = HostStandbyLeaseStore(tmp_path / "lease.json")
    lease_store.write(HostStandbyLease(owner="linux-1", version=1))
    inbox = HostStandbyJobInbox(tmp_path / "jobs")
    inbox.enqueue(_job("run-idle"))

    worker = HostStandbyWorker(
        host_id="mac-1",
        repo_root=tmp_path,
        lease_store=lease_store,
        inbox=inbox,
        dispatch_runner=lambda job: _summary(job),
    )

    result = worker.run_once()

    assert result.action == "standby"
    pending = list((tmp_path / "jobs" / "pending").glob("*.json"))
    assert len(pending) == 1


def test_host_standby_worker_completes_job_when_host_owns_lease(tmp_path: Path) -> None:
    lease_store = HostStandbyLeaseStore(tmp_path / "lease.json")
    lease_store.write(HostStandbyLease(owner="mac-1", version=3))
    inbox = HostStandbyJobInbox(tmp_path / "jobs")
    inbox.enqueue(_job("run-success"))

    worker = HostStandbyWorker(
        host_id="mac-1",
        repo_root=tmp_path,
        lease_store=lease_store,
        inbox=inbox,
        dispatch_runner=lambda job: _summary(job),
    )

    result = worker.run_once()

    assert result.action == "completed"
    completed = list((tmp_path / "jobs" / "completed").glob("*.json"))
    assert len(completed) == 1
    payload = json.loads(completed[0].read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["run_summary"]["final_status"] == "ready_for_promotion"


def test_host_standby_worker_marks_failed_result_into_failed_dir(tmp_path: Path) -> None:
    lease_store = HostStandbyLeaseStore(tmp_path / "lease.json")
    lease_store.write(HostStandbyLease(owner="mac-1", version=4))
    inbox = HostStandbyJobInbox(tmp_path / "jobs")
    inbox.enqueue(_job("run-failed"))

    worker = HostStandbyWorker(
        host_id="mac-1",
        repo_root=tmp_path,
        lease_store=lease_store,
        inbox=inbox,
        dispatch_runner=lambda job: _summary(job, final_status="human_review", error="needs human review"),
    )

    result = worker.run_once()

    assert result.action == "failed"
    failed = list((tmp_path / "jobs" / "failed").glob("*.json"))
    assert len(failed) == 1
    payload = json.loads(failed[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["error"] == "needs human review"
