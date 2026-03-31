from __future__ import annotations

import subprocess

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.core.dispatch.ssh_remote_adapter import SshRemoteAdapter, SshRemoteAdapterConfig
from autoresearch.shared.remote_run_contract import DispatchLane, RemoteRunStatus, RemoteTaskSpec


class _FakeCommandRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str | None, float | None]] = []

    def __call__(self, command: list[str], input_text: str | None, timeout: float | None) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, input_text, timeout))
        remote_script = command[-1]
        if "healthcheck" in remote_script:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"healthy": true, "host": "linux-worker", "detail": "ok", "metadata": {"adapter": "ssh"}}',
                stderr="",
            )
        if "dispatch" in remote_script:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"run_id":"run-ssh","requested_lane":"remote","lane":"remote","status":"queued","summary":"queued"}',
                stderr="",
            )
        if "poll" in remote_script:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"run_id":"run-ssh","requested_lane":"remote","lane":"remote","status":"running","summary":"running"}',
                stderr="",
            )
        if "fetch-summary" in remote_script:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"run_id":"run-ssh","requested_lane":"remote","lane":"remote","status":"failed","summary":"remote failed","failure_class":"transient_network"}',
                stderr="",
            )
        if "heartbeat" in remote_script:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected remote script: {remote_script}")


def _adapter(runner: _FakeCommandRunner | None = None) -> SshRemoteAdapter:
    return SshRemoteAdapter(
        config=SshRemoteAdapterConfig(
            ssh_destination="lisa@example.com",
            remote_repo_root="/srv/autonomous-agent-stack",
            ssh_options=("-p", "2222"),
            remote_env_file=".env.linux",
        ),
        command_runner=runner or _FakeCommandRunner(),
    )


def test_ssh_remote_adapter_dispatch_flow_uses_configured_ssh_command() -> None:
    runner = _FakeCommandRunner()
    adapter = _adapter(runner)
    spec = RemoteTaskSpec(
        run_id="run-ssh",
        requested_lane=DispatchLane.REMOTE,
        lane=DispatchLane.REMOTE,
        runtime_mode="night",
        job=JobSpec(run_id="run-ssh", agent_id="openhands", task="demo"),
    )

    health = adapter.healthcheck()
    queued = adapter.dispatch(spec)
    running = adapter.poll(spec.run_id)
    heartbeat = adapter.heartbeat(spec.run_id)
    summary = adapter.fetch_summary(spec.run_id)

    assert health.healthy is True
    assert queued.status is RemoteRunStatus.QUEUED
    assert running.status is RemoteRunStatus.RUNNING
    assert heartbeat is None
    assert summary.status is RemoteRunStatus.FAILED
    assert len(runner.calls) == 5
    first_command, _, first_timeout = runner.calls[0]
    dispatch_command, dispatch_input, _ = runner.calls[1]
    assert first_command[:4] == ["ssh", "-p", "2222", "lisa@example.com"]
    assert "healthcheck" in first_command[-1]
    assert "source .env.linux" in dispatch_command[-1]
    assert "dispatch --stdin" in dispatch_command[-1]
    assert dispatch_input is not None and '"run_id": "run-ssh"' in dispatch_input
    assert first_timeout == 10.0


def test_ssh_remote_adapter_healthcheck_reports_unhealthy_on_ssh_error() -> None:
    def _failing(command: list[str], input_text: str | None, timeout: float | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 255, stdout="", stderr="ssh: connection refused")

    adapter = SshRemoteAdapter(
        config=SshRemoteAdapterConfig(
            ssh_destination="lisa@example.com",
            remote_repo_root="/srv/autonomous-agent-stack",
        ),
        command_runner=_failing,
    )

    health = adapter.healthcheck()

    assert health.healthy is False
    assert "connection refused" in health.detail
