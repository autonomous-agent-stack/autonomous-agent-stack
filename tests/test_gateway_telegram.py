from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_approval_store_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_openclaw_memory_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_telegram_notifier_service,
    get_worker_orchestrator_service,
)
from autoresearch.api.main import app
from autoresearch.api.routers import gateway_telegram
from autoresearch.core.adapters import CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import CapabilityDomain, SkillCatalogRead
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_controlled_backend import AutoResearchControlledBackendService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openhands_controlled_backend import OpenHandsControlledBackendService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.worker_orchestrator import WorkerOrchestratorService
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    ClaudeAgentRunRead,
    ApprovalRequestRead,
    ApprovalRequestCreateRequest,
    OpenClawMemoryRecordRead,
    OpenClawSessionRead,
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
    ) -> bool:
        self.messages.append({"chat_id": chat_id, "text": text})
        return True

    def notify_manual_action(self, *, chat_id: str, entry: object, run_status: str) -> bool:
        return True


@pytest.fixture
def telegram_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "telegram-gateway.sqlite3"
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
    approval_service = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_gateway_it",
            model_cls=ApprovalRequestRead,
        )
    )
    worker_orchestrator = WorkerOrchestratorService(
        agent_service=claude_service,
        approval_service=approval_service,
        openhands_backend=OpenHandsControlledBackendService(repo_root=tmp_path, run_root=tmp_path / "oh-runs"),
        autoresearch_backend=AutoResearchControlledBackendService(repo_root=tmp_path, run_root=tmp_path / "ar-runs"),
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_openclaw_memory_service] = lambda: memory_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_worker_orchestrator_service] = lambda: worker_orchestrator
    app.dependency_overrides[get_admin_config_service] = lambda: admin_config_service

    with TestClient(app) as client:
        setattr(client, "_approval_store", approval_service)
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_gateway_guards() -> None:
    gateway_telegram._SEEN_UPDATES.clear()
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
    assert payload["agent_run_id"] is not None

    finalized = None
    for _ in range(20):
        fetched = telegram_client.get(f"/api/v1/openclaw/agents/{payload['agent_run_id']}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert finalized is not None
    assert finalized["status"] == "completed"
    assert "tg-agent-ok" in (finalized.get("stdout_preview") or "")

    session = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}")
    assert session.status_code == 200
    session_payload = session.json()
    assert session_payload["external_id"] == "9527"
    assert session_payload["scope"] == "personal"
    assert session_payload["session_key"] == "telegram:personal:user:9527"
    assert session_payload["chat_context"]["chat_type"] == "private"
    assert any(event["role"] == "user" for event in session_payload["events"])
    assert any("agent queued" in event["content"] for event in session_payload["events"])


