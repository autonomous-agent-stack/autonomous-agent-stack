from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from autoresearch.agent_protocol.models import FallbackStep, JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _write_manifest(
    repo_root: Path,
    agent_id: str,
    entrypoint: str,
    *,
    execution_semantics: str,
    default_mode: str = "runtime_only",
    allowed_paths: list[str] | None = None,
) -> None:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": entrypoint,
        "version": "0.1",
        "execution_semantics": execution_semantics,
        "default_mode": default_mode,
        "policy_defaults": {
            "allowed_paths": allowed_paths or [],
            "max_changed_files": 0,
            "max_patch_lines": 0,
        },
    }
    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_runtime_zero_change_success_is_completed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "runtime_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-runtime",
  "agent_id": "runtime-agent",
  "attempt": 1,
  "status": "succeeded",
  "summary": "runtime action completed",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "human_review",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)

    _write_manifest(
        repo_root,
        "runtime-agent",
        "drivers/runtime_adapter.sh",
        execution_semantics="runtime",
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-runtime",
            agent_id="runtime-agent",
            task="Send a runtime event.",
            mode="runtime_only",
        )
    )

    checks = {item.id: item for item in summary.validation.checks}

    assert summary.final_status == "completed"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.status != "completed"
    assert summary.promotion_patch_uri is None
    assert summary.promotion is None
    assert checks["builtin.runtime_no_repo_writes"].passed is True
    assert "builtin.nonempty_change_for_promote" not in checks


def test_runtime_repo_write_is_policy_blocked(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "runtime_writer.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$AEP_WORKSPACE/src"
echo "VALUE = 2" > "$AEP_WORKSPACE/src/changed.py"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-runtime-write",
  "agent_id": "runtime-writer",
  "attempt": 1,
  "status": "succeeded",
  "summary": "runtime action wrote repo files",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "human_review",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)

    _write_manifest(
        repo_root,
        "runtime-writer",
        "drivers/runtime_writer.sh",
        execution_semantics="runtime",
        allowed_paths=["src/**"],
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-runtime-write",
            agent_id="runtime-writer",
            task="Run a runtime skill.",
            mode="runtime_only",
        )
    )

    checks = {item.id: item for item in summary.validation.checks}

    assert summary.final_status == "blocked"
    assert summary.driver_result.status == "policy_blocked"
    assert checks["builtin.runtime_no_repo_writes"].passed is False
    assert checks["builtin.runtime_no_repo_writes"].detail == "src/changed.py"


@pytest.mark.parametrize(
    ("target_semantics", "target_mode"),
    [
        ("patch", "apply_in_workspace"),
        ("runtime", "runtime_only"),
    ],
)
def test_runtime_runs_reject_fallback_agent(
    tmp_path: Path,
    target_semantics: str,
    target_mode: str,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    runtime_adapter = repo_root / "drivers" / "runtime_failing_adapter.sh"
    runtime_adapter.parent.mkdir(parents=True, exist_ok=True)
    runtime_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-runtime-fallback",
  "agent_id": "runtime-primary",
  "attempt": 1,
  "status": "failed",
  "summary": "runtime action failed",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "fallback",
  "error": "boom"
}
JSON
""",
        encoding="utf-8",
    )
    runtime_adapter.chmod(0o755)

    target_adapter = repo_root / "drivers" / "fallback_target.sh"
    target_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "should not run" > "$AEP_WORKSPACE/target_ran.txt"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-runtime-fallback",
  "agent_id": "fallback-target",
  "attempt": 2,
  "status": "succeeded",
  "summary": "fallback executed",
  "changed_paths": ["target_ran.txt"],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    target_adapter.chmod(0o755)

    _write_manifest(
        repo_root,
        "runtime-primary",
        "drivers/runtime_failing_adapter.sh",
        execution_semantics="runtime",
        default_mode="runtime_only",
    )
    _write_manifest(
        repo_root,
        "fallback-target",
        "drivers/fallback_target.sh",
        execution_semantics=target_semantics,
        default_mode=target_mode,
        allowed_paths=["src/**"],
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id=f"run-runtime-fallback-{target_semantics}",
            agent_id="runtime-primary",
            task="Run runtime action with fallback.",
            mode="runtime_only",
            fallback=[FallbackStep(action="fallback_agent", agent_id="fallback-target")],
        )
    )

    events_path = tmp_path / "runtime" / f"run-runtime-fallback-{target_semantics}" / "events.ndjson"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert summary.final_status == "failed"
    assert not any(
        item.get("type") == "attempt_started" and item.get("agent_id") == "fallback-target"
        for item in events
    )
    assert any(
        item.get("type") == "fallback_blocked"
        and item.get("reason") == "runtime_runs_disallow_fallback_agent"
        and item.get("target_agent_id") == "fallback-target"
        for item in events
    )


def test_runtime_repo_root_db_path_fails_before_completed(tmp_path: Path, monkeypatch) -> None:
    source_repo_root = Path(__file__).resolve().parents[1]
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").symlink_to(source_repo_root / "src", target_is_directory=True)
    (repo_root / "drivers").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        source_repo_root / "drivers" / "openclaw_runtime_adapter.py",
        repo_root / "drivers" / "openclaw_runtime_adapter.py",
    )
    (repo_root / "drivers" / "openclaw_runtime_adapter.py").chmod(0o755)
    _write_manifest(
        repo_root,
        "openclaw_runtime",
        "drivers/openclaw_runtime_adapter.py",
        execution_semantics="runtime",
        default_mode="runtime_only",
    )

    runtime_root = tmp_path / "runtime"
    blocked_db_path = repo_root / "artifacts" / "api" / "runtime-guardrail-blocked.sqlite3"

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=runtime_root,
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(blocked_db_path))

    summary = runner.run_job(
        JobSpec(
            run_id="run-runtime-db-path-blocked",
            agent_id="openclaw_runtime",
            task="Send a runtime event.",
            mode="runtime_only",
            metadata={
                "openclaw_runtime": {
                    "protocol_version": "openclaw-runtime/v1",
                    "job_id": "run-runtime-db-path-blocked",
                    "action": "send_message",
                    "session_id": "oc_missing",
                    "content": "hello",
                }
            },
        )
    )

    assert summary.final_status == "failed"
    assert summary.driver_result.status == "contract_error"
    assert "runtime persistence path must stay outside repo/workspace roots" in (
        summary.driver_result.error or ""
    )
    assert not blocked_db_path.exists()
