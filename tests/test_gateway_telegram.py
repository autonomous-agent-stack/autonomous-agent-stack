from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from autoresearch.api import dependencies as api_dependencies
from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_approval_store_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_claude_session_record_service,
    get_github_issue_service,
    get_manager_agent_service,
    get_openclaw_memory_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_telegram_notifier_service,
    get_worker_inventory_service,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.main import app
from autoresearch.api.routers import gateway_telegram
from autoresearch.api.settings import clear_settings_caches
from autoresearch.agent_protocol.models import DriverResult, RunSummary, ValidationReport
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.adapters import CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import CapabilityDomain, SkillCatalogRead
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.github_issue_service import GitHubIssueCommentRead, GitHubIssueRead, GitHubIssueReference
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    ClaudeAgentRunRead,
    ClaudeRuntimeSessionRecordRead,
    ApprovalRequestRead,
    ApprovalRequestCreateRequest,
    OpenClawMemoryRecordRead,
    OpenClawSessionRead,
    PromotionDiffStats,
    PromotionResult,
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


class _StubSkillProvider:
    def __init__(self) -> None:
        self._descriptor = CapabilityProviderDescriptorRead(
            provider_id="openclaw-skills",
            domain=CapabilityDomain.SKILL,
            display_name="OpenClaw Skills",
            capabilities=["list_skills", "get_skill"],
            metadata={"stub": True},
        )
        self._skill = {
            "name": "Daily Brief",
            "skill_key": "daily_brief",
            "description": "Generate a concise daily brief",
            "source": "workspace",
            "base_dir": "/tmp/skills/daily_brief",
            "file_path": "/tmp/skills/daily_brief/SKILL.md",
            "metadata": {"stub": True},
        }

    def describe(self) -> CapabilityProviderDescriptorRead:
        return self._descriptor

    def list_skills(self) -> SkillCatalogRead:
        from autoresearch.shared.models import OpenClawSkillRead

        return SkillCatalogRead(
            provider_id="openclaw-skills",
            status="available",
            skills=[OpenClawSkillRead(**self._skill)],
        )

    def get_skill(self, skill_name: str):
        from autoresearch.shared.models import OpenClawSkillDetailRead

        normalized = skill_name.strip().lower()
        if normalized not in {"daily_brief", "daily brief"}:
            return None
        return OpenClawSkillDetailRead(**self._skill, content="# Daily Brief\nUse this skill.\n")


class _StubTelegramNotifier:
    def __init__(self) -> None:
        self.status_events: list[dict[str, str]] = []
        self.messages: list[dict[str, str]] = []
        self.sent_message_ids: list[int] = []
        self.edit_calls: list[dict[str, object]] = []

    @property
    def enabled(self) -> bool:
        return True

    def notify_status_magic_link(
        self,
        *,
        chat_id: str,
        summary_lines: list[str],
        magic_link_url: str | None,
        expires_at_iso: str | None,
        is_group_link: bool = False,
        mini_app_url: str | None = None,
    ) -> bool:
        self.status_events.append(
            {
                "chat_id": chat_id,
                "magic_link_url": magic_link_url or "",
                "expires_at": expires_at_iso or "",
                "summary": "\n".join(summary_lines),
                "is_group_link": str(is_group_link),
                "mini_app_url": mini_app_url or "",
            }
        )
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
    ) -> bool:
        self.messages.append({"chat_id": chat_id, "text": text, "message_thread_id": message_thread_id})
        return True

    def send_message_get_message_id(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, object] | None = None,
        message_thread_id: int | None = None,
        reply_to_message_id: int | None = None,
    ) -> int | None:
        self.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
            message_thread_id=message_thread_id,
            reply_to_message_id=reply_to_message_id,
        )
        mid = 880000 + len(self.sent_message_ids)
        self.sent_message_ids.append(mid)
        return mid

    def edit_message_text(
        self,
        *,
        chat_id: str,
        message_id: int,
        text: str,
        disable_web_page_preview: bool = True,
        message_thread_id: int | None = None,
    ) -> bool:
        self.edit_calls.append(
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "message_thread_id": message_thread_id,
            }
        )
        return True

    def notify_manual_action(self, *, chat_id: str, entry: object, run_status: str) -> bool:
        return True


class _StubExcelAuditService:
    def __init__(self, *, mode: str = "success") -> None:
        from autoresearch.shared.store import InMemoryRepository

        self._repository = InMemoryRepository()
        self._mode = mode
        self._counter = 0
        self.created_requests: list[object] = []
        self.executed_audit_ids: list[str] = []

    def create(self, request):
        from autoresearch.shared.excel_audit_contract import ExcelAuditRead
        from autoresearch.shared.models import JobStatus, utc_now

        self._counter += 1
        audit_id = f"ea_test_{self._counter:03d}"
        now = utc_now()
        record = ExcelAuditRead(
            audit_id=audit_id,
            task_brief=request.task_brief,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        self.created_requests.append(request)
        return self._repository.save(audit_id, record)

    def execute(self, audit_id: str):
        from autoresearch.shared.excel_audit_contract import ExcelAuditResultRead
        from autoresearch.shared.models import JobStatus, utc_now

        self.executed_audit_ids.append(audit_id)
        if self._mode == "raise":
            raise RuntimeError("simulated execute failure")

        record = self._repository.get(audit_id)
        assert record is not None

        if self._mode == "failed":
            updated = record.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "error": "simulated audit failure",
                    "updated_at": utc_now(),
                }
            )
        else:
            updated = record.model_copy(
                update={
                    "status": JobStatus.COMPLETED,
                    "result": ExcelAuditResultRead(
                        rows_checked=12,
                        rows_mismatched=2,
                        mismatch_amount_total=88.5,
                        findings_count=2,
                    ),
                    "artifacts": ["/tmp/report.md", "/tmp/report.json"],
                    "updated_at": utc_now(),
                }
            )

        return self._repository.save(audit_id, updated)

    def create_and_execute(self, request):
        raise AssertionError("gateway should not use synchronous create_and_execute")


