from __future__ import annotations

from pathlib import Path
import sys

from autoresearch.core.services.openhands_controlled_backend import (
    OpenHandsControlledBackendService,
)
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionRequest,
    ControlledRunStatus,
    FailureStrategy,
    ValidationStatus,
)


def _create_min_repo(repo_root: Path) -> None:
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")


def test_mock_backend_ready_for_promotion(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(repo_root=repo_root, run_root=run_root)
    request = ControlledExecutionRequest(
        task_id="demo-success",
        prompt="Create helper file",
        backend=ControlledBackend.MOCK,
        validation_command=[sys.executable, "-c", "print('ok')"],
        failure_strategy=FailureStrategy.HUMAN_IN_LOOP,
        max_retries=0,
        cleanup_workspace_on_success=False,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.READY_FOR_PROMOTION
    assert result.validation_status is ValidationStatus.PASSED
    assert "src/openhands_demo_task.py" in result.changed_files
    assert Path(result.execution_log).exists()
    assert Path(result.workspace).exists()
    assert any(item.kind == "summary" for item in result.artifacts)


def test_human_in_loop_when_validation_fails(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(repo_root=repo_root, run_root=run_root)
    request = ControlledExecutionRequest(
        task_id="demo-fail-human",
        prompt="Create helper file",
        backend=ControlledBackend.MOCK,
        validation_command=[sys.executable, "-c", "import sys; sys.exit(5)"],
        failure_strategy=FailureStrategy.HUMAN_IN_LOOP,
        max_retries=0,
        keep_workspace_on_failure=False,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.NEEDS_HUMAN_REVIEW
    assert result.validation_status is ValidationStatus.FAILED
    assert result.workspace_retained is False
    assert not Path(result.workspace).exists()


def test_fallback_to_mock_backend(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(repo_root=repo_root, run_root=run_root)
    request = ControlledExecutionRequest(
        task_id="demo-fallback",
        prompt="Create helper file",
        backend=ControlledBackend.OPENHANDS_CLI,
        fallback_backend=ControlledBackend.MOCK,
        validation_command=[sys.executable, "-c", "print('ok')"],
        failure_strategy=FailureStrategy.FALLBACK,
        max_retries=0,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.READY_FOR_PROMOTION
    assert result.backend_used is ControlledBackend.MOCK
    assert result.retries_used == 1
