from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime import (
    OpenClawRuntimeContractError,
    OpenClawRuntimeService,
)
from autoresearch.shared.models import OpenClawSessionCreateRequest, OpenClawSessionRead
from autoresearch.shared.openclaw_runtime_contract import OpenClawRuntimeJobSpec
from autoresearch.shared.store import SQLiteModelRepository


def _build_openclaw_service(db_path: Path, table_name: str = "openclaw_sessions_test") -> OpenClawCompatService:
    return OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name=table_name,
            model_cls=OpenClawSessionRead,
        )
    )


def _create_session(service: OpenClawCompatService) -> str:
    session = service.create_session(
        OpenClawSessionCreateRequest(
            channel="test",
            title="openclaw-runtime-test",
            metadata={"source": "test"},
        )
    )
    return session.session_id


def _write_skill(
    workspace_root: Path,
    dirname: str,
    *,
    skill_id: str,
    name: str,
    entry_point: str,
    python_source: str,
) -> None:
    skill_dir = workspace_root / "skills" / dirname
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": skill_id,
                "name": name,
                "entry_point": entry_point,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (skill_dir / entry_point).write_text(python_source, encoding="utf-8")


def test_openclaw_runtime_service_builds_runtime_only_job_spec(tmp_path: Path) -> None:
    openclaw_service = _build_openclaw_service(tmp_path / "runtime.sqlite3")
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=tmp_path,
        openclaw_service=openclaw_service,
    )

    spec = OpenClawRuntimeJobSpec(
        job_id="job-runtime-build",
        action="send_message",
        session_id=session_id,
        content="hello",
    )
    job = service.build_agent_job_spec(spec)

    assert job.agent_id == "openclaw_runtime"
    assert job.mode == "runtime_only"
    assert job.policy.allowed_paths == []
    assert job.policy.max_changed_files == 0
    assert job.metadata["openclaw_runtime"]["action"] == "send_message"


def test_send_message_appends_session_event(tmp_path: Path) -> None:
    db_path = tmp_path / "send-message.sqlite3"
    openclaw_service = _build_openclaw_service(db_path)
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=tmp_path,
        openclaw_service=openclaw_service,
    )

    result = asyncio.run(
        service.execute(
            OpenClawRuntimeJobSpec(
                job_id="job-send-message",
                action="send_message",
                session_id=session_id,
                role="assistant",
                content="hello runtime",
            )
        )
    )
    session = openclaw_service.get_session(session_id)

    assert session is not None
    assert session.events[-1]["content"] == "hello runtime"
    assert session.events[-1]["role"] == "assistant"
    assert result.event_id == session.events[-1]["event_id"]


def test_run_skill_executes_sync_and_async_legacy_skills(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = tmp_path / "run-skill.sqlite3"
    openclaw_service = _build_openclaw_service(db_path)
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=workspace_root,
        openclaw_service=openclaw_service,
    )

    _write_skill(
        workspace_root,
        "sync-skill",
        skill_id="sync-skill",
        name="Sync Skill",
        entry_point="main.py",
        python_source=(
            "def execute(payload, credentials=None):\n"
            "    return {'payload': payload, 'token': (credentials or {}).get('token')}\n"
        ),
    )
    _write_skill(
        workspace_root,
        "async-skill",
        skill_id="async-skill",
        name="Async Skill",
        entry_point="main.py",
        python_source=(
            "import asyncio\n"
            "async def execute(payload, credentials=None):\n"
            "    await asyncio.sleep(0)\n"
            "    return {'value': payload['value'], 'token': (credentials or {}).get('token')}\n"
        ),
    )

    sync_result = asyncio.run(
        service.execute(
            OpenClawRuntimeJobSpec(
                job_id="job-sync-skill",
                action="run_skill",
                session_id=session_id,
                skill_id="sync-skill",
                input={"name": "demo"},
                credentials={"token": "secret"},
            )
        )
    )
    async_result = asyncio.run(
        service.execute(
            OpenClawRuntimeJobSpec(
                job_id="job-async-skill",
                action="run_skill",
                session_id=session_id,
                skill_id="async-skill",
                input={"value": 7},
                credentials={"token": "secret"},
            )
        )
    )

    session = openclaw_service.get_session(session_id)

    assert sync_result.result == {"payload": {"name": "demo"}, "token": "secret"}
    assert async_result.result == {"value": 7, "token": "secret"}
    assert session is not None
    assert any(event["role"] == "status" for event in session.events)


