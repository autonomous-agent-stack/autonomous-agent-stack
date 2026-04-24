from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.standby_youtube_autoflow import StandbyYouTubeAutoflowService
from autoresearch.core.services.standby_youtube_bridge import StandbyYouTubeBridgeService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.core.services.youtube_fetcher import YouTubeSourceDescriptor, YouTubeVideoSnapshot
from autoresearch.core.repositories.youtube import InMemoryYouTubeRepository
from autoresearch.shared.models import (
    JobStatus,
    StandbyYouTubeAutoflowResult,
    StandbyYouTubeActionResult,
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerQueueName,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerTaskType,
    WorkerType,
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeResultKind,
    YouTubeTargetKind,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.workers.mac.client import InProcessMacWorkerClient
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.daemon import MacWorkerDaemon
from autoresearch.workers.mac.executor import MacWorkerExecutor, MacWorkerExecutionResult


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "mac-worker-daemon.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_daemon_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_daemon_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_daemon_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _build_daemon(
    tmp_path: Path,
    *,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    youtube_bridge: StandbyYouTubeBridgeService | None = None,
    youtube_autoflow: StandbyYouTubeAutoflowService | None = None,
    telegram_reply_brand: str | None = None,
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config_kwargs: dict[str, object] = dict(
        worker_id="mac-mini-01",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Mac Standby Worker",
        host="mac-mini.local",
        heartbeat_seconds=15,
        claim_poll_seconds=5,
        lease_ttl_seconds=60,
        housekeeping_root=tmp_path,
        dry_run=True,
    )
    if telegram_reply_brand is not None:
        config_kwargs["telegram_reply_brand"] = telegram_reply_brand
    config = MacWorkerConfig(**config_kwargs)  # type: ignore[arg-type]
    return MacWorkerDaemon(
        config=config,
        client=InProcessMacWorkerClient(worker_registry=registry, worker_scheduler=scheduler),
        executor=MacWorkerExecutor(config, youtube_bridge=youtube_bridge, youtube_autoflow=youtube_autoflow),
        sleep=lambda _: None,
    )


class _StandbyBridgeFetcher:
    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        if url != "https://www.youtube.com/watch?v=video-001":
            raise YouTubeAgentError(
                YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                f"unsupported source: {url}",
                failed_stage=YouTubeFailedStage.DISCOVERY,
            )
        return YouTubeSourceDescriptor(
            normalized_url=url,
            target_kind=YouTubeTargetKind.VIDEO,
            external_id="video-001",
            title="Bridge Demo Video",
        )

    def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
        return [
            YouTubeVideoSnapshot(
                video_id="video-001",
                source_url="https://www.youtube.com/watch?v=video-001",
                title="Bridge Demo Video",
                channel_id="channel-001",
                channel_title="Demo Channel",
                description="Bridge demo description.",
            )
        ]

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        return self.discover_videos(source_url, YouTubeTargetKind.VIDEO)[0]

    def fetch_transcript(self, source_url: str, *, preferred_languages: list[str], include_auto_generated: bool):
        raise YouTubeAgentError(
            YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
            "no subtitles or auto captions are available for this video",
            failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
        )


class _FakeStandbyYouTubeBridge:
    def __init__(self, result: StandbyYouTubeActionResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def execute_payload(
        self,
        payload: dict[str, object],
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, object] | None = None,
    ) -> StandbyYouTubeActionResult:
        self.calls.append(
            {
                "payload": payload,
                "queue_requested_by": queue_requested_by,
                "queue_metadata": queue_metadata,
            }
        )
        return self.result


class _FakeStandbyYouTubeAutoflow:
    def __init__(self, result: StandbyYouTubeAutoflowResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def execute_payload(
        self,
        payload: dict[str, object],
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, object] | None = None,
    ) -> StandbyYouTubeAutoflowResult:
        self.calls.append(
            {
                "payload": payload,
                "queue_requested_by": queue_requested_by,
                "queue_metadata": queue_metadata,
            }
        )
        return self.result


def _build_real_youtube_bridge(tmp_path: Path) -> StandbyYouTubeBridgeService:
    service = YouTubeAgentService(
        repository=InMemoryYouTubeRepository(),
        repo_root=tmp_path,
        fetcher=_StandbyBridgeFetcher(),
        digest_service=YouTubeDigestService(),
    )
    return StandbyYouTubeBridgeService(youtube_service=service)


def test_daemon_registers_claims_executes_and_reports_noop(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="noop",
            payload={"message": "hello from daemon"},
            requested_by="test",
        ),
        now=utc_now(),
    )

    first_tick = utc_now()
    processed = daemon.run_once(now=first_tick)

    assert processed is True
    worker = registry.get_worker("mac-mini-01", as_of=first_tick)
    assert worker is not None
    assert worker.worker_type == "mac"
    assert "claude_runtime" in worker.capabilities
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result == {"echo": "hello from daemon"}
    assert run.message == "hello from daemon"

    daemon.run_once(now=first_tick + timedelta(seconds=16))
    refreshed = registry.get_worker("mac-mini-01", as_of=first_tick + timedelta(seconds=16))
    assert refreshed is not None
    assert refreshed.last_heartbeat_at > worker.last_heartbeat_at


