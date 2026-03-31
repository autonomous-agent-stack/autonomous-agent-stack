from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import FallbackStep, JobSpec
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


def test_retry_then_fallback_agent(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    fail_adapter = repo_root / "drivers" / "fail_adapter.sh"
    fail_adapter.parent.mkdir(parents=True, exist_ok=True)
    fail_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-fallback",
  "agent_id": "primary",
  "attempt": 1,
  "status": "failed",
  "summary": "primary failed",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "fallback",
  "error": "failed"
}
JSON
exit 0
""",
        encoding="utf-8",
    )
    fail_adapter.chmod(0o755)

    success_adapter = repo_root / "drivers" / "success_adapter.sh"
    success_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$AEP_WORKSPACE/src"
echo 'print(7)' > "$AEP_WORKSPACE/src/success.py"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-fallback",
  "agent_id": "secondary",
  "attempt": 1,
  "status": "succeeded",
  "summary": "secondary succeeded",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 0, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
exit 0
""",
        encoding="utf-8",
    )
    success_adapter.chmod(0o755)

    _write_manifest(repo_root, "primary", "drivers/fail_adapter.sh")
    _write_manifest(repo_root, "secondary", "drivers/success_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-fallback",
            agent_id="primary",
            task="demo",
            fallback=[
                FallbackStep(action="retry", max_attempts=1),
                FallbackStep(action="fallback_agent", agent_id="secondary", max_attempts=1),
            ],
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.agent_id == "secondary"


def test_stalled_retry_is_skipped_before_fallback_agent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    stall_adapter = repo_root / "drivers" / "stall_adapter.sh"
    stall_adapter.parent.mkdir(parents=True, exist_ok=True)
    stall_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
sleep 30
""",
        encoding="utf-8",
    )
    stall_adapter.chmod(0o755)

    success_adapter = repo_root / "drivers" / "fallback_success.sh"
    success_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$AEP_WORKSPACE/src"
echo 'print(9)' > "$AEP_WORKSPACE/src/fallback.py"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-stall-fallback",
  "agent_id": "secondary",
  "attempt": 1,
  "status": "succeeded",
  "summary": "secondary succeeded",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 1, "commands": 1, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
exit 0
""",
        encoding="utf-8",
    )
    success_adapter.chmod(0o755)

    _write_manifest(repo_root, "primary", "drivers/stall_adapter.sh")
    _write_manifest(repo_root, "secondary", "drivers/fallback_success.sh")

    runtime_root = tmp_path / "runtime"
    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=runtime_root,
        manifests_dir=repo_root / "configs" / "agents",
    )
    monkeypatch.setattr(runner, "_stall_progress_timeout_sec", lambda timeout_sec: 2)

    summary = runner.run_job(
        JobSpec(
            run_id="run-stall-fallback",
            agent_id="primary",
            task="demo",
            fallback=[
                FallbackStep(action="retry", max_attempts=1),
                FallbackStep(action="fallback_agent", agent_id="secondary", max_attempts=1),
            ],
        )
    )

    events_path = runtime_root / "run-stall-fallback" / "events.ndjson"
    attempts = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    started_agents = [
        item["agent_id"] for item in attempts if item.get("type") == "attempt_started"
    ]

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.agent_id == "secondary"
    assert started_agents == ["primary", "secondary"]
    assert any(
        item.get("type") == "fallback_skipped" and item.get("reason") == "stalled_no_progress"
        for item in attempts
    )
