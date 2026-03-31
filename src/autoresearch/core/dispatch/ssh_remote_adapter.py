from __future__ import annotations

from dataclasses import dataclass
import json
import shlex
import subprocess
from typing import Callable

from autoresearch.core.dispatch.remote_adapter import RemoteDispatchAdapter
from autoresearch.shared.models import utc_now
from autoresearch.shared.remote_run_contract import (
    RemoteHeartbeat,
    RemoteRunRecord,
    RemoteRunSummary,
    RemoteTaskSpec,
    RemoteWorkerHealthRead,
)


@dataclass(frozen=True, slots=True)
class SshRemoteAdapterConfig:
    ssh_destination: str
    remote_repo_root: str
    ssh_bin: str = "ssh"
    ssh_options: tuple[str, ...] = ()
    remote_env_file: str | None = None
    remote_python_bin: str = ".venv/bin/python"
    remote_worker_script: str = "scripts/remote_exec_worker.py"
    command_timeout_seconds: float = 30.0
    healthcheck_timeout_seconds: float = 10.0


class SshRemoteAdapter(RemoteDispatchAdapter):
    def __init__(
        self,
        *,
        config: SshRemoteAdapterConfig,
        command_runner: Callable[[list[str], str | None, float | None], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self._config = config
        self._command_runner = command_runner or self._run_command

    def healthcheck(self) -> RemoteWorkerHealthRead:
        try:
            return self._invoke_json("healthcheck", model_cls=RemoteWorkerHealthRead, timeout=self._config.healthcheck_timeout_seconds)
        except Exception as exc:
            return RemoteWorkerHealthRead(
                healthy=False,
                host=self._config.ssh_destination,
                detail=str(exc),
                checked_at=utc_now(),
                metadata={"adapter": "ssh"},
            )

    def dispatch(self, spec: RemoteTaskSpec) -> RemoteRunRecord:
        return self._invoke_json(
            "dispatch",
            model_cls=RemoteRunRecord,
            stdin_payload=spec.model_dump(mode="json"),
        )

    def poll(self, run_id: str) -> RemoteRunRecord:
        return self._invoke_json(
            "poll",
            model_cls=RemoteRunRecord,
            extra_args=("--run-id", run_id),
        )

    def heartbeat(self, run_id: str) -> RemoteHeartbeat | None:
        result = self._invoke(
            "heartbeat",
            extra_args=("--run-id", run_id),
        )
        if not result.stdout.strip():
            return None
        payload = self._load_json_payload(result.stdout)
        return RemoteHeartbeat.model_validate(payload)

    def fetch_summary(self, run_id: str) -> RemoteRunSummary:
        return self._invoke_json(
            "fetch-summary",
            model_cls=RemoteRunSummary,
            extra_args=("--run-id", run_id),
        )

    def _invoke_json(
        self,
        command: str,
        *,
        model_cls,
        extra_args: tuple[str, ...] = (),
        stdin_payload: dict[str, object] | None = None,
        timeout: float | None = None,
    ):
        result = self._invoke(
            command,
            extra_args=extra_args,
            stdin_payload=stdin_payload,
            timeout=timeout,
        )
        payload = self._load_json_payload(result.stdout)
        return model_cls.model_validate(payload)

    def _invoke(
        self,
        command: str,
        *,
        extra_args: tuple[str, ...] = (),
        stdin_payload: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        ssh_command = self._build_ssh_command(command, extra_args=extra_args, use_stdin=stdin_payload is not None)
        input_text = json.dumps(stdin_payload, ensure_ascii=False) if stdin_payload is not None else None
        result = self._command_runner(
            ssh_command,
            input_text,
            timeout if timeout is not None else self._config.command_timeout_seconds,
        )
        if result.returncode != 0:
            error_text = result.stderr.strip() or result.stdout.strip() or f"remote {command} failed"
            raise RuntimeError(error_text)
        return result

    def _build_ssh_command(self, command: str, *, extra_args: tuple[str, ...], use_stdin: bool) -> list[str]:
        remote_parts = [f"cd {shlex.quote(self._config.remote_repo_root)}"]
        if self._config.remote_env_file:
            remote_parts.append(f"set -a && source {shlex.quote(self._config.remote_env_file)} && set +a")
        worker_command = [
            shlex.quote(self._config.remote_python_bin),
            shlex.quote(self._config.remote_worker_script),
            command,
        ]
        if use_stdin:
            worker_command.append("--stdin")
        worker_command.extend(shlex.quote(item) for item in extra_args)
        remote_parts.append(" ".join(worker_command))
        return [
            self._config.ssh_bin,
            *self._config.ssh_options,
            self._config.ssh_destination,
            "bash",
            "-lc",
            " && ".join(remote_parts),
        ]

    @staticmethod
    def _load_json_payload(stdout: str) -> dict[str, object]:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("remote command returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("remote command returned invalid JSON payload")
        return payload

    @staticmethod
    def _run_command(
        command: list[str],
        input_text: str | None,
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