def test_legacy_telegram_webhook_uses_same_processing_path(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('tg-legacy-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/telegram/webhook",
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
    assert payload["agent_run_id"] is not None


def test_telegram_webhook_routes_code_fix_to_openhands_worker(
    telegram_client: TestClient,
) -> None:
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2010,
            "message": {
                "message_id": 88,
                "text": "请修复 src/demo_fix.py 里的 bug 并补测试",
                "chat": {"id": 9527, "type": "private"},
                "from": {"id": 9527, "username": "alice"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["agent_run_id"] is not None
    assert payload["metadata"]["worker_route"] == "openhands"
    assert payload["metadata"]["selected_worker"] == "openhands"

    finalized = None
    for _ in range(40):
        fetched = telegram_client.get(f"/api/v1/openclaw/agents/{payload['agent_run_id']}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert finalized is not None
    assert finalized["status"] == "completed"
    orchestration = finalized["metadata"]["orchestration"]
    assert orchestration["route"] == "openhands"
    assert orchestration["selected_worker"] == "openhands"
    assert orchestration["promotion_mode"] == "patch"
    assert "src/demo_fix.py" in orchestration["changed_files"]


def test_telegram_webhook_executes_autoresearch_then_openhands_chain(
    telegram_client: TestClient,
) -> None:
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2014,
            "message": {
                "message_id": 92,
                "text": "先分析 src/demo_fix.py 的问题，再修复这个 bug 并补测试",
                "chat": {"id": 9527, "type": "private"},
                "from": {"id": 9527, "username": "alice"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["metadata"]["worker_route"] == "autoresearch_then_openhands"
    assert payload["metadata"]["selected_worker"] == "autoresearch"

    finalized = None
    for _ in range(40):
        fetched = telegram_client.get(f"/api/v1/openclaw/agents/{payload['agent_run_id']}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert finalized is not None
    assert finalized["status"] == "completed"
    orchestration = finalized["metadata"]["orchestration"]
    assert orchestration["route"] == "autoresearch_then_openhands"
    assert orchestration["analysis_promotion_finalize_skipped"] is True
    assert orchestration["analysis_run_id"]
    assert orchestration["execution_run_id"]
    assert "execution_plan" in orchestration["analysis_deliverables"]


def test_telegram_webhook_creates_approval_for_high_risk_write(
    telegram_client: TestClient,
) -> None:
    approval_store = getattr(telegram_client, "_approval_store")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2011,
            "message": {
                "message_id": 89,
                "text": "请删除 src/demo_fix.py 并直接合并到 main",
                "chat": {"id": 9527, "type": "private"},
                "from": {"id": 9527, "username": "alice"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["agent_run_id"] is None
    assert payload["reason"] == "approval required before worker execution"
    assert payload["metadata"]["selected_worker"] == "openhands"
    approval_id = payload["metadata"]["approval_id"]

    approval = approval_store.get_request(approval_id)
    assert approval is not None
    assert approval.risk.value == "destructive"
    assert approval.metadata["orchestration"]["route"] == "openhands"
    assert approval.metadata["orchestration"]["requires_approval"] is True
    assert approval.metadata["orchestration"]["resume_state"] == "pending_approval"
    assert approval.metadata["worker_orchestration_replay"]["request"]["prompt"].startswith("请删除")


def test_telegram_approve_command_resumes_worker_after_orchestration_approval(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        pending_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 2012,
                "message": {
                    "message_id": 90,
                    "text": "请修复 src/demo_fix.py 并直接合并到 main",
                    "chat": {"id": 9527, "type": "private"},
                    "from": {"id": 9527, "username": "alice"},
                },
            },
        )
        assert pending_response.status_code == 200
        approval_id = pending_response.json()["metadata"]["approval_id"]

        approve_response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 2013,
                "message": {
                    "message_id": 91,
                    "text": f"/approve {approval_id} approve approved for execution",
                    "chat": {"id": 9527, "type": "private"},
                    "from": {"id": 9527, "username": "alice"},
                },
            },
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        resumed_agent_run_id = approve_payload["metadata"]["resumed_agent_run_id"]
        assert resumed_agent_run_id is not None

        finalized = None
        for _ in range(40):
            fetched = telegram_client.get(f"/api/v1/openclaw/agents/{resumed_agent_run_id}")
            assert fetched.status_code == 200
            finalized = fetched.json()
            if finalized["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)

        assert finalized is not None
        assert finalized["status"] == "completed"
        orchestration = finalized["metadata"]["orchestration"]
        assert orchestration["approval_id"] == approval_id
        assert orchestration["approval_status"] == "approved"
        assert orchestration["resume_state"] == "completed"

        assert len(notifier.messages) >= 3
        assert "高风险写操作" in notifier.messages[0]["text"]
        assert "[Approval Decision]" in notifier.messages[-2]["text"]
        assert "[Worker 结果]" in notifier.messages[-1]["text"]
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


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
        assert "/approve <approval_id> approve" in help_text
        assert "/memory <内容>" in help_text
        assert "/mode shared" in help_text
        assert "/help" in help_text
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)


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
