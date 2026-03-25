from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_claude_agent_service, get_openclaw_compat_service
from autoresearch.api.main import app
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import ClaudeAgentRunRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


def test_openclaw_session_and_claude_agent_scheduler(tmp_path: Path) -> None:
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

    try:
        with TestClient(app) as client:
            created_session = client.post(
                "/api/v1/openclaw/sessions",
                json={
                    "channel": "telegram",
                    "title": "compat-smoke",
                    "metadata": {"source": "test"},
                },
            )
            assert created_session.status_code == 201
            session_id = created_session.json()["session_id"]

            spawned = client.post(
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

            finalized = None
            for _ in range(20):
                fetched = client.get(f"/api/v1/openclaw/agents/{agent_run_id}")
                assert fetched.status_code == 200
                finalized = fetched.json()
                if finalized["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.05)

            assert finalized is not None
            assert finalized["status"] == "completed"
            assert "claude-subagent-ok" in (finalized.get("stdout_preview") or "")

            session = client.get(f"/api/v1/openclaw/sessions/{session_id}")
            assert session.status_code == 200
            events = session.json()["events"]
            assert len(events) >= 2
            assert any("agent queued" in event["content"] for event in events)
            assert any("agent completed" in event["content"] for event in events)
    finally:
        app.dependency_overrides.clear()
