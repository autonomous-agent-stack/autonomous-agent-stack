from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from autoresearch.api.dependencies import (
    get_control_plane_service,
    get_telegram_notifier_service,
    get_telegram_settings,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.main import app
from autoresearch.api.settings import TelegramSettings
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalDecisionRequest,
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalRead,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneRunStatus,
    ControlPlaneSessionRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    JobStatus,
    SessionEventRead,
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRegisterRequest,
    WorkerRunReportRequest,
    WorkerType,
    WorkerMode,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


class _StubTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    @property
    def enabled(self) -> bool:
        return True

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, object] | None = None,
        message_thread_id: int | None = None,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        self.messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
                "message_thread_id": message_thread_id,
                "parse_mode": parse_mode,
            }
        )
        return True


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "worker-run-reporting.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_reporting_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_reporting_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_reporting_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _build_control_plane_service(
    tmp_path: Path,
    scheduler: WorkerSchedulerService,
) -> tuple[ControlPlaneService, SessionEventService]:
    db_path = tmp_path / "worker-run-control-plane.sqlite3"
    session_events = SessionEventService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="session_events_reporting_cp_test",
            model_cls=SessionEventRead,
        )
    )
    service = ControlPlaneService(
        repositories=ControlPlaneRepositories(
            sessions=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_sessions_reporting_test",
                model_cls=ControlPlaneSessionRead,
            ),
            tasks=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_tasks_reporting_test",
                model_cls=ControlPlaneTaskRead,
            ),
            runs=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_runs_reporting_test",
                model_cls=ControlPlaneRunRead,
            ),
            approvals=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_approvals_reporting_test",
                model_cls=ControlPlaneApprovalRead,
            ),
            approval_grants=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_approval_grants_reporting_test",
                model_cls=ControlPlaneApprovalGrantRead,
            ),
            artifacts=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_artifacts_reporting_test",
                model_cls=ControlPlaneArtifactRead,
            ),
            audit_events=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_audit_events_reporting_test",
                model_cls=ControlPlaneAuditEventRead,
            ),
            promotions=SQLiteModelRepository(
                db_path=db_path,
                table_name="control_plane_promotions_reporting_test",
                model_cls=ControlPlanePromotionRead,
            ),
        ),
        worker_scheduler=scheduler,
        session_events=session_events,
    )
    return service, session_events


@pytest.fixture
def worker_client(worker_services: tuple[WorkerRegistryService, WorkerSchedulerService]) -> TestClient:
    registry, scheduler = worker_services
    app.dependency_overrides[get_worker_registry_service] = lambda: registry
    app.dependency_overrides[get_worker_scheduler_service] = lambda: scheduler
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _register_worker(registry: WorkerRegistryService, *, worker_id: str) -> None:
    registry.register(
        WorkerRegisterRequest(
            worker_id=worker_id,
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            role="housekeeper",
            capabilities=["housekeeping"],
        )
    )