def test_run_skill_selector_ambiguity_fails_closed(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    openclaw_service = _build_openclaw_service(tmp_path / "ambiguity.sqlite3")
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=workspace_root,
        openclaw_service=openclaw_service,
    )

    _write_skill(
        workspace_root,
        "first",
        skill_id="shared-skill",
        name="First Skill",
        entry_point="main.py",
        python_source="def execute(payload, credentials=None):\n    return {'ok': True}\n",
    )
    _write_skill(
        workspace_root,
        "second",
        skill_id="shared-skill",
        name="Second Skill",
        entry_point="main.py",
        python_source="def execute(payload, credentials=None):\n    return {'ok': True}\n",
    )

    try:
        asyncio.run(
            service.execute(
                OpenClawRuntimeJobSpec(
                    job_id="job-ambiguous-skill",
                    action="run_skill",
                    session_id=session_id,
                    skill_id="shared-skill",
                    input={},
                )
            )
        )
    except OpenClawRuntimeContractError as exc:
        assert "ambiguous skill selector" in str(exc)
    else:
        raise AssertionError("expected OpenClawRuntimeContractError")


def test_run_skill_missing_selector_fails_closed(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "skills").mkdir(parents=True, exist_ok=True)
    openclaw_service = _build_openclaw_service(tmp_path / "missing.sqlite3")
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=workspace_root,
        openclaw_service=openclaw_service,
    )

    try:
        asyncio.run(
            service.execute(
                OpenClawRuntimeJobSpec(
                    job_id="job-missing-skill",
                    action="run_skill",
                    session_id=session_id,
                    skill_id="does-not-exist",
                    input={},
                )
            )
        )
    except OpenClawRuntimeContractError as exc:
        assert "skill not found" in str(exc)
    else:
        raise AssertionError("expected OpenClawRuntimeContractError")


