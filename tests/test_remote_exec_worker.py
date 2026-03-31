from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.shared.remote_run_contract import DispatchLane, RemoteRunStatus, RemoteTaskSpec


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "remote_exec_worker.py"
    spec = importlib.util.spec_from_file_location("remote_exec_worker", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _StubRunner:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def run_job(self, job: JobSpec) -> RunSummary:
        return RunSummary(
            run_id=job.run_id,
            final_status="ready_for_promotion",
            driver_result=DriverResult(
                run_id=job.run_id,
                agent_id=job.agent_id,
                status="succeeded",
                summary="remote worker stub succeeded",
                changed_paths=["src/demo.py"],
                recommended_action="promote",
            ),
            validation=ValidationReport(run_id=job.run_id, passed=True),
            promotion_patch_uri="artifacts/promotion.patch",
        )


class _StubProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_remote_exec_worker_healthcheck_and_run_once(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / "repo"
    (repo_root / "drivers").mkdir(parents=True)
    (repo_root / "drivers" / "openhands_adapter.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    spec = RemoteTaskSpec(
        run_id="run-remote-worker",
        requested_lane=DispatchLane.REMOTE,
        lane=DispatchLane.REMOTE,
        runtime_mode="night",
        job=JobSpec(run_id="run-remote-worker", agent_id="openhands", task="demo"),
    )
    task_spec_path = repo_root / ".masfactory_runtime" / "runs" / spec.run_id / "remote_control" / "task_spec.json"
    task_spec_path.parent.mkdir(parents=True, exist_ok=True)
    task_spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")

    health = module.healthcheck(repo_root=repo_root)
    summary = module.run_once(
        task_spec_path=task_spec_path,
        repo_root=repo_root,
        runner_factory=lambda root: _StubRunner(root),
    )

    assert health.healthy is True
    assert summary.status is RemoteRunStatus.SUCCEEDED
    assert (task_spec_path.parent / "summary.json").exists()
    assert (task_spec_path.parent / "record.json").exists()


def test_remote_exec_worker_dispatch_and_poll_marks_dead_process_as_failed(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / "repo"
    (repo_root / "drivers").mkdir(parents=True)
    (repo_root / "drivers" / "openhands_adapter.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    spec = RemoteTaskSpec(
        run_id="run-dead-process",
        requested_lane=DispatchLane.REMOTE,
        lane=DispatchLane.REMOTE,
        runtime_mode="night",
        job=JobSpec(run_id="run-dead-process", agent_id="openhands", task="demo"),
    )

    queued = module.dispatch(
        spec=spec,
        repo_root=repo_root,
        spawner=lambda command, cwd, stdout_path, stderr_path: _StubProcess(999999),
    )
    polled = module.poll(run_id=spec.run_id, repo_root=repo_root)

    assert queued.status is RemoteRunStatus.QUEUED
    assert polled.status is RemoteRunStatus.FAILED
    assert "exited before writing summary" in polled.summary