def test_enqueue_claim_and_report_lifecycle_via_api(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")

    created = worker_client.post(
        "/api/v1/worker-runs",
        json={
            "queue_name": "housekeeping",
            "task_type": "noop",
            "payload": {"message": "hello"},
            "requested_by": "local_test",
        },
    )
    assert created.status_code == 201
    queued = created.json()
    assert queued["task_name"] == "noop"
    assert queued["task_type"] == "noop"
    assert queued["status"] == "queued"

    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.claimed is True
    assert claimed.run is not None

    running = worker_client.post(
        f"/api/v1/workers/mac-mini-01/runs/{claimed.run.run_id}/report",
        json={
            "status": "running",
            "message": "started noop",
            "progress": {"current": 1, "total": 1},
            "metrics": {"operations": 1},
        },
    )
    assert running.status_code == 200
    running_body = running.json()
    assert running_body["status"] == "running"
    assert running_body["message"] == "started noop"
    assert running_body["started_at"] is not None

    completed = worker_client.post(
        f"/api/v1/workers/mac-mini-01/runs/{claimed.run.run_id}/report",
        json={
            "status": "succeeded",
            "message": "noop completed",
            "result": {"echo": "hello"},
        },
    )
    assert completed.status_code == 200
    completed_body = completed.json()
    assert completed_body["status"] == "completed"
    assert completed_body["completed_at"] is not None
    assert completed_body["result"]["echo"] == "hello"
    assert completed_body["metadata"]["worker_id"] == "mac-mini-01"
    assert completed_body["metadata"]["run_id"] == claimed.run.run_id
    assert completed_body["metadata"]["task_type"] == "noop"
    assert completed_body["metadata"]["status"] == "completed"
    assert completed_body["metadata"]["summary"] == "noop completed"

    leases = scheduler.list_leases()
    assert len(leases) == 1
    assert leases[0].active is False


def test_report_terminal_control_plane_run_updates_v2_state(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    tmp_path: Path,
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    control_plane, session_events = _build_control_plane_service(tmp_path, scheduler)
    task = control_plane.create_task(
        ControlPlaneTaskCreateRequest(
            name="worker report sync",
            session_id="session-worker-report-sync",
            requested_by="report-test",
        )
    )
    assert task.run_id is not None
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.run is not None

    app.dependency_overrides[get_control_plane_service] = lambda: control_plane
    try:
        completed = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{task.run_id}/report",
            json={
                "status": "completed",
                "message": "worker report complete",
                "result": {"summary": "v2 projection updated"},
                "metrics": {"rows": 12},
            },
        )
        assert completed.status_code == 200
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)

    projected = control_plane.get_task(task.task_id)
    assert projected is not None
    assert projected.status == ControlPlaneTaskStatus.SUCCEEDED
    assert projected.result == {"summary": "v2 projection updated"}
    run = control_plane.get_run(task.run_id)
    assert run is not None
    assert run.status == ControlPlaneRunStatus.SUCCEEDED
    assert run.output == {"summary": "v2 projection updated"}
    assert run.metadata["worker_status"] == "completed"
    assert run.metadata["worker_message"] == "worker report complete"
    assert run.metadata["worker_result"] == {"summary": "v2 projection updated"}
    assert run.metadata["worker_metrics"] == {"rows": 12}
    assert run.metadata["worker_run_id"] == task.run_id
    timeline = session_events.timeline(session_id="session-worker-report-sync")
    event_types = [event.event_type for event in timeline.events]
    assert "run.succeeded" in event_types


