#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][local_pr_patch_digest] missing env: ${key}" >&2
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
import subprocess
import time
from pathlib import Path
import sys


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} failed")
    return completed


workspace = Path(sys.argv[1])
job_path = Path(sys.argv[2])
result_path = Path(sys.argv[3])
artifact_dir = Path(sys.argv[4])
payload = json.loads(job_path.read_text(encoding="utf-8"))
started = time.perf_counter()

try:
    inside = run_git(["rev-parse", "--is-inside-work-tree"]).stdout.strip()
    if inside != "true":
        raise RuntimeError("repository root is not a git work tree")

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    has_origin_main = run_git(
        ["show-ref", "--verify", "--quiet", "refs/remotes/origin/main"],
        check=False,
    ).returncode == 0

    if has_origin_main:
        base_label = "origin/main"
        base_ref = run_git(["merge-base", "HEAD", "origin/main"]).stdout.strip()
    else:
        head_parent = run_git(["rev-parse", "HEAD~1"], check=False)
        if head_parent.returncode != 0:
            raise RuntimeError("local_pr_patch_digest requires either origin/main or at least two commits")
        base_label = "HEAD~1"
        base_ref = head_parent.stdout.strip()

    name_status = run_git(["diff", "--name-status", f"{base_ref}..HEAD"]).stdout.splitlines()
    numstat_lines = run_git(["diff", "--numstat", f"{base_ref}..HEAD"]).stdout.splitlines()
    shortstat = run_git(["diff", "--shortstat", f"{base_ref}..HEAD"]).stdout.strip() or "no committed diff"
    dirty_status = run_git(["status", "--short"]).stdout.splitlines()

    insertions = 0
    deletions = 0
    changed_files: list[str] = []
    for line in numstat_lines:
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if added.isdigit():
            insertions += int(added)
        if removed.isdigit():
            deletions += int(removed)
        changed_files.append(path)

    digest_rel = Path("docs/local_pr_patch_digest.md")
    digest_path = workspace / digest_rel
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_lines = [
        "# Local PR Patch Digest",
        "",
        f"- task: {payload.get('task', '').strip() or 'unspecified'}",
        f"- branch: {branch}",
        f"- base: {base_label}",
        f"- changed files: {len(changed_files)}",
        f"- insertions: {insertions}",
        f"- deletions: {deletions}",
        f"- shortstat: {shortstat}",
        "",
        "## Changed Files",
    ]
    if name_status:
        digest_lines.extend(f"- `{line}`" for line in name_status[:20])
    else:
        digest_lines.append("- none")
    digest_lines.extend(["", "## Dirty Working Tree"])
    if dirty_status:
        digest_lines.extend(f"- `{line}`" for line in dirty_status[:20])
    else:
        digest_lines.append("- clean")
    digest_path.write_text("\n".join(digest_lines) + "\n", encoding="utf-8")
    artifact_report_path = artifact_dir / "local_pr_patch_digest.md"
    shutil.copyfile(digest_path, artifact_report_path)

    stats_path = artifact_dir / "local_pr_patch_digest_stats.json"
    stats_payload = {
        "branch": branch,
        "base_label": base_label,
        "base_ref": base_ref,
        "changed_files": changed_files,
        "insertions": insertions,
        "deletions": deletions,
        "dirty_status": dirty_status,
    }
    stats_path.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    duration_ms = int((time.perf_counter() - started) * 1000)
    result = {
        "protocol_version": "aep/v0",
        "run_id": payload.get("run_id", "unknown-run"),
        "agent_id": payload.get("agent_id", "local_pr_patch_digest"),
        "attempt": 1,
        "status": "succeeded",
        "summary": f"Generated patch digest at {digest_rel.as_posix()} using base {base_label}",
        "changed_paths": [digest_rel.as_posix()],
        "output_artifacts": [
            {
                "name": "local_pr_patch_digest_report",
                "kind": "report",
                "uri": str(artifact_report_path),
                "sha256": None,
            },
            {
                "name": "local_pr_patch_digest_stats",
                "kind": "report",
                "uri": str(stats_path),
                "sha256": None,
            }
        ],
        "metrics": {
            "duration_ms": duration_ms,
            "steps": 1,
            "commands": 4,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": "promote",
        "error": None,
    }
except Exception as exc:
    result = {
        "protocol_version": "aep/v0",
        "run_id": payload.get("run_id", "unknown-run"),
        "agent_id": payload.get("agent_id", "local_pr_patch_digest"),
        "attempt": 1,
        "status": "contract_error",
        "summary": "local_pr_patch_digest could not determine a local diff source",
        "changed_paths": [],
        "output_artifacts": [],
        "metrics": {
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "steps": 0,
            "commands": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": "reject",
        "error": str(exc),
    }

result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
PY

if [[ "$?" -eq 0 ]]; then
  exit 0
fi
exit 40
