from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from autoresearch.core.services.openhands_controlled_backend import (
    OpenHandsControlledBackendService,
    _BackendExecutionOutcome,
)
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionRequest,
    ControlledRunStatus,
    ValidationStatus,
)


def _create_min_repo(repo_root: Path) -> None:
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_git_repo(repo_root: Path) -> None:
    _git(repo_root, "init", "-b", "main")
    _git(repo_root, "config", "user.email", "tests@example.com")
    _git(repo_root, "config", "user.name", "Tests")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "initial")


def test_mock_backend_ready_for_patch_promotion(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=run_root,
    )
    request = ControlledExecutionRequest(
        task_id="demo-success",
        prompt="Create helper file",
        allowed_paths=["src/openhands_demo_task.py"],
        test_command=[sys.executable, "-m", "py_compile", "src/openhands_demo_task.py"],
        backend=ControlledBackend.MOCK,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.READY_FOR_PROMOTION
    assert result.validation_status is ValidationStatus.PASSED
    assert result.changed_files == ["src/openhands_demo_task.py"]
    assert result.patch_result is not None
    assert result.patch_result.output_mode == "patch"
    assert result.patch_result.changed_files == ["src/openhands_demo_task.py"]
    assert result.promotion is not None
    assert result.promotion.success is True
    assert result.promotion.mode.value == "patch"


def test_scope_violation_is_policy_blocked_and_never_promoted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=run_root,
    )

    def _bad_backend(
        *,
        prompt: str,
        workspace: Path,
        log_file: Path,
        allowed_paths: list[str],
    ):
        _ = prompt, allowed_paths
        leaked = workspace / "memory" / "secret.md"
        leaked.parent.mkdir(parents=True, exist_ok=True)
        leaked.write_text("secret\n", encoding="utf-8")
        service._append_log(log_file, "[mock-backend] wrote forbidden file\n")
        return _BackendExecutionOutcome(exit_code=0, stdout="wrote forbidden file\n")

    monkeypatch.setattr(service, "_run_mock_backend", _bad_backend)

    request = ControlledExecutionRequest(
        task_id="demo-blocked",
        prompt="Create helper file",
        allowed_paths=["src/allowed.py"],
        test_command=[sys.executable, "-c", "print('ok')"],
        backend=ControlledBackend.MOCK,
        keep_workspace_on_failure=False,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.POLICY_BLOCKED
    assert result.validation_status is ValidationStatus.SKIPPED
    assert result.promotion is None
    assert result.patch_result is not None
    assert "memory/secret.md" in result.changed_files
    assert "disallowed files" in (result.error or "")
    assert result.workspace_retained is False


def test_failed_test_command_stays_failed_after_max_iterations(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=run_root,
    )
    request = ControlledExecutionRequest(
        task_id="demo-fail",
        prompt="Create helper file",
        allowed_paths=["src/openhands_demo_task.py"],
        test_command=[sys.executable, "-c", "import sys; sys.exit(5)"],
        backend=ControlledBackend.MOCK,
        max_iterations=2,
        keep_workspace_on_failure=False,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.FAILED
    assert result.validation_status is ValidationStatus.FAILED
    assert result.iterations_used == 1
    assert result.promotion is None
    assert result.patch_result is not None
    assert result.workspace_retained is False


def test_openhands_cli_env_strips_git_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _create_min_repo(repo_root)
    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=tmp_path / "runs",
    )

    monkeypatch.setenv("GITHUB_TOKEN", "ghs-secret")
    monkeypatch.setenv("GH_TOKEN", "gh-secret")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Alice")
    monkeypatch.setenv("SAFE_ENV", "ok")

    env = service._build_openhands_env(
        workspace=repo_root / "workspace",
        artifacts_dir=repo_root / "artifacts",
    )

    assert env["SAFE_ENV"] == "ok"
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "GITHUB_TOKEN" not in env
    assert "GH_TOKEN" not in env
    assert "SSH_AUTH_SOCK" not in env
    assert "GIT_AUTHOR_NAME" not in env


def test_dirty_repo_blocks_openhands_cli_before_execution(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _create_min_repo(repo_root)
    _init_git_repo(repo_root)
    (repo_root / "src" / "dirty.py").write_text("print('dirty')\n", encoding="utf-8")

    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=tmp_path / "runs",
    )
    request = ControlledExecutionRequest(
        task_id="demo-dirty",
        prompt="Create helper file",
        allowed_paths=["src/openhands_demo_task.py"],
        test_command=[sys.executable, "-c", "print('ok')"],
        backend=ControlledBackend.OPENHANDS_CLI,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.POLICY_BLOCKED
    assert "clean git checkout" in (result.error or "")
    assert result.promotion is None


def test_openhands_cli_can_fallback_to_mock_patch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = tmp_path / "runs"
    repo_root.mkdir()
    _create_min_repo(repo_root)

    service = OpenHandsControlledBackendService(
        repo_root=repo_root,
        run_root=run_root,
    )
    request = ControlledExecutionRequest(
        task_id="demo-fallback",
        prompt="Create helper file",
        allowed_paths=["src/openhands_demo_task.py"],
        test_command=[sys.executable, "-m", "py_compile", "src/openhands_demo_task.py"],
        backend=ControlledBackend.OPENHANDS_CLI,
        fallback_backend=ControlledBackend.MOCK,
        max_iterations=1,
    )

    result = service.run(request)

    assert result.status is ControlledRunStatus.READY_FOR_PROMOTION
    assert result.backend_used is ControlledBackend.MOCK
    assert result.iterations_used == 1
    assert result.patch_result is not None
    assert result.patch_result.changed_files == ["src/openhands_demo_task.py"]
