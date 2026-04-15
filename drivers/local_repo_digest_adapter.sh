#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][local_repo_digest] missing env: ${key}" >&2
    exit 40
  fi
}

require_env "AEP_WORKSPACE"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"
require_env "AEP_ARTIFACT_DIR"

PY_BIN="${PYTHON_BIN:-python3}"

"${PY_BIN}" - "${AEP_WORKSPACE}" "${AEP_JOB_SPEC}" "${AEP_RESULT_PATH}" "${AEP_ARTIFACT_DIR}" <<'PY'
from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from pathlib import Path


def is_ignored(path: Path) -> bool:
    parts = set(path.parts)
    return any(
        name in parts
        for name in {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache", ".masfactory_runtime"}
    )


def classify(path: Path) -> str:
    if path.suffix:
        return path.suffix.lower()
    return "<no_ext>"


workspace = Path(__import__("sys").argv[1])
job_path = Path(__import__("sys").argv[2])
result_path = Path(__import__("sys").argv[3])
artifact_dir = Path(__import__("sys").argv[4])
payload = json.loads(job_path.read_text(encoding="utf-8"))

started = time.perf_counter()
files = [
    path.relative_to(workspace)
    for path in workspace.rglob("*")
    if path.is_file() and not is_ignored(path.relative_to(workspace))
]
file_types = Counter(classify(path) for path in files)
top_dirs = Counter(path.parts[0] if len(path.parts) > 1 else "<root>" for path in files)
notable = [
    candidate
    for candidate in (
        Path("README.md"),
        Path("Makefile"),
        Path("pyproject.toml"),
        Path("configs/agents"),
        Path("drivers"),
        Path("tests"),
    )
    if (workspace / candidate).exists()
]

digest_rel = Path("docs/local_repo_digest.md")
digest_path = workspace / digest_rel
digest_path.parent.mkdir(parents=True, exist_ok=True)

digest_lines = [
    "# Local Repository Digest",
    "",
    f"- task: {payload.get('task', '').strip() or 'unspecified'}",
    f"- total files: {len(files)}",
    f"- top-level areas: {', '.join(f'{name} ({count})' for name, count in top_dirs.most_common(6)) or 'none'}",
    "",
    "## Notable Entrypoints",
]
if notable:
    digest_lines.extend(f"- `{path.as_posix()}`" for path in notable)
else:
    digest_lines.append("- none")

digest_lines.extend(
    [
        "",
        "## File Type Breakdown",
    ]
)
if file_types:
    digest_lines.extend(
        f"- `{suffix}`: {count}" for suffix, count in file_types.most_common(10)
    )
else:
    digest_lines.append("- none")

digest_lines.extend(
    [
        "",
        "## Sample Paths",
    ]
)
if files:
    digest_lines.extend(f"- `{path.as_posix()}`" for path in files[:12])
else:
    digest_lines.append("- none")

digest_path.write_text("\n".join(digest_lines) + "\n", encoding="utf-8")
artifact_report_path = artifact_dir / "local_repo_digest.md"
shutil.copyfile(digest_path, artifact_report_path)

stats_path = artifact_dir / "local_repo_digest_stats.json"
stats_payload = {
    "total_files": len(files),
    "file_types": file_types.most_common(10),
    "top_dirs": top_dirs.most_common(10),
    "notable": [path.as_posix() for path in notable],
}
stats_path.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2), encoding="utf-8")

duration_ms = int((time.perf_counter() - started) * 1000)
result = {
    "protocol_version": "aep/v0",
    "run_id": payload.get("run_id", "unknown-run"),
    "agent_id": payload.get("agent_id", "local_repo_digest"),
    "attempt": 1,
    "status": "succeeded",
    "summary": f"Generated repository digest at {digest_rel.as_posix()}",
    "changed_paths": [digest_rel.as_posix()],
    "output_artifacts": [
        {
            "name": "local_repo_digest_report",
            "kind": "report",
            "uri": str(artifact_report_path),
            "sha256": None,
        },
        {
            "name": "local_repo_digest_stats",
            "kind": "report",
            "uri": str(stats_path),
            "sha256": None,
        }
    ],
    "metrics": {
        "duration_ms": duration_ms,
        "steps": 1,
        "commands": 0,
        "prompt_tokens": None,
        "completion_tokens": None,
    },
    "recommended_action": "promote",
    "error": None,
}
result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
PY

exit 0
