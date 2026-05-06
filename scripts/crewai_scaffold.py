#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold an AAS-governed CrewAI-style agent.")
    parser.add_argument("agent", help="lower_snake_case agent id")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--force", action="store_true", help="overwrite generated files")
    return parser.parse_args()


def normalize_agent_id(value: str) -> str:
    agent_id = value.strip()
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", agent_id):
        raise ValueError("agent id must be lower_snake_case")
    return agent_id


def write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_text(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_manifest(agent_id: str) -> str:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": "drivers/crewai_adapter.py",
        "version": "0.1",
        "execution_semantics": "patch",
        "capabilities": ["crewai", "write_repo", "produce_patchable_changes"],
        "default_mode": "apply_in_workspace",
        "policy_defaults": {
            "timeout_sec": 300,
            "max_steps": 1,
            "network": "disabled",
            "network_allowlist": [],
            "tool_allowlist": ["read", "write", "bash"],
            "allowed_paths": ["apps/**", "docs/**", "tests/**"],
            "forbidden_paths": [".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
            "max_changed_files": 6,
            "max_patch_lines": 1200,
            "allow_binary_changes": False,
            "cleanup_on_success": True,
            "retain_workspace_on_failure": True,
        },
        "metadata": {
            "crewai": {
                "project_path": f"examples/crewai_agents/{agent_id}",
                "entrypoint": f"examples.crewai_agents.{agent_id}.crew",
                "output_mode": "json",
                "require_package": False,
            }
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_crew(agent_id: str) -> str:
    return f'''from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "task"


def main() -> int:
    task = os.getenv("AAS_TASK", "Draft an AAS governed CrewAI artifact.").strip()
    run_id = os.getenv("AAS_RUN_ID", "crewai-demo")
    out_dir = Path("apps") / "crewai_demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{{_slug(task)[:48]}}.md"
    out_path.write_text(
        "# CrewAI Governed Demo\\n\\n"
        f"- agent: {agent_id}\\n"
        f"- run_id: {{run_id}}\\n"
        f"- task: {{task}}\\n\\n"
        "This artifact was produced by a CrewAI-style agent running under AAS policy gates.\\n",
        encoding="utf-8",
    )
    print(json.dumps({{
        "summary": f"CrewAI-style agent {agent_id} completed: {{task}}",
        "changed_paths": [out_path.as_posix()],
        "recommended_action": "promote",
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_init() -> str:
    return '"""AAS-governed CrewAI-style demo package."""\n'


def build_snippet(agent_id: str) -> str:
    return f"""# {agent_id} CrewAI Agent

中文：这个示例展示如何把 CrewAI 风格的 agent 放进 AAS 的 AEP runner、策略、验证和审计闭环。
English: This example shows how to run a CrewAI-style agent through the AAS AEP runner, policy, validation, and audit loop.

```bash
make crewai-run AGENT={agent_id} TASK="Write a short governed demo artifact"
```
"""


def main() -> int:
    args = parse_args()
    agent_id = normalize_agent_id(args.agent)
    repo_root = Path(args.root).resolve()

    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    package_root = repo_root / "examples" / "crewai_agents" / agent_id
    snippet_path = repo_root / "docs" / "agent-snippets" / f"{agent_id}.md"

    write_text(manifest_path, build_manifest(agent_id), force=args.force)
    ensure_text(repo_root / "examples" / "__init__.py", build_init())
    ensure_text(repo_root / "examples" / "crewai_agents" / "__init__.py", build_init())
    write_text(package_root / "__init__.py", build_init(), force=args.force)
    write_text(package_root / "crew.py", build_crew(agent_id), force=args.force)
    write_text(snippet_path, build_snippet(agent_id), force=args.force)

    print(json.dumps(
        {
            "agent_id": agent_id,
            "manifest": manifest_path.as_posix(),
            "entrypoint": (package_root / "crew.py").as_posix(),
            "snippet": snippet_path.as_posix(),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