def test_report_xreach_auth_pause_queues_hermes_recovery_and_sends_card(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    tmp_path: Path,
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    control_plane, session_events = _build_control_plane_service(tmp_path, scheduler)
    task = control_plane.create_task(
        ControlPlaneTaskCreateRequest(
            name="整理X书签",
            intent="整理X书签",
            session_id="session-xreach-auth-pause",
            capability_id="source_collect",
            parameters={
                "canonical_task_type": "source_collect.collect",
                "source_kind": "x_bookmarks",
                "downstream_capability_id": "content_kb",
            },
            requested_by="9536",
        )
    )
    approved = control_plane.decide_task(
        task.task_id,
        ControlPlaneApprovalDecisionRequest(decision="approved", decided_by="9536"),
    )
    assert approved is not None
    assert approved.run_id is not None
    scheduler.merge_queue_metadata(
        approved.run_id,
        {
            "telegram_completion_via_api": True,
            "chat_id": "9536",
            "session_key": "telegram:personal:user:9536",
            "telegram_queue_ack_message_id": 123,
        },
    )
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.run is not None
    notifier = _StubTelegramNotifier()

    app.dependency_overrides[get_control_plane_service] = lambda: control_plane
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_telegram_settings] = lambda: TelegramSettings(
        bot_token="fake-token",
        allowed_uids={"9536"},
    )
    try:
        response = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{approved.run_id}/report",
            json={
                "status": "running",
                "message": "source_collect waiting for X auth recovery",
                "result": {
                    "summary": "X 书签采集需要恢复本机登录态，管家已交给 Hermes 兜底。",
                    "collector": "xreach",
                    "error_kind": "collector_auth_required",
                    "collector_error": "GraphQL Error: Could not authenticate you",
                    "xreach_auth_attempts": [{"step": "auth check", "returncode": 1}],
                },
                "metrics": {
                    "worker_pause_reason": "xreach_auth_required",
                    "error_kind": "collector_auth_required",
                    "collector": "xreach",
                    "telegram_notify_status": "deferred",
                },
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_telegram_settings, None)

    stored = scheduler.get_run(approved.run_id)
    assert stored is not None
    assert stored.status == JobStatus.RUNNING
    assert stored.metadata["telegram_xreach_auth_recovery_sent"] is True
    leases = scheduler.list_leases()
    assert len(leases) == 1
    assert leases[0].active is False

    projected = control_plane.get_task(task.task_id)
    assert projected is not None
    assert projected.status == ControlPlaneTaskStatus.RUNNING
    assert projected.metadata["xreach_auth_recovery_worker_run_id"]
    recovery_run = scheduler.get_run(projected.metadata["xreach_auth_recovery_worker_run_id"])
    assert recovery_run is not None
    assert recovery_run.task_type.value == "claude_runtime"
    assert recovery_run.payload["runtime_id"] == "hermes"

    assert notifier.messages
    recovery_message = notifier.messages[-1]
    text = str(recovery_message["text"])
    assert "需要你配合恢复 X 书签采集" in text
    assert "Could not authenticate" not in text
    reply_markup = recovery_message["reply_markup"]
    assert isinstance(reply_markup, dict)
    buttons = reply_markup["inline_keyboard"]
    assert buttons[0][0]["callback_data"] == f"/xreach-auth-open {approved.run_id}"
    assert buttons[0][1]["callback_data"] == f"/xreach-auth-resume {approved.run_id}"
    event_types = [event.event_type for event in session_events.timeline(session_id="session-xreach-auth-pause").events]
    assert "run.recovery_queued" in event_types


def test_report_control_plane_sync_failure_does_not_break_report(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="noop",
            payload={"message": "hello"},
            metadata={"control_plane_task_id": "task_missing"},
        ),
        now=utc_now(),
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())

    class _FailingControlPlane:
        def sync_worker_run(self, run: WorkerQueueItemRead) -> None:
            raise RuntimeError(f"boom {run.run_id}")

    app.dependency_overrides[get_control_plane_service] = lambda: _FailingControlPlane()
    try:
        response = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{queued.run_id}/report",
            json={
                "status": "completed",
                "message": "still stored",
                "result": {"ok": True},
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)

    stored = scheduler.get_run(queued.run_id)
    assert stored is not None
    assert stored.status == JobStatus.COMPLETED
    assert stored.result == {"ok": True}


def test_cancel_queued_control_plane_run_updates_v2_state(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    tmp_path: Path,
) -> None:
    _, scheduler = worker_services
    control_plane, session_events = _build_control_plane_service(tmp_path, scheduler)
    task = control_plane.create_task(
        ControlPlaneTaskCreateRequest(
            name="worker cancel sync",
            session_id="session-worker-cancel-sync",
            requested_by="cancel-test",
        )
    )
    assert task.run_id is not None

    app.dependency_overrides[get_control_plane_service] = lambda: control_plane
    try:
        response = worker_client.post(
            f"/api/v1/worker-runs/{task.run_id}/cancel",
            json={"reason": "operator cancelled queued work"},
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)

    projected = control_plane.get_task(task.task_id)
    assert projected is not None
    assert projected.status == ControlPlaneTaskStatus.CANCELLED
    run = control_plane.get_run(task.run_id)
    assert run is not None
    assert run.status == ControlPlaneRunStatus.CANCELLED
    assert run.error == "operator cancelled queued work"
    timeline = session_events.timeline(session_id="session-worker-cancel-sync")
    event_types = [event.event_type for event in timeline.events]
    assert "run.cancelled" in event_types


