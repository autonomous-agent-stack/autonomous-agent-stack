#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autoresearch.agent_protocol.models import RunSummary
from autoresearch.core.dispatch.failure_classifier import classify_remote_terminal
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.shared.models import utc_now
from autoresearch.shared.remote_run_contract import (
    RemoteHeartbeat,
    RemoteRunRecord,
    RemoteRunStatus,
    RemoteRunSummary,
    RemoteTaskSpec,
    RemoteWorkerHealthRead,
)


def healthcheck(*, repo_root: Path | None = None) -> RemoteWorkerHealthRead:
    root = (repo_root or REPO_ROOT).resolve()
    runtime_root = root / ".masfactory_runtime" / "runs"
    runtime_root.mkdir(parents=True, exist_ok=True)
    driver_path = root / "drivers" / "openhands_adapter.sh"
    healthy = driver_path.exists() and os.access(runtime_root, os.W_OK)
    detail = "remote worker ready" if healthy else "remote worker is missing driver or writable runtime root"
    return RemoteWorkerHealthRead(
        healthy=healthy,
        host=socket.gethostname(),
        detail=detail,
        metadata={
            "repo_root": str(root),
            "runtime_root": str(runtime_root),
            "driver_path": str(driver_path),
            "python": sys.executable,
        },
    )


def dispatch(
    *,
    spec: RemoteTaskSpec,
    repo_root: Path | None = None,
    spawner: Callable[..., subprocess.Popen[str]] | None = None,
) -> RemoteRunRecord:
    root = (repo_root or REPO_ROOT).resolve()
    control_dir = _control_dir(root, spec.run_id)
    control_dir.mkdir(parents=True, exist_ok=True)
    task_spec_path = control_dir / "task_spec.json"
    _write_json(task_spec_path, spec.model_dump(mode="json"))
    record = RemoteRunRecord(
        run_id=spec.run_id,
        requested_lane=spec.requested_lane,
        lane=spec.lane,
        status=RemoteRunStatus.QUEUED,
        summary=f"remote dispatch queued for {spec.lane.value} lane",
        artifact_paths=_artifact_paths(root, spec.run_id),
        metadata={
            "runtime_mode": spec.runtime_mode,
            "planner_plan_id": spec.planner_plan_id,
            "planner_candidate_id": spec.planner_candidate_id,
            **spec.metadata,
        },
    )
    launcher = spawner or _spawn_background
    stdout_path = control_dir / "worker.stdout.log"
    stderr_path = control_dir / "worker.stderr.log"
    process = launcher(
        [sys.executable, str(Path(__file__).resolve()), "run-once", "--task-spec", str(task_spec_path)],
        cwd=root,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    record = record.model_copy(
        update={
            "metadata": {
                **record.metadata,
                "launcher_pid": process.pid,
                "worker_stdout": _relpath(root, stdout_path),
                "worker_stderr": _relpath(root, stderr_path),
            }
        }
    )
    _write_json(control_dir / "record.json", record.model_dump(mode="json"))
    _append_event(control_dir / "events.ndjson", {"type": "queued", "pid": process.pid, "recorded_at": utc_now().isoformat()})
    return record


def poll(*, run_id: str, repo_root: Path | None = None) -> RemoteRunRecord:
    root = (repo_root or REPO_ROOT).resolve()
    control_dir = _control_dir(root, run_id)
    summary_path = control_dir / "summary.json"
    if summary_path.exists():
        summary = RemoteRunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
        return RemoteRunRecord.model_validate(summary.model_dump(mode="json", exclude={"run_summary"}))

    record_path = control_dir / "record.json"
    if not record_path.exists():
        raise FileNotFoundError(f"remote record not found for run: {run_id}")
    record = RemoteRunRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    pid = record.metadata.get("launcher_pid")
    if record.status in {RemoteRunStatus.QUEUED, RemoteRunStatus.RUNNING} and isinstance(pid, int) and not _pid_is_running(pid):
        failure = _build_process_exit_failure(root=root, record=record)
        _write_json(summary_path, failure.model_dump(mode="json"))
        _write_json(record_path, RemoteRunRecord.model_validate(failure.model_dump(mode="json", exclude={"run_summary"})).model_dump(mode="json"))
        return RemoteRunRecord.model_validate(failure.model_dump(mode="json", exclude={"run_summary"}))
    return record


def heartbeat(*, run_id: str, repo_root: Path | None = None) -> RemoteHeartbeat | None:
    root = (repo_root or REPO_ROOT).resolve()
    heartbeat_path = _control_dir(root, run_id) / "heartbeat.json"
    if not heartbeat_path.exists():
        return None
    return RemoteHeartbeat.model_validate_json(heartbeat_path.read_text(encoding="utf-8"))


def fetch_summary(*, run_id: str, repo_root: Path | None = None) -> RemoteRunSummary:
    root = (repo_root or REPO_ROOT).resolve()
    summary_path = _control_dir(root, run_id) / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"remote summary is not available for run: {run_id}")
    return RemoteRunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))


