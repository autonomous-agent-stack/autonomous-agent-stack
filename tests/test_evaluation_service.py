from __future__ import annotations

import json
from pathlib import Path
import sys

from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.shared.models import (
    EvaluationCreateRequest,
    EvaluatorCommand,
    JobStatus,
    utc_now,
)


def test_recover_interrupted_marks_running_records(tmp_path: Path) -> None:
    db_path = tmp_path / "evaluations.sqlite3"
    repository = SQLiteEvaluationRepository(db_path=db_path)
    service = EvaluationService(
        repository=repository,
        repo_root=tmp_path,
    )
    request = EvaluationCreateRequest(
        task_name="demo-task",
        config_path=str(tmp_path / "task.json"),
        description="persist me",
    )

    created = service.create(request)
    running = created.model_copy(
        update={
            "status": JobStatus.RUNNING,
            "summary": "Evaluation running.",
            "updated_at": utc_now(),
        }
    )
    repository.update(running)

    restarted_service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=db_path),
        repo_root=tmp_path,
    )
    recovered_count = restarted_service.recover_interrupted()
    restored = restarted_service.get(created.evaluation_id)

    assert recovered_count == 1
    assert restored is not None
    assert restored.status is JobStatus.INTERRUPTED
    assert restored.summary == "API service restarted before evaluation finished."
    assert restored.error == "API service restarted before evaluation finished."


def test_execute_persists_completed_result(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "evaluations.sqlite3"
    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=db_path),
        repo_root=tmp_path,
    )
    request = EvaluationCreateRequest(
        task_name="demo-task",
        config_path=str(tmp_path / "task.json"),
        description="run evaluation",
        metadata={"initiator": "test"},
    )

    def fake_run_task(
        config_path: str | Path,
        description: str,
        evaluator_command: EvaluatorCommand | None = None,
    ) -> dict[str, object]:
        return {
            "run_id": "run-123",
            "branch": "main",
            "commit": "abc1234",
            "comparison": "first run",
            "best_before": "n/a",
            "command": ["python", "evaluate.py"],
            "command_source": "task_config",
            "timeout_seconds": 30,
            "work_dir": str(tmp_path),
            "env_overrides": {},
            "returncode": 0,
            "duration_seconds": 0.25,
            "artifact_dir": str(tmp_path / "artifacts" / "run-123"),
            "stdout_log": str(tmp_path / "artifacts" / "run-123" / "stdout.log"),
            "stderr_log": str(tmp_path / "artifacts" / "run-123" / "stderr.log"),
            "stdout_preview": None,
            "stderr_preview": None,
            "result": {
                "status": "pass",
                "score": 0.91,
                "summary": "all checks passed",
                "metrics": {"cases": 12},
            },
        }

    monkeypatch.setattr("autoresearch.core.services.evaluations.run_task", fake_run_task)

    created = service.create(request)
    service.execute(created.evaluation_id, request)

    reloaded_service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=db_path),
        repo_root=tmp_path,
    )
    stored = reloaded_service.get(created.evaluation_id)

    assert stored is not None
    assert stored.status is JobStatus.COMPLETED
    assert stored.result_status == "pass"
    assert stored.run_id == "run-123"
    assert stored.score == 0.91
    assert stored.metrics == {"cases": 12}
    assert stored.metadata["initiator"] == "test"
    assert stored.metadata["command"] == ["python", "evaluate.py"]
    assert stored.metadata["command_source"] == "task_config"
    assert stored.error is None


def test_execute_uses_evaluator_override_and_persists_failure_details(tmp_path: Path) -> None:
    config_path = tmp_path / "task.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "demo-task",
                "evaluate": {
                    "command": ["missing-default-command"],
                    "timeout_seconds": 30,
                    "score_direction": "maximize",
                },
                "artifacts_dir": "artifacts/demo-task",
            }
        ),
        encoding="utf-8",
    )

    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=tmp_path / "evaluations.sqlite3"),
        repo_root=tmp_path,
    )
    request = EvaluationCreateRequest(
        task_name="demo-task",
        config_path=str(config_path),
        description="override failure",
        evaluator_command=EvaluatorCommand(
            command=[
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('override boom\\n'); sys.exit(3)",
            ],
            timeout_seconds=5,
            work_dir=".",
            env={"OVERRIDE_MODE": "enabled"},
        ),
    )

    created = service.create(request)
    service.execute(created.evaluation_id, request)
    stored = service.get(created.evaluation_id)

    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert stored.result_status == "crash"
    assert stored.metadata["command_source"] == "request_override"
    assert stored.metadata["command"] == [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('override boom\\n'); sys.exit(3)",
    ]
    assert stored.metadata["timeout_seconds"] == 5
    assert stored.metadata["work_dir"] == str(tmp_path.resolve())
    assert stored.metadata["env_overrides"] == {"OVERRIDE_MODE": "enabled"}
    assert stored.metadata["returncode"] == 3
    assert "override boom" in stored.metadata["stderr_preview"]
    assert "evaluator did not write AUTORESEARCH_OUTPUT_JSON" in (stored.error or "")
