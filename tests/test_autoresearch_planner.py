from __future__ import annotations

import os
from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.api.dependencies import (
    get_autoresearch_planner_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.shared.autoresearch_planner_contract import (
    AutoResearchPlanDispatchStatus,
    AutoResearchPlannerRequest,
    UpstreamWatchDecision,
    UpstreamWatchRead,
)
from autoresearch.shared.models import JobStatus
from autoresearch.shared.store import InMemoryRepository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class StubTelegramNotifier:
    def __init__(self, *, send_results: list[bool] | None = None) -> None:
        self.messages: list[dict[str, object]] = []
        self._send_results = list(send_results or [])

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
    ) -> bool:
        self.messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": disable_web_page_preview,
                "reply_markup": reply_markup,
            }
        )
        if self._send_results:
            return self._send_results.pop(0)
        return True


class StubUpstreamWatcher:
    def __init__(self, result: UpstreamWatchRead) -> None:
        self._result = result
        self.calls = 0

    def inspect(self) -> UpstreamWatchRead:
        self.calls += 1
        return self._result


def _successful_run_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="worker completed successfully",
            changed_paths=list(job.policy.allowed_paths),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="/tmp/autoresearch.patch",
    )


def test_planner_selects_high_signal_marker_and_emits_worker_specs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "demo_service.py",
        "\n".join(
            [
                "def handle() -> str:",
                "    # FIXME: normalize promotion preflight before returning",
                "    return 'ok'",
                "",
            ]
        ),
    )
    _write(
        repo_root / "src" / "misc.py",
        "\n".join(
            [
                "def noop() -> None:",
                "    # TODO: clean this up later",
                "    return None",
                "",
            ]
        ),
    )

    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )

    plan = service.create(AutoResearchPlannerRequest())

    assert plan.status is JobStatus.COMPLETED
    assert plan.selected_candidate is not None
    assert plan.selected_candidate.source_path == "src/autoresearch/core/services/demo_service.py"
    assert plan.worker_spec is not None
    assert plan.controlled_request is not None
    assert plan.agent_job is not None
    assert plan.worker_spec.allowed_paths == [
        "src/autoresearch/core/services/demo_service.py",
        "tests/test_demo_service.py",
    ]
    assert plan.worker_spec.test_command == "pytest -q tests/test_demo_service.py"
    assert plan.controlled_request.backend.value == "openhands_cli"
    assert plan.controlled_request.pipeline_target.value == "draft_pr"
    assert plan.agent_job.mode == "patch_only"
    assert plan.agent_job.metadata["planner_candidate_id"] == plan.selected_candidate.candidate_id
    assert "FIXME" in plan.selected_candidate.title


def test_planner_falls_back_to_test_gap_when_repo_has_no_markers(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    large_body = "\n".join([f"def fn_{index}() -> int:\n    return {index}\n" for index in range(60)])
    _write(repo_root / "src" / "autoresearch" / "core" / "services" / "large_module.py", large_body)

    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )

    plan = service.create(AutoResearchPlannerRequest(max_candidates=3, pipeline_target="patch"))

    assert plan.status is JobStatus.COMPLETED
    assert plan.selected_candidate is not None
    assert plan.selected_candidate.category == "test_gap"
    assert plan.selected_candidate.source_path == "src/autoresearch/core/services/large_module.py"
    assert plan.worker_spec is not None
    assert plan.worker_spec.pipeline_target == "patch"
    assert plan.worker_spec.allowed_paths[-1] == "tests/test_large_module.py"


def test_planner_records_optional_upstream_watch_result(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    watcher = StubUpstreamWatcher(
        UpstreamWatchRead(
            upstream_url="https://github.com/openclaw/openclaw.git",
            decision=UpstreamWatchDecision.SKIP,
            summary="Recent upstream changes remain in non-core areas (LINE, Zalo); auto-skipped.",
            focus_areas=["extension:line", "extension:zalo"],
            cleaned_up=True,
        )
    )

    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        upstream_watcher=watcher,
    )

    plan = service.create(AutoResearchPlannerRequest(include_upstream_watch=True))

    assert watcher.calls == 1
    assert plan.upstream_watch is not None
    assert plan.upstream_watch.decision is UpstreamWatchDecision.SKIP
    assert "Upstream watcher auto-skipped merge noise" in plan.summary


@pytest.fixture
def autoresearch_plan_client(tmp_path: Path) -> TestClient:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "planner_target.py",
        "\n".join(
            [
                "def check() -> bool:",
                "    # FIXME: add strict regression coverage",
                "    return True",
                "",
            ]
        ),
    )
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        mini_app_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_autoresearch_planner_service] = lambda: service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    with TestClient(app) as client:
        setattr(client, "_planner", service)
        setattr(client, "_notifier", notifier)
        yield client
    app.dependency_overrides.clear()