def test_force_fail_control_plane_run_updates_v2_state(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    tmp_path: Path,
) -> None:
    _, scheduler = worker_services
    control_plane, session_events = _build_control_plane_service(tmp_path, scheduler)
    task = control_plane.create_task(
        ControlPlaneTaskCreateRequest(
            name="worker force fail sync",
            session_id="session-worker-force-fail-sync",
            requested_by="force-fail-test",
        )
    )
    assert task.run_id is not None

    app.dependency_overrides[get_control_plane_service] = lambda: control_plane
    try:
        response = worker_client.post(
            f"/api/v1/worker-runs/{task.run_id}/force-fail",
            json={"reason": "operator forced failure"},
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)

    projected = control_plane.get_task(task.task_id)
    assert projected is not None
    assert projected.status == ControlPlaneTaskStatus.FAILED
    run = control_plane.get_run(task.run_id)
    assert run is not None
    assert run.status == ControlPlaneRunStatus.FAILED
    assert run.error == "operator forced failure"
    timeline = session_events.timeline(session_id="session-worker-force-fail-sync")
    event_types = [event.event_type for event in timeline.events]
    assert "run.failed" in event_types


def test_cancel_and_force_fail_control_plane_sync_failure_does_not_break_endpoint(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    _, scheduler = worker_services
    cancel_queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="noop",
            payload={"message": "cancel"},
            metadata={"control_plane_task_id": "task_missing_cancel"},
        ),
        now=utc_now(),
    )
    fail_queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="noop",
            payload={"message": "force-fail"},
            metadata={"control_plane_task_id": "task_missing_force_fail"},
        ),
        now=utc_now(),
    )

    class _FailingControlPlane:
        def sync_worker_run(self, run: WorkerQueueItemRead) -> None:
            raise RuntimeError(f"boom {run.run_id}")

    app.dependency_overrides[get_control_plane_service] = lambda: _FailingControlPlane()
    try:
        cancelled = worker_client.post(
            f"/api/v1/worker-runs/{cancel_queued.run_id}/cancel",
            json={"reason": "cancel despite sync failure"},
        )
        failed = worker_client.post(
            f"/api/v1/worker-runs/{fail_queued.run_id}/force-fail",
            json={"reason": "fail despite sync failure"},
        )
    finally:
        app.dependency_overrides.pop(get_control_plane_service, None)

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"


def test_report_persists_failure_metadata_for_summary_chain(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", payload={"message": "hello"}),
        now=utc_now(),
    )
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.run is not None

    failed = worker_client.post(
        f"/api/v1/workers/mac-mini-01/runs/{queued.run_id}/report",
        json={
            "status": "failed",
            "message": "noop failed",
            "error": "permission denied",
            "metadata": {
                "error_kind": "permission_denied",
                "failed_stage": "execute",
                "artifacts": ["/tmp/report.md"],
            },
        },
    )
    assert failed.status_code == 200
    body = failed.json()
    assert body["metadata"]["error_kind"] == "permission_denied"
    assert body["metadata"]["failed_stage"] == "execute"
    assert body["metadata"]["artifacts"] == ["/tmp/report.md"]


