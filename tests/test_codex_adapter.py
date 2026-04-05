from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

from autoresearch.agent_protocol.models import ExecutionPolicy, JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _write_manifest(repo_root: Path, entrypoint: str) -> None:
    manifest_path = repo_root / "configs" / "agents" / "codex.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "id": "codex",
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
    source = source_root / "drivers" / "codex_adapter.sh"
    target = repo_root / "drivers" / "codex_adapter.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(0o755)


def test_codex_dry_run_emits_patch_candidate(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/codex_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.setenv("CODEX_DRY_RUN", "1")
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-codex-dry",
            agent_id="codex",
            task="Create a single file in the allowed path.",
            policy=ExecutionPolicy(
                allowed_paths=["src/generated_codex.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.status == "succeeded"
    assert summary.validation.passed is True
    assert summary.driver_result.changed_paths == ["src/generated_codex.py"]

    patch_text = Path(summary.promotion_patch_uri or "").read_text(encoding="utf-8")
    assert "src/generated_codex.py" in patch_text


def test_codex_missing_cli_is_contract_error(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/codex_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CODEX_DRY_RUN", raising=False)
    monkeypatch.setenv("CODEX_BIN", "/definitely/missing/codex")
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-codex-missing",
            agent_id="codex",
            task="Create a single file in the allowed path.",
        )
    )

    assert summary.driver_result.status == "contract_error"
    assert summary.final_status == "failed"
    assert "Codex CLI not found" in (summary.driver_result.error or "")


def test_codex_auto_mode_falls_back_to_danger_full_access(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/codex_adapter.sh")

    fake_codex = tmp_path / "fake_codex.sh"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

mode="unknown"
last_message=""
workspace=""
prompt=""
while (($#)); do
  case "$1" in
    exec)
      shift
      ;;
    --full-auto)
      mode="full_auto"
      shift
      ;;
    --sandbox)
      if [[ "${2:-}" == "danger-full-access" ]]; then
        mode="danger_full_access"
      fi
      shift 2
      ;;
    --skip-git-repo-check|--color)
      shift
      if [[ "${1:-}" != "" && "$0" != "$1" ]]; then
        if [[ "$1" != "-C" && "$1" != "-o" ]]; then
          shift
        fi
      fi
      ;;
    -C)
      workspace="$2"
      shift 2
      ;;
    -o)
      last_message="$2"
      shift 2
      ;;
    *)
      prompt="$1"
      shift
      ;;
  esac
done

if [[ "$mode" == "full_auto" ]]; then
  echo "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted" >&2
  printf 'Could not complete the file creation because local tool execution is failing in this session with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.\n\nNo files changed.\n' >"$last_message"
  exit 0
fi

mkdir -p "$workspace/src"
cat >"$workspace/src/demo_math.py" <<'PY'
def add(a, b):
    return a + b
PY
printf 'Codex completed in %s mode. Changed file: src/demo_math.py\\n' "$mode" >"$last_message"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{\"access_token\":\"ok\"}\n", encoding="utf-8")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CODEX_DRY_RUN", raising=False)
    monkeypatch.setenv("CODEX_BIN", str(fake_codex))
    monkeypatch.setenv("CODEX_AUTH_FILE", str(auth_file))
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-codex-auto",
            agent_id="codex",
            task="Create src/demo_math.py with add(a,b).",
            policy=ExecutionPolicy(
                allowed_paths=["src/demo_math.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.agent_id == "codex"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["src/demo_math.py"]

    preflight = next(
        item for item in summary.driver_result.output_artifacts if item.name == "codex_preflight"
    )
    preflight_payload = json.loads(Path(preflight.uri).read_text(encoding="utf-8"))
    assert preflight_payload["selected_mode"] == "danger_full_access"
    assert preflight_payload["attempted_modes"] == ["full_auto", "danger_full_access"]


def test_codex_missing_auth_is_contract_error(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/codex_adapter.sh")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CODEX_DRY_RUN", raising=False)
    monkeypatch.setenv("CODEX_BIN", "/bin/echo")
    monkeypatch.setenv("CODEX_AUTH_FILE", str(tmp_path / "missing-auth.json"))
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-codex-auth-missing",
            agent_id="codex",
            task="Create a single file in the allowed path.",
        )
    )

    assert summary.driver_result.status == "contract_error"
    assert summary.final_status == "failed"
    assert "auth file missing" in (summary.driver_result.error or "").lower()


def test_codex_auto_mode_kills_stuck_full_auto_on_live_bwrap_error(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "__init__.py").write_text("", encoding="utf-8")
    _copy_adapter(repo_root)
    _write_manifest(repo_root, "drivers/codex_adapter.sh")

    fake_codex = tmp_path / "fake_codex_hang.sh"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

mode="unknown"
last_message=""
workspace=""
while (($#)); do
  case "$1" in
    exec)
      shift
      ;;
    --full-auto)
      mode="full_auto"
      shift
      ;;
    --sandbox)
      if [[ "${2:-}" == "danger-full-access" ]]; then
        mode="danger_full_access"
      fi
      shift 2
      ;;
    --skip-git-repo-check|--color)
      shift
      if [[ "${1:-}" != "" && "$0" != "$1" ]]; then
        if [[ "$1" != "-C" && "$1" != "-o" ]]; then
          shift
        fi
      fi
      ;;
    -C)
      workspace="$2"
      shift 2
      ;;
    -o)
      last_message="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$mode" == "full_auto" ]]; then
  trap 'exit 143' TERM
  echo "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted" >&2
  sleep 30
  exit 0
fi

mkdir -p "$workspace/src"
cat >"$workspace/src/demo_math.py" <<'PY'
def add(a, b):
    return a + b
PY
printf 'Codex completed in %s mode. Changed file: src/demo_math.py\\n' "$mode" >"$last_message"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{\"access_token\":\"ok\"}\n", encoding="utf-8")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.delenv("CODEX_DRY_RUN", raising=False)
    monkeypatch.setenv("CODEX_BIN", str(fake_codex))
    monkeypatch.setenv("CODEX_AUTH_FILE", str(auth_file))
    monkeypatch.setenv("PYTHON_BIN", sys.executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-codex-auto-live-bwrap",
            agent_id="codex",
            task="Create src/demo_math.py with add(a,b).",
            policy=ExecutionPolicy(
                allowed_paths=["src/demo_math.py"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.agent_id == "codex"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["src/demo_math.py"]

    preflight = next(
        item for item in summary.driver_result.output_artifacts if item.name == "codex_preflight"
    )
    preflight_payload = json.loads(Path(preflight.uri).read_text(encoding="utf-8"))
    assert preflight_payload["selected_mode"] == "danger_full_access"
    assert preflight_payload["attempted_modes"] == ["full_auto", "danger_full_access"]
