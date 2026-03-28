from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_openclaw_compat_service, get_openclaw_memory_service
from autoresearch.api.main import app
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.shared.models import OpenClawMemoryRecordRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def openclaw_memory_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "openclaw-memory.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_memory_it",
            model_cls=OpenClawSessionRead,
        )
    )
    memory_service = OpenClawMemoryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_memories_it",
            model_cls=OpenClawMemoryRecordRead,
        ),
        openclaw_service=openclaw_service,
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_openclaw_memory_service] = lambda: memory_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_memory_endpoint_defaults_to_personal_scope_for_personal_session(
    openclaw_memory_client: TestClient,
) -> None:
    created = openclaw_memory_client.post(
        "/api/v1/openclaw/sessions",
        json={
            "channel": "telegram",
            "external_id": "42",
            "title": "personal-memory",
            "scope": "personal",
            "session_key": "telegram:personal:user:42",
            "assistant_id": "telegram-user:42",
            "actor": {"user_id": "42", "username": "alice", "role": "owner"},
            "chat_context": {"chat_id": "42", "chat_type": "private", "user_id": "42"},
            "metadata": {},
        },
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    remembered = openclaw_memory_client.post(
        f"/api/v1/openclaw/sessions/{session_id}/memory",
        json={"content": "用户偏好：周报只看结论"},
    )
    assert remembered.status_code == 201
    payload = remembered.json()
    assert payload["scope"] == "personal"
    assert payload["actor_user_id"] == "42"

    bundle = openclaw_memory_client.get(f"/api/v1/openclaw/sessions/{session_id}/memory")
    assert bundle.status_code == 200
    assert bundle.json()["personal_memories"][0]["content"] == "用户偏好：周报只看结论"


def test_memory_bundle_returns_shared_long_term_for_shared_session(
    openclaw_memory_client: TestClient,
) -> None:
    created = openclaw_memory_client.post(
        "/api/v1/openclaw/sessions",
        json={
            "channel": "telegram",
            "external_id": "-10001",
            "title": "shared-memory",
            "scope": "shared",
            "session_key": "telegram:shared:chat:-10001",
            "assistant_id": "household-main",
            "actor": {"user_id": "99", "username": "lisa", "role": "partner"},
            "chat_context": {"chat_id": "-10001", "chat_type": "supergroup", "user_id": "99"},
            "metadata": {},
        },
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    event = openclaw_memory_client.post(
        f"/api/v1/openclaw/sessions/{session_id}/events",
        json={"role": "user", "content": "周日晚上一起整理旅行清单", "metadata": {}},
    )
    assert event.status_code == 200

    remembered = openclaw_memory_client.post(
        f"/api/v1/openclaw/sessions/{session_id}/memory",
        json={"content": "共享偏好：旅行清单统一放在 shared assistant", "tags": ["travel", "shared"]},
    )
    assert remembered.status_code == 201
    assert remembered.json()["scope"] == "shared"
    assert remembered.json()["assistant_id"] == "household-main"

    bundle = openclaw_memory_client.get(f"/api/v1/openclaw/sessions/{session_id}/memory")
    assert bundle.status_code == 200
    payload = bundle.json()
    assert payload["session_scope"] == "shared"
    assert len(payload["session_events"]) == 1
    assert payload["shared_memories"][0]["content"] == "共享偏好：旅行清单统一放在 shared assistant"