def test_report_rejects_other_worker_for_active_lease(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    _register_worker(registry, worker_id="mac-mini-02")

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", payload={"message": "hello"}),
        now=utc_now(),
    )
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))
    assert claimed.run is not None

    response = worker_client.post(
        f"/api/v1/workers/mac-mini-02/runs/{queued.run_id}/report",
        json={"status": "failed", "message": "nope", "error": "wrong worker"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Run is leased to another worker"


def test_report_rejects_original_worker_after_lease_expired_until_reclaimed(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    now = utc_now()
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", payload={"message": "hello"}),
        now=now,
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=now + timedelta(seconds=1))
    scheduler.report(
        "mac-mini-01",
        queued.run_id,
        WorkerRunReportRequest(
            status="running",
            message="started",
        ),
        now=now + timedelta(seconds=2),
    )
    with pytest.raises(Exception) as exc:
        scheduler.report(
            "mac-mini-01",
            queued.run_id,
            WorkerRunReportRequest(status="running", message="late heartbeat"),
            now=now + timedelta(seconds=70),
        )
    assert "lease expired" in str(exc.value)


def test_worker_run_ops_requeue_and_force_fail(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", payload={"message": "hello"}, max_retries=3),
        now=utc_now(),
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))
    scheduler.report(
        "mac-mini-01",
        queued.run_id,
        WorkerRunReportRequest(
            status="running",
            message="started",
        ),
        now=utc_now() + timedelta(seconds=2),
    )
    requeued = worker_client.post(
        f"/api/v1/worker-runs/{queued.run_id}/requeue",
        json={"reason": "manual recovery", "backoff_seconds": 5},
    )
    assert requeued.status_code == 200
    rbody = requeued.json()
    assert rbody["status"] == "queued"
    assert rbody["retry_count"] == 1
    assert rbody["recovery_reason"] == "manual recovery"

    failed = worker_client.post(
        f"/api/v1/worker-runs/{queued.run_id}/force-fail",
        json={"reason": "operator abort"},
    )
    assert failed.status_code == 200
    fbody = failed.json()
    assert fbody["status"] == "failed"
    assert fbody["error"] == "operator abort"

    second_force = worker_client.post(
        f"/api/v1/worker-runs/{queued.run_id}/force-fail",
        json={"reason": "again"},
    )
    assert second_force.status_code == 409


def test_worker_run_list_endpoint_exposes_priority_and_retry_fields(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    _, scheduler = worker_services
    scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", priority=6, max_retries=5),
        now=utc_now(),
    )
    response = worker_client.get("/api/v1/worker-runs")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert "priority" in items[0]
    assert "retry_count" in items[0]
    assert "max_retries" in items[0]


def test_enqueue_youtube_autoflow_via_api(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, _ = worker_services
    _register_worker(registry, worker_id="mac-mini-01")

    created = worker_client.post(
        "/api/v1/worker-runs/youtube-autoflow",
        json={
            "input_text": "请处理 https://www.youtube.com/watch?v=video-001",
            "repo_hint": "acme/demo",
            "requested_by": "local_test",
            "metadata": {"source": "api_test"},
        },
    )

    assert created.status_code == 201
    queued = created.json()
    assert queued["task_type"] == "youtube_autoflow"
    assert queued["requested_by"] == "local_test"
    assert queued["payload"]["repo_hint"] == "acme/demo"


def test_enqueue_source_collect_via_api(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, _ = worker_services
    _register_worker(registry, worker_id="mac-mini-01")

    created = worker_client.post(
        "/api/v1/worker-runs/source-collect",
        json={
            "source_kind": "x_bookmarks",
            "fixture_path": "/tmp/x-bookmarks.fixture.json",
            "limit": 12,
            "max_pages": 2,
            "collector": "xreach",
            "title": "整理 X 书签",
            "requested_by": "local_test",
            "metadata": {"source": "api_test"},
        },
    )

    assert created.status_code == 201
    queued = created.json()
    assert queued["task_type"] == "source_collect"
    assert queued["requested_by"] == "local_test"
    assert queued["payload"]["source_kind"] == "x_bookmarks"
    assert queued["payload"]["fixture_path"] == "/tmp/x-bookmarks.fixture.json"
    assert queued["payload"]["limit"] == 12
    assert queued["payload"]["max_pages"] == 2
    assert queued["payload"]["collector"] == "xreach"


# -----------------------------------------------------------------------------
# Butler completion fallback (ux-butler-parity)
# -----------------------------------------------------------------------------


class _StubNotifier:
    def __init__(self, *, edit_ok: bool = True, send_ok: bool = True, enabled: bool = True) -> None:
        self.edit_ok = edit_ok
        self.send_ok = send_ok
        self._enabled = enabled
        self.edits: list[dict[str, object]] = []
        self.sends: list[dict[str, object]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def edit_message_text(self, **kwargs: object) -> bool:
        self.edits.append(kwargs)
        return self.edit_ok

    def send_message(self, **kwargs: object) -> bool:
        self.sends.append(kwargs)
        return self.send_ok


def _enqueue_and_claim_claude_runtime(
    scheduler,
    *,
    chat_id: str = "777",
    ack_message_id: int = 4242,
    extra_metadata: dict[str, object] | None = None,
) -> str:
    meta: dict[str, object] = {
        "telegram_queue_ack_message_id": ack_message_id,
        "telegram_completion_via_api": True,
    }
    if extra_metadata:
        meta.update(extra_metadata)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="claude_runtime",
            task_type="claude_runtime",
            payload={"chat_id": chat_id, "prompt": "hi"},
            metadata=meta,
        ),
        now=utc_now(),
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))
    return queued.run_id


def test_butler_fallback_fires_when_worker_notify_failed(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """When worker reports notify=failed, API edits the queue ack as a safety net."""
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "completed",
                "message": "ok",
                "metrics": {
                    "telegram_notify_status": "failed",
                    "telegram_notify_attempts": 3,
                    "telegram_notify_error": "URLError(timeout)",
                    "exit_reason": "terminal_timeout",
                },
            },
        )
        assert report.status_code == 200
        assert len(notifier.edits) == 1
        edit = notifier.edits[0]
        assert edit["chat_id"] == "777"
        assert edit["message_id"] == 4242
        text = str(edit["text"])
        assert edit["parse_mode"] == "MarkdownV2"
        assert "AAS Worker" in text
        assert "管家兜底" in text
        assert "诊断" in text
        assert "terminal\\_timeout" in text
        assert run_id.replace("_", "\\_") in text
        # Dedup marker should be persisted on the run.
        stored = scheduler.get_run(run_id)
        assert stored is not None
        assert stored.metadata.get("telegram_butler_fallback_sent") is True
        assert stored.metadata.get("telegram_butler_fallback_reason") == "failed"
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_fallback_explains_source_collect_auth_failure(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """source_collect auth failures should show a concise action hint, not raw collector noise."""
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="整理X书签",
            task_type="source_collect",
            payload={
                "chat_id": "777",
                "runtime_id": "source_collect",
                "capability_id": "source_collect",
                "agent_name": "source_collect",
                "target_agents": ["source_collect"],
            },
            metadata={
                "telegram_queue_ack_message_id": 4242,
                "telegram_completion_via_api": True,
                "capability_id": "source_collect",
            },
        ),
        now=utc_now(),
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{queued.run_id}/report",
            json={
                "status": "failed",
                "message": "source_collect failed: X 书签采集器 xreach 鉴权失败，无法读取书签。",
                "error": "X 书签采集器 xreach 鉴权失败，无法读取书签。",
                "metrics": {
                    "telegram_notify_status": "failed",
                    "error_kind": "collector_auth_failed",
                    "exit_reason": "collector_auth_failed",
                    "collector": "xreach",
                },
                "result": {
                    "summary": "X 书签采集器 xreach 鉴权失败，无法读取书签。",
                    "telegram_hint": "请在本机重新完成 xreach 登录后重试；如果只想验证链路，可先传 fixture_path 做离线 smoke。",
                    "error_kind": "collector_auth_failed",
                    "exit_reason": "collector_auth_failed",
                    "collector": "xreach",
                    "collector_error": "Error: GraphQL Error: Could not authenticate you",
                },
            },
        )
        assert report.status_code == 200
        assert len(notifier.edits) == 1
        text = str(notifier.edits[0]["text"])
        assert "AAS Worker" in text
        assert "初代worker" not in text
        assert "source\\_collect" in text
        assert "collector\\_auth\\_failed" in text
        assert "xreach 登录" in text
        assert "Could not authenticate you" not in text
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_primary_edits_ack_when_worker_delegates_card(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """API edits the queue ack bubble using the worker-built card (管家同一条消息)."""
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        card = "【AAS Worker】\n任务已结束。\n\n| 项 | 值 |\n| --- | --- |\n| 任务 | x |\n\n正文第一行\n第二行"
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "completed",
                "message": "ok",
                "metrics": {
                    "telegram_notify_status": "delegated_api",
                    "telegram_notify_attempts": 0,
                },
                "result": {"telegram_completion_card_text": card},
            },
        )
        assert report.status_code == 200
        assert len(notifier.edits) == 1
        assert notifier.edits[0]["chat_id"] == "777"
        assert notifier.edits[0]["message_id"] == 4242
        assert "正文第一行" in str(notifier.edits[0]["text"])
        assert notifier.edits[0]["parse_mode"] is None
        assert notifier.sends == []
        stored = scheduler.get_run(run_id)
        assert stored is not None
        assert stored.metadata.get("telegram_butler_primary_sent") is True
        assert stored.metadata.get("telegram_butler_fallback_sent") is not True
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_fallback_skipped_when_worker_already_delivered(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """When worker reports notify=edited|sent, API must NOT double-message."""
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "completed",
                "message": "ok",
                "metrics": {"telegram_notify_status": "edited", "telegram_notify_attempts": 1},
            },
        )
        assert report.status_code == 200
        assert notifier.edits == []
        assert notifier.sends == []
        stored = scheduler.get_run(run_id)
        assert stored is not None
        assert "telegram_butler_fallback_sent" not in (stored.metadata or {})
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_fallback_falls_back_to_send_when_edit_fails(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier(edit_ok=False, send_ok=True)
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "failed",
                "message": "fail",
                "error": "boom",
                "metrics": {"telegram_notify_status": "skipped_no_token"},
            },
        )
        assert report.status_code == 200
        assert len(notifier.edits) == 1
        assert len(notifier.sends) == 1
        send_text = str(notifier.sends[0]["text"])
        assert notifier.sends[0]["parse_mode"] == "MarkdownV2"
        assert "AAS Worker" in send_text
        assert "诊断" in send_text
        assert "boom" in send_text
        stored = scheduler.get_run(run_id)
        assert stored is not None
        assert stored.metadata.get("telegram_butler_fallback_sent") is True
        assert stored.metadata.get("telegram_butler_fallback_reason") == "skipped_no_token"
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_fallback_skipped_when_no_chat_id(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="claude_runtime",
            task_type="claude_runtime",
            payload={"prompt": "hi"},  # no chat_id
            metadata={"telegram_queue_ack_message_id": 1},
        ),
        now=utc_now(),
    )
    scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{queued.run_id}/report",
            json={
                "status": "completed",
                "message": "ok",
                "metrics": {"telegram_notify_status": "failed"},
            },
        )
        assert report.status_code == 200
        assert notifier.edits == []
        assert notifier.sends == []
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_fallback_disabled_by_setting(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app
    from autoresearch.api.settings import (
        get_telegram_settings as real_get_telegram_settings,
    )

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    disabled_settings = real_get_telegram_settings().model_copy(
        update={
            "butler_completion_fallback_enabled": False,
            "butler_api_completion_enabled": False,
        }
    )
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    # Override the settings dependency directly for this request.
    from autoresearch.api.settings import get_telegram_settings as settings_dep

    app.dependency_overrides[settings_dep] = lambda: disabled_settings
    try:
        report = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "completed",
                "message": "ok",
                "metrics": {"telegram_notify_status": "failed"},
            },
        )
        assert report.status_code == 200
        assert notifier.edits == []
        assert notifier.sends == []
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(settings_dep, None)


