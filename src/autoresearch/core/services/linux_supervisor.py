from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Callable

from autoresearch.agent_protocol.models import RunSummary
from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorConclusion,
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
    LinuxSupervisorTaskCreateRequest,
    LinuxSupervisorTaskHeartbeatRead,
    LinuxSupervisorTaskRead,
    LinuxSupervisorTaskStatus,
    LinuxSupervisorTaskStatusRead,
    LinuxSupervisorTaskSummaryRead,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.store import create_resource_id


@dataclass(frozen=True, slots=True)
class _TaskPaths:
    task_dir: Path
    task_path: Path
    status_path: Path
    heartbeat_path: Path
    summary_path: Path
    artifacts_dir: Path
    stdout_path: Path
    stderr_path: Path


class LinuxSupervisorService:
    def __init__(
        self,
        *,
        repo_root: Path,
        runtime_root: Path | None = None,
        python_bin: str | None = None,
        poll_interval_sec: float = 1.0,
        heartbeat_interval_sec: float = 5.0,
        command_builder: Callable[[LinuxSupervisorTaskRead, Path], list[str]] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._runtime_root = (
            runtime_root or self._repo_root / ".masfactory_runtime" / "linux-housekeeper"
        ).resolve()
        self._queue_root = self._runtime_root / "queue"
        self._state_root = self._runtime_root / "state"
        self._python_bin = python_bin or sys.executable
        self._poll_interval_sec = max(0.1, poll_interval_sec)
        self._heartbeat_interval_sec = max(self._poll_interval_sec, heartbeat_interval_sec)
        self._command_builder = command_builder or self._default_command_builder
        self._sleep = sleep_fn or time.sleep

    @property
    def runtime_root(self) -> Path:
        return self._runtime_root

    @property
    def queue_root(self) -> Path:
        return self._queue_root

    def enqueue_task(self, request: LinuxSupervisorTaskCreateRequest) -> LinuxSupervisorTaskRead:
        self._ensure_layout()
        now = utc_now()
        task_id = create_resource_id("hktask")
        run_id = create_resource_id("hkrun")
        task = LinuxSupervisorTaskRead(
            task_id=task_id,
            run_id=run_id,
            prompt=request.prompt,
            agent_id=request.agent_id,
            retry=request.retry,
            fallback_agent=request.fallback_agent,
            validator_commands=list(request.validator_commands),
            total_timeout_sec=request.total_timeout_sec,
            stall_timeout_sec=request.stall_timeout_sec,
            metadata=dict(request.metadata),
            created_at=now,
        )
        paths = self._task_paths(self._queue_root / task.task_id)
        paths.task_dir.mkdir(parents=True, exist_ok=False)
        paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(paths.task_path, task.model_dump(mode="json"))
        self._write_status(
            paths,
            LinuxSupervisorTaskStatusRead(
                task_id=task.task_id,
                run_id=task.run_id,
                status=LinuxSupervisorTaskStatus.QUEUED,
                updated_at=now,
                current_phase="queued",
            ),
        )
        self._write_heartbeat(
            paths,
            LinuxSupervisorTaskHeartbeatRead(
                task_id=task.task_id,
                run_id=task.run_id,
                status=LinuxSupervisorTaskStatus.QUEUED,
                observed_at=now,
                current_phase="queued",
                elapsed_seconds=0.0,
            ),
        )
        return task

    def run_once(self) -> LinuxSupervisorTaskSummaryRead | None:
        self._ensure_layout()
        task_dir = self._next_pending_task_dir()
        queue_depth = self._queue_depth()
        if task_dir is None:
            self._write_process_status(
                LinuxSupervisorProcessStatusRead(
                    status="idle",
                    pid=os.getpid(),
                    current_task_id=None,
                    last_task_id=None,
                    queue_depth=queue_depth,
                    started_at=utc_now(),
                    updated_at=utc_now(),
                    message="queue idle",
                )
            )
            self._write_process_heartbeat(
                LinuxSupervisorProcessHeartbeatRead(
                    observed_at=utc_now(),
                    pid=os.getpid(),
                    current_task_id=None,
                    queue_depth=queue_depth,
                    status="idle",
                )
            )
            return None
        return self._execute_task_dir(task_dir)

    def run_forever(self) -> None:
        self._ensure_layout()
        started_at = utc_now()
        self.repair_orphaned_tasks()
        try:
            while True:
                task_dir = self._next_pending_task_dir()
                queue_depth = self._queue_depth()
                if task_dir is None:
                    now = utc_now()
                    self._write_process_status(
                        LinuxSupervisorProcessStatusRead(
                            status="idle",
                            pid=os.getpid(),
                            current_task_id=None,
                            last_task_id=None,
                            queue_depth=queue_depth,
                            started_at=started_at,
                            updated_at=now,
                            message="queue idle",
                        )
                    )
                    self._write_process_heartbeat(
                        LinuxSupervisorProcessHeartbeatRead(
                            observed_at=now,
                            pid=os.getpid(),
                            current_task_id=None,
                            queue_depth=queue_depth,
                            status="idle",
                        )
                    )
                    self._sleep(self._poll_interval_sec)
                    continue
                self._execute_task_dir(task_dir, process_started_at=started_at)
        except KeyboardInterrupt:
            stopped_at = utc_now()
            self._write_process_status(
                LinuxSupervisorProcessStatusRead(
                    status="stopped",
                    pid=os.getpid(),
                    current_task_id=None,
                    last_task_id=None,
                    queue_depth=self._queue_depth(),
                    started_at=started_at,
                    updated_at=stopped_at,
                    message="supervisor stopped",
                )
            )
            self._write_process_heartbeat(
                LinuxSupervisorProcessHeartbeatRead(
                    observed_at=stopped_at,
                    pid=os.getpid(),
                    current_task_id=None,
                    queue_depth=self._queue_depth(),
                    status="stopped",
                )
            )

    def repair_orphaned_tasks(self) -> int:
        self._ensure_layout()
        repaired = 0
        for task_dir in self._iter_task_dirs():
            paths = self._task_paths(task_dir)
            if paths.summary_path.exists():
                continue
            status = self._read_status(paths)
            if status is None or status.status is not LinuxSupervisorTaskStatus.RUNNING:
                continue
            task = self._read_task(paths)
            now = utc_now()
            summary = LinuxSupervisorTaskSummaryRead(
                task_id=task.task_id,
                run_id=task.run_id,
                status=LinuxSupervisorTaskStatus.FAILED,
                conclusion=LinuxSupervisorConclusion.INFRA_ERROR,
                success=False,
                agent_id=task.agent_id,
                started_at=status.started_at or now,
                finished_at=now,
                duration_seconds=max(
                    0.0,
                    (now - (status.started_at or now)).total_seconds(),
                ),
                process_returncode=None,
                aep_final_status=None,
                aep_driver_status=None,
                used_mock_fallback=False,
                message="supervisor restarted before the task produced summary.json",
                task_dir=str(paths.task_dir),
                run_dir=str(self._run_dir(task.run_id)),
                artifacts={},
                metadata={"repair_reason": "orphaned_running_task"},
            )
            self._write_summary(paths, summary)
            self._write_status(
                paths,
                LinuxSupervisorTaskStatusRead(
                    task_id=task.task_id,
                    run_id=task.run_id,
                    status=LinuxSupervisorTaskStatus.FAILED,
                    updated_at=now,
                    claimed_at=status.claimed_at,
                    started_at=status.started_at,
                    completed_at=now,
                    pid=status.pid,
                    current_phase="repaired",
                    last_error=summary.message,
                    conclusion=summary.conclusion,
                    metadata={"repair_reason": "orphaned_running_task"},
                ),
            )
            repaired += 1
        return repaired

    def status_snapshot(self) -> dict[str, object]:
        self._ensure_layout()
        status = self._read_model(
            self._state_root / "supervisor_status.json",
            LinuxSupervisorProcessStatusRead,
        )
        heartbeat = self._read_model(
            self._state_root / "supervisor_heartbeat.json",
            LinuxSupervisorProcessHeartbeatRead,
        )
        return {
            "runtime_root": str(self._runtime_root),
            "queue_depth": self._queue_depth(),
            "queued_task_ids": [task_dir.name for task_dir in self._iter_pending_task_dirs()],
            "status": status.model_dump(mode="json") if status is not None else None,
            "heartbeat": heartbeat.model_dump(mode="json") if heartbeat is not None else None,
        }

    def _execute_task_dir(
        self,
        task_dir: Path,
        *,
        process_started_at: datetime | None = None,
    ) -> LinuxSupervisorTaskSummaryRead:
        paths = self._task_paths(task_dir)
        task = self._read_task(paths)
        run_dir = self._run_dir(task.run_id)
        now = utc_now()
        status = LinuxSupervisorTaskStatusRead(
            task_id=task.task_id,
            run_id=task.run_id,
            status=LinuxSupervisorTaskStatus.RUNNING,
            updated_at=now,
            claimed_at=now,
            started_at=now,
            pid=None,
            current_phase="launching",
        )
        self._write_status(paths, status)
        started_at = now
        self._write_process_status(
            LinuxSupervisorProcessStatusRead(
                status="running",
                pid=os.getpid(),
                current_task_id=task.task_id,
                last_task_id=None,
                queue_depth=self._queue_depth(),
                started_at=process_started_at or now,
                updated_at=now,
                message="launching task",
            )
        )

        command = self._command_builder(task, run_dir)
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = f"src{os.pathsep}{current_pythonpath}" if current_pythonpath else "src"

        forced_conclusion: LinuxSupervisorConclusion | None = None
        returncode: int | None = None
        last_progress_at: datetime | None = None
        last_progress_signature: str | None = self._progress_signature(run_dir)
        start_monotonic = time.monotonic()
        last_progress_monotonic = start_monotonic
        last_heartbeat_monotonic = start_monotonic

        with paths.stdout_path.open("wb") as stdout_handle, paths.stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                command,
                cwd=self._repo_root,
                stdout=stdout_handle,
                stderr=stderr_handle,
                env=env,
                start_new_session=True,
            )
            status = status.model_copy(
                update={
                    "pid": process.pid,
                    "updated_at": utc_now(),
                    "current_phase": "running",
                }
            )
            self._write_status(paths, status)

            while True:
                now_monotonic = time.monotonic()
                now_dt = utc_now()
                signature = self._progress_signature(run_dir)
                if signature != last_progress_signature:
                    last_progress_signature = signature
                    last_progress_at = now_dt
                    last_progress_monotonic = now_monotonic

                if now_monotonic - last_heartbeat_monotonic >= self._heartbeat_interval_sec:
                    elapsed = max(0.0, now_monotonic - start_monotonic)
                    self._write_heartbeat(
                        paths,
                        LinuxSupervisorTaskHeartbeatRead(
                            task_id=task.task_id,
                            run_id=task.run_id,
                            status=LinuxSupervisorTaskStatus.RUNNING,
                            observed_at=now_dt,
                            pid=process.pid,
                            current_phase="running",
                            elapsed_seconds=elapsed,
                            last_progress_at=last_progress_at,
                            last_progress_signature=last_progress_signature,
                        ),
                    )
                    self._write_process_heartbeat(
                        LinuxSupervisorProcessHeartbeatRead(
                            observed_at=now_dt,
                            pid=os.getpid(),
                            current_task_id=task.task_id,
                            queue_depth=self._queue_depth(),
                            status="running",
                            metadata={
                                "run_id": task.run_id,
                                "last_progress_signature": last_progress_signature,
                            },
                        )
                    )
                    self._write_process_status(
                        LinuxSupervisorProcessStatusRead(
                            status="running",
                            pid=os.getpid(),
                            current_task_id=task.task_id,
                            last_task_id=None,
                            queue_depth=self._queue_depth(),
                            started_at=process_started_at or started_at,
                            updated_at=now_dt,
                            message="task running",
                            metadata={"run_id": task.run_id},
                        )
                    )
                    last_heartbeat_monotonic = now_monotonic

                returncode = process.poll()
                if returncode is not None:
                    break

                elapsed = now_monotonic - start_monotonic
                if elapsed >= task.total_timeout_sec:
                    forced_conclusion = LinuxSupervisorConclusion.TIMED_OUT
                    self._terminate_process(process)
                    returncode = process.wait(timeout=5)
                    break

                stalled_for = now_monotonic - last_progress_monotonic
                if stalled_for >= task.stall_timeout_sec:
                    forced_conclusion = LinuxSupervisorConclusion.STALLED_NO_PROGRESS
                    self._terminate_process(process)
                    returncode = process.wait(timeout=5)
                    break

                self._sleep(self._poll_interval_sec)

        summary = self._build_summary(
            task=task,
            paths=paths,
            run_dir=run_dir,
            started_at=started_at,
            finished_at=utc_now(),
            process_returncode=returncode,
            forced_conclusion=forced_conclusion,
        )
        self._write_summary(paths, summary)
        self._write_status(
            paths,
            LinuxSupervisorTaskStatusRead(
                task_id=task.task_id,
                run_id=task.run_id,
                status=summary.status,
                updated_at=summary.finished_at,
                claimed_at=started_at,
                started_at=started_at,
                completed_at=summary.finished_at,
                pid=status.pid,
                current_phase="finished",
                last_error=None if summary.success else summary.message,
                conclusion=summary.conclusion,
                metadata={"aep_final_status": summary.aep_final_status},
            ),
        )
        self._write_heartbeat(
            paths,
            LinuxSupervisorTaskHeartbeatRead(
                task_id=task.task_id,
                run_id=task.run_id,
                status=summary.status,
                observed_at=summary.finished_at,
                pid=status.pid,
                current_phase="finished",
                elapsed_seconds=summary.duration_seconds,
                last_progress_at=last_progress_at,
                last_progress_signature=last_progress_signature,
                metadata={"conclusion": summary.conclusion.value},
            ),
        )
        self._write_process_status(
            LinuxSupervisorProcessStatusRead(
                status="idle",
                pid=os.getpid(),
                current_task_id=None,
                last_task_id=task.task_id,
                queue_depth=self._queue_depth(),
                started_at=process_started_at or started_at,
                updated_at=summary.finished_at,
                message=f"last task finished with {summary.conclusion.value}",
                metadata={"run_id": task.run_id},
            )
        )
        self._write_process_heartbeat(
            LinuxSupervisorProcessHeartbeatRead(
                observed_at=summary.finished_at,
                pid=os.getpid(),
                current_task_id=None,
                queue_depth=self._queue_depth(),
                status="idle",
                metadata={"last_task_id": task.task_id, "run_id": task.run_id},
            )
        )
        return summary

    def _build_summary(
        self,
        *,
        task: LinuxSupervisorTaskRead,
        paths: _TaskPaths,
        run_dir: Path,
        started_at: datetime,
        finished_at: datetime,
        process_returncode: int | None,
        forced_conclusion: LinuxSupervisorConclusion | None,
    ) -> LinuxSupervisorTaskSummaryRead:
        duration_seconds = max(0.0, (finished_at - started_at).total_seconds())
        artifacts = self._collect_task_artifacts(paths=paths, run_dir=run_dir)
        aep_summary = self._read_model(run_dir / "summary.json", RunSummary)
        used_mock_fallback = self._detect_mock_fallback(run_dir / "events.ndjson")
        conclusion = self._classify_summary(
            forced_conclusion=forced_conclusion,
            run_summary=aep_summary,
            process_returncode=process_returncode,
            used_mock_fallback=used_mock_fallback,
        )
        success = bool(aep_summary and aep_summary.final_status in {"ready_for_promotion", "promoted"})
        status = LinuxSupervisorTaskStatus.COMPLETED if success else LinuxSupervisorTaskStatus.FAILED
        message = self._summary_message(
            conclusion=conclusion,
            run_summary=aep_summary,
            process_returncode=process_returncode,
            forced_conclusion=forced_conclusion,
        )
        return LinuxSupervisorTaskSummaryRead(
            task_id=task.task_id,
            run_id=task.run_id,
            status=status,
            conclusion=conclusion,
            success=success,
            agent_id=task.agent_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            process_returncode=process_returncode,
            aep_final_status=aep_summary.final_status if aep_summary is not None else None,
            aep_driver_status=aep_summary.driver_result.status if aep_summary is not None else None,
            used_mock_fallback=used_mock_fallback,
            message=message,
            task_dir=str(paths.task_dir),
            run_dir=str(run_dir),
            artifacts=artifacts,
            metadata={"fallback_agent": task.fallback_agent},
        )

    def _summary_message(
        self,
        *,
        conclusion: LinuxSupervisorConclusion,
        run_summary: RunSummary | None,
        process_returncode: int | None,
        forced_conclusion: LinuxSupervisorConclusion | None,
    ) -> str:
        if forced_conclusion is LinuxSupervisorConclusion.TIMED_OUT:
            return "supervisor hit total timeout budget and terminated the task"
        if forced_conclusion is LinuxSupervisorConclusion.STALLED_NO_PROGRESS:
            return "supervisor observed no run-directory progress and terminated the task"
        if run_summary is not None:
            failed_checks = [check.detail for check in run_summary.validation.checks if not check.passed and check.detail]
            if failed_checks:
                return failed_checks[0]
            if run_summary.driver_result.error:
                return run_summary.driver_result.error
            return run_summary.driver_result.summary
        if process_returncode is not None:
            return f"task exited without aep summary (returncode={process_returncode})"
        return f"task ended with {conclusion.value}"

    def _classify_summary(
        self,
        *,
        forced_conclusion: LinuxSupervisorConclusion | None,
        run_summary: RunSummary | None,
        process_returncode: int | None,
        used_mock_fallback: bool,
    ) -> LinuxSupervisorConclusion:
        if forced_conclusion is not None:
            return forced_conclusion
        if run_summary is None:
            return LinuxSupervisorConclusion.INFRA_ERROR
        if run_summary.driver_result.status == "timed_out":
            return LinuxSupervisorConclusion.TIMED_OUT
        if run_summary.driver_result.status == "stalled_no_progress":
            return LinuxSupervisorConclusion.STALLED_NO_PROGRESS
        if used_mock_fallback:
            return LinuxSupervisorConclusion.MOCK_FALLBACK
        if self._has_assertion_failure(run_summary):
            return LinuxSupervisorConclusion.ASSERTION_FAILED
        if run_summary.driver_result.status == "contract_error":
            return LinuxSupervisorConclusion.INFRA_ERROR
        if run_summary.final_status in {"ready_for_promotion", "promoted"}:
            return LinuxSupervisorConclusion.SUCCEEDED
        if process_returncode not in {0, 2, None}:
            return LinuxSupervisorConclusion.INFRA_ERROR
        return LinuxSupervisorConclusion.UNKNOWN

    @staticmethod
    def _has_assertion_failure(run_summary: RunSummary) -> bool:
        details = " ".join(
            check.detail for check in run_summary.validation.checks if not check.passed and check.detail
        ).lower()
        if not details:
            details = str(run_summary.driver_result.error or "").lower()
        return "assert" in details or "assertion" in details or "pytest" in details

    @staticmethod
    def _detect_mock_fallback(events_path: Path) -> bool:
        if not events_path.exists():
            return False
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "attempt_started" and payload.get("agent_id") == "mock":
                return True
        return False

    def _collect_task_artifacts(self, *, paths: _TaskPaths, run_dir: Path) -> dict[str, str]:
        artifacts: dict[str, str] = {}
        for path in (paths.stdout_path, paths.stderr_path):
            if path.exists():
                artifacts[path.name] = str(path)

        copies = {
            run_dir / "summary.json": paths.artifacts_dir / "aep_summary.json",
            run_dir / "events.ndjson": paths.artifacts_dir / "aep_events.ndjson",
            run_dir / "driver_result.json": paths.artifacts_dir / "aep_driver_result.json",
            run_dir / "artifacts" / "promotion.patch": paths.artifacts_dir / "promotion.patch",
        }
        for source, destination in copies.items():
            if not source.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            artifacts[destination.name] = str(destination)
        return artifacts

    def _default_command_builder(self, task: LinuxSupervisorTaskRead, run_dir: Path) -> list[str]:
        command = [
            self._python_bin,
            "scripts/agent_run.py",
            "--agent",
            task.agent_id,
            "--task",
            task.prompt,
            "--run-id",
            task.run_id,
            "--retry",
            str(task.retry),
        ]
        if task.fallback_agent:
            command.extend(["--fallback-agent", task.fallback_agent])
        for validator in task.validator_commands:
            command.extend(["--validator-cmd", validator])
        return command

    def _next_pending_task_dir(self) -> Path | None:
        for task_dir in self._iter_pending_task_dirs():
            return task_dir
        return None

    def _iter_pending_task_dirs(self) -> list[Path]:
        pending: list[Path] = []
        for task_dir in self._iter_task_dirs():
            paths = self._task_paths(task_dir)
            if paths.summary_path.exists():
                continue
            status = self._read_status(paths)
            if status is None or status.status is LinuxSupervisorTaskStatus.QUEUED:
                pending.append(task_dir)
        return pending

    def _iter_task_dirs(self) -> list[Path]:
        if not self._queue_root.exists():
            return []
        return sorted(path for path in self._queue_root.iterdir() if path.is_dir())

    def _queue_depth(self) -> int:
        return len(self._iter_pending_task_dirs())

    def _task_paths(self, task_dir: Path) -> _TaskPaths:
        return _TaskPaths(
            task_dir=task_dir,
            task_path=task_dir / "task.json",
            status_path=task_dir / "status.json",
            heartbeat_path=task_dir / "heartbeat.json",
            summary_path=task_dir / "summary.json",
            artifacts_dir=task_dir / "artifacts",
            stdout_path=task_dir / "artifacts" / "stdout.log",
            stderr_path=task_dir / "artifacts" / "stderr.log",
        )

    def _run_dir(self, run_id: str) -> Path:
        return self._repo_root / ".masfactory_runtime" / "runs" / run_id

    def _progress_signature(self, run_dir: Path) -> str | None:
        if not run_dir.exists():
            return None
        latest_mtime = run_dir.stat().st_mtime_ns
        file_count = 0
        for path in run_dir.rglob("*"):
            if not path.is_file():
                continue
            file_count += 1
            latest_mtime = max(latest_mtime, path.stat().st_mtime_ns)
        return f"{file_count}:{latest_mtime}"

    @staticmethod
    def _terminate_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
            return
        except Exception:
            pass

        try:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
            return
        except Exception:
            pass

        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:
            return

    def _ensure_layout(self) -> None:
        self._queue_root.mkdir(parents=True, exist_ok=True)
        self._state_root.mkdir(parents=True, exist_ok=True)

    def _read_task(self, paths: _TaskPaths) -> LinuxSupervisorTaskRead:
        return self._read_model(paths.task_path, LinuxSupervisorTaskRead)

    def _read_status(self, paths: _TaskPaths) -> LinuxSupervisorTaskStatusRead | None:
        return self._read_model(paths.status_path, LinuxSupervisorTaskStatusRead)

    def _write_status(self, paths: _TaskPaths, status: LinuxSupervisorTaskStatusRead) -> None:
        self._write_json(paths.status_path, status.model_dump(mode="json"))

    def _write_heartbeat(self, paths: _TaskPaths, heartbeat: LinuxSupervisorTaskHeartbeatRead) -> None:
        self._write_json(paths.heartbeat_path, heartbeat.model_dump(mode="json"))

    def _write_summary(self, paths: _TaskPaths, summary: LinuxSupervisorTaskSummaryRead) -> None:
        self._write_json(paths.summary_path, summary.model_dump(mode="json"))

    def _write_process_status(self, status: LinuxSupervisorProcessStatusRead) -> None:
        self._write_json(
            self._state_root / "supervisor_status.json",
            status.model_dump(mode="json"),
        )

    def _write_process_heartbeat(self, heartbeat: LinuxSupervisorProcessHeartbeatRead) -> None:
        self._write_json(
            self._state_root / "supervisor_heartbeat.json",
            heartbeat.model_dump(mode="json"),
        )

    @staticmethod
    def _read_model(path: Path, model_cls):
        if not path.exists():
            return None
        return model_cls.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
