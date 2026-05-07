from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from autoresearch.core.services.study_workbench import StudyWorkbenchService
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
    db_path = tmp_path / "study-worker.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_study_worker_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_study_worker_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_study_worker_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _settings(tmp_path: Path) -> SimpleNamespace:
    vault = tmp_path / "vault"
    goodnotes_inbox = tmp_path / "GoodNotes-Inbox"
    goodnotes_backup = tmp_path / "GoodNotes-Backup"
    marginnote_inbox = tmp_path / "MarginNote-Inbox"
    marginnote_export = tmp_path / "MarginNote-Export"
    for path in [vault, goodnotes_inbox, goodnotes_backup, marginnote_inbox, marginnote_export]:
        path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=vault, check=True, capture_output=True, text=True)
    return SimpleNamespace(
        obsidian_vault_dir=vault,
        goodnotes_inbox_dir=goodnotes_inbox,
        goodnotes_backup_dirs=[goodnotes_backup],
        marginnote_inbox_dir=marginnote_inbox,
        marginnote_export_dirs=[marginnote_export],
        git_repo_dir=vault,
        review_inbox_relative_dir="inbox_review",
        git_push_enabled=False,
        ocr_command="",
    )


def _build_daemon(
    tmp_path: Path,
    *,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    settings: SimpleNamespace,
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config = MacWorkerConfig(
        worker_id="test-study-worker",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Test Study Worker",
        host="test.local",
        heartbeat_seconds=15,
        claim_poll_seconds=0,
        lease_ttl_seconds=60,
        housekeeping_root=tmp_path,
        dry_run=True,
    )
    study_service = StudyWorkbenchService(
        settings=settings,
        state_db_path=tmp_path / "study-state.sqlite3",
        artifact_root=tmp_path / "artifacts" / "study_workbench",
    )
    return MacWorkerDaemon(
        config=config,
        client=InProcessMacWorkerClient(worker_registry=registry, worker_scheduler=scheduler),
        executor=MacWorkerExecutor(config, study_workbench=study_service),
        sleep=lambda _: None,
    )


def test_mac_worker_executes_study_prepare(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    settings = _settings(tmp_path)
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services, settings=settings)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.STUDY_PREPARE,
            payload={"title": "Attention", "markdown_text": "Q K V"},
        ),
        now=utc_now(),
    )

    assert daemon.run_once(now=utc_now()) is True
    run = scheduler.get_run(queued.run_id)

    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None
    assert run.result["prepared_count"] == 1
    assert (settings.goodnotes_inbox_dir / "attention.pdf").exists()


def test_mac_worker_ingest_enqueues_and_executes_git_sync(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    settings = _settings(tmp_path)
    pdf = settings.goodnotes_backup_dirs[0] / "lecture.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    pdf.with_suffix(".txt").write_text("handwriting transcript", encoding="utf-8")
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services, settings=settings)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type=WorkerTaskType.STUDY_INGEST),
        now=utc_now(),
    )

    assert daemon.run_once(now=utc_now()) is True
    ingest_run = scheduler.get_run(queued.run_id)
    assert ingest_run is not None
    assert ingest_run.status == JobStatus.COMPLETED
    assert ingest_run.result is not None
    git_sync_run_id = ingest_run.result["git_sync_run_id"]

    assert daemon.run_once(now=utc_now()) is True
    git_sync_run = scheduler.get_run(git_sync_run_id)
    assert git_sync_run is not None
    assert git_sync_run.status == JobStatus.COMPLETED
    assert git_sync_run.task_type == WorkerTaskType.STUDY_GIT_SYNC
    assert git_sync_run.result is not None
    assert git_sync_run.result["commit_sha"]
