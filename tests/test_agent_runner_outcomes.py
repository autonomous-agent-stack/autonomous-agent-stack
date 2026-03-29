from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _write_manifest(repo_root: Path, agent_id: str, entrypoint: str) -> None:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": entrypoint,
        "version": "0.1",
    }
    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_failed_driver_is_terminal_failure_not_human_review(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "failed_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-failed",
  "agent_id": "failed",
  "attempt": 1,
  "status": "failed",
  "summary": "adapter failed",
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
    adapter.chmod(0o755)
    _write_manifest(repo_root, "failed", "drivers/failed_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(JobSpec(run_id="run-failed", agent_id="failed", task="demo"))

    assert summary.final_status == "failed"
    checks = {item.id: item for item in summary.validation.checks}
    assert checks["builtin.driver_success"].passed is False


def test_zero_change_success_is_blocked(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "nochange_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-zero",
  "agent_id": "zero",
  "attempt": 1,
  "status": "succeeded",
  "summary": "no changes made",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)
    _write_manifest(repo_root, "zero", "drivers/nochange_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(JobSpec(run_id="run-zero", agent_id="zero", task="demo"))

    assert summary.final_status == "blocked"
    checks = {item.id: item for item in summary.validation.checks}
    assert checks["builtin.nonempty_change_for_promote"].passed is False


def test_openhands_environment_preflight_blocks_dirty_runtime_before_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "openhands_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "adapter should not run" > "$AEP_WORKSPACE/should_not_exist.txt"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-preflight",
  "agent_id": "openhands",
  "attempt": 1,
  "status": "succeeded",
  "summary": "should not happen",
  "changed_paths": ["should_not_exist.txt"],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)
    _write_manifest(repo_root, "openhands", "drivers/openhands_adapter.sh")

    preflight = repo_root / "scripts" / "fake_preflight.sh"
    preflight.parent.mkdir(parents=True, exist_ok=True)
    preflight.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "docker socket is stale for current user" >&2
exit 1
""",
        encoding="utf-8",
    )
    preflight.chmod(0o755)

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    monkeypatch.setenv("OPENHANDS_RUNTIME", "ai-lab")
    monkeypatch.setenv("OPENHANDS_PREFLIGHT_CMD", f"bash {preflight}")

    summary = runner.run_job(
        JobSpec(
            run_id="run-preflight",
            agent_id="openhands",
            task="demo",
        )
    )

    events_path = tmp_path / "runtime" / "run-preflight" / "events.ndjson"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert summary.final_status == "failed"
    assert summary.driver_result.status == "contract_error"
    assert summary.driver_result.error is not None
    assert summary.driver_result.error.startswith("EnvironmentCheckFailed:")
    assert not any(item.get("type") == "attempt_started" for item in events)
    assert any(
        item.get("type") == "attempt_blocked"
        and item.get("reason") == "environment_preflight_failed"
        for item in events
    )