def test_daemon_executes_cleanup_appledouble_in_dry_run(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    scheduler = worker_services[1]
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    cleanup_root = tmp_path / "cleanup-target"
    cleanup_root.mkdir()
    dirty_file = cleanup_root / "._demo.txt"
    dirty_file.write_text("demo", encoding="utf-8")

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="cleanup_appledouble",
            payload={
                "root_path": str(cleanup_root),
                "recursive": True,
                "dry_run": True,
            },
            requested_by="test",
        ),
        now=utc_now(),
    )

    processed = daemon.run_once(now=utc_now())

    assert processed is True
    assert dirty_file.exists()
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None
    assert run.result["dry_run"] is True
    assert run.result["deleted_count"] == 1
    assert str(dirty_file) in run.result["deleted_paths"]


def test_daemon_executes_youtube_action_through_bridge(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    scheduler = worker_services[1]
    daemon = _build_daemon(
        tmp_path,
        worker_services=worker_services,
        youtube_bridge=_build_real_youtube_bridge(tmp_path),
    )
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="youtube_action",
            payload={
                "action": "subscribe",
                "target_url": "https://www.youtube.com/watch?v=video-001",
            },
            requested_by="manual_test",
            metadata={"source": "standby_test"},
        ),
        now=utc_now(),
    )

    processed = daemon.run_once(now=utc_now())

    assert processed is True
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None
    assert run.result["success"] is True
    assert run.result["action"] == "subscribe"
    assert run.result["subscription_id"] is not None


def test_daemon_reports_failed_youtube_action_with_structured_result(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    scheduler = worker_services[1]
    bridge = _FakeStandbyYouTubeBridge(
        StandbyYouTubeActionResult(
            success=False,
            action="fetch_transcript",
            status=JobStatus.FAILED,
            result_kind=YouTubeResultKind.FAILED,
            error_kind="timeout_failure",
            failed_stage="transcript_fetch",
            reason="yt-dlp timed out after 0.001 seconds",
            video_id="video-001",
            run_id="ytrun_demo",
        )
    )
    daemon = _build_daemon(
        tmp_path,
        worker_services=worker_services,
        youtube_bridge=bridge,  # type: ignore[arg-type]
    )
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="youtube_action",
            payload={
                "action": "fetch_transcript",
                "video_id": "video-001",
            },
            requested_by="manual_test",
        ),
        now=utc_now(),
    )

    processed = daemon.run_once(now=utc_now())

    assert processed is True
    assert len(bridge.calls) == 1
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.FAILED
    assert run.error == "yt-dlp timed out after 0.001 seconds"
    assert run.result is not None
    assert run.result["error_kind"] == "timeout_failure"
    assert run.result["failed_stage"] == "transcript_fetch"


def test_daemon_does_not_invoke_youtube_bridge_without_queued_run(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    bridge = _FakeStandbyYouTubeBridge(
        StandbyYouTubeActionResult(
            success=True,
            action="subscribe",
            status=JobStatus.COMPLETED,
            result_kind=YouTubeResultKind.SUCCESS,
        )
    )
    daemon = _build_daemon(
        tmp_path,
        worker_services=worker_services,
        youtube_bridge=bridge,  # type: ignore[arg-type]
    )

    processed = daemon.run_once(now=utc_now())

    assert processed is False
    assert bridge.calls == []


def test_daemon_executes_youtube_autoflow_with_structured_result(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    scheduler = worker_services[1]
    autoflow = _FakeStandbyYouTubeAutoflow(
        StandbyYouTubeAutoflowResult(
            success=True,
            status=JobStatus.COMPLETED,
            source_url="https://www.youtube.com/watch?v=video-001",
            subscription_id="ytsub_001",
            video_id="video-001",
            digest_id="ytdigest_001",
            repo="acme/demo",
            github_run_dir="/tmp/github-run",
            github_run_status="draft_pr_opened",
            pr_url="https://github.com/acme/demo/pull/7",
        )
    )
    daemon = _build_daemon(
        tmp_path,
        worker_services=worker_services,
        youtube_autoflow=autoflow,  # type: ignore[arg-type]
    )
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type="youtube_autoflow",
            payload={
                "input_text": "请处理 https://www.youtube.com/watch?v=video-001",
                "repo_hint": "acme/demo",
            },
            requested_by="manual_test",
        ),
        now=utc_now(),
    )

    processed = daemon.run_once(now=utc_now())

    assert processed is True
    assert len(autoflow.calls) == 1
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None
    assert run.result["video_id"] == "video-001"
    assert run.result["repo"] == "acme/demo"
    assert run.result["pr_url"] == "https://github.com/acme/demo/pull/7"