def test_autoresearch_plan_api_round_trip(autoresearch_plan_client: TestClient) -> None:
    notifier = getattr(autoresearch_plan_client, "_notifier")
    response = autoresearch_plan_client.post(
        "/api/v1/autoresearch/plans",
        json={
            "goal": "Find the next safe promotion candidate.",
            "max_candidates": 2,
            "pipeline_target": "patch",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["selected_candidate"]["source_path"] == "src/autoresearch/core/services/planner_target.py"
    assert payload["worker_spec"]["pipeline_target"] == "patch"
    assert payload["telegram_uid"] == "10001"
    assert payload["notification_sent"] is True
    parsed = urlparse(payload["panel_action_url"])
    assert parsed.netloc == "panel.example"
    query = parse_qs(parsed.query)
    assert query["planId"] == [payload["plan_id"]]
    assert "token" in query
    assert notifier.messages[0]["chat_id"] == "10001"
    assert "AutoResearch 发现新优化点" in str(notifier.messages[0]["text"])
    assert notifier.messages[0]["reply_markup"] == {
        "inline_keyboard": [[{"text": "打开 Mini App 审批", "web_app": {"url": payload["panel_action_url"]}}]]
    }

    list_response = autoresearch_plan_client.get("/api/v1/autoresearch/plans")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    plan_id = items[0]["plan_id"]

    get_response = autoresearch_plan_client.get(f"/api/v1/autoresearch/plans/{plan_id}")
    assert get_response.status_code == 200
    assert get_response.json()["plan_id"] == plan_id


def test_autoresearch_plan_api_falls_back_to_text_only_notify_when_panel_url_is_not_https(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "planner_target.py",
        "\n".join(
            [
                "def check() -> bool:",
                "    # FIXME: add strict regression coverage",
                "    return True",
                "",
            ]
        ),
    )
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="http://127.0.0.1:8000/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_autoresearch_planner_service] = lambda: service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/autoresearch/plans",
            json={
                "goal": "Find the next safe promotion candidate.",
                "max_candidates": 2,
                "pipeline_target": "patch",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["notification_sent"] is True
    assert notifier.messages[0]["reply_markup"] is None


def test_autoresearch_plan_api_falls_back_to_url_button_when_web_app_send_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "planner_target.py",
        "\n".join(
            [
                "def check() -> bool:",
                "    # FIXME: add strict regression coverage",
                "    return True",
                "",
            ]
        ),
    )
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        mini_app_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier(send_results=[False, True])

    app.dependency_overrides[get_autoresearch_planner_service] = lambda: service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/autoresearch/plans",
            json={
                "goal": "Find the next safe promotion candidate.",
                "max_candidates": 2,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["notification_sent"] is True
    assert len(notifier.messages) == 2
    assert notifier.messages[0]["reply_markup"] == {
        "inline_keyboard": [[{"text": "打开 Mini App 审批", "web_app": {"url": payload["panel_action_url"]}}]]
    }
    assert notifier.messages[1]["reply_markup"] == {
        "inline_keyboard": [[{"text": "打开 Panel 审批", "url": payload["panel_action_url"]}]]
    }
    assert "Mini App 审批执行" in str(notifier.messages[0]["text"])
    assert "Panel 审批执行" in str(notifier.messages[1]["text"])


def test_autoresearch_plan_api_uses_secure_url_button_when_only_https_panel_url_is_available(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "planner_target.py",
        "\n".join(
            [
                "def check() -> bool:",
                "    # FIXME: add strict regression coverage",
                "    return True",
                "",
            ]
        ),
    )
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_autoresearch_planner_service] = lambda: service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/autoresearch/plans",
            json={
                "goal": "Find the next safe promotion candidate.",
                "max_candidates": 2,
                "pipeline_target": "patch",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    parsed = urlparse(payload["panel_action_url"])
    query = parse_qs(parsed.query)
    assert query["planId"] == [payload["plan_id"]]
    assert "token" in query
    assert notifier.messages[0]["reply_markup"] == {
        "inline_keyboard": [[{"text": "打开 Panel 审批", "url": payload["panel_action_url"]}]]
    }


def test_planner_dispatch_lifecycle_records_run_summary(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "dispatch_target.py",
        "\n".join(
            [
                "def check() -> bool:",
                "    # FIXME: dispatch this through the worker",
                "    return True",
                "",
            ]
        ),
    )
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_successful_run_summary,
    )

    plan = service.create(AutoResearchPlannerRequest(telegram_uid="10001"))
    queued = service.request_dispatch(plan.plan_id, requested_by="10001")
    dispatched = service.execute_dispatch(plan.plan_id)

    assert queued.dispatch_status is AutoResearchPlanDispatchStatus.DISPATCHING
    assert dispatched.dispatch_status is AutoResearchPlanDispatchStatus.DISPATCHED
    assert dispatched.dispatch_requested_by == "10001"
    assert dispatched.dispatch_completed_at is not None
    assert dispatched.run_summary is not None
    assert dispatched.run_summary.final_status == "ready_for_promotion"
    assert dispatched.run_summary.promotion_patch_uri == "/tmp/autoresearch.patch"


def test_autoresearch_plan_api_sends_low_noise_upstream_skip_report(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        upstream_watcher=StubUpstreamWatcher(
            UpstreamWatchRead(
                upstream_url="https://github.com/openclaw/openclaw.git",
                decision=UpstreamWatchDecision.SKIP,
                summary="Recent upstream changes remain in non-core areas (LINE, Zalo); auto-skipped.",
                focus_areas=["extension:line", "extension:zalo"],
                cleaned_up=True,
            )
        ),
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_autoresearch_planner_service] = lambda: service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/autoresearch/plans",
            json={
                "goal": "Scan planner backlog and upstream noise.",
                "include_upstream_watch": True,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["selected_candidate"] is None
    assert payload["upstream_watch"]["decision"] == "skip"
    assert payload["notification_sent"] is True
    assert payload["panel_action_url"] is None
    assert len(notifier.messages) == 1
    assert "已完成上游巡检" in str(notifier.messages[0]["text"])
    assert "LINE/Zalo" in str(notifier.messages[0]["text"])


def _git(repo: Path, *args: str, cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Codex Tests",
            "GIT_AUTHOR_EMAIL": "codex-tests@example.com",
            "GIT_COMMITTER_NAME": "Codex Tests",
            "GIT_COMMITTER_EMAIL": "codex-tests@example.com",
        }
    )
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd or repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


def _commit(repo: Path, rel_path: str, content: str, message: str) -> None:
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", rel_path)
    _git(repo, "commit", "-m", message)
