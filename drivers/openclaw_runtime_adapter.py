#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autoresearch.agent_protocol.models import ArtifactRef, DriverMetrics, DriverResult, JobSpec
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime import (
    OpenClawRuntimeContractError,
    OpenClawRuntimeExecutionError,
    OpenClawRuntimeService,
)
from autoresearch.shared.models import OpenClawSessionRead
from autoresearch.shared.openclaw_runtime_contract import (
    OpenClawRuntimeJobSpec,
    OpenClawRuntimeResult,
)
from autoresearch.shared.store import SQLiteModelRepository


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _artifact_ref(path: Path, name: str) -> ArtifactRef:
    return ArtifactRef(name=name, kind="custom", uri=str(path))


def _write_driver_result(path: Path, result: DriverResult) -> None:
    _write_json(path, result.model_dump(mode="json"))


def _load_env_path(name: str) -> Path:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise OpenClawRuntimeContractError(f"missing required env var: {name}")
    return Path(value)


def _api_db_path() -> Path:
    raw = (os.environ.get("AUTORESEARCH_API_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        Path(tempfile.gettempdir()) / "autoresearch_openclaw_runtime" / "evaluations.sqlite3"
    ).resolve()


def _is_within_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_runtime_db_path(*, repo_root: Path, workspace_root: Path) -> Path:
    db_path = _api_db_path()
    for blocked_root in (repo_root.resolve(), workspace_root.resolve()):
        if _is_within_root(db_path, blocked_root):
            raise OpenClawRuntimeContractError(
                f"runtime persistence path must stay outside repo/workspace roots: {db_path}"
            )
    return db_path


def _write_failure_outputs(
    *,
    result_path: Path,
    runtime_result_path: Path,
    request_artifact_path: Path | None,
    job: JobSpec | None,
    action: str,
    session_id: str,
    skill_id: str | None,
    status: str,
    summary: str,
    error: str,
    recommended_action: str,
) -> None:
    runtime_result = OpenClawRuntimeResult(
        job_id=job.run_id if job is not None else "unknown",
        action=action,
        session_id=session_id,
        success=False,
        summary=summary,
        error=error,
        skill_id=skill_id,
        metadata={"action": action},
    )
    _write_json(runtime_result_path, runtime_result.model_dump(mode="json"))

    output_artifacts = [_artifact_ref(runtime_result_path, "openclaw_runtime_result")]
    if request_artifact_path is not None and request_artifact_path.exists():
        output_artifacts.insert(0, _artifact_ref(request_artifact_path, "openclaw_runtime_request"))

    _write_driver_result(
        result_path,
        DriverResult(
            run_id=job.run_id if job is not None else "unknown",
            agent_id=job.agent_id if job is not None else "openclaw_runtime",
            status=status,
            summary=summary,
            changed_paths=[],
            output_artifacts=output_artifacts,
            metrics=DriverMetrics(),
            recommended_action=recommended_action,
            error=error,
        ),
    )


async def _run() -> int:
    workspace_root = _load_env_path("AEP_WORKSPACE")
    artifacts_dir = _load_env_path("AEP_ARTIFACT_DIR")
    job_path = _load_env_path("AEP_JOB_SPEC")
    result_path = _load_env_path("AEP_RESULT_PATH")

    request_artifact_path = artifacts_dir / "openclaw_runtime_request.json"
    runtime_result_path = artifacts_dir / "openclaw_runtime_result.json"

    job: JobSpec | None = None
    spec: OpenClawRuntimeJobSpec | None = None
    try:
        job_payload = json.loads(job_path.read_text(encoding="utf-8"))
        job = JobSpec.model_validate(job_payload)
        runtime_payload = job.metadata.get("openclaw_runtime")
        if runtime_payload is None:
            raise OpenClawRuntimeContractError("JobSpec.metadata.openclaw_runtime is required")
        if job.agent_id != "openclaw_runtime":
            raise OpenClawRuntimeContractError(
                "openclaw runtime jobs must target agent_id=openclaw_runtime"
            )
        if job.mode != "runtime_only":
            raise OpenClawRuntimeContractError("openclaw runtime jobs must use mode=runtime_only")

        spec = OpenClawRuntimeJobSpec.model_validate(runtime_payload)
        if spec.job_id != job.run_id:
            raise OpenClawRuntimeContractError("openclaw runtime job_id must match JobSpec.run_id")

        _write_json(request_artifact_path, spec.model_dump(mode="json"))
        db_path = _resolve_runtime_db_path(
            repo_root=REPO_ROOT,
            workspace_root=workspace_root,
        )

        openclaw_service = OpenClawCompatService(
            repository=SQLiteModelRepository(
                db_path=db_path,
                table_name="openclaw_sessions",
                model_cls=OpenClawSessionRead,
            )
        )
        runtime_service = OpenClawRuntimeService(
            repo_root=REPO_ROOT,
            workspace_root=workspace_root,
            openclaw_service=openclaw_service,
        )
        runtime_result = await runtime_service.execute(spec)
    except OpenClawRuntimeContractError as exc:
        _write_failure_outputs(
            result_path=result_path,
            runtime_result_path=runtime_result_path,
            request_artifact_path=request_artifact_path,
            job=job,
            action=spec.action if spec is not None else "send_message",
            session_id=spec.session_id if spec is not None else "",
            skill_id=spec.skill_id if spec is not None else None,
            status="contract_error",
            summary="openclaw runtime contract error",
            error=str(exc),
            recommended_action="human_review",
        )
        return 40
    except OpenClawRuntimeExecutionError as exc:
        _write_failure_outputs(
            result_path=result_path,
            runtime_result_path=runtime_result_path,
            request_artifact_path=request_artifact_path,
            job=job,
            action=spec.action if spec is not None else "run_skill",
            session_id=spec.session_id if spec is not None else "",
            skill_id=spec.skill_id if spec is not None else None,
            status="failed",
            summary="openclaw runtime execution failed",
            error=str(exc),
            recommended_action="fallback",
        )
        return 20
    except Exception as exc:
        _write_failure_outputs(
            result_path=result_path,
            runtime_result_path=runtime_result_path,
            request_artifact_path=request_artifact_path,
            job=job,
            action=spec.action if spec is not None else "send_message",
            session_id=spec.session_id if spec is not None else "",
            skill_id=spec.skill_id if spec is not None else None,
            status="contract_error",
            summary="openclaw runtime adapter crashed",
            error=f"{exc.__class__.__name__}: {exc}",
            recommended_action="human_review",
        )
        return 40

    _write_json(runtime_result_path, runtime_result.model_dump(mode="json"))
    _write_driver_result(
        result_path,
        DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary=f"OpenClaw runtime action completed: {spec.action}",
            changed_paths=[],
            output_artifacts=[
                _artifact_ref(request_artifact_path, "openclaw_runtime_request"),
                _artifact_ref(runtime_result_path, "openclaw_runtime_result"),
            ],
            metrics=DriverMetrics(),
            recommended_action="human_review",
            error=None,
        ),
    )
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
