from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_claude_agent_service,
    get_openclaw_compat_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    ClaudeAgentRunRead,
    OpenClawSessionRead,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def admin_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "admin.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_admin_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_admin_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )
    admin_service = AdminConfigService(
        agent_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_agent_configs_it",
            model_cls=AdminAgentConfigRead,
        ),
        channel_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_channel_configs_it",
            model_cls=AdminChannelConfigRead,
        ),
        revision_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_config_revisions_it",
            model_cls=AdminConfigRevisionRead,
        ),
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_admin_config_service] = lambda: admin_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def _wait_terminal(client: TestClient, agent_run_id: str, attempts: int = 40) -> dict[str, object]:
    finalized: dict[str, object] | None = None
    for _ in range(attempts):
        fetched = client.get(f"/api/v1/openclaw/agents/{agent_run_id}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed", "interrupted"}:
            break
        time.sleep(0.05)
    assert finalized is not None
    return finalized


def test_admin_agent_crud_history_rollback(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/agents",
        json={
            "name": "writer",
            "description": "copy writer",
            "task_name": "write-copy",
            "prompt_template": "Write concise ad copy",
            "default_timeout_seconds": 60,
            "default_generation_depth": 1,
            "default_env": {"A": "1"},
            "channel_bindings": ["telegram"],
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    agent_id = payload["agent_id"]
    assert payload["version"] == 1
    assert payload["status"] == "active"

    updated = admin_client.put(
        f"/api/v1/admin/agents/{agent_id}",
        json={
            "description": "copy writer v2",
            "metadata_updates": {"team": "growth"},
            "actor": "test-admin",
            "reason": "tune copy style",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["description"] == "copy writer v2"
    assert updated.json()["metadata"]["team"] == "growth"

    deactivated = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/deactivate",
        json={"actor": "test-admin", "reason": "maintenance"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["version"] == 3

    rolled = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/rollback",
        json={"version": 1, "actor": "test-admin", "reason": "restore baseline"},
    )
    assert rolled.status_code == 200
    assert rolled.json()["version"] == 4
    assert rolled.json()["status"] == "active"
    assert rolled.json()["description"] == "copy writer"

    history = admin_client.get(f"/api/v1/admin/agents/{agent_id}/history")
    assert history.status_code == 200
    actions = [item["action"] for item in history.json()]
    assert "create" in actions
    assert "update" in actions
    assert "deactivate" in actions
    assert "rollback" in actions


def test_admin_agent_launch_from_config(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/agents",
        json={
            "name": "runner",
            "task_name": "run-task",
            "prompt_template": "execute",
            "default_timeout_seconds": 20,
            "default_generation_depth": 1,
            "command_override": [sys.executable, "-c", "print('admin-run-ok')"],
            "append_prompt": False,
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    agent_id = created.json()["agent_id"]

    launched = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/launch",
        json={
            "metadata_updates": {"launch_source": "test"},
            "env_overrides": {"TEST_ENV": "1"},
        },
    )
    assert launched.status_code == 202
    launch_payload = launched.json()
    assert launch_payload["status"] == "queued"
    assert launch_payload["metadata"]["agent_config_id"] == agent_id

    finalized = _wait_terminal(admin_client, launch_payload["agent_run_id"], attempts=30)
    assert finalized["status"] == "completed"
    assert "admin-run-ok" in (finalized.get("stdout_preview") or "")


def test_admin_channel_crud_and_duplicate_key_guard(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/channels",
        json={
            "key": "telegram-main",
            "display_name": "Telegram Main",
            "provider": "telegram",
            "allowed_chat_ids": ["-10001"],
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    channel_id = created.json()["channel_id"]
    assert created.json()["version"] == 1

    duplicate = admin_client.post(
        "/api/v1/admin/channels",
        json={
            "key": "telegram-main",
            "display_name": "Telegram Backup",
            "provider": "telegram",
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert duplicate.status_code == 400
    assert "duplicate channel key" in duplicate.json()["detail"]

    updated = admin_client.put(
        f"/api/v1/admin/channels/{channel_id}",
        json={
            "display_name": "Telegram Main Updated",
            "allowed_user_ids": ["10086"],
            "metadata_updates": {"region": "cn"},
            "actor": "test-admin",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["display_name"] == "Telegram Main Updated"

    deactivated = admin_client.post(
        f"/api/v1/admin/channels/{channel_id}/deactivate",
        json={"actor": "test-admin"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["version"] == 3

    history = admin_client.get(f"/api/v1/admin/channels/{channel_id}/history")
    assert history.status_code == 200
    versions = sorted(item["version"] for item in history.json())
    assert versions == [1, 2, 3]
