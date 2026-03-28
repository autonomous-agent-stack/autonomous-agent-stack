from __future__ import annotations

import pytest

from autoresearch.core.services.autoresearch_worker import AutoResearchWorkerService
from autoresearch.shared.autoresearch_controlled_contract import AutoResearchBackend
from autoresearch.shared.autoresearch_worker_contract import AutoResearchWorkerJobSpec


def test_autoresearch_worker_builds_patch_only_job_spec() -> None:
    service = AutoResearchWorkerService()
    spec = AutoResearchWorkerJobSpec(
        job_id="job-1",
        research_task="Inspect parser code, propose a narrow fix, and include a focused test plan.",
        allowed_paths=["src/parser.py", "tests/test_parser.py"],
        test_command="pytest tests/test_parser.py -q",
    )

    job = service.build_agent_job_spec(spec)

    assert job.agent_id == "autoresearch"
    assert job.role == "analyst"
    assert job.mode == "patch_only"
    assert job.policy.allowed_paths == ["src/parser.py", "tests/test_parser.py"]
    assert job.validators[0].command == "pytest tests/test_parser.py -q"
    assert job.metadata["worker_output_mode"] == "patch"
    assert job.metadata["pipeline_target"] == "patch"
    assert job.metadata["deliverables"] == [
        "execution_plan",
        "test_plan",
        "risk_summary",
        "patch_suggestion",
    ]
    assert "deliverables:" in job.task
    assert "Do not finalize promotion" in job.task


def test_autoresearch_worker_builds_controlled_request() -> None:
    service = AutoResearchWorkerService()
    spec = AutoResearchWorkerJobSpec(
        job_id="job-2",
        research_task="Analyze the worker contract and emit a focused patch candidate.",
        allowed_paths=["src/autoresearch/core/services/autoresearch_worker.py"],
        test_command="python -m py_compile src/autoresearch/core/services/autoresearch_worker.py",
        pipeline_target="draft_pr",
        max_iterations=2,
        deliverables=["execution_plan", "risk_summary"],
        network_policy="allowlist",
        network_allowlist=["docs.example.invalid"],
    )

    request = service.build_controlled_request(spec)

    assert request.backend is AutoResearchBackend.MOCK
    assert request.allowed_paths == ["src/autoresearch/core/services/autoresearch_worker.py"]
    assert request.test_command == [
        "python",
        "-m",
        "py_compile",
        "src/autoresearch/core/services/autoresearch_worker.py",
    ]
    assert request.worker_output_mode == "patch"
    assert request.pipeline_target.value == "draft_pr"
    assert request.max_iterations == 2
    assert request.deliverables == ["execution_plan", "risk_summary"]
    assert request.metadata["network_policy"] == "allowlist"
    assert request.metadata["network_allowlist"] == ["docs.example.invalid"]


def test_autoresearch_worker_rejects_absolute_allowed_paths() -> None:
    with pytest.raises(ValueError):
        AutoResearchWorkerJobSpec(
            job_id="job-3",
            research_task="No-op",
            allowed_paths=["/etc/passwd"],
            test_command="pytest -q",
        )