def test_butler_fallback_does_not_double_send_after_marker_set(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """If a prior call already wrote the dedup marker, the helper must skip even if notify_state is bad.

    This covers the case where someone bumps a run's metadata out-of-band.
    """
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app
    from autoresearch.api.routers.workers import _maybe_send_butler_completion_fallback
    from autoresearch.api.settings import get_telegram_settings as real_get_telegram_settings

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)
    # Pre-mark dedup so a direct helper call should bail early.
    scheduler.merge_queue_metadata(run_id, {"telegram_butler_fallback_sent": True})

    notifier = _StubNotifier()
    settings = real_get_telegram_settings()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        # Flip status to terminal manually then re-fetch.
        scheduler.report(
            "mac-mini-01",
            run_id,
            __import__(
                "autoresearch.shared.models",
                fromlist=["WorkerRunReportRequest"],
            ).WorkerRunReportRequest(
                status="completed",
                message="ok",
                metrics={"telegram_notify_status": "failed"},
            ),
        )
        stored = scheduler.get_run(run_id)
        assert stored is not None
        _maybe_send_butler_completion_fallback(
            stored,
            notifier=notifier,
            settings=settings,
            scheduler=scheduler,
        )
        assert notifier.edits == []
        assert notifier.sends == []
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_live_edit_on_running_report(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app
    import autoresearch.api.routers.workers as workers_mod

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    clock = {"t": 1000.0}

    def fake_time() -> float:
        return float(clock["t"])

    monkeypatch.setattr(workers_mod.time, "time", fake_time)
    try:
        live_body = {
            "status": "running",
            "message": "Hermes 运行中（0s）· running",
            "metrics": {
                "telegram_live_phase": "running",
                "telegram_live_elapsed_s": 0,
                "hermes_status": "running",
                "hermes_runtime_run_id": "run-h",
                "telegram_display_runtime_id": "hermes",
                "telegram_display_agent_name": "assistant-main",
            },
        }
        r1 = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=live_body,
        )
        assert r1.status_code == 200
        assert len(notifier.edits) == 1
        assert notifier.edits[0]["parse_mode"] == "MarkdownV2"
        assert "管家运行中" in str(notifier.edits[0]["text"])
        assert "hermes" in str(notifier.edits[0]["text"])
        assert "assistant\\-main" in str(notifier.edits[0]["text"])

        clock["t"] = 1002.0
        r2 = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=live_body,
        )
        assert r2.status_code == 200
        assert len(notifier.edits) == 1
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_live_edit_skips_within_interval_same_hash(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service
    from autoresearch.api.main import app
    import autoresearch.api.routers.workers as workers_mod

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    clock = {"t": 2000.0}

    def fake_time() -> float:
        return float(clock["t"])

    monkeypatch.setattr(workers_mod.time, "time", fake_time)
    body = {
        "status": "running",
        "message": "Hermes 运行中（0s）· running",
        "metrics": {
            "telegram_live_phase": "running",
            "telegram_live_elapsed_s": 0,
            "hermes_status": "running",
            "hermes_runtime_run_id": "run-h",
            "telegram_display_runtime_id": "hermes",
            "telegram_display_agent_name": "assistant-main",
        },
    }
    try:
        assert worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=body,
        ).status_code == 200
        assert len(notifier.edits) == 1
        clock["t"] = 2005.0
        assert worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=body,
        ).status_code == 200
        assert len(notifier.edits) == 1
        clock["t"] = 2040.0
        assert worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=body,
        ).status_code == 200
        assert len(notifier.edits) == 2
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_butler_live_edit_disabled_by_setting(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    from autoresearch.api.dependencies import get_telegram_notifier_service, get_telegram_settings
    from autoresearch.api.main import app

    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    run_id = _enqueue_and_claim_claude_runtime(scheduler)

    notifier = _StubNotifier()
    s = get_telegram_settings().model_copy(update={"butler_live_updates_enabled": False})
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_telegram_settings] = lambda: s
    try:
        r = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json={
                "status": "running",
                "message": "x",
                "metrics": {"telegram_live_phase": "running", "telegram_live_elapsed_s": 1},
            },
        )
        assert r.status_code == 200
        assert notifier.edits == []
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_telegram_settings, None)
