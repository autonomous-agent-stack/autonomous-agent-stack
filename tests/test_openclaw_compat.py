from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_claude_agent_service, get_openclaw_compat_service
from autoresearch.api.main import app
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import ClaudeAgentCreateRequest, ClaudeAgentRunRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def openclaw_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "openclaw.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service

    with TestClient(app) as client:
        setattr(client, "_claude_service", claude_service)
        yield client

    app.dependency_overrides.clear()


def _create_session(client: TestClient, title: str) -> str:
    created_session = client.post(
        "/api/v1/openclaw/sessions",
        json={
            "channel": "telegram",
            "title": title,
            "metadata": {"source": "test"},
        },
    )
    assert created_session.status_code == 201
    return created_session.json()["session_id"]


def _wait_terminal(client: TestClient, agent_run_id: str, attempts: int = 40) -> dict[str, object]:
    finalized: dict[str, object] | None = None
    for _ in range(attempts):
        fetched = client.get(f"/api/v1/openclaw/agents/{agent_run_id}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed", "interrupted", "cancelled"}:
            break
        time.sleep(0.05)
    assert finalized is not None
    return finalized


def test_openclaw_session_and_claude_agent_scheduler(openclaw_client: TestClient) -> None:
    session_id = _create_session(openclaw_client, title="compat-smoke")

    spawned = openclaw_client.post(
        "/api/v1/openclaw/agents",
        json={
            "task_name": "claude-subagent-smoke",
            "prompt": "say hello",
            "session_id": session_id,
            "generation_depth": 1,
            "timeout_seconds": 5,
            "command_override": [sys.executable, "-c", "print('claude-subagent-ok')"],
            "append_prompt": False,
        },
    )
    assert spawned.status_code == 202
    agent_run_id = spawned.json()["agent_run_id"]
    assert spawned.json()["status"] == "queued"

    finalized = _wait_terminal(openclaw_client, agent_run_id, attempts=20)
    assert finalized["status"] == "completed"
    assert "claude-subagent-ok" in (finalized.get("stdout_preview") or "")

    session = openclaw_client.get(f"/api/v1/openclaw/sessions/{session_id}")
    assert session.status_code == 200
    events = session.json()["events"]
    assert len(events) >= 2
    assert any("agent queued" in event["content"] for event in events)
    assert any("agent completed" in event["content"] for event in events)


def test_openclaw_cancel_agent(openclaw_client: TestClient) -> None:
    session_id = _create_session(openclaw_client, title="cancel-smoke")
    claude_service = getattr(openclaw_client, "_claude_service")
    request_payload = ClaudeAgentCreateRequest(
        task_name="long-running-agent",
        prompt="long run",
        session_id=session_id,
        generation_depth=1,
        timeout_seconds=20,
        command_override=[sys.executable, "-c", "import time; time.sleep(3); print('late-output')"],
        append_prompt=False,
    )
    created = claude_service.create(request_payload)
    worker = threading.Thread(
        target=claude_service.execute,
        args=(created.agent_run_id, request_payload),
        daemon=True,
    )
    worker.start()
    time.sleep(0.1)

    cancelled = openclaw_client.post(
        f"/api/v1/openclaw/agents/{created.agent_run_id}/cancel",
        json={"reason": "manual-stop"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    worker.join(timeout=5)

    finalized = _wait_terminal(openclaw_client, created.agent_run_id)
    assert finalized["status"] == "cancelled"
    assert finalized["error"] == "manual-stop"


def test_openclaw_retry_and_tree_view(openclaw_client: TestClient) -> None:
    session_id = _create_session(openclaw_client, title="retry-tree-smoke")

    spawned = openclaw_client.post(
        "/api/v1/openclaw/agents",
        json={
            "task_name": "fail-agent",
            "prompt": "fail it",
            "session_id": session_id,
            "generation_depth": 1,
            "timeout_seconds": 10,
            "command_override": [sys.executable, "-c", "import sys; print('first-fail'); sys.exit(2)"],
            "append_prompt": False,
        },
    )
    assert spawned.status_code == 202
    failed_run_id = spawned.json()["agent_run_id"]

    first_final = _wait_terminal(openclaw_client, failed_run_id, attempts=25)
    assert first_final["status"] == "failed"

    retried = openclaw_client.post(
        f"/api/v1/openclaw/agents/{failed_run_id}/retry",
        json={
            "reason": "try-again",
            "metadata_updates": {"from_test": True},
        },
    )
    assert retried.status_code == 202
    retry_run_id = retried.json()["agent_run_id"]
    assert retry_run_id != failed_run_id

    retry_final = _wait_terminal(openclaw_client, retry_run_id, attempts=25)
    assert retry_final["status"] in {"failed", "completed", "interrupted", "cancelled"}
    assert retry_final["parent_agent_id"] == failed_run_id

    tree = openclaw_client.get("/api/v1/openclaw/agents/tree", params={"session_id": session_id})
    assert tree.status_code == 200
    tree_payload = tree.json()
    edge_pairs = {
        (edge["parent_agent_run_id"], edge["child_agent_run_id"])
        for edge in tree_payload["edges"]
    }
    assert (failed_run_id, retry_run_id) in edge_pairs
    assert "graph TD" in tree_payload["mermaid"]
