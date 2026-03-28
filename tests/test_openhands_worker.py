from __future__ import annotations

import pytest

from autoresearch.core.services.openhands_worker import OpenHandsWorkerService
from autoresearch.shared.openhands_controlled_contract import ControlledBackend, FailureStrategy
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec


def test_openhands_worker_builds_patch_only_agent_job_spec() -> None:
    service = OpenHandsWorkerService()
    spec = OpenHandsWorkerJobSpec(
        job_id="job-1",
        problem_statement="Fix the parser regression in foo and add a focused test.",
        allowed_paths=["src/foo.py", "tests/test_foo.py"],
        test_command="pytest tests/test_foo.py -q",
        metadata={"issue_id": "BUG-1"},
    )

    job = service.build_agent_job_spec(spec)

    assert job.agent_id == "openhands"
    assert job.mode == "patch_only"
    assert job.policy.allowed_paths == ["src/foo.py", "tests/test_foo.py"]
    assert job.validators[0].command == "pytest tests/test_foo.py -q"
    assert job.metadata["worker_contract"] == "openhands-worker/v1"
    assert job.metadata["promotion_mode"] == "patch"
    assert "Do not run git add, git commit, git push" in job.task
    assert "allowed_paths:" in job.task


def test_openhands_worker_builds_controlled_request_with_mock_fallback() -> None:
    service = OpenHandsWorkerService()
    spec = OpenHandsWorkerJobSpec(
        job_id="job-2",
        problem_statement="Update the OpenHands adapter without touching control-plane routes.",
        allowed_paths=["src/autoresearch/core/services/openhands_worker.py"],
        test_command="python -m py_compile src/autoresearch/core/services/openhands_worker.py",
        max_retries=1,
    )

    request = service.build_controlled_request(spec)

    assert request.backend is ControlledBackend.OPENHANDS_CLI
    assert request.fallback_backend is ControlledBackend.MOCK
    assert request.failure_strategy is FailureStrategy.FALLBACK
    assert request.validation_command == [
        "python",
        "-m",
        "py_compile",
        "src/autoresearch/core/services/openhands_worker.py",
    ]
    assert request.metadata["allowed_paths"] == ["src/autoresearch/core/services/openhands_worker.py"]
    assert request.metadata["promotion_mode"] == "patch"


def test_openhands_worker_rejects_absolute_allowed_paths() -> None:
    with pytest.raises(ValueError):
        OpenHandsWorkerJobSpec(
            job_id="job-3",
            problem_statement="No-op",
            allowed_paths=["/etc/passwd"],
            test_command="pytest -q",
        )