def test_notify_telegram_edit_in_place_when_ack_message_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    send_calls: list[dict[str, object]] = []

    def _edit(**kw: object) -> bool:
        edit_calls.append(kw)
        return True

    def _send(**kw: object) -> None:
        send_calls.append(kw)

    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", _edit)
    monkeypatch.setattr(daemon, "_worker_telegram_send_message_with_retries", _send)
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_tg_edit",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "42"},
        metadata={"telegram_queue_ack_message_id": 777},
        created_at=now,
        updated_at=now,
    )
    outcome = MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hello-out"})
    daemon._notify_telegram_result(run=run, outcome=outcome)

    assert len(edit_calls) == 1
    assert edit_calls[0]["message_id"] == 777
    assert edit_calls[0]["chat_id"] == "42"
    text = str(edit_calls[0]["text"])
    assert "【初代worker】" in text
    assert "hello-out" in text
    assert send_calls == []


def test_notify_telegram_falls_back_to_send_when_edit_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    send_calls: list[dict[str, object]] = []

    def _send(**kw: object) -> tuple[bool, int, str | None]:
        send_calls.append(kw)
        return True, 1, None

    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: False)
    monkeypatch.setattr(daemon, "_worker_telegram_send_message_with_retries", _send)
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_tg_fallback",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "99"},
        metadata={"telegram_queue_ack_message_id": 1},
        created_at=now,
        updated_at=now,
    )
    outcome = MacWorkerExecutionResult(message="ok", result={"stdout_preview": "x"})
    daemon._notify_telegram_result(run=run, outcome=outcome)

    assert len(send_calls) == 1
    assert send_calls[0]["chat_id"] == "99"
    assert "x" in str(send_calls[0]["text"])


def test_notify_telegram_omits_brand_prefix_when_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []

    def _edit(**kw: object) -> bool:
        edit_calls.append(kw)
        return True

    daemon = _build_daemon(
        tmp_path,
        worker_services=worker_services,
        telegram_reply_brand="",
    )
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", _edit)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 1, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_tg_nobrand",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 2},
        created_at=now,
        updated_at=now,
    )
    daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "y"}),
    )
    assert "【" not in str(edit_calls[0]["text"])


def test_notify_telegram_skips_when_not_claude_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    send_calls: list[dict[str, object]] = []

    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: edit_calls.append(kw) or True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (send_calls.append(kw), (True, 1, None))[1],
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_skip",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="noop",
        task_type=WorkerTaskType.NOOP,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 9},
        created_at=now,
        updated_at=now,
    )
    daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={}),
    )
    assert edit_calls == []
    assert send_calls == []


def test_notify_telegram_returns_edited_delivery_dict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 1, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_edited",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 42},
        created_at=now,
        updated_at=now,
    )
    delivery = daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hi"}),
    )
    assert delivery == {
        "telegram_notify_status": "edited",
        "telegram_notify_attempts": 1,
        "telegram_notify_error": None,
    }


def test_notify_telegram_returns_sent_when_no_ack_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 2, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_sent",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "5"},
        created_at=now,
        updated_at=now,
    )
    delivery = daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hi"}),
    )
    assert delivery == {
        "telegram_notify_status": "sent",
        "telegram_notify_attempts": 2,
        "telegram_notify_error": None,
    }


def test_notify_telegram_returns_failed_when_send_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: False)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (False, 3, "URLError(timeout)"),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_failed",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "7"},
        metadata={"telegram_queue_ack_message_id": 99},
        created_at=now,
        updated_at=now,
    )
    delivery = daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hi"}),
    )
    assert delivery == {
        "telegram_notify_status": "failed",
        "telegram_notify_attempts": 3,
        "telegram_notify_error": "URLError(timeout)",
    }


def test_notify_telegram_skips_when_no_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.delenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_no_tok",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        created_at=now,
        updated_at=now,
    )
    delivery = daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hi"}),
    )
    assert delivery["telegram_notify_status"] == "skipped_no_token"
    assert delivery["telegram_notify_attempts"] == 0
    assert "TELEGRAM_BOT_TOKEN" in str(delivery["telegram_notify_error"])


def test_notify_telegram_skips_when_no_chat_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_no_chat",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={},
        created_at=now,
        updated_at=now,
    )
    delivery = daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(message="ok", result={"stdout_preview": "hi"}),
    )
    assert delivery == {
        "telegram_notify_status": "skipped_no_chat",
        "telegram_notify_attempts": 0,
        "telegram_notify_error": None,
    }