def run_once(
    *,
    task_spec_path: Path,
    repo_root: Path | None = None,
    runner_factory: Callable[[Path], Any] = AgentExecutionRunner,
) -> RemoteRunSummary:
    root = (repo_root or REPO_ROOT).resolve()
    spec = RemoteTaskSpec.model_validate_json(task_spec_path.read_text(encoding="utf-8"))
    control_dir = _control_dir(root, spec.run_id)
    record_path = control_dir / "record.json"
    heartbeat_path = control_dir / "heartbeat.json"
    summary_path = control_dir / "summary.json"
    events_path = control_dir / "events.ndjson"
    now = utc_now()
    running = RemoteRunRecord(
        run_id=spec.run_id,
        requested_lane=spec.requested_lane,
        lane=spec.lane,
        status=RemoteRunStatus.RUNNING,
        summary="remote execution running",
        started_at=now,
        updated_at=now,
        artifact_paths=_artifact_paths(root, spec.run_id, include_heartbeat=True),
        metadata=spec.metadata,
    )
    _write_json(record_path, running.model_dump(mode="json"))
    _write_json(
        heartbeat_path,
        RemoteHeartbeat(
            run_id=spec.run_id,
            lane=spec.lane,
            status=RemoteRunStatus.RUNNING,
            sequence=1,
            summary="remote execution started",
            artifact_paths=_artifact_paths(root, spec.run_id, include_heartbeat=True),
        ).model_dump(mode="json"),
    )
    _append_event(events_path, {"type": "running", "recorded_at": now.isoformat()})

    try:
        runner = runner_factory(root)
        run_summary = runner.run_job(spec.job)
        status = (
            RemoteRunStatus.SUCCEEDED
            if run_summary.final_status in {"ready_for_promotion", "promoted"}
            else RemoteRunStatus.FAILED
        )
        disposition = classify_remote_terminal(status=status, run_summary=run_summary)
        finished = utc_now()
        summary = RemoteRunSummary(
            run_id=spec.run_id,
            requested_lane=spec.requested_lane,
            lane=spec.lane,
            status=status,
            failure_class=disposition.failure_class,
            recovery_action=disposition.recovery_action,
            artifact_paths=_artifact_paths(root, spec.run_id, include_heartbeat=True, include_summary=True),
            summary=f"remote execution completed with final_status={run_summary.final_status}",
            started_at=running.started_at,
            updated_at=finished,
            finished_at=finished,
            metadata={**spec.metadata, "runtime_mode": spec.runtime_mode},
            run_summary=run_summary,
        )
    except Exception as exc:
        disposition = classify_remote_terminal(status=RemoteRunStatus.FAILED, error_text=str(exc))
        finished = utc_now()
        summary = RemoteRunSummary(
            run_id=spec.run_id,
            requested_lane=spec.requested_lane,
            lane=spec.lane,
            status=RemoteRunStatus.FAILED,
            failure_class=disposition.failure_class,
            recovery_action=disposition.recovery_action,
            artifact_paths=_artifact_paths(root, spec.run_id, include_heartbeat=True, include_summary=True),
            summary=f"remote execution failed before summary: {exc}",
            started_at=running.started_at,
            updated_at=finished,
            finished_at=finished,
            metadata={**spec.metadata, "runtime_mode": spec.runtime_mode, "error": str(exc)},
            run_summary=None,
        )

    _write_json(summary_path, summary.model_dump(mode="json"))
    _write_json(record_path, RemoteRunRecord.model_validate(summary.model_dump(mode="json", exclude={"run_summary"})).model_dump(mode="json"))
    _append_event(events_path, {"type": "completed", "recorded_at": utc_now().isoformat(), "status": summary.status.value})
    return summary


