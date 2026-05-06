from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from autoresearch.core.services.release_gate import ReleaseGateService


GA_TESTS = [
    "tests/ga/test_ga_definition.py",
    "tests/ga/test_certification_matrix.py",
    "tests/ga/test_event_store_postgres_contract.py",
    "tests/ga/test_runtime_isolation.py",
    "tests/ga/test_bypass_ga.py",
    "tests/ga/test_release_gate.py",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = ReleaseGateService(repo_root=repo_root).run()
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    if report.status != "passed":
        return 1
    pytest_cmd = [sys.executable, "-m", "pytest", *GA_TESTS, "-q"]
    completed = subprocess.run(pytest_cmd, cwd=repo_root, check=False)
    if completed.returncode != 0:
        return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
