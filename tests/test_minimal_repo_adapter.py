from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = REPO_ROOT / "drivers" / "minimal_repo_adapter.sh"


def _run_adapter(
    tmp_path: Path,
    *,
    existing_text: str,
    append_text: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object], Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "docs" / "demo.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(existing_text, encoding="utf-8")

    job_path = tmp_path / "job.json"
    result_path = tmp_path / "driver_result.json"
    job_path.write_text(
        json.dumps(
            {
                "run_id": "run-minimal",
                "agent_id": "minimal_repo",
                "task": "append a demo marker",
                "metadata": {"demo_append_text": append_text},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [str(ADAPTER)],
        env={
            **os.environ,
            "AEP_WORKSPACE": str(workspace),
            "AEP_JOB_SPEC": str(job_path),
            "AEP_RESULT_PATH": str(result_path),
            "AEP_ATTEMPT": "1",
            "PYTHON": sys.executable,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    return completed, payload, target


def test_minimal_repo_adapter_reports_actual_docs_change(tmp_path: Path) -> None:
    completed, payload, target = _run_adapter(
        tmp_path,
        existing_text="seed\n",
        append_text="hello from test",
    )

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "succeeded"
    assert payload["recommended_action"] == "promote"
    assert payload["changed_paths"] == ["docs/demo.md"]
    assert target.read_text(encoding="utf-8") == "seed\nhello from test\n"


def test_minimal_repo_adapter_returns_partial_for_noop(tmp_path: Path) -> None:
    completed, payload, target = _run_adapter(
        tmp_path,
        existing_text="seed\nhello again\n",
        append_text="hello again",
    )

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "partial"
    assert payload["recommended_action"] == "human_review"
    assert payload["changed_paths"] == []
    assert target.read_text(encoding="utf-8") == "seed\nhello again\n"


def test_minimal_repo_adapter_appends_marker_when_text_only_exists_as_substring(
    tmp_path: Path,
) -> None:
    completed, payload, target = _run_adapter(
        tmp_path,
        existing_text="seed\nnote: hello from test appears inside prose\n",
        append_text="hello from test",
    )

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "succeeded"
    assert payload["changed_paths"] == ["docs/demo.md"]
    assert target.read_text(encoding="utf-8") == (
        "seed\n"
        "note: hello from test appears inside prose\n"
        "hello from test\n"
    )


def test_minimal_repo_adapter_rejects_multiline_marker_input(tmp_path: Path) -> None:
    completed, payload, target = _run_adapter(
        tmp_path,
        existing_text="seed\n",
        append_text="first line\nsecond line",
    )

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "failed"
    assert payload["recommended_action"] == "human_review"
    assert payload["changed_paths"] == []
    assert payload["error"] == "demo_append_text must be a single line"
    assert target.read_text(encoding="utf-8") == "seed\n"
