from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import time

from autoresearch.agent_protocol.models import ExecutionPolicy, JobSpec, ValidatorSpec
from autoresearch.core.services.git_promotion_gate import GitPromotionGateService
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.shared.models import GitRemoteProbe


class _FakeGitPromotionProvider:
    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe:
        _ = repo_root, base_branch
        return GitRemoteProbe(
            remote_name="origin",
            remote_url="git@example.invalid/repo.git",
            healthy=True,
            credentials_available=True,
            base_branch_exists=True,
        )

    def create_branch(
        self,
        repo_root: Path,
        *,
        branch_name: str,
        base_branch: str,
        workspace_dir: Path,
    ) -> None:
        _ = repo_root, branch_name, base_branch
        workspace_dir.mkdir(parents=True, exist_ok=True)

    def commit_changes(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        patch_uri: Path,
        changed_files: list[str],
        commit_message: str,
        validator_commands: list[str] | None = None,
        validator_log_dir: Path | None = None,
    ) -> str:
        _ = repo_root, workspace_dir, branch_name, patch_uri, changed_files, commit_message
        _ = validator_commands, validator_log_dir
        return "abc123def456"

    def push_branch(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
    ) -> None:
        _ = repo_root, workspace_dir, branch_name

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str:
        _ = repo_root, workspace_dir, title, body
        return f"https://example.invalid/{branch_name}?base={base_branch}"


def _write_manifest(repo_root: Path, entrypoint: str) -> None:
    manifest_path = repo_root / "configs" / "agents" / "openhands.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "id": "openhands",
                "kind": "process",
                "entrypoint": entrypoint,
                "version": "0.1",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _copy_worker_scripts(repo_root: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    for relative in ("drivers/openhands_adapter.sh", "scripts/openhands_start.sh"):
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o755)


def _write_adapter(repo_root: Path, relative: str, source: str) -> None:
    target = repo_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    target.chmod(0o755)


def test_openhands_dry_run_emits_patch_candidate_and_reaches_draft_pr(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_worker_scripts(repo_root)
    _write_manifest(repo_root, "drivers/openhands_adapter.sh")

    promotion_gate = GitPromotionGateService(
        repo_root=repo_root,
        provider=_FakeGitPromotionProvider(),
    )
    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
        promotion_gate=promotion_gate,
    )

    monkeypatch.setenv("OPENHANDS_DRY_RUN", "1")
    monkeypatch.setenv("OPENHANDS_CMD", "openhands")

    summary = runner.run_job(
        JobSpec(
            run_id="run-openhands-strict",
            agent_id="openhands",
            task="Create a single patch candidate inside the allowed path.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/generated_worker.py",
                )
            ],
            policy=ExecutionPolicy(
                allowed_paths=["src/generated_worker.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
            metadata={
                "pipeline_target": "draft_pr",
                "approval_granted": True,
                "branch_name": "codex/openhands-worker-strict",
                "pr_title": "OpenHands strict worker draft",
                "pr_body": "Autogenerated in dry-run mode.",
            },
        )
    )

    assert summary.final_status == "promoted"
    assert summary.driver_result.status == "succeeded"
    assert summary.validation.passed is True
    assert summary.promotion is not None
    assert summary.promotion.success is True
    assert summary.promotion.mode.value == "draft_pr"
    assert summary.promotion.pr_url is not None
    assert summary.driver_result.changed_paths == ["src/generated_worker.py"]

    patch_text = Path(summary.promotion_patch_uri or "").read_text(encoding="utf-8")
    assert "src/generated_worker.py" in patch_text


