from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import os
from pathlib import Path
import shutil

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.agent_protocol.runtime_models import (
    RuntimeRunRead,
    RuntimeRunRequest,
)
from autoresearch.core.services.hermes_command_builder import HermesCommandPlan, build_hermes_command_plan
from autoresearch.core.services.hermes_runtime_contract import (
    normalize_hermes_metadata,
    reject_unsupported_cli_args,
    reject_unsupported_request_surface,
)
from autoresearch.core.services.hermes_runtime_errors import HermesRuntimeErrorKind, HermesRuntimeFailure
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService
from autoresearch.shared.models import ClaudeAgentRunRead, JobStatus


class HermesRuntimeAdapterService(OpenClawRuntimeAdapterService):
    """Hermes runtime adapter behind a stable runtime contract.

    Hermes runs through a fixed one-shot CLI path so AAS keeps the same
    create_session/run/stream/cancel/status surface while using the real
    Hermes executable underneath.
    """

    CONTRACT_VERSION = "1.0"
    STRUCTURED_METADATA_KEYS = (
        "provider",
        "model",
        "profile",
        "toolsets",
        "approval_mode",
        "session_mode",
    )

    def __init__(
        self,
        openclaw_service: OpenClawCompatService,
        claude_service: ClaudeAgentService,
    ) -> None:
        super().__init__(
            openclaw_service=openclaw_service,
            claude_service=claude_service,
            runtime_id="hermes",
            metadata_namespace="hermes",
        )

    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead:
        reject_unsupported_request_surface(request)
        sanitized_request = request.model_copy(update={"cli_args": reject_unsupported_cli_args(request.cli_args)})
        normalized_metadata, _, effective_model = normalize_hermes_metadata(
            sanitized_request.metadata,
            contract_version=self.CONTRACT_VERSION,
            runtime_id=self._runtime_id,
        )
        session_id = self._resolve_session_id(sanitized_request)
        try:
            plan = build_hermes_command_plan(sanitized_request, effective_model)
        except HermesRuntimeFailure as exc:
            return self._fail_before_start(
                request=sanitized_request,
                session_id=session_id,
                normalized_metadata=normalized_metadata,
                failure=exc,
            )

        preflight_failure = self._preflight_hermes_command(plan.argv)
        command_metadata = self._apply_plan_metadata(
            normalized_metadata,
            plan=plan,
            failure=preflight_failure,
        )
        base_create_request = self._build_create_request(sanitized_request, session_id=session_id)
        create_request = base_create_request.model_copy(
            update={
                "metadata": command_metadata,
                "cli_args": [],
                "command_override": plan.argv,
                "append_prompt": False,
                "env": plan.env,
            }
        )
        created = self._claude_service.create(create_request)

        if preflight_failure is not None:
            failed = self._claude_service.fail_preflight(created.agent_run_id, create_request, preflight_failure.message)
            session = self._require_session(session_id)
            return self._map_run(
                failed,
                output_artifacts=self._build_artifacts(session=session, run=failed),
            )

        self._start_created_run(created.agent_run_id, create_request)
        return self._map_run(created)

    def run_from_job(self, job: JobSpec, session_id: str | None = None) -> RuntimeRunRead:
        hermes_metadata = self._openclaw_metadata(job.metadata)
        bound_session_id = session_id or self._string_value(hermes_metadata.get("session_id"))
        request_metadata = {
            "source": "job_spec",
            "aep_run_id": job.run_id,
            "aep_agent_id": job.agent_id,
            "aep_mode": job.mode,
            "aep_input_artifacts": [artifact.model_dump(mode="json") for artifact in job.input_artifacts],
            "aep_allowed_paths": list(job.policy.allowed_paths),
            "aep_max_changed_files": job.policy.max_changed_files,
            "hermes": self._extract_structured_metadata(hermes_metadata),
        }
        request = RuntimeRunRequest(
            runtime_id=self._runtime_id,
            session_id=bound_session_id,
            task_name=self._string_value(hermes_metadata.get("task_name")) or job.run_id,
            prompt=job.task,
            timeout_seconds=job.policy.timeout_sec,
            work_dir=self._string_value(hermes_metadata.get("work_dir")),
            cli_args=self._string_list(hermes_metadata.get("cli_args")),
            env=self._string_mapping(hermes_metadata.get("env")),
            metadata=request_metadata,
        )
        return self.run(request)

    def _preflight_hermes_command(self, command: list[str]) -> HermesRuntimeFailure | None:
        executable = command[0].strip() if command else ""
        if not executable:
            return HermesRuntimeFailure(
                kind=HermesRuntimeErrorKind.BINARY_MISSING,
                message="AUTORESEARCH_HERMES_COMMAND resolved to an empty executable",
                failed_stage="preflight",
            )

        if self._looks_like_path(executable):
            candidate = Path(executable).expanduser()
            if not candidate.exists():
                return HermesRuntimeFailure(
                    kind=HermesRuntimeErrorKind.BINARY_MISSING,
                    message=f"Hermes executable path not found: {executable}",
                    failed_stage="preflight",
                )
            if not candidate.is_file():
                return HermesRuntimeFailure(
                    kind=HermesRuntimeErrorKind.BINARY_MISSING,
                    message=f"Hermes executable path is not a file: {executable}",
                    failed_stage="preflight",
                )
            if not os.access(candidate, os.X_OK):
                return HermesRuntimeFailure(
                    kind=HermesRuntimeErrorKind.BINARY_MISSING,
                    message=f"Hermes executable is not executable: {executable}",
                    failed_stage="preflight",
                )
            return None

        if shutil.which(executable) is None:
            return HermesRuntimeFailure(
                kind=HermesRuntimeErrorKind.BINARY_MISSING,
                message=f"Hermes executable not found in PATH: {executable}",
                failed_stage="preflight",
            )
        return None

    @staticmethod
    def _looks_like_path(value: str) -> bool:
        if value.startswith(("~", ".", "/")):
            return True
        return any(sep and sep in value for sep in (os.sep, os.altsep))

    def _extract_structured_metadata(self, payload: Mapping[str, object]) -> dict[str, object]:
        return {
            key: payload[key]
            for key in self.STRUCTURED_METADATA_KEYS
            if key in payload
        }

    def _compose_runtime_metadata(self, run: ClaudeAgentRunRead) -> dict[str, Any]:
        metadata = super()._compose_runtime_metadata(run)
        hermes_metadata = dict(self._mapping_value(metadata.get("hermes")))
        hermes_metadata.setdefault("contract_version", self.CONTRACT_VERSION)
        metadata["hermes"] = hermes_metadata

        error_kind, failed_stage = self._classify_failure(run, metadata)
        if error_kind is not None:
            metadata["error_kind"] = error_kind.value
        if failed_stage is not None:
            metadata["failed_stage"] = failed_stage
        return metadata

    def _compose_summary(self, run: ClaudeAgentRunRead) -> str:
        metadata = self._compose_runtime_metadata(run)
        error_kind = self._string_value(metadata.get("error_kind"))

        if run.status is JobStatus.COMPLETED:
            line = self._first_output_line(run.stdout_preview)
            return f"Hermes completed: {line}" if line else "Hermes completed successfully."
        if run.status is JobStatus.CANCELLED:
            return "Hermes run cancelled."
        if error_kind == HermesRuntimeErrorKind.BINARY_MISSING.value:
            return "Hermes executable is unavailable."
        if error_kind == HermesRuntimeErrorKind.COMMAND_BUILD_FAILED.value:
            return "Hermes command construction failed."
        if error_kind == HermesRuntimeErrorKind.LAUNCH_FAILED.value:
            return "Hermes failed to launch."
        if error_kind == HermesRuntimeErrorKind.TIMEOUT.value:
            return f"Hermes timed out after {run.timeout_seconds}s."
        if error_kind == HermesRuntimeErrorKind.NONZERO_EXIT.value:
            return f"Hermes exited with code {run.returncode}."
        if error_kind == HermesRuntimeErrorKind.INTERNAL_ERROR.value:
            return "Hermes runtime failed with an internal error."
        return super()._compose_summary(run)

    def _fail_before_start(
        self,
        *,
        request: RuntimeRunRequest,
        session_id: str,
        normalized_metadata: dict[str, object],
        failure: HermesRuntimeFailure,
    ) -> RuntimeRunRead:
        fallback_command = ["hermes", "chat", "-Q", "-q", request.prompt]
        hermes_record = dict(self._mapping_value(normalized_metadata.get("hermes")))
        effective_record = self._mapping_value(hermes_record.get("effective"))
        metadata = self._apply_failure_metadata(
            normalized_metadata,
            failure=failure,
            command_projection={
                "argv": fallback_command,
                "cwd": request.work_dir,
                "timeout_seconds": request.timeout_seconds,
                "mapped_fields": [],
                "unmapped_fields": [],
                "blocked_cli_args": [],
            },
            safety_flags={
                "approval_mode": self._string_value(effective_record.get("approval_mode")),
                "oneshot_only": True,
                "cli_args_escape_hatch_used": bool(request.cli_args),
                "blocked_cli_args": [],
            },
        )
        base_create_request = self._build_create_request(request, session_id=session_id)
        create_request = base_create_request.model_copy(
            update={
                "metadata": metadata,
                "cli_args": [],
                "command_override": fallback_command,
                "append_prompt": False,
            }
        )
        created = self._claude_service.create(create_request)
        failed = self._claude_service.fail_preflight(created.agent_run_id, create_request, failure.message)
        session = self._require_session(session_id)
        return self._map_run(
            failed,
            output_artifacts=self._build_artifacts(session=session, run=failed),
        )

    def _apply_plan_metadata(
        self,
        metadata: dict[str, object],
        *,
        plan: HermesCommandPlan,
        failure: HermesRuntimeFailure | None = None,
    ) -> dict[str, object]:
        return self._apply_failure_metadata(
            metadata,
            failure=failure,
            command_projection=plan.to_command_projection(),
            safety_flags=plan.safety_flags,
            effective_metadata=plan.effective_metadata,
        )

    def _apply_failure_metadata(
        self,
        metadata: dict[str, object],
        *,
        failure: HermesRuntimeFailure | None,
        command_projection: dict[str, Any],
        safety_flags: dict[str, Any],
        effective_metadata: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        normalized = dict(metadata)
        hermes_metadata = dict(self._mapping_value(normalized.get("hermes")))
        if effective_metadata is not None:
            hermes_metadata["effective"] = effective_metadata
        hermes_metadata["command_projection"] = command_projection
        hermes_metadata["safety_flags"] = safety_flags
        normalized["hermes"] = hermes_metadata
        if failure is not None:
            normalized["error_kind"] = failure.kind.value
            normalized["failed_stage"] = failure.failed_stage
        return normalized

    def _classify_failure(
        self,
        run: ClaudeAgentRunRead,
        metadata: Mapping[str, object],
    ) -> tuple[HermesRuntimeErrorKind | None, str | None]:
        raw_kind = self._string_value(metadata.get("error_kind"))
        if raw_kind:
            try:
                return HermesRuntimeErrorKind(raw_kind), self._string_value(metadata.get("failed_stage"))
            except ValueError:
                pass
        if run.status is JobStatus.CANCELLED:
            return HermesRuntimeErrorKind.CANCELLED, "cancel"
        if bool(metadata.get("preflight_failed")):
            return HermesRuntimeErrorKind.BINARY_MISSING, "preflight"
        if bool(metadata.get("launch_failed")):
            return HermesRuntimeErrorKind.LAUNCH_FAILED, "launch"
        if bool(metadata.get("timeout_failed")):
            return HermesRuntimeErrorKind.TIMEOUT, "execute"
        if bool(metadata.get("internal_failure")):
            return HermesRuntimeErrorKind.INTERNAL_ERROR, "execute"
        if run.status is JobStatus.FAILED and run.returncode not in {None, 0, -1}:
            return HermesRuntimeErrorKind.NONZERO_EXIT, "execute"
        return None, None

    @staticmethod
    def _first_output_line(value: str | None, *, limit: int = 120) -> str | None:
        if value is None:
            return None
        line = next((item.strip() for item in value.splitlines() if item.strip()), "")
        if not line:
            return None
        if len(line) <= limit:
            return line
        return f"{line[: limit - 3]}..."
