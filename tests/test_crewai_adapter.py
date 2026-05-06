from __future__ import annotations

import shutil
from pathlib import Path

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _write_demo_repo(repo_root: Path, *, missing_dependency: bool = False) -> None:
    (repo_root / "drivers").mkdir(parents=True)
    shutil.copy2(Path.cwd() / "drivers" / "crewai_adapter.py", repo_root / "drivers" / "crewai_adapter.py")
    (repo_root / "drivers" / "crewai_adapter.py").chmod(0o755)

    (repo_root / "configs" / "agents").mkdir(parents=True)
    required_import = (
        '"required_import": "definitely_missing_crewai_dependency_xyz",'
        if missing_dependency
        else ""
    )
    (repo_root / "configs" / "agents" / "demo_crewai.yaml").write_text(
        f"""
{{
  "id": "demo_crewai",
  "kind": "process",
  "entrypoint": "drivers/crewai_adapter.py",
  "execution_semantics": "patch",
  "default_mode": "apply_in_workspace",
  "policy_defaults": {{
    "timeout_sec": 30,
    "allowed_paths": ["apps/**"],
    "forbidden_paths": [".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
    "max_changed_files": 3,
    "max_patch_lines": 100,
    "cleanup_on_success": true,
    "retain_workspace_on_failure": true
  }},
  "metadata": {{
    "crewai": {{
      "entrypoint": "examples.crewai_agents.demo.crew",
      "require_package": {str(missing_dependency).lower()},
      {required_import}
      "command": []
    }}
  }}
}}
""",
        encoding="utf-8",
    )

    package_dir = repo_root / "examples" / "crewai_agents" / "demo"
    package_dir.mkdir(parents=True)
    (repo_root / "examples" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "examples" / "crewai_agents" / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "crew.py").write_text(
        """
from __future__ import annotations

import json
from pathlib import Path

out = Path("apps") / "demo" / "result.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("demo result\\n", encoding="utf-8")
print(json.dumps({"summary": "done", "changed_paths": [out.as_posix()], "recommended_action": "promote"}))
""",
        encoding="utf-8",
    )


def test_crewai_adapter_maps_success_to_governed_driver_result(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_demo_repo(repo_root)

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(JobSpec(run_id="run-crewai", agent_id="demo_crewai", task="demo"))

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["apps/demo/result.md"]


def test_crewai_adapter_maps_missing_dependency_to_contract_error(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_demo_repo(repo_root, missing_dependency=True)

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(JobSpec(run_id="run-crewai-missing", agent_id="demo_crewai", task="demo"))

    assert summary.final_status == "failed"
    assert summary.driver_result.status == "contract_error"
    assert "definitely_missing_crewai_dependency_xyz" in (summary.driver_result.summary or "")