def test_run_skill_resolves_by_name_and_dirname(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    openclaw_service = _build_openclaw_service(tmp_path / "selector.sqlite3")
    session_id = _create_session(openclaw_service)
    service = OpenClawRuntimeService(
        repo_root=tmp_path,
        workspace_root=workspace_root,
        openclaw_service=openclaw_service,
    )

    _write_skill(
        workspace_root,
        "dirname-match",
        skill_id="skill-by-dir",
        name="Skill By Directory",
        entry_point="main.py",
        python_source=(
            "def execute(payload, credentials=None):\n"
            "    return {'matched': 'dirname', 'payload': payload}\n"
        ),
    )
    _write_skill(
        workspace_root,
        "name-skill-dir",
        skill_id="skill-by-name",
        name="Skill By Name",
        entry_point="main.py",
        python_source=(
            "def execute(payload, credentials=None):\n"
            "    return {'matched': 'name', 'payload': payload}\n"
        ),
    )

    by_name = asyncio.run(
        service.execute(
            OpenClawRuntimeJobSpec(
                job_id="job-name-selector",
                action="run_skill",
                session_id=session_id,
                skill_id="skill by name",
                input={"selector": "name"},
            )
        )
    )
    by_dirname = asyncio.run(
        service.execute(
            OpenClawRuntimeJobSpec(
                job_id="job-dir-selector",
                action="run_skill",
                session_id=session_id,
                skill_id="dirname-match",
                input={"selector": "dirname"},
            )
        )
    )

    assert by_name.result == {"matched": "name", "payload": {"selector": "name"}}
    assert by_dirname.result == {"matched": "dirname", "payload": {"selector": "dirname"}}


def test_driver_writes_runtime_artifacts_for_send_message(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "driver.sqlite3"
    artifacts_dir = tmp_path / "artifacts"
    result_path = tmp_path / "driver_result.json"
    job_path = tmp_path / "job.json"

    openclaw_service = _build_openclaw_service(db_path, table_name="openclaw_sessions")
    session_id = _create_session(openclaw_service)

    payload = OpenClawRuntimeJobSpec(
        job_id="job-driver-send-message",
        action="send_message",
        session_id=session_id,
        content="hello from driver",
    )
    job_payload = {
        "protocol_version": "aep/v0",
        "run_id": "job-driver-send-message",
        "agent_id": "openclaw_runtime",
        "role": "executor",
        "mode": "runtime_only",
        "task": "OpenClaw runtime action: send_message",
        "input_artifacts": [],
        "policy": {},
        "validators": [],
        "fallback": [],
        "metadata": {
            "openclaw_runtime": payload.model_dump(mode="json"),
        },
    }
    job_path.write_text(json.dumps(job_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    env = dict(os.environ)
    env.update(
        {
            "AEP_WORKSPACE": str(workspace_root),
            "AEP_ARTIFACT_DIR": str(artifacts_dir),
            "AEP_JOB_SPEC": str(job_path),
            "AEP_RESULT_PATH": str(result_path),
            "AUTORESEARCH_API_DB_PATH": str(db_path),
        }
    )

    completed = subprocess.run(
        [str(repo_root / "drivers" / "openclaw_runtime_adapter.py")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    driver_result = json.loads(result_path.read_text(encoding="utf-8"))
    runtime_result = json.loads(
        (artifacts_dir / "openclaw_runtime_result.json").read_text(encoding="utf-8")
    )

    assert completed.returncode == 0, completed.stderr
    assert driver_result["status"] == "succeeded"
    assert runtime_result["success"] is True
    assert (artifacts_dir / "openclaw_runtime_request.json").exists()
    assert (artifacts_dir / "openclaw_runtime_result.json").exists()


def test_driver_rejects_repo_root_runtime_db_path(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = tmp_path / "artifacts"
    result_path = tmp_path / "driver_result.json"
    job_path = tmp_path / "job.json"
    blocked_db_path = repo_root / "artifacts" / "api" / f"runtime-blocked-{uuid4().hex}.sqlite3"

    payload = OpenClawRuntimeJobSpec(
        job_id="job-driver-db-blocked",
        action="send_message",
        session_id="oc_missing",
        content="hello from driver",
    )
    job_payload = {
        "protocol_version": "aep/v0",
        "run_id": "job-driver-db-blocked",
        "agent_id": "openclaw_runtime",
        "role": "executor",
        "mode": "runtime_only",
        "task": "OpenClaw runtime action: send_message",
        "input_artifacts": [],
        "policy": {},
        "validators": [],
        "fallback": [],
        "metadata": {
            "openclaw_runtime": payload.model_dump(mode="json"),
        },
    }
    job_path.write_text(json.dumps(job_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    env = dict(os.environ)
    env.update(
        {
            "AEP_WORKSPACE": str(workspace_root),
            "AEP_ARTIFACT_DIR": str(artifacts_dir),
            "AEP_JOB_SPEC": str(job_path),
            "AEP_RESULT_PATH": str(result_path),
            "AUTORESEARCH_API_DB_PATH": str(blocked_db_path),
        }
    )

    completed = subprocess.run(
        [str(repo_root / "drivers" / "openclaw_runtime_adapter.py")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    driver_result = json.loads(result_path.read_text(encoding="utf-8"))
    runtime_result = json.loads(
        (artifacts_dir / "openclaw_runtime_result.json").read_text(encoding="utf-8")
    )

    assert completed.returncode == 40
    assert driver_result["status"] == "contract_error"
    assert runtime_result["success"] is False
    assert "runtime persistence path must stay outside repo/workspace roots" in (
        driver_result["error"] or ""
    )
    assert not blocked_db_path.exists()