def test_notify_telegram_strips_hermes_warning_lines_from_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: edit_calls.append(kw) or True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 1, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_noisy",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 1},
        created_at=now,
        updated_at=now,
    )
    daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(
            message="ok",
            result={
                "summary": "Hermes completed: Warning: Unknown toolsets: shell, git",
                "stdout_preview": "Warning: Unknown toolsets: shell, git\n先看看仓库当前状态。",
            },
        ),
    )
    text = str(edit_calls[0]["text"])
    # main body should pick the post-warning useful line, not the warning header
    assert "先看看仓库当前状态" in text
    assert "Warning:" not in text
    # Summary row is omitted when it would only duplicate the first line of the body.
    assert "| 摘要 |" not in text


def test_notify_telegram_omits_summary_row_when_hermes_stub_redundant_with_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Vacuous ``Hermes completed.`` + real stdout: do not show a useless 摘要 row duplicating body."""
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: edit_calls.append(kw) or True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 1, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_vacuous_sum",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 1},
        created_at=now,
        updated_at=now,
    )
    daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(
            message="ok",
            result={
                "summary": "Hermes completed.",
                "stdout_preview": "Warning: x\n先看看当前仓库状态和未分类情况。\n第二行说明。",
            },
        ),
    )
    text = str(edit_calls[0]["text"])
    assert "先看看当前仓库状态和未分类情况" in text
    assert "| 摘要 |" not in text


def test_notify_telegram_emits_no_output_template_when_only_warnings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: edit_calls.append(kw) or True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (True, 1, None),
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_d_only_warn",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "1"},
        metadata={"telegram_queue_ack_message_id": 1},
        created_at=now,
        updated_at=now,
    )
    daemon._notify_telegram_result(
        run=run,
        outcome=MacWorkerExecutionResult(
            message="ok",
            result={
                "summary": "",
                "stdout_preview": "Warning: a\nWarning: b",
            },
        ),
    )
    text = str(edit_calls[0]["text"])
    # When everything is warnings we still want a meaningful card with run_id.
    assert "run_d_only_warn" in text
    assert "仅有警告输出" in text or "无文本输出" in text
    # Should NOT just dump the raw warning lines as the whole body.
    assert "Warning: a" not in text or "仅有警告输出" in text


def test_notify_telegram_skips_worker_http_when_delegated_to_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """telegram_completion_via_api: worker only fills result + metrics; no Telegram HTTP."""
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    edit_calls: list[dict[str, object]] = []
    send_calls: list[dict[str, object]] = []

    daemon = _build_daemon(tmp_path, worker_services=worker_services)
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: edit_calls.append(kw) or True)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (send_calls.append(kw), (True, 1, None))[1],
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_deleg",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="demo",
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"chat_id": "9"},
        metadata={"telegram_completion_via_api": True, "telegram_queue_ack_message_id": 55},
        created_at=now,
        updated_at=now,
    )
    outcome = MacWorkerExecutionResult(message="ok", result={"stdout_preview": "worker stdout"})
    delivery = daemon._notify_telegram_result(run=run, outcome=outcome)
    assert delivery["telegram_notify_status"] == "delegated_api"
    assert edit_calls == []
    assert send_calls == []
    assert "telegram_completion_card_text" in (outcome.result or {})
    assert "worker stdout" in str(outcome.result.get("telegram_completion_card_text"))


def test_process_run_records_delivery_status_into_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """End-to-end: delivery dict from _notify_telegram_result lands in worker_run.metrics."""
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "fake-bot-token")
    registry, scheduler = worker_services
    registry.register(
        WorkerRegisterRequest(
            worker_id="mac-mini-01",
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            role="housekeeper",
            capabilities=["claude_runtime"],
        )
    )
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="claude_runtime",
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={"chat_id": "1", "prompt": "hi"},
        ),
        now=utc_now(),
    )
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.run is not None

    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    # Stub the executor to return a known outcome (so we don't touch real claude runtime).
    monkeypatch.setattr(
        daemon._executor,
        "execute",
        lambda run: MacWorkerExecutionResult(
            message="ok",
            status=JobStatus.COMPLETED,
            result={"stdout_preview": "hello"},
        ),
    )
    # Force the in-place edit path to fail and the send path to also fail, so
    # the recorded delivery_status should be "failed".
    monkeypatch.setattr(daemon, "_worker_telegram_edit_or_send", lambda **kw: False)
    monkeypatch.setattr(
        daemon,
        "_worker_telegram_send_message_with_retries",
        lambda **kw: (False, 3, "boom"),
    )

    daemon._process_run(claimed.run)

    stored = scheduler.get_run(queued.run_id)
    assert stored is not None
    assert stored.status == JobStatus.COMPLETED
    assert stored.metrics.get("telegram_notify_status") == "failed"
    assert stored.metrics.get("telegram_notify_attempts") == 3
    assert stored.metrics.get("telegram_notify_error") == "boom"
