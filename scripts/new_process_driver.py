#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a new AEP process driver.")
    parser.add_argument("agent_id", help="agent id, for example local_repo_digest")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
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


def build_manifest(agent_id: str) -> str:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": f"drivers/{agent_id}_adapter.sh",
        "version": "0.1",
        "capabilities": ["read_repo", "write_repo", "run_shell", "produce_patchable_changes"],
        "default_mode": "apply_in_workspace",
        "policy_defaults": {
            "timeout_sec": 900,
            "max_steps": 1,
            "network": "disabled",
            "network_allowlist": [],
            "tool_allowlist": ["read", "write", "bash"],
            "allowed_paths": ["src/**", "tests/**", "docs/**"],
            "forbidden_paths": [".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
            "max_changed_files": 10,
            "max_patch_lines": 400,
            "allow_binary_changes": False,
            "cleanup_on_success": True,
            "retain_workspace_on_failure": True,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_adapter(agent_id: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

require_env() {{
  local key="$1"
  if [[ -z "${{!key:-}}" ]]; then
    echo "[aep][{agent_id}] missing env: ${{key}}" >&2
    exit 40
  fi
}}

require_env "AEP_WORKSPACE"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"

PY_BIN="${{PYTHON_BIN:-python3}}"

"${{PY_BIN}}" - "${{AEP_JOB_SPEC}}" "${{AEP_RESULT_PATH}}" <<'PY'
import json
import sys
from pathlib import Path

job_path = Path(sys.argv[1])
result_path = Path(sys.argv[2])
payload = json.loads(job_path.read_text(encoding="utf-8"))

result = {{
    "protocol_version": "aep/v0",
    "run_id": payload.get("run_id", "unknown-run"),
    "agent_id": payload.get("agent_id", "{agent_id}"),
    "attempt": 1,
    "status": "contract_error",
    "summary": "scaffolded adapter not implemented",
    "changed_paths": [],
    "output_artifacts": [],
    "metrics": {{
        "duration_ms": 0,
        "steps": 0,
        "commands": 0,
        "prompt_tokens": None,
        "completion_tokens": None,
    }},
    "recommended_action": "reject",
    "error": "replace scaffold logic in drivers/{agent_id}_adapter.sh",
}}
result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
PY

exit 40
"""


def build_test(agent_id: str) -> str:
    return f"""from __future__ import annotations

from pathlib import Path


def test_{agent_id}_scaffold_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "configs" / "agents" / "{agent_id}.yaml").exists()
    assert (repo_root / "drivers" / "{agent_id}_adapter.sh").exists()
"""


def build_readme_snippet(agent_id: str) -> str:
    return f"""Use this driver via:

```bash
make agent-run AEP_AGENT={agent_id} AEP_TASK="Describe the task here."
```

Generated files:

- `configs/agents/{agent_id}.yaml`
- `drivers/{agent_id}_adapter.sh`
- `tests/test_{agent_id}_adapter.py`
"""


def main() -> int:
    args = parse_args()
    agent_id = normalize_agent_id(args.agent_id)
    repo_root = Path(args.root).resolve()

    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    adapter_path = repo_root / "drivers" / f"{agent_id}_adapter.sh"
    test_path = repo_root / "tests" / f"test_{agent_id}_adapter.py"
    snippet_path = repo_root / "docs" / "agent-snippets" / f"{agent_id}.md"

    write_text(manifest_path, build_manifest(agent_id), force=args.force)
    write_text(adapter_path, build_adapter(agent_id), force=args.force)
    adapter_path.chmod(0o755)
    write_text(test_path, build_test(agent_id), force=args.force)
    write_text(snippet_path, build_readme_snippet(agent_id), force=args.force)

    print(json.dumps(
        {
            "agent_id": agent_id,
            "manifest": manifest_path.as_posix(),
            "adapter": adapter_path.as_posix(),
            "test": test_path.as_posix(),
            "readme_snippet": snippet_path.as_posix(),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