class _StubGitHubIssueService:
    def __init__(self) -> None:
        self.comments: list[dict[str, str]] = []

    def fetch_issue(self, raw_reference: str) -> GitHubIssueRead:
        return GitHubIssueRead(
            reference=GitHubIssueReference(owner="owner", repo="repo", number=123),
            title="Audit trail crashes when comment body is empty",
            body="Steps:\n1. Trigger the task.\n2. Observe the failure.\n\nExpected: dispatch succeeds.",
            url="https://github.com/owner/repo/issues/123",
            state="OPEN",
            author="founder",
            labels=("bug", "telegram"),
            comments=(
                GitHubIssueCommentRead(author="reviewer", body="Please keep the fix scoped and tested."),
            ),
        )

    def build_manager_prompt(self, issue: GitHubIssueRead, *, operator_note: str | None = None) -> str:
        note = operator_note or ""
        return f"Fix GitHub issue {issue.reference.display}. {note}".strip()

    def post_comment(self, raw_reference: str, body: str) -> str:
        self.comments.append({"issue_reference": raw_reference, "body": body})
        return f"commented on {raw_reference}"


def _build_manager_service(db_path: Path) -> ManagerAgentService:
    repository = SQLiteModelRepository(
        db_path=db_path,
        table_name="manager_agent_dispatches_gateway_it",
        model_cls=ManagerDispatchRead,
    )

    def _dispatch_runner(job_spec) -> RunSummary:
        return RunSummary(
            run_id=job_spec.run_id,
            final_status="ready_for_promotion",
            driver_result=DriverResult(
                run_id=job_spec.run_id,
                agent_id=job_spec.agent_id,
                status="succeeded",
                summary="stub manager runner completed",
                changed_paths=["src/autoresearch/api/routers/admin.py"],
                recommended_action="promote",
            ),
            validation=ValidationReport(run_id=job_spec.run_id, passed=True),
            promotion_patch_uri="artifacts/promotion.patch",
            promotion=None,
        ).model_copy(
            update={
                "promotion": PromotionResult(
                    run_id=job_spec.run_id,
                    success=True,
                    mode="draft_pr",
                    pr_url=f"https://github.com/owner/repo/pull/{job_spec.run_id[-3:]}",
                    changed_files=["src/autoresearch/api/routers/admin.py"],
                    diff_stats=PromotionDiffStats(files_changed=1, insertions=12, deletions=2),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            }
        )

    return ManagerAgentService(
        repository=repository,
        repo_root=Path(__file__).resolve().parents[1],
        dispatch_runner=_dispatch_runner,
    )


@pytest.fixture
def telegram_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "telegram-gateway.sqlite3"
    os.environ["AUTORESEARCH_API_DB_PATH"] = str(db_path)
    clear_settings_caches()
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS telegram_inbound_update_ids")
        conn.commit()
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_gateway_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_gateway_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )
    admin_config_service = AdminConfigService(
        agent_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_agent_configs_gateway_it",
            model_cls=AdminAgentConfigRead,
        ),
        channel_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_channel_configs_gateway_it",
            model_cls=AdminChannelConfigRead,
        ),
        revision_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_config_revisions_gateway_it",
            model_cls=AdminConfigRevisionRead,
        ),
    )
    memory_service = OpenClawMemoryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_memories_gateway_it",
            model_cls=OpenClawMemoryRecordRead,
        ),
        openclaw_service=openclaw_service,
    )
    worker_registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_gateway_it",
            model_cls=WorkerRegistrationRead,
        )
    )
    worker_scheduler = WorkerSchedulerService(
        worker_registry=worker_registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_gateway_it",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_gateway_it",
            model_cls=WorkerLeaseRead,
        ),
    )
    approval_service = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_gateway_it",
            model_cls=ApprovalRequestRead,
        )
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_openclaw_memory_service] = lambda: memory_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_admin_config_service] = lambda: admin_config_service
    app.dependency_overrides[get_worker_registry_service] = lambda: worker_registry
    app.dependency_overrides[get_worker_scheduler_service] = lambda: worker_scheduler
    app.dependency_overrides[get_worker_inventory_service] = lambda: WorkerInventoryService(
        worker_registry=worker_registry,
        worker_scheduler=worker_scheduler,
    )
    app.dependency_overrides[get_claude_session_record_service] = lambda: ClaudeSessionRecordService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_runtime_session_records_it",
            model_cls=ClaudeRuntimeSessionRecordRead,
        )
    )

    with TestClient(app) as client:
        setattr(client, "_approval_store", approval_service)
        setattr(client, "_worker_scheduler", worker_scheduler)
        try:
            yield client
        finally:
            os.environ.pop("AUTORESEARCH_API_DB_PATH", None)
            clear_settings_caches()

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_gateway_guards() -> None:
    gateway_telegram._CHAT_RATE_WINDOWS.clear()


