"""Tests for content_kb_ingest worker task type."""
from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    JobStatus,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.workers.mac.client import InProcessMacWorkerClient
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.daemon import MacWorkerDaemon
from autoresearch.workers.mac.executor import MacWorkerExecutor


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "ckb-ingest-test.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_ingest_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_ingest_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_ingest_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _build_daemon(
    tmp_path: Path,
    *,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config = MacWorkerConfig(
        worker_id="test-worker-ingest",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Test Worker Ingest",
        host="test.local",
        heartbeat_seconds=15,
        claim_poll_seconds=5,
        lease_ttl_seconds=60,
        housekeeping_root=tmp_path,
        dry_run=True,
    )
    return MacWorkerDaemon(
        config=config,
        client=InProcessMacWorkerClient(worker_registry=registry, worker_scheduler=scheduler),
        executor=MacWorkerExecutor(config),
        sleep=lambda _: None,
    )


def _write_srt(tmp_path: Path, filename: str = "test.srt") -> Path:
    """Write a minimal SRT file for testing."""
    srt_path = tmp_path / filename
    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n人工智能和深度学习最新进展\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n大模型发展趋势分析\n",
        encoding="utf-8",
    )
    return srt_path


def test_content_kb_ingest_task_type_registered() -> None:
    """Verify CONTENT_KB_INGEST exists in the enum."""
    assert hasattr(WorkerTaskType, "CONTENT_KB_INGEST")
    assert WorkerTaskType.CONTENT_KB_INGEST.value == "content_kb_ingest"


def test_content_kb_ingest_full_lifecycle(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Full lifecycle: enqueue → claim → execute → report for content_kb_ingest."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "AI Weekly Report",
                "topic": "",
                "source_url": "https://example.com/video/ai-weekly",
            },
            requested_by="test",
        ),
        now=utc_now(),
    )
    assert queued.status == JobStatus.QUEUED
    assert queued.task_type == WorkerTaskType.CONTENT_KB_INGEST

    processed = daemon.run_once(now=utc_now())
    assert processed is True

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None

    # Verify classification was auto-applied
    assert run.result["topic"] == "ai-status-and-outlook"
    assert "repo" in run.result
    assert "indexes" in run.result
    assert "topic" in run.result["indexes"]
    assert run.result["indexes"]["topic"]["topics"]["ai-status-and-outlook"]["count"] == 1


def test_content_kb_ingest_with_explicit_topic(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Ingest with pre-specified topic skips auto-classification."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "Economy Talk",
                "topic": "economy",
            },
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result["topic"] == "economy"


def test_content_kb_ingest_fails_without_file(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Verify executor reports FAILED when file is missing."""
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={"subtitle_text_path": "/nonexistent/file.srt"},
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.FAILED
    assert "not found" in (run.error or "").lower()


def test_content_kb_ingest_fails_without_path(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Verify executor reports FAILED when subtitle_text_path is empty."""
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={},
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.FAILED
    assert "subtitle_text_path" in (run.error or "").lower()


def test_content_kb_ingest_draft_pr_hook(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Verify draft PR metadata is included when open_draft_pr=True."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "AI Deep Dive",
                "topic": "ai-status-and-outlook",
                "open_draft_pr": True,
                "owner": "my-org",
                "default_repo": "knowledge-base",
            },
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result["draft_pr_requested"] is True
    assert run.result["draft_pr_hint"]["repo"] == "my-org/knowledge-base"
    assert run.result["draft_pr_hint"]["branch_prefix"] == "content-kb/ingest"
    assert "title_prefix" in run.result["draft_pr_hint"]
    assert run.metrics["draft_pr_requested"] == 1


def test_content_kb_ingest_no_draft_pr_by_default(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Verify no draft PR metadata when open_draft_pr is not set."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "Test",
                "topic": "economy",
            },
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert "draft_pr_requested" not in (run.result or {})
    assert run.metrics["draft_pr_requested"] == 0


def test_content_kb_ingest_via_api(tmp_path: Path) -> None:
    """Verify the convenience endpoint returns a queued run."""
    from fastapi.testclient import TestClient

    from autoresearch.api.main import app

    srt_path = _write_srt(tmp_path)

    client = TestClient(app)
    response = client.post(
        "/api/v1/worker-runs/content-kb-ingest",
        json={
            "subtitle_text_path": str(srt_path),
            "title": "API Ingest Test",
            "topic": "economy",
            "requested_by": "api-test",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_type"] == "content_kb_ingest"
    assert data["status"] == "queued"
    assert data["run_id"]
    assert data["payload"]["subtitle_text_path"] == str(srt_path)
    assert data["payload"]["open_draft_pr"] is False
