from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import JobSpec
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
