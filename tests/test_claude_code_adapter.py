from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

from autoresearch.agent_protocol.models import ExecutionPolicy, JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _write_manifest(repo_root: Path, entrypoint: str) -> None:
    manifest_path = repo_root / "configs" / "agents" / "claude_code.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "id": "claude_code",
                "kind": "process",
                "entrypoint": entrypoint,
                "version": "0.1",
                "default_mode": "apply_in_workspace",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _copy_adapter(repo_root: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    source = source_root / "drivers" / "claude_code_adapter.sh"
    target = repo_root / "drivers" / "claude_code_adapter.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(0o755)


def test_claude_code_dry_run_emits_patch_candidate(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/claude_code_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.setenv("CLAUDE_CODE_DRY_RUN", "1")
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-claude-code-dry",
            agent_id="claude_code",
            task="Create a single file in the allowed path.",
            policy=ExecutionPolicy(
                allowed_paths=["src/generated_claude.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.status == "succeeded"
    assert summary.validation.passed is True
    assert summary.driver_result.changed_paths == ["src/generated_claude.py"]


def test_claude_code_missing_cli_is_contract_error(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/claude_code_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CLAUDE_CODE_DRY_RUN", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_BIN", "/definitely/missing/claude")
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-claude-code-missing",
            agent_id="claude_code",
            task="Create a single file in the allowed path.",
        )
    )

    assert summary.driver_result.status == "contract_error"
    assert summary.final_status == "failed"
    assert "Claude CLI not found" in (summary.driver_result.error or "")


def test_claude_code_missing_auth_is_contract_error(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/claude_code_adapter.sh")

    auth_status = tmp_path / "claude-auth.json"
    auth_status.write_text('{"loggedIn": false, "authMethod": "oauth_token"}\n', encoding="utf-8")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CLAUDE_CODE_DRY_RUN", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_BIN", "/bin/echo")
    monkeypatch.setenv("CLAUDE_CODE_AUTH_STATUS_FILE", str(auth_status))
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-claude-code-auth-missing",
            agent_id="claude_code",
            task="Create a single file in the allowed path.",
        )
    )

    assert summary.driver_result.status == "contract_error"
    assert summary.final_status == "failed"
    assert "not logged in" in (summary.driver_result.error or "").lower()


def test_claude_code_auto_mode_falls_back_to_bypass_permissions(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/claude_code_adapter.sh")

    fake_claude = tmp_path / "fake_claude.sh"
    fake_claude.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "auth" && "${2:-}" == "status" ]]; then
  printf '{"loggedIn": true, "authMethod": "oauth_token"}\\n'
  exit 0
fi

mode=""
while (($#)); do
  case "$1" in
    -p|--print|--output-format)
      shift
      if [[ "${1:-}" == "json" ]]; then
        shift
      fi
      ;;
    --permission-mode)
      mode="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$mode" == "acceptEdits" ]]; then
  printf '{"type":"result","subtype":"success","is_error":false,"result":"permission denied","permission_denials":["Edit"],"session_id":"s1"}\\n'
  exit 0
fi

mkdir -p src
cat >src/demo_math.py <<'PY'
def add(a, b):
    return a + b
PY
printf '{"type":"result","subtype":"success","is_error":false,"result":"Created src/demo_math.py","permission_denials":[],"session_id":"s2"}\\n'
""",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CLAUDE_CODE_DRY_RUN", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_BIN", str(fake_claude))
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-claude-code-auto",
            agent_id="claude_code",
            task="Create src/demo_math.py with add(a,b).",
            policy=ExecutionPolicy(
                allowed_paths=["src/demo_math.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.agent_id == "claude_code"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["src/demo_math.py"]

    preflight = next(
        item for item in summary.driver_result.output_artifacts if item.name == "claude_code_preflight"
    )
    preflight_payload = json.loads(Path(preflight.uri).read_text(encoding="utf-8"))
    assert preflight_payload["selected_mode"] == "bypassPermissions"
    assert preflight_payload["attempted_modes"] == ["acceptEdits", "bypassPermissions"]
