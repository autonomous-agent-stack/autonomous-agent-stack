#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml_like(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if yaml is None:
            raise RuntimeError("PyYAML is required to read CrewAI agent manifests")
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"invalid manifest payload: {path}")
    return payload


def _write_result(
    *,
    result_path: Path,
    run_id: str,
    agent_id: str,
    attempt: int,
    status: str,
    summary: str,
    changed_paths: list[str] | None = None,
    recommended_action: str = "human_review",
    error: str | None = None,
    duration_ms: int = 0,
    commands: int = 0,
    output_artifacts: list[dict[str, Any]] | None = None,
) -> None:
    payload = {
        "protocol_version": "aep/v0",
        "run_id": run_id,
        "agent_id": agent_id,
        "attempt": attempt,
        "status": status,
        "summary": summary[:4000],
        "changed_paths": changed_paths or [],
        "output_artifacts": output_artifacts or [],
        "metrics": {
            "duration_ms": duration_ms,
            "steps": 1 if commands else 0,
            "commands": commands,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": recommended_action,
        "error": error,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _last_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    for line in reversed(lines):
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def main() -> int:
    workspace = Path(os.environ["AEP_WORKSPACE"]).resolve()
    artifact_dir = Path(os.environ["AEP_ARTIFACT_DIR"]).resolve()
    job_path = Path(os.environ["AEP_JOB_SPEC"]).resolve()
    result_path = Path(os.environ["AEP_RESULT_PATH"]).resolve()
    attempt = int(os.environ.get("AEP_ATTEMPT", "1"))
    repo_root = Path.cwd().resolve()

    job = _read_json(job_path)
    run_id = str(job.get("run_id") or "crewai-run")
    agent_id = str(job.get("agent_id") or "crewai")
    policy = job.get("policy") if isinstance(job.get("policy"), dict) else {}
    timeout_seconds = int(policy.get("timeout_sec") or 900)

    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    started = time.perf_counter()
    if not manifest_path.exists():
        _write_result(
            result_path=result_path,
            run_id=run_id,
            agent_id=agent_id,
            attempt=attempt,
            status="contract_error",
            summary=f"CrewAI manifest not found: {manifest_path}",
            recommended_action="reject",
            error=f"manifest not found: {manifest_path}",
        )
        return 40

    manifest = _read_yaml_like(manifest_path)
    crewai_meta = dict((manifest.get("metadata") or {}).get("crewai") or {})
    if crewai_meta.get("require_package"):
        required_import = str(crewai_meta.get("required_import") or "crewai").strip() or "crewai"
        try:
            __import__(required_import)
        except Exception as exc:
            _write_result(
                result_path=result_path,
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                status="contract_error",
                summary=(
                    f"{required_import} dependency is missing. Run `make crewai-setup` before "
                    "using agents that require the CrewAI package."
                ),
                recommended_action="reject",
                error=str(exc),
            )
            return 40

    command = _string_list(crewai_meta.get("command"))
    module = str(crewai_meta.get("entrypoint") or "").strip()
    if not command:
        if not module:
            _write_result(
                result_path=result_path,
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                status="contract_error",
                summary="CrewAI manifest must set metadata.crewai.entrypoint or metadata.crewai.command.",
                recommended_action="reject",
                error="missing crewai entrypoint",
            )
            return 40
        command = [sys.executable, "-m", module]

    env = os.environ.copy()
    env["AAS_TASK"] = str(job.get("task") or "")
    env["AAS_AGENT_ID"] = agent_id
    env["AAS_RUN_ID"] = run_id
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(workspace),
            str(workspace / "src"),
            env.get("PYTHONPATH", ""),
        ]
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    crew_stdout = artifact_dir / "crewai_stdout.log"
    crew_stderr = artifact_dir / "crewai_stderr.log"
    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        crew_stdout.write_text(exc.stdout or "", encoding="utf-8")
        crew_stderr.write_text(exc.stderr or "", encoding="utf-8")
        _write_result(
            result_path=result_path,
            run_id=run_id,
            agent_id=agent_id,
            attempt=attempt,
            status="timed_out",
            summary=f"CrewAI agent timed out after {timeout_seconds}s.",
            recommended_action="retry",
            error=f"timeout after {timeout_seconds}s",
            duration_ms=duration_ms,
            commands=1,
        )
        return 124

    duration_ms = int((time.perf_counter() - started) * 1000)
    crew_stdout.write_text(completed.stdout or "", encoding="utf-8")
    crew_stderr.write_text(completed.stderr or "", encoding="utf-8")
    payload = _last_json_object(completed.stdout or "")

    if completed.returncode != 0:
        summary = ""
        if payload is not None:
            summary = str(payload.get("summary") or payload.get("error") or "").strip()
        if not summary:
            summary = (completed.stderr or completed.stdout or "CrewAI agent failed.").strip()
        _write_result(
            result_path=result_path,
            run_id=run_id,
            agent_id=agent_id,
            attempt=attempt,
            status="failed",
            summary=summary,
            recommended_action="retry",
            error=(completed.stderr or summary).strip()[:4000],
            duration_ms=duration_ms,
            commands=1,
        )
        return completed.returncode

    summary = "CrewAI agent completed."
    changed_paths: list[str] = []
    output_artifacts: list[dict[str, Any]] = []
    recommended_action = "promote"
    if payload is not None:
        summary = str(payload.get("summary") or summary).strip() or summary
        changed_paths = _string_list(payload.get("changed_paths"))
        recommended_action = str(payload.get("recommended_action") or recommended_action).strip()
        raw_artifacts = payload.get("output_artifacts")
        if isinstance(raw_artifacts, list):
            output_artifacts = [item for item in raw_artifacts if isinstance(item, dict)]
    else:
        text = (completed.stdout or "").strip()
        if text:
            summary = text[-4000:]

    _write_result(
        result_path=result_path,
        run_id=run_id,
        agent_id=agent_id,
        attempt=attempt,
        status="succeeded",
        summary=summary,
        changed_paths=changed_paths,
        recommended_action=recommended_action if recommended_action else "promote",
        duration_ms=duration_ms,
        commands=1,
        output_artifacts=output_artifacts,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
