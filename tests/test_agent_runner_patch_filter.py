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


def test_runner_rejects_forbidden_path_changes_and_filters_patch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "fake_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$AEP_WORKSPACE/src" "$AEP_WORKSPACE/memory" "$AEP_WORKSPACE/logs"
echo 'print(42)' > "$AEP_WORKSPACE/src/ok.py"
echo 'secret' > "$AEP_WORKSPACE/memory/secret.md"
echo 'runtime' > "$AEP_WORKSPACE/logs/runtime.txt"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "run-filter",
  "agent_id": "fake",
  "attempt": 1,
  "status": "succeeded",
  "summary": "adapter completed",
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

    _write_manifest(repo_root, "fake", "drivers/fake_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-filter",
            agent_id="fake",
            task="demo",
        )
    )

    assert summary.final_status == "human_review"
    checks = {item.id: item for item in summary.validation.checks}
    assert checks["builtin.forbidden_paths"].passed is False

    assert summary.promotion_patch_uri is not None
    patch_text = Path(summary.promotion_patch_uri).read_text(encoding="utf-8")
    assert "src/ok.py" in patch_text
    assert "memory/secret.md" not in patch_text
    assert "logs/runtime.txt" not in patch_text


def test_missing_driver_result_is_contract_error(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "broken_adapter.sh"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n", encoding="utf-8")
    adapter.chmod(0o755)

    _write_manifest(repo_root, "broken", "drivers/broken_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    summary = runner.run_job(
        JobSpec(
            run_id="run-contract",
            agent_id="broken",
            task="demo",
        )
    )

    assert summary.driver_result.status == "contract_error"
    assert summary.final_status == "failed"
