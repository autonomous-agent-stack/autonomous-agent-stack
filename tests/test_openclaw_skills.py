from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_openclaw_skill_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.shared.models import ClaudeAgentRunRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


def _write_skill(
    *,
    root_dir: Path,
    name: str,
    description: str,
    metadata_block: str,
    body: str,
) -> None:
    skill_dir = root_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f'description: "{description}"',
                f"metadata: {metadata_block}",
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


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


@pytest.fixture
def openclaw_skills_client(tmp_path: Path) -> TestClient:
    skills_root = tmp_path / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    _write_skill(
        root_dir=skills_root,
        name="weather",
        description="Weather checks for a city",
        metadata_block='{"openclaw":{"skillKey":"weather"}}',
        body="# Weather Skill\n\nUse curl wttr.in to check weather.",
    )
    _write_skill(
        root_dir=skills_root,
        name="voice-call",
        description="Start voice calls via plugin",
        metadata_block='{"openclaw":{"skillKey":"voice-call"}}',
        body="# Voice Call Skill\n\nUse voice call tool for outbound calls.",
    )

    db_path = tmp_path / "openclaw-skills.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_skills_it",
            model_cls=OpenClawSessionRead,
        )
    )
    skill_service = OpenClawSkillService(
        repo_root=tmp_path,
        skill_roots=[skills_root],
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_skills_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        openclaw_skill_service=skill_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_openclaw_skill_service] = lambda: skill_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_openclaw_skill_catalog_endpoints(openclaw_skills_client: TestClient) -> None:
    listed = openclaw_skills_client.get("/api/v1/openclaw/skills")
    assert listed.status_code == 200
    skills = listed.json()
    names = {skill["name"] for skill in skills}
    assert {"weather", "voice-call"} <= names

    weather = openclaw_skills_client.get("/api/v1/openclaw/skills/weather")
    assert weather.status_code == 200
    payload = weather.json()
    assert payload["name"] == "weather"
    assert payload["skill_key"] == "weather"
    assert "Weather Skill" in payload["content"]
    assert payload["source"] in {"workspace", "openclaw"} or payload["source"].startswith("/")


def test_load_session_skills_and_inject_into_agent_prompt(openclaw_skills_client: TestClient) -> None:
    created_session = openclaw_skills_client.post(
        "/api/v1/openclaw/sessions",
        json={
            "channel": "api",
            "title": "skills-session",
        },
    )
    assert created_session.status_code == 201
    session_id = created_session.json()["session_id"]

    loaded = openclaw_skills_client.post(
        f"/api/v1/openclaw/sessions/{session_id}/skills",
        json={
            "skill_names": ["voice-call"],
            "merge": True,
        },
    )
    assert loaded.status_code == 200
    loaded_payload = loaded.json()
    assert loaded_payload["metadata"]["loaded_skill_names"] == ["voice-call"]

    spawned = openclaw_skills_client.post(
        "/api/v1/openclaw/agents",
        json={
            "task_name": "skill-injected-run",
            "prompt": "say hello",
            "session_id": session_id,
            "generation_depth": 1,
            "timeout_seconds": 5,
            "command_override": [sys.executable, "-c", "import sys; print(sys.argv[-1])"],
            "append_prompt": True,
        },
    )
    assert spawned.status_code == 202
    agent_run_id = spawned.json()["agent_run_id"]

    finalized = _wait_terminal(openclaw_skills_client, agent_run_id)
    assert finalized["status"] == "completed"
    stdout_preview = finalized.get("stdout_preview") or ""
    assert "<available_skills>" in stdout_preview
    assert "voice-call" in stdout_preview
    assert "say hello" in stdout_preview


def test_unknown_skill_is_rejected(openclaw_skills_client: TestClient) -> None:
    created_session = openclaw_skills_client.post(
        "/api/v1/openclaw/sessions",
        json={"channel": "api", "title": "skills-error"},
    )
    assert created_session.status_code == 201
    session_id = created_session.json()["session_id"]

    failed_load = openclaw_skills_client.post(
        f"/api/v1/openclaw/sessions/{session_id}/skills",
        json={"skill_names": ["missing-skill"]},
    )
    assert failed_load.status_code == 400
    assert "missing-skill" in failed_load.json()["detail"]

    failed_spawn = openclaw_skills_client.post(
        "/api/v1/openclaw/agents",
        json={
            "task_name": "skill-missing-run",
            "prompt": "hello",
            "session_id": session_id,
            "generation_depth": 1,
            "timeout_seconds": 5,
            "skill_names": ["missing-skill"],
            "command_override": [sys.executable, "-c", "print('never-run')"],
            "append_prompt": False,
        },
    )
    assert failed_spawn.status_code == 400
    assert "missing-skill" in failed_spawn.json()["detail"]
