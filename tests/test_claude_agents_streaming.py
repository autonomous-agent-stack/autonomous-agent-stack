from __future__ import annotations

import threading
from pathlib import Path

import pytest

from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.context_manager import ContextManager
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    JobStatus,
    OpenClawSessionRead,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def agent_repo(tmp_path: Path) -> SQLiteModelRepository[ClaudeAgentRunRead]:
    return SQLiteModelRepository(
        db_path=tmp_path / "claude_stream.sqlite3",
        table_name="claude_agent_stream_test",
        model_cls=ClaudeAgentRunRead,
    )


def test_persist_running_stdout_preview_updates_running_row(
    tmp_path: Path,
    agent_repo: SQLiteModelRepository[ClaudeAgentRunRead],
) -> None:
    db_path = tmp_path / "combined.sqlite3"
    openclaw = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_stream",
            model_cls=OpenClawSessionRead,
        )
    )
    svc = ClaudeAgentService(
        repository=agent_repo,
        openclaw_service=openclaw,
        repo_root=tmp_path,
        context_manager=ContextManager(openclaw),
    )
    run = ClaudeAgentRunRead(
        agent_run_id="ar-live-1",
        task_name="t",
        prompt="p",
        status=JobStatus.RUNNING,
        generation_depth=1,
        timeout_seconds=60,
        command=["x"],
        created_at=utc_now(),
        updated_at=utc_now(),
        metadata={},
    )
    agent_repo.save(run.agent_run_id, run)
    chunks_out = ["hello", " world"]
    chunks_err: list[str] = []
    lock = threading.Lock()
    svc._persist_running_stdout_preview(
        "ar-live-1",
        started_perf=0.0,
        request=ClaudeAgentCreateRequest(task_name="t", prompt="p", env={}),
        work_dir=tmp_path,
        chunks_out=chunks_out,
        chunks_err=chunks_err,
        buf_lock=lock,
    )
    loaded = svc.get("ar-live-1")
    assert loaded is not None
    assert loaded.stdout_preview == "hello world"
