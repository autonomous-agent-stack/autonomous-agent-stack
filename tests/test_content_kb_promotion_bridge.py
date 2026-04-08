"""Tests for content_kb → draft PR promotion bridge and end-to-end orchestration."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.content_kb_promotion_bridge import (
    CliContentKBPromotionProvider,
    ContentKBPromotionBridge,
    ContentKBPromotionResult,
    build_content_kb_promotion_bridge,
)
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


class _FakePromotionProvider:
    """Fake provider that records calls and returns a PR URL."""

    def __init__(self, pr_url: str = "https://github.com/my-org/knowledge-base/pull/42"):
        self.pr_url = pr_url
        self.calls: list[dict] = []

    def open_draft_pr(
        self,
        *,
        repo: str,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
        files: dict[str, str],
    ) -> str:
        self.calls.append({
            "repo": repo,
            "branch_name": branch_name,
            "base_branch": base_branch,
            "title": title,
            "body": body,
            "files": files,
        })
        return self.pr_url


class _FailingPromotionProvider:
    """Provider that always fails."""

    def open_draft_pr(self, **kwargs) -> str:
        raise RuntimeError("GitHub API unavailable")


def _mock_completed(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["mock"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# ============================================================================
# Bridge unit tests
# ============================================================================


def test_bridge_skips_non_ingest_tasks() -> None:
    """Bridge returns pr_requested=False for non-ingest tasks."""
    bridge = ContentKBPromotionBridge()
    result = bridge.maybe_promote(task_type="noop", result={"draft_pr_requested": True})
    assert result.pr_requested is False
    assert result.pr_attempted is False


def test_bridge_skips_when_no_result() -> None:
    bridge = ContentKBPromotionBridge()
    result = bridge.maybe_promote(task_type="content_kb_ingest", result=None)
    assert result.pr_requested is False


def test_bridge_skips_when_no_hint() -> None:
    bridge = ContentKBPromotionBridge()
    result = bridge.maybe_promote(
        task_type="content_kb_ingest",
        result={"topic": "economy", "repo": "test/repo"},
    )
    assert result.pr_requested is False


def test_bridge_returns_not_attempted_without_provider() -> None:
    """Bridge reports not attempted when no provider is configured."""
    bridge = ContentKBPromotionBridge(_provider=None)
    result = bridge.maybe_promote(
        task_type="content_kb_ingest",
        result={
            "draft_pr_requested": True,
            "draft_pr_hint": {"repo": "test/repo", "branch_prefix": "ckb", "title_prefix": "test"},
        },
    )
    assert result.pr_requested is True
    assert result.pr_attempted is False
    assert "no contentkbpromotionprovider configured" in (result.failure_reason or "").lower()


def test_bridge_creates_pr_via_provider() -> None:
    """Bridge calls provider and returns PR URL."""
    provider = _FakePromotionProvider()
    bridge = ContentKBPromotionBridge(_provider=provider)

    result = bridge.maybe_promote(
        task_type="content_kb_ingest",
        result={
            "draft_pr_requested": True,
            "draft_pr_hint": {
                "repo": "my-org/knowledge-base",
                "branch_prefix": "content-kb/ingest",
                "title_prefix": "docs(content-kb): ingest AI Weekly",
            },
            "topic": "ai-status-and-outlook",
            "job_id": "job-123",
            "directory": "subtitles/ai/ai-weekly",
            "files_written": ["normalized_subtitle.txt"],
            "indexes": {
                "topic": {"version": "topics/v1", "topics": {}},
            },
        },
    )

    assert result.pr_requested is True
    assert result.pr_attempted is True
    assert result.pr_url == "https://github.com/my-org/knowledge-base/pull/42"
    assert result.branch_name is not None
    assert "content-kb/ingest" in result.branch_name
    assert result.failure_reason is None
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["repo"] == "my-org/knowledge-base"
    assert call["base_branch"] == "main"
    assert "indexes/topic.json" in call["files"]


def test_bridge_handles_provider_failure() -> None:
    """Bridge captures provider exceptions as failure_reason."""
    provider = _FailingPromotionProvider()
    bridge = ContentKBPromotionBridge(_provider=provider)

    result = bridge.maybe_promote(
        task_type="content_kb_ingest",
        result={
            "draft_pr_requested": True,
            "draft_pr_hint": {
                "repo": "test/repo",
                "branch_prefix": "ckb",
                "title_prefix": "test",
            },
            "topic": "economy",
        },
    )

    assert result.pr_requested is True
    assert result.pr_attempted is True
    assert result.pr_url is None
    assert "unavailable" in (result.failure_reason or "")


# ============================================================================
# CliContentKBPromotionProvider unit tests (mocked subprocess)
# ============================================================================


def test_cli_provider_creates_worktree_commits_and_pr(tmp_path: Path) -> None:
    """CliContentKBPromotionProvider runs the full git + gh pipeline."""
    repo_dir = tmp_path / "repos" / "my-org--kb"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()  # mark as git checkout

    provider = CliContentKBPromotionProvider(repos_root=tmp_path / "repos")

    call_sequence: list[list[str]] = []

    def mock_run(cmd, *, cwd=None, capture_output=False, text=False, check=False, env=None):
        call_sequence.append(cmd)
        cmd_name = Path(cmd[0]).name if cmd else ""
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "fetch":
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "add" in cmd:
            wt_dir = Path(cmd[4]) if len(cmd) > 4 else tmp_path / "wt"
            wt_dir.mkdir(parents=True, exist_ok=True)
            (wt_dir / ".git").mkdir(exist_ok=True)
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "add":
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "status":
            return _mock_completed(stdout="A  indexes/topic.json\n")
        if cmd_name == "git" and "-c" in cmd and "commit" in cmd:
            return _mock_completed(stdout="[main abc123] done")
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "push":
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "remove" in cmd:
            return _mock_completed()
        if cmd_name == "gh":
            return _mock_completed(stdout="https://github.com/my-org/kb/pull/55\n")
        return _mock_completed()

    with patch("autoresearch.core.services.content_kb_promotion_bridge.subprocess.run", side_effect=mock_run):
        pr_url = provider.open_draft_pr(
            repo="my-org/kb",
            branch_name="content-kb/ingest/test-abc",
            base_branch="main",
            title="docs(content-kb): ingest test",
            body="## Content KB Ingest\n\n- Topic: test",
            files={"indexes/topic.json": '{"version": "topics/v1"}'},
        )

    assert pr_url == "https://github.com/my-org/kb/pull/55"
    # Verify key commands were run
    cmd_strs = [" ".join(c) for c in call_sequence]
    assert any("fetch" in s for s in cmd_strs)
    assert any("worktree add" in s for s in cmd_strs)
    assert any("commit" in s for s in cmd_strs)
    assert any("push" in s for s in cmd_strs)
    assert any("gh pr create" in s for s in cmd_strs)


def test_cli_provider_fails_when_gh_errors(tmp_path: Path) -> None:
    """Provider raises when gh pr create returns non-zero."""
    repo_dir = tmp_path / "repos" / "org--repo"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()

    provider = CliContentKBPromotionProvider(repos_root=tmp_path / "repos")

    def mock_run(cmd, **kwargs):
        cmd_name = Path(cmd[0]).name if cmd else ""
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "add" in cmd:
            Path(cmd[4]).mkdir(parents=True, exist_ok=True)
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "remove" in cmd:
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "status":
            return _mock_completed(stdout="A  file.txt\n")
        if cmd_name == "git":
            return _mock_completed()
        if cmd_name == "gh":
            return _mock_completed(returncode=1, stderr="rate limited")
        return _mock_completed()

    with patch("autoresearch.core.services.content_kb_promotion_bridge.subprocess.run", side_effect=mock_run):
        with pytest.raises(RuntimeError, match="rate limited"):
            provider.open_draft_pr(
                repo="org/repo",
                branch_name="test-branch",
                base_branch="main",
                title="test",
                body="test",
                files={"file.txt": "content"},
            )


def test_cli_provider_raises_on_no_changes(tmp_path: Path) -> None:
    """Provider raises when git status shows no changes after file writes."""
    repo_dir = tmp_path / "repos" / "org--repo"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()

    provider = CliContentKBPromotionProvider(repos_root=tmp_path / "repos")

    def mock_run(cmd, **kwargs):
        cmd_name = Path(cmd[0]).name if cmd else ""
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "add" in cmd:
            Path(cmd[4]).mkdir(parents=True, exist_ok=True)
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "worktree" and "remove" in cmd:
            return _mock_completed()
        if cmd_name == "git" and len(cmd) > 1 and cmd[1] == "status":
            return _mock_completed(stdout="")  # no changes
        return _mock_completed()

    with patch("autoresearch.core.services.content_kb_promotion_bridge.subprocess.run", side_effect=mock_run):
        with pytest.raises(RuntimeError, match="no changes to commit"):
            provider.open_draft_pr(
                repo="org/repo",
                branch_name="test-branch",
                base_branch="main",
                title="test",
                body="test",
                files={},
            )


# ============================================================================
# build_content_kb_promotion_bridge factory tests
# ============================================================================


def test_factory_returns_none_without_gh(tmp_path: Path) -> None:
    """Factory returns None when gh CLI is not available."""
    with patch("autoresearch.core.services.content_kb_promotion_bridge.shutil.which", return_value=None):
        bridge = build_content_kb_promotion_bridge(repos_root=tmp_path)
    assert bridge is None


def test_factory_returns_none_without_repos_root() -> None:
    """Factory returns None when repos_root is None."""
    with patch("autoresearch.core.services.content_kb_promotion_bridge.shutil.which", return_value="/usr/bin/gh"):
        bridge = build_content_kb_promotion_bridge(repos_root=None)
    assert bridge is None


def test_factory_returns_bridge_when_available(tmp_path: Path) -> None:
    """Factory returns a working bridge when prerequisites are met."""
    with patch("autoresearch.core.services.content_kb_promotion_bridge.shutil.which", return_value="/usr/bin/gh"):
        bridge = build_content_kb_promotion_bridge(repos_root=tmp_path)
    assert bridge is not None
    assert bridge._provider is not None


# ============================================================================
# End-to-end orchestration tests (daemon + bridge + executor)
# ============================================================================


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "ckb-bridge-test.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_bridge_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_bridge_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_bridge_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _write_srt(tmp_path: Path) -> Path:
    srt = tmp_path / "test-bridge.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n人工智能和深度学习\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n大模型发展\n",
        encoding="utf-8",
    )
    return srt


def _build_daemon_with_bridge(
    tmp_path: Path,
    *,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
    bridge: ContentKBPromotionBridge,
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config = MacWorkerConfig(
        worker_id="test-worker-bridge",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Test Worker Bridge",
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
        content_kb_promotion_bridge=bridge,
    )


def test_e2e_ingest_triggers_promotion_bridge(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """End-to-end: ingest with open_draft_pr=True triggers bridge → PR created."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    provider = _FakePromotionProvider(pr_url="https://github.com/my-org/kb/pull/99")
    bridge = ContentKBPromotionBridge(_provider=provider)
    daemon = _build_daemon_with_bridge(tmp_path, worker_services=worker_services, bridge=bridge)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "AI Bridge Test",
                "topic": "ai-status-and-outlook",
                "open_draft_pr": True,
                "owner": "my-org",
                "default_repo": "kb",
            },
            requested_by="e2e-test",
        ),
        now=utc_now(),
    )

    processed = daemon.run_once(now=utc_now())
    assert processed is True

    # Verify worker task completed
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result["draft_pr_requested"] is True

    # Verify bridge was called and PR was created
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["repo"] == "my-org/kb"
    assert "content-kb/ingest" in call["branch_name"]
    assert call["base_branch"] == "main"
    assert "indexes/topic.json" in call["files"]


def test_e2e_ingest_without_pr_flag_does_not_trigger_bridge(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """End-to-end: ingest without open_draft_pr does NOT trigger bridge."""
    srt_path = _write_srt(tmp_path)
    _, scheduler = worker_services
    provider = _FakePromotionProvider()
    bridge = ContentKBPromotionBridge(_provider=provider)
    daemon = _build_daemon_with_bridge(tmp_path, worker_services=worker_services, bridge=bridge)

    scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": str(srt_path),
                "title": "No PR Test",
                "topic": "economy",
            },
            requested_by="e2e-test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    # Provider should NOT have been called
    assert len(provider.calls) == 0


def test_e2e_classify_does_not_trigger_bridge(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """End-to-end: classify task never triggers bridge regardless."""
    _, scheduler = worker_services
    provider = _FakePromotionProvider()
    bridge = ContentKBPromotionBridge(_provider=provider)
    daemon = _build_daemon_with_bridge(tmp_path, worker_services=worker_services, bridge=bridge)

    scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_CLASSIFY,
            payload={"text": "人工智能"},
            requested_by="e2e-test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())
    assert len(provider.calls) == 0
