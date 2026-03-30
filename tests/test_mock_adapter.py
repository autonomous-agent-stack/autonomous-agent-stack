from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_ADAPTER = REPO_ROOT / "drivers" / "mock_adapter.sh"


def _run_mock_adapter(tmp_path: Path, *, allowed_paths: list[str], validator_command: str) -> tuple[dict[str, object], Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    job_path = tmp_path / "job.json"
    result_path = tmp_path / "driver_result.json"
    job_path.write_text(
        json.dumps(
            {
                "run_id": "run-mock",
                "agent_id": "mock",
                "task": "Create a bounded patch candidate.",
                "policy": {"allowed_paths": allowed_paths},
                "validators": [
                    {
                        "id": "worker.test_command",
                        "kind": "command",
                        "command": validator_command,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [str(MOCK_ADAPTER)],
        env={
            **os.environ,
            "AEP_WORKSPACE": str(workspace),
            "AEP_JOB_SPEC": str(job_path),
            "AEP_RESULT_PATH": str(result_path),
            "PY_BIN": sys.executable,
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    return json.loads(result_path.read_text(encoding="utf-8")), workspace


def test_mock_adapter_prefers_validator_targeted_test_file(tmp_path: Path) -> None:
    payload, workspace = _run_mock_adapter(
        tmp_path,
        allowed_paths=["scripts/check_prompt_hygiene.py", "tests/test_check_prompt_hygiene.py"],
        validator_command=f"{sys.executable} -m pytest -q tests/test_check_prompt_hygiene.py",
    )

    target = workspace / "tests" / "test_check_prompt_hygiene.py"
    assert payload["changed_paths"] == ["tests/test_check_prompt_hygiene.py"]
    assert "def test_mock_autoresearch_candidate" in target.read_text(encoding="utf-8")


def test_mock_adapter_falls_back_to_first_allowed_source_file(tmp_path: Path) -> None:
    payload, workspace = _run_mock_adapter(
        tmp_path,
        allowed_paths=["scripts/check_prompt_hygiene.py"],
        validator_command=f"{sys.executable} -m py_compile scripts/check_prompt_hygiene.py",
    )

    target = workspace / "scripts" / "check_prompt_hygiene.py"
    assert payload["changed_paths"] == ["scripts/check_prompt_hygiene.py"]
    assert "def run()" in target.read_text(encoding="utf-8")


def test_mock_adapter_uses_validator_target_inside_globbed_apps_scope(tmp_path: Path) -> None:
    payload, workspace = _run_mock_adapter(
        tmp_path,
        allowed_paths=["apps/malu/**"],
        validator_command=f"{sys.executable} -m py_compile apps/malu/lead_capture.py",
    )

    target = workspace / "apps" / "malu" / "lead_capture.py"
    assert payload["changed_paths"] == ["apps/malu/lead_capture.py"]
    assert "class PhoneValidator" in target.read_text(encoding="utf-8")


def test_mock_adapter_builds_source_and_test_for_pytest_validated_business_surface(tmp_path: Path) -> None:
    payload, workspace = _run_mock_adapter(
        tmp_path,
        allowed_paths=["apps/malu/**", "tests/apps/test_malu_landing_page.py"],
        validator_command="pytest -q tests/apps/test_malu_landing_page.py",
    )

    source_target = workspace / "apps" / "malu" / "lead_capture.py"
    test_target = workspace / "tests" / "apps" / "test_malu_landing_page.py"
    assert payload["changed_paths"] == [
        "apps/malu/lead_capture.py",
        "tests/apps/test_malu_landing_page.py",
    ]
    assert "class PhoneValidator" in source_target.read_text(encoding="utf-8")
    assert "from apps.malu.lead_capture import PhoneValidator, capture_lead" in test_target.read_text(encoding="utf-8")
