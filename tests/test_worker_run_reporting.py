from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from autoresearch.api.dependencies import get_worker_registry_service, get_worker_scheduler_service
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRegisterRequest,
    WorkerType,
    WorkerMode,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


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
                },
            },
        )
        assert report.status_code == 200
        assert len(notifier.edits) == 1
        edit = notifier.edits[0]
        assert edit["chat_id"] == "777"
        assert edit["message_id"] == 4242
        text = str(edit["text"])
        assert "【初代worker】" in text
        assert "管家兜底" in text
        assert run_id in text
        # Dedup marker should be persisted on the run.
        stored = scheduler.get_run(run_id)
        assert stored is not None
        assert stored.metadata.get("telegram_butler_fallback_sent") is True
        assert stored.metadata.get("telegram_butler_fallback_reason") == "failed"
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
        card = "【初代worker】\n任务已结束。\n\n| 项 | 值 |\n| --- | --- |\n| 任务 | x |\n\n正文第一行\n第二行"
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
        assert "【初代worker】" in send_text
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
        TelegramSettings,
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
            },
        }
        r1 = worker_client.post(
            f"/api/v1/workers/mac-mini-01/runs/{run_id}/report",
            json=live_body,
        )
        assert r1.status_code == 200
        assert len(notifier.edits) == 1
        assert "Hermes 运行中" in str(notifier.edits[0]["text"])

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
