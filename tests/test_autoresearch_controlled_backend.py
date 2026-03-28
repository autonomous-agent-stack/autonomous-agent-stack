from __future__ import annotations

from pathlib import Path
import sys

import pytest

from autoresearch.core.services.autoresearch_controlled_backend import (
    AutoResearchControlledBackendService,
    _AutoResearchOutcome,
)
from autoresearch.shared.autoresearch_controlled_contract import (
    AutoResearchBackend,
    AutoResearchExecutionRequest,
    AutoResearchRunStatus,
    AutoResearchValidationStatus,
)


def _create_min_repo(repo_root: Path) -> None:
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")


def test_autoresearch_mock_backend_emits_artifacts_and_patch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = AutoResearchControlledBackendService(repo_root=repo_root, run_root=run_root)
    request = AutoResearchExecutionRequest(
        task_id="demo-success",
        prompt="Analyze the code and emit a narrow patch candidate.",
        allowed_paths=["src/autoresearch_generated.py"],
        test_command=[sys.executable, "-m", "py_compile", "src/autoresearch_generated.py"],
        deliverables=["execution_plan", "test_plan", "risk_summary", "patch_suggestion"],
    )

    result = service.run(request)

    assert result.status is AutoResearchRunStatus.READY_FOR_PROMOTION
    assert result.validation_status is AutoResearchValidationStatus.PASSED
    assert result.changed_files == ["src/autoresearch_generated.py"]
    assert result.patch_result is not None
    assert set(result.deliverable_artifacts) == {
        "execution_plan",
        "test_plan",
        "risk_summary",
        "patch_suggestion",
    }
    assert result.promotion is not None
    assert result.promotion.success is True
    assert result.promotion.mode.value == "patch"


def test_autoresearch_scope_violation_blocks_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = AutoResearchControlledBackendService(repo_root=repo_root, run_root=run_root)

    def _bad_backend(
        *,
        prompt: str,
        workspace: Path,
        artifacts_dir: Path,
        log_file: Path,
        allowed_paths: list[str],
        deliverables: list[str],
        test_command: list[str],
    ):
        _ = prompt, artifacts_dir, log_file, allowed_paths, deliverables, test_command
        leaked = workspace / "memory" / "secret.md"
        leaked.parent.mkdir(parents=True, exist_ok=True)
        leaked.write_text("secret\n", encoding="utf-8")
        return _AutoResearchOutcome(exit_code=0, stdout="bad\n"), {}

    monkeypatch.setattr(service, "_run_mock_backend", _bad_backend)

    request = AutoResearchExecutionRequest(
        task_id="demo-blocked",
        prompt="Analyze the code and emit a narrow patch candidate.",
        allowed_paths=["src/allowed.py"],
        test_command=[sys.executable, "-c", "print('ok')"],
    )

    result = service.run(request)

    assert result.status is AutoResearchRunStatus.POLICY_BLOCKED
    assert result.validation_status is AutoResearchValidationStatus.SKIPPED
    assert result.promotion is None
    assert "memory/secret.md" in result.changed_files


def test_autoresearch_failed_test_command_stays_failed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = AutoResearchControlledBackendService(repo_root=repo_root, run_root=run_root)
    request = AutoResearchExecutionRequest(
        task_id="demo-fail",
        prompt="Analyze the code and emit a narrow patch candidate.",
        allowed_paths=["src/autoresearch_generated.py"],
        test_command=[sys.executable, "-c", "import sys; sys.exit(5)"],
        max_iterations=2,
        keep_workspace_on_failure=False,
    )

    result = service.run(request)

    assert result.status is AutoResearchRunStatus.FAILED
    assert result.validation_status is AutoResearchValidationStatus.FAILED
    assert result.iterations_used == 1
    assert result.promotion is None
    assert result.workspace_retained is False