def test_telegram_webhook_routes_to_openclaw_and_agents(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('tg-agent-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1001,
            "message": {
                "message_id": 77,
                "text": "给我一条口红营销文案",
                "chat": {"id": 9527, "type": "private"},
                "from": {"id": 9527, "username": "alice"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["chat_id"] == "9527"
    assert payload["session_id"] is not None
    # Default chat now routes to worker queue instead of direct agent execution
    assert payload.get("metadata", {}).get("routed_to") == "worker_queue"
    run_id = payload.get("metadata", {}).get("run_id")
    assert run_id is not None

    session = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}")
    assert session.status_code == 200
    session_payload = session.json()
    assert session_payload["external_id"] == "9527"
    assert session_payload["scope"] == "personal"
    assert session_payload["session_key"] == "telegram:personal:user:9527"
    assert session_payload["chat_context"]["chat_type"] == "private"
    assert any(event["role"] == "user" for event in session_payload["events"])


def test_legacy_telegram_webhook_uses_same_processing_path(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('tg-legacy-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    # Legacy `/telegram/webhook` is only mounted when AUTORESEARCH_ENABLE_LEGACY_TELEGRAM_WEBHOOK=true
    # in a freshly built app; the default TestClient app runs minimal mode without that mount.
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1099,
            "message": {
                "message_id": 78,
                "text": "legacy webhook smoke",
                "chat": {"id": 9528, "type": "private"},
                "from": {"id": 9528, "username": "legacy"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["chat_id"] == "9528"
    # Default chat now routes to worker queue
    assert payload.get("metadata", {}).get("routed_to") == "worker_queue"


def test_telegram_webhook_separates_private_and_group_sessions(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('scope-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_OWNER_UIDS", "3001")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_USERNAMES", "clawxbot")

    private_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1301,
            "message": {
                "message_id": 81,
                "text": "private scope",
                "chat": {"id": 3001, "type": "private"},
                "from": {"id": 3001, "username": "duo"},
            },
        },
    )
    assert private_response.status_code == 200

    group_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1302,
            "message": {
                "message_id": 82,
                "text": "@clawxbot group scope",
                "chat": {"id": -1003001, "type": "supergroup"},
                "from": {"id": 3001, "username": "duo"},
            },
        },
    )
    assert group_response.status_code == 200

    sessions = telegram_client.get("/api/v1/openclaw/sessions")
    assert sessions.status_code == 200
    payload = sessions.json()
    assert len(payload) == 2

    session_by_scope = {item["scope"]: item for item in payload}
    assert session_by_scope["personal"]["session_key"] == "telegram:personal:user:3001"
    assert session_by_scope["personal"]["actor"]["role"] == "owner"
    assert session_by_scope["personal"]["chat_context"]["chat_type"] == "private"
    assert session_by_scope["shared"]["session_key"] == "telegram:shared:chat:-1003001"
    assert session_by_scope["shared"]["assistant_id"] == "telegram-shared"
    assert session_by_scope["shared"]["chat_context"]["chat_type"] == "supergroup"


def test_telegram_memory_command_persists_long_term_memory(
    telegram_client: TestClient,
) -> None:
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1310,
            "message": {
                "message_id": 83,
                "text": "/memory 晚上 10 点后不要主动推送",
                "chat": {"id": 9529, "type": "private"},
                "from": {"id": 9529, "username": "memory-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["agent_run_id"] is None
    assert payload["metadata"]["scope"] == "personal"

    bundle = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}/memory")
    assert bundle.status_code == 200
    bundle_payload = bundle.json()
    assert bundle_payload["personal_memories"][0]["content"] == "晚上 10 点后不要主动推送"


def test_telegram_private_chat_rejects_non_allowlisted_user_when_configured(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9600")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1311,
            "message": {
                "message_id": 84,
                "text": "hello",
                "chat": {"id": 9601, "type": "private"},
                "from": {"id": 9601, "username": "blocked-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["reason"] == "telegram user is not allowlisted"


def test_telegram_group_ambient_chatter_is_ignored_when_group_whitelist_enabled(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9701")
    monkeypatch.setenv("AUTORESEARCH_INTERNAL_GROUPS", "-1009701")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1312,
            "message": {
                "message_id": 85,
                "text": "just ambient chatter",
                "chat": {"id": -1009701, "type": "supergroup"},
                "from": {"id": 9701, "username": "allowed-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["reason"] == "group message ignored without explicit bot address"


def test_telegram_group_mention_is_accepted_when_group_whitelist_enabled(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9702")
    monkeypatch.setenv("AUTORESEARCH_INTERNAL_GROUPS", "-1009702")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_BOT_USERNAMES", "clawxbot")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('group-mention-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1313,
            "message": {
                "message_id": 86,
                "text": "@clawxbot summarize this thread",
                "chat": {"id": -1009702, "type": "supergroup"},
                "from": {"id": 9702, "username": "allowed-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["session_id"] is not None

    session = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}")
    assert session.status_code == 200
    assert session.json()["scope"] == "shared"


def test_telegram_group_reply_to_bot_is_accepted_when_group_whitelist_enabled(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9703")
    monkeypatch.setenv("AUTORESEARCH_INTERNAL_GROUPS", "-1009703")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('group-reply-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1314,
            "message": {
                "message_id": 87,
                "text": "replying to bot",
                "chat": {"id": -1009703, "type": "supergroup"},
                "from": {"id": 9703, "username": "allowed-user"},
                "reply_to_message": {
                    "message_id": 1,
                    "from": {"id": 999999, "username": "clawxbot", "is_bot": True},
                },
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["session_id"] is not None


def test_telegram_youtube_link_enqueues_existing_autoflow_and_tracks_session(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 1315,
                "message": {
                    "message_id": 88,
                    "text": "请处理这个视频 https://www.youtube.com/watch?v=6yjJ7Prt-RI",
                    "chat": {"id": 9710, "type": "private"},
                    "from": {"id": 9710, "username": "youtube-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        assert payload["session_id"] is not None
        assert payload["metadata"]["source"] == "telegram_youtube_autoflow"
        assert payload["metadata"]["status"] == "accepted"
        assert payload["metadata"]["task_type"] == "youtube_autoflow"
        run_id = payload["metadata"]["run_id"]
        assert run_id

        worker_scheduler = getattr(telegram_client, "_worker_scheduler")
        queued_run = worker_scheduler.get_run(run_id)
        assert queued_run is not None
        assert queued_run.task_type.value == "youtube_autoflow"
        assert queued_run.payload["source_url"] == "https://www.youtube.com/watch?v=6yjJ7Prt-RI"
        assert queued_run.payload["input_text"] == "请处理这个视频 https://www.youtube.com/watch?v=6yjJ7Prt-RI"
        assert queued_run.payload["source"] == "telegram_gateway"
        assert queued_run.metadata["session_id"] == payload["session_id"]

        session = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}")
        assert session.status_code == 200
        session_payload = session.json()
        assert any(event["role"] == "user" for event in session_payload["events"])
        assert any("youtube autoflow queued" in event["content"] for event in session_payload["events"])
        assert session_payload["metadata"]["latest_telegram_youtube_autoflow_run_id"] == run_id

        assert len(notifier.messages) == 1
        assert "status: accepted" in notifier.messages[0]["text"]
        assert run_id in notifier.messages[0]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_youtube_link_rejects_multiple_urls(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 1316,
                "message": {
                    "message_id": 89,
                    "text": "先处理 https://youtu.be/6yjJ7Prt-RI 再处理 https://youtu.be/dQw4w9WgXcQ",
                    "chat": {"id": 9711, "type": "private"},
                    "from": {"id": 9711, "username": "youtube-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is False
        assert payload["session_id"] is not None
        assert payload["metadata"]["source"] == "telegram_youtube_autoflow"
        assert payload["metadata"]["status"] == "rejected"
        assert payload["reason"] == "当前只支持每条消息提交 1 条 YouTube 链接。"

        worker_scheduler = getattr(telegram_client, "_worker_scheduler")
        assert worker_scheduler.list_queue() == []

        assert len(notifier.messages) == 1
        assert "status: rejected" in notifier.messages[0]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_youtube_reference_without_valid_url_is_rejected(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 1317,
                "message": {
                    "message_id": 90,
                    "text": "处理这个 youtu.be/6yjJ7Prt-RI",
                    "chat": {"id": 9712, "type": "private"},
                    "from": {"id": 9712, "username": "youtube-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is False
        assert payload["metadata"]["status"] == "rejected"
        assert payload["reason"] == "未找到合法的 YouTube URL。"

        worker_scheduler = getattr(telegram_client, "_worker_scheduler")
        assert worker_scheduler.list_queue() == []

        assert len(notifier.messages) == 1
        assert "未找到合法的 YouTube URL" in notifier.messages[0]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_non_youtube_url_continues_to_existing_agent_path(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('non-youtube-link-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1318,
            "message": {
                "message_id": 91,
                "text": "请看这个链接 https://example.com/docs",
                "chat": {"id": 9713, "type": "private"},
                "from": {"id": 9713, "username": "link-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    # Default chat now routes to worker queue
    assert payload.get("metadata", {}).get("routed_to") == "worker_queue"
    assert payload["metadata"].get("source") != "telegram_youtube_autoflow"


def test_telegram_butler_excel_audit_is_accepted_and_reports_background_success(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    excel_service = _StubExcelAuditService(mode="success")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    monkeypatch.setattr(api_dependencies, "get_excel_audit_service", lambda: excel_service)

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 1320,
                "message": {
                    "message_id": 93,
                    "text": "帮我核对 sales.xlsx 和 commission.xlsx 的提成差异",
                    "chat": {"id": 9715, "type": "private"},
                    "from": {"id": 9715, "username": "excel-user"},
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["reason"] == "butler routed to excel_audit (async)"
        assert payload["metadata"]["audit_id"] == "ea_test_001"
        assert payload["metadata"]["butler_task_type"] == "excel_audit"
        assert excel_service.created_requests
        assert excel_service.created_requests[0].source_files == ["sales.xlsx", "commission.xlsx"]
        assert excel_service.executed_audit_ids == ["ea_test_001"]

        assert len(notifier.messages) == 2
        assert "Excel 核对已受理" in notifier.messages[0]["text"]
        assert "ea_test_001" in notifier.messages[0]["text"]
        assert "Excel 核对完成" in notifier.messages[1]["text"]
        assert "任务号: ea_test_001" in notifier.messages[1]["text"]
        assert "/tmp/report.md" in notifier.messages[1]["text"]
        assert "/tmp/report.json" in notifier.messages[1]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_butler_excel_audit_reports_background_failure(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    excel_service = _StubExcelAuditService(mode="raise")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    monkeypatch.setattr(api_dependencies, "get_excel_audit_service", lambda: excel_service)

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 1321,
                "message": {
                    "message_id": 94,
                    "text": "请核对 report.xlsx",
                    "chat": {"id": 9716, "type": "private"},
                    "from": {"id": 9716, "username": "excel-user"},
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["metadata"]["audit_id"] == "ea_test_001"
        assert excel_service.executed_audit_ids == ["ea_test_001"]

        assert len(notifier.messages) == 2
        assert "Excel 核对已受理" in notifier.messages[0]["text"]
        assert "Excel 核对失败 (ea_test_001): simulated execute failure" == notifier.messages[1]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_non_excel_request_keeps_original_route_and_skips_excel_dispatch(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excel_service = _StubExcelAuditService(mode="success")
    monkeypatch.setattr(api_dependencies, "get_excel_audit_service", lambda: excel_service)
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('non-excel-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1322,
            "message": {
                "message_id": 95,
                "text": "普通聊天，不是表格任务",
                "chat": {"id": 9717, "type": "private"},
                "from": {"id": 9717, "username": "chat-user"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload.get("metadata", {}).get("routed_to") == "worker_queue"
    assert "audit_id" not in payload.get("metadata", {})
    assert excel_service.created_requests == []
    assert excel_service.executed_audit_ids == []


def test_telegram_short_affirmation_rewrites_followup_from_previous_assistant_question(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"import sys; print(sys.argv[-1])\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "true")

    openclaw_service = app.dependency_overrides[get_openclaw_compat_service]()
    session = openclaw_service.create_session(
        gateway_telegram.OpenClawSessionCreateRequest(
            channel="telegram",
            external_id="9714",
            title="Telegram 9714",
            metadata={"source": "test"},
        )
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=gateway_telegram.OpenClawSessionEventAppendRequest(
            role="assistant",
            content="今天还没有跑过视频字幕处理。需要我现在触发一次处理吗？",
            metadata={"source": "test"},
        ),
    )

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1319,
            "message": {
                "message_id": 92,
                "text": "好",
                "chat": {"id": 9714, "type": "private"},
                "from": {"id": 9714, "username": "confirm-user"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    # Default chat now routes to worker queue
    assert payload.get("metadata", {}).get("routed_to") == "worker_queue"
    run_id = payload.get("metadata", {}).get("run_id")
    assert run_id is not None

    # Verify the queued task has the context-resolved prompt
    scheduler = app.dependency_overrides[get_worker_scheduler_service]()
    queued_run = scheduler.get_run(run_id)
    assert queued_run is not None
    assert queued_run.payload["prompt"].startswith("请按我上一条确认，立即触发一次今天的视频字幕处理。")

def test_telegram_webhook_secret_token_guard(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "secret-123")
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2001,
            "message": {
                "message_id": 88,
                "text": "hello",
                "chat": {"id": 10086},
            },
        },
    )
    assert response.status_code == 401

    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('token-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    ok_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "secret-123"},
        json={
            "update_id": 2002,
            "message": {
                "message_id": 89,
                "text": "hello with secret",
                "chat": {"id": 10086},
            },
        },
    )
    assert ok_response.status_code == 200
    assert ok_response.json()["accepted"] is True


def test_telegram_webhook_secret_required_in_production(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", raising=False)
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2101,
            "message": {
                "message_id": 91,
                "text": "prod check",
                "chat": {"id": 10087},
            },
        },
    )
    assert response.status_code == 503


def test_telegram_webhook_replay_rejected(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('replay-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    payload = {
        "update_id": 2201,
        "message": {"message_id": 92, "text": "hello", "chat": {"id": 10088}},
    }
    first = telegram_client.post("/api/v1/gateway/telegram/webhook", json=payload)
    assert first.status_code == 200

    second = telegram_client.post("/api/v1/gateway/telegram/webhook", json=payload)
    assert second.status_code == 409


def test_telegram_webhook_rate_limit_rejected(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('rate-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    chat_id = 10089
    for i in range(1, 32):
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 2300 + i,
                "message": {"message_id": 100 + i, "text": f"load-{i}", "chat": {"id": chat_id}},
            },
        )
        if i <= 30:
            assert response.status_code == 200
        else:
            assert response.status_code == 429


def test_telegram_status_query_returns_magic_link(
    telegram_client: TestClient,
) -> None:
    panel_access = PanelAccessService(
        secret="tg-panel-secret",
        base_url="https://panel.example.com/api/v1/panel/view",
    )
    notifier = _StubTelegramNotifier()
    capability_registry = CapabilityProviderRegistry()
    capability_registry.register(_StubSkillProvider())
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3001,
                "message": {
                    "message_id": 90,
                    "text": "/status",
                    "chat": {"id": 9527},
                    "from": {"username": "alice"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        link = payload["metadata"]["magic_link_url"]
        assert link.startswith("https://panel.example.com/api/v1/panel/view?")
        token = parse_qs(urlparse(link).query)["token"][0]
        claims = panel_access.verify_token(token)
        assert claims.telegram_uid == "9527"

        assert len(notifier.status_events) == 1
        assert notifier.status_events[0]["chat_id"] == "9527"
        assert notifier.status_events[0]["magic_link_url"] == link
        assert "providers: 1" in notifier.status_events[0]["summary"]
        assert "skill_providers: 1" in notifier.status_events[0]["summary"]
    finally:
        app.dependency_overrides.pop(get_panel_access_service, None)
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_capability_provider_registry, None)


def test_telegram_location_query_includes_runtime_and_worker_summary(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    capability_registry = CapabilityProviderRegistry()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry
    monkeypatch.setattr(
        gateway_telegram,
        "get_runtime_identity",
        lambda: {
            "runtime_computer_name": "Linux VM",
            "runtime_host": "linux-vm.local",
            "runtime_host_short": "linux-vm",
            "runtime_platform": "Linux",
            "runtime_family": "linux",
            "runtime_display": "Linux VM (linux)",
            "runtime_fingerprint": "linux:linux-vm.local",
        },
    )

    try:
        registered = telegram_client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "linux-01",
                "worker_type": "linux",
                "name": "Linux Worker",
                "host": "linux-vm.local",
                "mode": "active",
                "role": "housekeeper",
                "capabilities": ["youtube_autoflow"],
            },
        )
        assert registered.status_code == 200

        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3002,
                "message": {
                    "message_id": 91,
                    "text": "在哪",
                    "chat": {"id": 9527, "type": "private"},
                    "from": {"id": 9527, "username": "alice"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None

        assert len(notifier.status_events) == 1
        summary = notifier.status_events[0]["summary"]
        assert "runtime: Linux VM (linux)" in summary
        assert "runtime_host: linux-vm.local" in summary
        assert "workers_online: 1" in summary
        assert "worker linux-01 | linux/active | linux-vm.local | ok" in summary
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_capability_provider_registry, None)


def test_telegram_worker_inventory_query_returns_inventory_card(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    capability_registry = CapabilityProviderRegistry()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry
    monkeypatch.setattr(
        gateway_telegram,
        "get_runtime_identity",
        lambda: {
            "runtime_computer_name": "Linux VM",
            "runtime_host": "linux-vm.local",
            "runtime_host_short": "linux-vm",
            "runtime_platform": "Linux",
            "runtime_family": "linux",
            "runtime_display": "Linux VM (linux)",
            "runtime_fingerprint": "linux:linux-vm.local",
        },
    )

    try:
        registered = telegram_client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "linux-01",
                "worker_type": "linux",
                "name": "Linux Worker",
                "host": "linux-vm.local",
                "mode": "active",
                "role": "housekeeper",
                "capabilities": ["content_kb_ingest"],
            },
        )
        assert registered.status_code == 200

        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3005,
                "message": {
                    "message_id": 94,
                    "text": "当前 worker 情况",
                    "chat": {"id": 9527, "type": "private"},
                    "from": {"id": 9527, "username": "alice"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["metadata"]["worker_count"] == 1

        assert len(notifier.status_events) == 1
        summary = notifier.status_events[0]["summary"]
        assert "当前 Worker 概况" in summary
        assert "共 1 个 worker" in summary
        assert "linux-01：online" in summary
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_capability_provider_registry, None)


def test_telegram_runtime_switch_sends_notification(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    capability_registry = CapabilityProviderRegistry()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry

    try:
        monkeypatch.setattr(
            gateway_telegram,
            "get_runtime_identity",
            lambda: {
                "runtime_computer_name": "Mac Mini",
                "runtime_host": "mac-mini.local",
                "runtime_host_short": "mac-mini",
                "runtime_platform": "Darwin",
                "runtime_family": "mac",
                "runtime_display": "Mac Mini (mac)",
                "runtime_fingerprint": "mac:mac-mini.local",
            },
        )
        first = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3003,
                "message": {
                    "message_id": 92,
                    "text": "/memory 记住当前运行位置",
                    "chat": {"id": 9531, "type": "private"},
                    "from": {"id": 9531, "username": "runtime-user"},
                },
            },
        )
        assert first.status_code == 200
        first_payload = first.json()

        monkeypatch.setattr(
            gateway_telegram,
            "get_runtime_identity",
            lambda: {
                "runtime_computer_name": "Linux VM",
                "runtime_host": "linux-vm.local",
                "runtime_host_short": "linux-vm",
                "runtime_platform": "Linux",
                "runtime_family": "linux",
                "runtime_display": "Linux VM (linux)",
                "runtime_fingerprint": "linux:linux-vm.local",
            },
        )
        second = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3004,
                "message": {
                    "message_id": 93,
                    "text": "/status",
                    "chat": {"id": 9531, "type": "private"},
                    "from": {"id": 9531, "username": "runtime-user"},
                },
            },
        )
        assert second.status_code == 200
        assert any("执行环境已切换" in item["text"] for item in notifier.messages)

        session = telegram_client.get(f"/api/v1/openclaw/sessions/{first_payload['session_id']}")
        assert session.status_code == 200
        session_payload = session.json()
        assert session_payload["metadata"]["runtime_display"] == "Linux VM (linux)"
        assert session_payload["metadata"]["runtime_previous_display"] == "Mac Mini (mac)"
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_capability_provider_registry, None)


def test_telegram_skills_command_returns_catalog_and_detail(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    capability_registry = CapabilityProviderRegistry()
    capability_registry.register(_StubSkillProvider())
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry

    try:
        catalog_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3101,
                "message": {
                    "message_id": 101,
                    "text": "/skills",
                    "chat": {"id": 9530, "type": "private"},
                    "from": {"id": 9530, "username": "skill-user"},
                },
            },
        )
        assert catalog_response.status_code == 200
        assert catalog_response.json()["accepted"] is True
        assert catalog_response.json()["agent_run_id"] is None
        assert catalog_response.json()["metadata"]["skill_count"] == 1

        detail_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3102,
                "message": {
                    "message_id": 102,
                    "text": "/skills daily_brief",
                    "chat": {"id": 9530, "type": "private"},
                    "from": {"id": 9530, "username": "skill-user"},
                },
            },
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["accepted"] is True
        assert detail_response.json()["metadata"]["skill_query"] == "daily_brief"

        assert len(notifier.messages) == 2
        assert "[Skills]" in notifier.messages[0]["text"]
        assert "daily_brief | Daily Brief" in notifier.messages[0]["text"]
        assert "[Skill Detail]" in notifier.messages[1]["text"]
        assert "Use this skill." in notifier.messages[1]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_capability_provider_registry, None)


def test_telegram_help_command_returns_available_commands(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3151,
                "message": {
                    "message_id": 150,
                    "text": "/help",
                    "chat": {"id": 9534, "type": "private"},
                    "from": {"id": 9534, "username": "help-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        assert payload["metadata"]["source"] == "telegram_help"

        assert len(notifier.messages) == 1
        help_text = notifier.messages[0]["text"]
        assert "[Telegram Commands]" in help_text
        assert "/status" in help_text
        assert "/task <需求>" in help_text
        assert "/task --approve <需求>" in help_text
        assert "/approve <approval_id> approve" in help_text
        assert "/memory <内容>" in help_text
        assert "/mode shared" in help_text
        assert "/help" in help_text
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_start_command_returns_available_commands(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3152,
                "message": {
                    "message_id": 151,
                    "text": "/start",
                    "chat": {"id": 9535, "type": "private"},
                    "from": {"id": 9535, "username": "start-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        assert payload["metadata"]["source"] == "telegram_help"

        assert len(notifier.messages) == 1
        help_text = notifier.messages[0]["text"]
        assert "[Telegram Commands]" in help_text
        assert "/start 查看欢迎信息和命令列表" in help_text
        assert "/status" in help_text
        assert "/help" in help_text
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_task_issue_dispatches_manager_and_queues_issue_reply_approval(
    telegram_client: TestClient,
    tmp_path: Path,
) -> None:
    notifier = _StubTelegramNotifier()
    github_issue_service = _StubGitHubIssueService()
    manager_service = _build_manager_service(tmp_path / "manager.sqlite3")
    approval_service = getattr(telegram_client, "_approval_store")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_github_issue_service] = lambda: github_issue_service
    app.dependency_overrides[get_manager_agent_service] = lambda: manager_service

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3161,
                "message": {
                    "message_id": 154,
                    "text": "/task issue owner/repo#123 优先检查 Telegram 审批回路",
                    "chat": {"id": 9537, "type": "private"},
                    "from": {"id": 9537, "username": "task-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        assert payload["metadata"]["source"] == "telegram_manager_task"
        assert payload["metadata"]["task_source"] == "issue"
        assert payload["metadata"]["dispatch_id"]
        assert payload["metadata"]["issue_reference"] == "owner/repo#123"

        dispatch = manager_service.get_dispatch(payload["metadata"]["dispatch_id"])
        assert dispatch is not None
        assert dispatch.status.value == "completed"
        assert dispatch.run_summary is not None
        assert dispatch.run_summary.promotion is not None
        assert dispatch.run_summary.promotion.pr_url

        approvals = approval_service.list_requests(telegram_uid="9537", limit=10)
        assert len(approvals) == 1
        approval = approvals[0]
        assert approval.metadata["action_type"] == "github_issue_comment"
        assert approval.metadata["issue_reference"] == "owner/repo#123"
        assert "Automated progress update" in approval.metadata["comment_body"]

        assert len(notifier.messages) >= 3
        assert any("已接收，开始拆解并执行" in item["text"] for item in notifier.messages)
        assert any("draft_pr:" in item["text"] for item in notifier.messages)
        assert any("[GitHub Reply Pending]" in item["text"] for item in notifier.messages)
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_github_issue_service, None)
        app.dependency_overrides.pop(get_manager_agent_service, None)


def test_telegram_task_approve_flag_grants_owner_dispatch_context(
    telegram_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    manager_service = _build_manager_service(tmp_path / "manager-approve-flag.sqlite3")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_manager_agent_service] = lambda: manager_service
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_OWNER_UIDS", "9541")

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3164,
                "message": {
                    "message_id": 157,
                    "text": "/task --approve 为美妆品牌玛露开发 6g 遮瑕膏落地页",
                    "chat": {"id": 9541, "type": "private"},
                    "from": {"id": 9541, "username": "owner-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        dispatch = manager_service.get_dispatch(payload["metadata"]["dispatch_id"])

        assert dispatch is not None
        backend_task = dispatch.execution_plan.tasks[0]
        assert backend_task.worker_spec is not None
        assert backend_task.agent_job is not None
        assert backend_task.worker_spec.metadata["approval_granted"] is True
        assert backend_task.agent_job.metadata["approval_granted"] is True
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_manager_agent_service, None)


def test_telegram_task_approve_flag_is_ignored_for_non_admin_user(
    telegram_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifier = _StubTelegramNotifier()
    manager_service = _build_manager_service(tmp_path / "manager-non-admin-approve.sqlite3")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_manager_agent_service] = lambda: manager_service
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9542")

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3165,
                "message": {
                    "message_id": 158,
                    "text": "/task --approve 为美妆品牌玛露开发 6g 遮瑕膏落地页",
                    "chat": {"id": 9542, "type": "private"},
                    "from": {"id": 9542, "username": "member-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        dispatch = manager_service.get_dispatch(payload["metadata"]["dispatch_id"])

        assert dispatch is not None
        backend_task = dispatch.execution_plan.tasks[0]
        assert backend_task.worker_spec is not None
        assert backend_task.agent_job is not None
        assert backend_task.worker_spec.metadata["approval_granted"] is False
        assert backend_task.agent_job.metadata["approval_granted"] is False
        assert any("仅对 owner/partner 生效" in item["text"] for item in notifier.messages)
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_manager_agent_service, None)


def test_telegram_approve_command_posts_github_issue_reply_for_issue_tasks(
    telegram_client: TestClient,
    tmp_path: Path,
) -> None:
    notifier = _StubTelegramNotifier()
    github_issue_service = _StubGitHubIssueService()
    manager_service = _build_manager_service(tmp_path / "manager-approve.sqlite3")
    approval_service = getattr(telegram_client, "_approval_store")
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    app.dependency_overrides[get_github_issue_service] = lambda: github_issue_service
    app.dependency_overrides[get_manager_agent_service] = lambda: manager_service

    try:
        task_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3162,
                "message": {
                    "message_id": 155,
                    "text": "/task issue #123 带上修复摘要",
                    "chat": {"id": 9538, "type": "private"},
                    "from": {"id": 9538, "username": "task-user"},
                },
            },
        )
        assert task_response.status_code == 200
        approvals = approval_service.list_requests(telegram_uid="9538", limit=10)
        assert len(approvals) == 1
        approval = approvals[0]

        approve_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3163,
                "message": {
                    "message_id": 156,
                    "text": f"/approve {approval.approval_id} approve 发出去",
                    "chat": {"id": 9538, "type": "private"},
                    "from": {"id": 9538, "username": "task-user"},
                },
            },
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["accepted"] is True

        resolved = approval_service.get_request(approval.approval_id)
        assert resolved is not None
        assert resolved.status.value == "approved"
        assert resolved.metadata["comment_posted"] is True
        assert github_issue_service.comments[0]["issue_reference"] == "owner/repo#123"
        assert "Automated progress update" in github_issue_service.comments[0]["body"]
        assert any("[GitHub Reply Posted]" in item["text"] for item in notifier.messages)
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
        app.dependency_overrides.pop(get_github_issue_service, None)
        app.dependency_overrides.pop(get_manager_agent_service, None)


def test_telegram_approve_command_lists_and_reads_pending_approvals(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    approval_service = getattr(telegram_client, "_approval_store")
    approval = approval_service.create_request(
        ApprovalRequestCreateRequest(
            title="Approve branch promotion",
            summary="Review and promote branch after regression",
            source="git_policy",
            telegram_uid="9535",
            session_id="oc_approve_session",
            agent_run_id="run_approve_1",
        )
    )
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        list_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3171,
                "message": {
                    "message_id": 151,
                    "text": "/approve",
                    "chat": {"id": 9535, "type": "private"},
                    "from": {"id": 9535, "username": "approve-user"},
                },
            },
        )
        assert list_response.status_code == 200
        assert list_response.json()["accepted"] is True
        assert list_response.json()["metadata"]["source"] == "telegram_approve_query"

        detail_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3172,
                "message": {
                    "message_id": 152,
                    "text": f"/approve {approval.approval_id}",
                    "chat": {"id": 9535, "type": "private"},
                    "from": {"id": 9535, "username": "approve-user"},
                },
            },
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["accepted"] is True
        assert detail_response.json()["metadata"]["approval_id"] == approval.approval_id

        assert len(notifier.messages) == 2
        assert "[Pending Approvals]" in notifier.messages[0]["text"]
        assert approval.approval_id in notifier.messages[0]["text"]
        assert "[Approval Detail]" in notifier.messages[1]["text"]
        assert "Approve branch promotion" in notifier.messages[1]["text"]
        assert f"/approve {approval.approval_id} approve" in notifier.messages[1]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_approve_command_can_resolve_pending_approval(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    approval_service = getattr(telegram_client, "_approval_store")
    approval = approval_service.create_request(
        ApprovalRequestCreateRequest(
            title="Approve signed skill update",
            summary="Promote signed skill after audit",
            source="skill_registry",
            telegram_uid="9536",
            session_id="oc_approve_session_resolve",
            agent_run_id="run_approve_2",
        )
    )
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        approve_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3173,
                "message": {
                    "message_id": 153,
                    "text": f"/approve {approval.approval_id} approve looks good",
                    "chat": {"id": 9536, "type": "private"},
                    "from": {"id": 9536, "username": "approve-user"},
                },
            },
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        assert approve_payload["accepted"] is True
        assert approve_payload["metadata"]["source"] == "telegram_approve_decision"
        assert approve_payload["metadata"]["approval_id"] == approval.approval_id
        assert approve_payload["metadata"]["decision"] == "approve"

        resolved = approval_service.get_request(approval.approval_id)
        assert resolved is not None
        assert resolved.status.value == "approved"
        assert resolved.decided_by == "9536"
        assert resolved.decision_note == "looks good"
        assert resolved.metadata["resolved_via"] == "telegram_command"

        assert len(notifier.messages) == 1
        assert "[Approval Decision]" in notifier.messages[0]["text"]
        assert "status: approved" in notifier.messages[0]["text"]
        assert "note: looks good" in notifier.messages[0]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_reset_command_rotates_active_session(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('after-reset-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        first = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3201,
                "message": {
                    "message_id": 103,
                    "text": "first task",
                    "chat": {"id": 9531, "type": "private"},
                    "from": {"id": 9531, "username": "reset-user"},
                },
            },
        )
        assert first.status_code == 200
        first_session_id = first.json()["session_id"]

        reset = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3202,
                "message": {
                    "message_id": 104,
                    "text": "/reset",
                    "chat": {"id": 9531, "type": "private"},
                    "from": {"id": 9531, "username": "reset-user"},
                },
            },
        )
        assert reset.status_code == 200
        reset_payload = reset.json()
        assert reset_payload["accepted"] is True
        assert reset_payload["agent_run_id"] is None
        assert reset_payload["session_id"] != first_session_id
        assert reset_payload["metadata"]["previous_session_id"] == first_session_id

        second = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3203,
                "message": {
                    "message_id": 105,
                    "text": "second task",
                    "chat": {"id": 9531, "type": "private"},
                    "from": {"id": 9531, "username": "reset-user"},
                },
            },
        )
        assert second.status_code == 200
        assert second.json()["session_id"] == reset_payload["session_id"]

        sessions = telegram_client.get("/api/v1/openclaw/sessions")
        assert sessions.status_code == 200
        payload = sessions.json()
        archived = next(item for item in payload if item["session_id"] == first_session_id)
        current = next(item for item in payload if item["session_id"] == reset_payload["session_id"])
        assert archived["status"] == "interrupted"
        assert "#archived:" in archived["session_key"]
        assert current["session_key"] == "telegram:personal:user:9531"

        assert any("会话已重置" in item["text"] for item in notifier.messages)
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_mode_command_switches_private_chat_to_shared_scope(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('shared-mode-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        mode_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3301,
                "message": {
                    "message_id": 106,
                    "text": "/mode shared",
                    "chat": {"id": 9532, "type": "private"},
                    "from": {"id": 9532, "username": "mode-user"},
                },
            },
        )
        assert mode_response.status_code == 200
        mode_payload = mode_response.json()
        assert mode_payload["accepted"] is True
        assert mode_payload["agent_run_id"] is None
        assert mode_payload["metadata"]["scope"] == "shared"

        status_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3302,
                "message": {
                    "message_id": 107,
                    "text": "/mode",
                    "chat": {"id": 9532, "type": "private"},
                    "from": {"id": 9532, "username": "mode-user"},
                },
            },
        )
        assert status_response.status_code == 200
        assert status_response.json()["metadata"]["scope"] == "shared"

        message_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3303,
                "message": {
                    "message_id": 108,
                    "text": "shared follow-up",
                    "chat": {"id": 9532, "type": "private"},
                    "from": {"id": 9532, "username": "mode-user"},
                },
            },
        )
        assert message_response.status_code == 200
        assert message_response.json()["session_id"] == mode_payload["session_id"]

        session = telegram_client.get(f"/api/v1/openclaw/sessions/{mode_payload['session_id']}")
        assert session.status_code == 200
        session_payload = session.json()
        assert session_payload["scope"] == "shared"
        assert session_payload["session_key"] == "telegram:shared:chat:9532"
        assert session_payload["metadata"]["telegram_mode_preference"] == "shared"

        assert any("模式已切换到 shared" in item["text"] for item in notifier.messages)
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


def test_telegram_reset_preserves_mode_preference_for_followup_messages(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('shared-after-reset-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    mode_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 3401,
            "message": {
                "message_id": 109,
                "text": "/mode shared",
                "chat": {"id": 9533, "type": "private"},
                "from": {"id": 9533, "username": "mode-reset-user"},
            },
        },
    )
    assert mode_response.status_code == 200
    mode_payload = mode_response.json()
    assert mode_payload["metadata"]["scope"] == "shared"

    reset_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 3402,
            "message": {
                "message_id": 110,
                "text": "/reset",
                "chat": {"id": 9533, "type": "private"},
                "from": {"id": 9533, "username": "mode-reset-user"},
            },
        },
    )
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert reset_payload["metadata"]["scope"] == "shared"
    assert reset_payload["session_id"] != mode_payload["session_id"]

    followup_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 3403,
            "message": {
                "message_id": 111,
                "text": "shared after reset",
                "chat": {"id": 9533, "type": "private"},
                "from": {"id": 9533, "username": "mode-reset-user"},
            },
        },
    )
    assert followup_response.status_code == 200
    assert followup_response.json()["session_id"] == reset_payload["session_id"]

    current_session = telegram_client.get(f"/api/v1/openclaw/sessions/{reset_payload['session_id']}")
    assert current_session.status_code == 200
    current_payload = current_session.json()
    assert current_payload["scope"] == "shared"
    assert current_payload["metadata"]["telegram_mode_preference"] == "shared"


def test_telegram_queue_ack_message_includes_table_and_status_hint() -> None:
    from autoresearch.api.routers import gateway_telegram as gt

    text = gt._telegram_queue_ack_message(
        task_name="tg_6421432917_48",
        run_id="run_0b88e9edbe3e",
        worker_brand="初代worker",
    )
    assert "收到" in text
    assert "tg_6421432917_48" in text
    assert "run_0b88e9edbe3e" in text
    assert "/status" in text
    assert "| 项 | 值 |" in text


def test_telegram_two_column_table_escapes_pipes() -> None:
    from autoresearch.api.routers import gateway_telegram as gt

    lines = gt._telegram_two_column_table([("a|b", "c|d")])
    joined = "\n".join(lines)
    assert "a/b" in joined
    assert "c/d" in joined


def test_telegram_webhook_sends_queue_notice_with_table(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('queue-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 19001,
                "message": {
                    "message_id": 501,
                    "text": "queue notice formatting",
                    "chat": {"id": 777001, "type": "private"},
                    "from": {"id": 777001, "username": "queue-user"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload.get("metadata", {}).get("routed_to") == "worker_queue"
        run_id = payload.get("metadata", {}).get("run_id")
        assert run_id
        assert notifier.messages, "queue path should notify user"
        body = notifier.messages[-1]["text"]
        assert "收到" in body
        assert "| 项 | 值 |" in body
        assert str(run_id) in body
        assert "/status" in body
        assert notifier.sent_message_ids
        stored = telegram_client._worker_scheduler.get_run(str(run_id))
        assert stored is not None
        assert stored.metadata.get("telegram_queue_ack_message_id") == notifier.sent_message_ids[-1]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
