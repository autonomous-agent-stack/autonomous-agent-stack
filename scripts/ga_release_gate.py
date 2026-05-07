from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from autoresearch.core.services.release_gate import ReleaseGateService


REPORT_PATH = Path("ga_release_gate_report.json")

GA_TESTS = [
    "tests/ga/test_ga_definition.py",
    "tests/ga/test_certification_matrix.py",
    "tests/ga/test_event_store_postgres_contract.py",
    "tests/ga/test_runtime_isolation.py",
    "tests/ga/test_bypass_ga.py",
    "tests/ga/test_external_write_gate.py",
    "tests/ga/test_furniture_e2e.py",
    "tests/ga/test_model_gateway_image.py",
    "tests/ga/test_release_gate.py",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = ReleaseGateService(repo_root=repo_root).run()
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    pytest_cmd = [sys.executable, "-m", "pytest", *GA_TESTS, "-q"]
    if report.status != "passed":
        _write_report(repo_root, report, pytest_cmd=pytest_cmd, pytest_return_code=None)
        return 1
    completed = subprocess.run(pytest_cmd, cwd=repo_root, check=False)
    _write_report(repo_root, report, pytest_cmd=pytest_cmd, pytest_return_code=completed.returncode)
    return completed.returncode


def _write_report(
    repo_root: Path, report: object, *, pytest_cmd: list[str], pytest_return_code: int | None
) -> None:
    failed_checks = [check for check in report.checks if check.status == "failed"]
    payload = {
        "status": "passed" if report.status == "passed" and pytest_return_code == 0 else "failed",
        "release_gate_status": report.status,
        "checks": _sanitize_for_report(
            [check.model_dump(mode="json") for check in report.checks],
            repo_root,
        ),
        "failed_checks": _sanitize_for_report(
            [check.model_dump(mode="json") for check in failed_checks],
            repo_root,
        ),
        "ga_pytest_command": _sanitize_for_report(pytest_cmd, repo_root),
        "ga_pytest_return_code": pytest_return_code,
    }
    (repo_root / REPORT_PATH).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sanitize_for_report(value: Any, repo_root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_report(item, repo_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_report(item, repo_root) for item in value]
    if isinstance(value, str):
        root = repo_root.as_posix()
        if value == root:
            return "."
        if value.startswith(f"{root}/"):
            return value[len(root) + 1 :]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