def _build_process_exit_failure(*, root: Path, record: RemoteRunRecord) -> RemoteRunSummary:
    disposition = classify_remote_terminal(
        status=RemoteRunStatus.FAILED,
        error_text="remote worker exited before writing summary",
    )
    now = utc_now()
    return RemoteRunSummary(
        run_id=record.run_id,
        requested_lane=record.requested_lane,
        lane=record.lane,
        status=RemoteRunStatus.FAILED,
        failure_class=disposition.failure_class,
        recovery_action=disposition.recovery_action,
        artifact_paths=_artifact_paths(root, record.run_id, include_summary=True),
        summary="remote worker exited before writing summary",
        started_at=record.started_at,
        updated_at=now,
        finished_at=now,
        fallback_reason=record.fallback_reason,
        metadata=record.metadata,
        run_summary=None,
    )


def _spawn_background(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[str]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_path.open("a", encoding="utf-8")
    stderr_handle = stderr_path.open("a", encoding="utf-8")
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
        start_new_session=True,
    )


def _control_dir(repo_root: Path, run_id: str) -> Path:
    return repo_root / ".masfactory_runtime" / "runs" / run_id / "remote_control"


def _artifact_paths(
    repo_root: Path,
    run_id: str,
    *,
    include_heartbeat: bool = False,
    include_summary: bool = False,
) -> dict[str, str]:
    control_dir = _control_dir(repo_root, run_id)
    paths = {
        "task_spec": _relpath(repo_root, control_dir / "task_spec.json"),
        "record": _relpath(repo_root, control_dir / "record.json"),
        "events": _relpath(repo_root, control_dir / "events.ndjson"),
    }
    if include_heartbeat:
        paths["heartbeat"] = _relpath(repo_root, control_dir / "heartbeat.json")
    if include_summary:
        paths["summary"] = _relpath(repo_root, control_dir / "summary.json")
    legacy_summary = repo_root / ".masfactory_runtime" / "runs" / run_id / "summary.json"
    if legacy_summary.exists():
        paths["legacy_run_summary"] = _relpath(repo_root, legacy_summary)
    return paths


def _relpath(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _load_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("expected JSON payload on stdin")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("stdin JSON payload must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote execution worker for SSH-backed dispatch lanes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("healthcheck")

    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_parser.add_argument("--stdin", action="store_true")

    poll_parser = subparsers.add_parser("poll")
    poll_parser.add_argument("--run-id", required=True)

    heartbeat_parser = subparsers.add_parser("heartbeat")
    heartbeat_parser.add_argument("--run-id", required=True)

    summary_parser = subparsers.add_parser("fetch-summary")
    summary_parser.add_argument("--run-id", required=True)

    run_once_parser = subparsers.add_parser("run-once")
    run_once_parser.add_argument("--task-spec", required=True)

    args = parser.parse_args()

    if args.command == "healthcheck":
        print(healthcheck().model_dump_json(indent=2))
        return 0
    if args.command == "dispatch":
        if not args.stdin:
            raise ValueError("dispatch currently requires --stdin")
        spec = RemoteTaskSpec.model_validate(_load_stdin_json())
        print(dispatch(spec=spec).model_dump_json(indent=2))
        return 0
    if args.command == "poll":
        print(poll(run_id=args.run_id).model_dump_json(indent=2))
        return 0
    if args.command == "heartbeat":
        value = heartbeat(run_id=args.run_id)
        if value is not None:
            print(value.model_dump_json(indent=2))
        return 0
    if args.command == "fetch-summary":
        print(fetch_summary(run_id=args.run_id).model_dump_json(indent=2))
        return 0
    if args.command == "run-once":
        print(run_once(task_spec_path=Path(args.task_spec)).model_dump_json(indent=2))
        return 0
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