def test_runner_shadow_workspace_blocks_out_of_scope_write_with_permission_error(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "src" / "allowed.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo_root / "src" / "forbidden.py").write_text("SECRET = 1\n", encoding="utf-8")
    _write_adapter(
        repo_root,
        "drivers/shadow_probe.py",
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path

workspace = Path(os.environ["AEP_WORKSPACE"])
result_path = Path(os.environ["AEP_RESULT_PATH"])
allowed = workspace / "src" / "allowed.py"
forbidden = workspace / "src" / "forbidden.py"

error = "missing denial"
try:
    forbidden.write_text("SECRET = 2\\n", encoding="utf-8")
except Exception as exc:  # pragma: no cover - exercised via runner integration
    error = f"{type(exc).__name__}: {exc}"

allowed.write_text("VALUE = 2\\n", encoding="utf-8")
payload = {
    "protocol_version": "aep/v0",
    "run_id": "run-shadow-probe",
    "agent_id": "openhands",
    "attempt": 1,
    "status": "succeeded",
    "summary": error,
    "changed_paths": ["src/allowed.py"],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": None, "completion_tokens": None},
    "recommended_action": "promote",
    "error": None,
}
result_path.write_text(json.dumps(payload), encoding="utf-8")
""",
    )
    _write_manifest(repo_root, "drivers/shadow_probe.py")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-shadow-probe",
            agent_id="openhands",
            task="Only update src/allowed.py.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/allowed.py",
                )
            ],
            policy=ExecutionPolicy(
                allowed_paths=["src/allowed.py"],
                forbidden_paths=["src/forbidden.py", ".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
            metadata={"pipeline_target": "patch"},
        )
    )

    assert summary.driver_result.status == "succeeded"
    assert "PermissionError" in summary.driver_result.summary
    assert (repo_root / "src" / "forbidden.py").read_text(encoding="utf-8") == "SECRET = 1\n"
    assert "src/forbidden.py" not in summary.driver_result.changed_paths

    repeated = runner.run_job(
        JobSpec(
            run_id="run-shadow-probe",
            agent_id="openhands",
            task="Only update src/allowed.py.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/allowed.py",
                )
            ],
            policy=ExecutionPolicy(
                allowed_paths=["src/allowed.py"],
                forbidden_paths=["src/forbidden.py", ".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
            metadata={"pipeline_target": "patch"},
        )
    )

    assert repeated.driver_result.status == "succeeded"


def test_runner_fast_fail_aborts_long_running_syntax_breakage(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "src" / "broken_worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    _write_adapter(
        repo_root,
        "drivers/slow_broken_probe.py",
        """#!/usr/bin/env python3
import os
import time
from pathlib import Path

workspace = Path(os.environ["AEP_WORKSPACE"])
target = workspace / "src" / "broken_worker.py"
target.write_text("def broken(:\\n", encoding="utf-8")
time.sleep(30)
""",
    )
    _write_manifest(repo_root, "drivers/slow_broken_probe.py")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    started = time.perf_counter()
    summary = runner.run_job(
        JobSpec(
            run_id="run-fast-fail-probe",
            agent_id="openhands",
            task="Update src/broken_worker.py.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/broken_worker.py",
                )
            ],
            policy=ExecutionPolicy(
                timeout_sec=60,
                allowed_paths=["src/broken_worker.py"],
                cleanup_on_success=False,
            ),
        )
    )
    duration = time.perf_counter() - started

    assert duration < 15
    assert summary.final_status == "failed"
    assert summary.driver_result.status == "failed"
    assert summary.driver_result.summary == "adapter aborted by fast-fail probe"
    assert "SyntaxError" in (summary.driver_result.error or "")


def test_runner_stall_watchdog_aborts_no_progress_adapter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "src" / "idle_worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    _write_adapter(
        repo_root,
        "drivers/idle_probe.py",
        """#!/usr/bin/env python3
import time

time.sleep(30)
""",
    )
    _write_manifest(repo_root, "drivers/idle_probe.py")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    monkeypatch.setattr(runner, "_stall_progress_timeout_sec", lambda timeout_sec: 2)

    started = time.perf_counter()
    summary = runner.run_job(
        JobSpec(
            run_id="run-stall-probe",
            agent_id="openhands",
            task="Wait forever without writing any files.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/idle_worker.py",
                )
            ],
            policy=ExecutionPolicy(
                timeout_sec=60,
                allowed_paths=["src/idle_worker.py"],
                cleanup_on_success=False,
            ),
        )
    )
    duration = time.perf_counter() - started

    assert duration < 10
    assert summary.final_status == "failed"
    assert summary.driver_result.status == "stalled_no_progress"
    assert summary.driver_result.summary == "adapter stalled after 2s without workspace progress"
    assert summary.driver_result.error == "no workspace progress for 2s"
    assert summary.driver_result.metrics.first_progress_ms is None
    assert summary.driver_result.metrics.first_scoped_write_ms is None
    assert summary.driver_result.metrics.first_state_heartbeat_ms is None


def test_runner_records_first_progress_metrics_for_state_and_scoped_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "src" / "active_worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    _write_adapter(
        repo_root,
        "drivers/progress_probe.py",
        """#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

workspace = Path(os.environ["AEP_WORKSPACE"])
result_path = Path(os.environ["AEP_RESULT_PATH"])
state_dir = workspace / ".openhands-state"
target = workspace / "src" / "active_worker.py"

time.sleep(1)
state_dir.mkdir(parents=True, exist_ok=True)
(state_dir / "heartbeat.json").write_text("{\\"ok\\": true}\\n", encoding="utf-8")
time.sleep(1.5)
target.write_text("VALUE = 2\\n", encoding="utf-8")
time.sleep(2.5)
payload = {
    "protocol_version": "aep/v0",
    "run_id": "run-progress-probe",
    "agent_id": "openhands",
    "attempt": 1,
    "status": "succeeded",
    "summary": "progress recorded",
    "changed_paths": ["src/active_worker.py"],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": 1, "commands": 1, "prompt_tokens": None, "completion_tokens": None},
    "recommended_action": "promote",
    "error": None,
}
result_path.write_text(json.dumps(payload), encoding="utf-8")
""",
    )
    _write_manifest(repo_root, "drivers/progress_probe.py")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-progress-probe",
            agent_id="openhands",
            task="Touch .openhands-state first, then update src/active_worker.py.",
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=f"{sys.executable} -m py_compile src/active_worker.py",
                )
            ],
            policy=ExecutionPolicy(
                timeout_sec=60,
                allowed_paths=["src/active_worker.py"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "blocked"
    assert summary.driver_result.status == "policy_blocked"
    assert summary.driver_result.metrics.first_progress_ms is not None
    assert summary.driver_result.metrics.first_scoped_write_ms is not None
    assert summary.driver_result.metrics.first_state_heartbeat_ms is not None
    assert summary.driver_result.metrics.first_progress_ms <= summary.driver_result.metrics.first_state_heartbeat_ms
    assert summary.driver_result.metrics.first_state_heartbeat_ms < summary.driver_result.metrics.first_scoped_write_ms
