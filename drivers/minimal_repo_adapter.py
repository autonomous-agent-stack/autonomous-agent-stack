#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value
    raise RuntimeError(f"missing env: {key}")


def _load_job(job_path: Path) -> dict[str, object]:
    return json.loads(job_path.read_text(encoding="utf-8"))


def _single_line_marker(job: dict[str, object]) -> tuple[str | None, str | None]:
    metadata = job.get("metadata")
    if isinstance(metadata, dict):
        raw = str(metadata.get("demo_append_text") or "").strip()
        if raw:
            if "\n" in raw or "\r" in raw:
                return None, "demo_append_text must be a single line"
            return raw, None
    return "minimal_repo touched demo.md", None


def _changed_paths(target: Path, workspace: Path, before: str, after: str) -> list[str]:
    if before == after:
        return []
    return [target.relative_to(workspace).as_posix()]


def _build_result(
    *,
    job: dict[str, object],
    attempt: int,
    status: str,
    summary: str,
    changed_paths: list[str],
    recommended_action: str,
    error: str | None = None,
) -> dict[str, object]:
    return {
        "protocol_version": "aep/v0",
        "run_id": str(job["run_id"]),
        "agent_id": str(job["agent_id"]),
        "attempt": attempt,
        "status": status,
        "summary": summary,
        "changed_paths": changed_paths,
        "output_artifacts": [],
        "metrics": {
            "duration_ms": 0,
            "steps": 1,
            "commands": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": recommended_action,
        "error": error,
    }


def main() -> int:
    workspace = Path(_require_env("AEP_WORKSPACE"))
    result_path = Path(_require_env("AEP_RESULT_PATH"))
    job_path = Path(_require_env("AEP_JOB_SPEC"))
    attempt = int(os.environ.get("AEP_ATTEMPT", "1"))
    job = _load_job(job_path)

    target = workspace / "docs" / "demo.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    before = target.read_text(encoding="utf-8") if target.exists() else ""
    marker_line, marker_error = _single_line_marker(job)
    if marker_error is not None:
        payload = _build_result(
            job=job,
            attempt=attempt,
            status="failed",
            summary=marker_error,
            changed_paths=[],
            recommended_action="human_review",
            error=marker_error,
        )
        result_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 0

    existing_lines = before.splitlines()
    has_marker_line = marker_line in existing_lines
    if has_marker_line:
        after = before
    else:
        separator = "" if not before or before.endswith("\n") else "\n"
        after = f"{before}{separator}{marker_line}\n"
    if after != before:
        target.write_text(after, encoding="utf-8")

    changed_paths = _changed_paths(target, workspace, before, after)
    status = "succeeded" if changed_paths else "partial"
    recommended_action = "promote" if changed_paths else "human_review"
    summary = (
        "appended demo marker to docs/demo.md"
        if changed_paths
        else "no-op; demo marker already present"
    )

    payload = _build_result(
        job=job,
        attempt=attempt,
        status=status,
        summary=summary,
        changed_paths=changed_paths,
        recommended_action=recommended_action,
    )
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
