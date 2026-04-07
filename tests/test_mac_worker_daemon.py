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
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
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
from autoresearch.workers.mac.executor import MacWorkerExecutor


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
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config = MacWorkerConfig(
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
