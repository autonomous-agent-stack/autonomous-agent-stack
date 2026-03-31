from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.core.dispatch.fake_remote_adapter import FakeRemoteAdapter
from autoresearch.shared.remote_run_contract import DispatchLane, FailureClass, RemoteRunStatus, RemoteTaskSpec


def _success_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="local runner succeeded",
            changed_paths=["src/demo.py"],
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="artifacts/promotion.patch",
    )


def _task_spec(
    *,
    run_id: str,
    lane: DispatchLane,
    requested_lane: DispatchLane | None = None,
    scenario: str | None = None,
) -> RemoteTaskSpec:
    metadata: dict[str, object] = {}
    if scenario is not None:
        metadata["remote_scenario"] = scenario
    return RemoteTaskSpec(
        run_id=run_id,
        requested_lane=requested_lane or lane,
        lane=lane,
        runtime_mode="night",
        planner_plan_id="plan_test",
        planner_candidate_id="candidate_test",
        job=JobSpec(run_id=run_id, agent_id="openhands", task="demo"),
        metadata=metadata,
    )


def test_fake_remote_adapter_success_flow(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(run_id="run-success", lane=DispatchLane.REMOTE, scenario="success")

    queued = adapter.dispatch(spec)
    running = adapter.poll(spec.run_id)
    heartbeat = adapter.heartbeat(spec.run_id)
    terminal = adapter.poll(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert queued.status is RemoteRunStatus.QUEUED
    assert running.status is RemoteRunStatus.RUNNING
    assert heartbeat is not None
    assert terminal.status is RemoteRunStatus.SUCCEEDED
    assert summary.status is RemoteRunStatus.SUCCEEDED
    assert summary.run_summary is None
    assert (
        repo_root
        / ".masfactory_runtime"
        / "runs"
        / spec.run_id
        / "remote_control"
        / "summary.json"
    ).exists()


def test_fake_remote_adapter_stalled_flow_uses_missing_heartbeat_signal(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(run_id="run-stalled", lane=DispatchLane.REMOTE, scenario="stalled")

    adapter.dispatch(spec)
    running = adapter.poll(spec.run_id)
    stalled = adapter.poll(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert running.status is RemoteRunStatus.RUNNING
    assert adapter.heartbeat(spec.run_id) is None
    assert stalled.status is RemoteRunStatus.STALLED
    assert summary.failure_class is FailureClass.EXECUTOR_STALLED


def test_fake_remote_adapter_timeout_flow(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(run_id="run-timeout", lane=DispatchLane.REMOTE, scenario="timed_out")

    adapter.dispatch(spec)
    adapter.poll(spec.run_id)
    timed_out = adapter.poll(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert timed_out.status is RemoteRunStatus.TIMED_OUT
    assert summary.failure_class is FailureClass.TOOL_TIMEOUT


@pytest.mark.parametrize(
    ("scenario", "failure_class"),
    [
        ("env_missing", FailureClass.ENV_MISSING),
        ("transient_network", FailureClass.TRANSIENT_NETWORK),
    ],
)
def test_fake_remote_adapter_failure_mapping(
    tmp_path: Path,
    scenario: str,
    failure_class: FailureClass,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(run_id=f"run-{scenario}", lane=DispatchLane.REMOTE, scenario=scenario)

    adapter.dispatch(spec)
    failed = adapter.poll(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert failed.status is RemoteRunStatus.FAILED
    assert summary.failure_class is failure_class


def test_fake_remote_adapter_records_remote_to_local_fallback(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(
        run_id="run-fallback",
        lane=DispatchLane.LOCAL,
        requested_lane=DispatchLane.REMOTE,
    )

    queued = adapter.dispatch(spec)
    adapter.poll(spec.run_id)
    terminal = adapter.poll(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert queued.requested_lane is DispatchLane.REMOTE
    assert queued.lane is DispatchLane.LOCAL
    assert queued.fallback_reason is not None
    assert terminal.status is RemoteRunStatus.SUCCEEDED
    assert summary.run_summary is not None
    assert summary.run_summary.final_status == "ready_for_promotion"


def test_fake_remote_adapter_result_fetch_failure_raises(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    adapter = FakeRemoteAdapter(repo_root=repo_root, local_runner=_success_summary)
    spec = _task_spec(
        run_id="run-fetch-failure",
        lane=DispatchLane.REMOTE,
        scenario="result_fetch_failure",
    )

    adapter.dispatch(spec)
    adapter.poll(spec.run_id)
    terminal = adapter.poll(spec.run_id)

    assert terminal.status is RemoteRunStatus.SUCCEEDED
    with pytest.raises(FileNotFoundError):
        adapter.fetch_summary(spec.run_id)
