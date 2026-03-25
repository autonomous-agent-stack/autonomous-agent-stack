from __future__ import annotations

import json
from pathlib import Path
import sys

from autoresearch.core.task_runner import run_task
from autoresearch.shared.models import EvaluationCreateRequest, EvaluatorCommand


def test_evaluation_request_accepts_legacy_command_list() -> None:
    request = EvaluationCreateRequest(
        task_name="legacy-request",
        evaluator_command=["python", "evaluate.py"],
    )

    assert request.evaluator_command is not None
    assert request.evaluator_command.command == ["python", "evaluate.py"]
    assert request.evaluator_command.timeout_seconds == 300


def test_run_task_uses_evaluator_override_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "task.json"
    work_dir = tmp_path / "override-workdir"
    work_dir.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "name": "override-task",
                "evaluate": {
                    "command": ["missing-default-command"],
                    "timeout_seconds": 30,
                    "score_direction": "maximize",
                },
                "artifacts_dir": "artifacts/override-task",
            }
        ),
        encoding="utf-8",
    )

    override = EvaluatorCommand(
        command=[
            sys.executable,
            "-c",
            (
                "import json, os; "
                "from pathlib import Path; "
                "payload = {"
                "'score': 1.0, "
                "'status': 'pass', "
                "'summary': os.environ['CUSTOM_FLAG'], "
                "'metrics': {'cwd': os.getcwd()}"
                "}; "
                "Path(os.environ['AUTORESEARCH_OUTPUT_JSON']).write_text(json.dumps(payload),"
                " encoding='utf-8')"
            ),
        ],
        timeout_seconds=7,
        work_dir=str(work_dir),
        env={"CUSTOM_FLAG": "override-used"},
    )

    task_run = run_task(
        config_path=config_path,
        description="override run",
        evaluator_command=override,
    )

    assert task_run["command_source"] == "request_override"
    assert task_run["command"] == override.command
    assert task_run["timeout_seconds"] == 7
    assert task_run["work_dir"] == str(work_dir.resolve())
    assert task_run["env_overrides"] == {"CUSTOM_FLAG": "override-used"}
    assert task_run["returncode"] == 0
    assert task_run["result"]["status"] == "pass"
    assert task_run["result"]["summary"] == "override-used"
    assert task_run["result"]["metrics"]["cwd"] == str(work_dir.resolve())
