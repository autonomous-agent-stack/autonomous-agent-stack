from __future__ import annotations

from dataclasses import dataclass, field
import os
import shlex
from typing import Any

from autoresearch.agent_protocol.runtime_models import HermesRuntimeMetadata, RuntimeRunRequest
from autoresearch.core.services.hermes_runtime_errors import HermesRuntimeErrorKind, HermesRuntimeFailure

_LEGACY_BUTLER_PROFILE = "butler"


def _remap_legacy_butler_profile_argv(argv: list[str]) -> list[str]:
    """Old docs/examples used `butler` as a profile name; Hermes has no such stock profile."""
    if len(argv) < 2:
        return argv
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        low = tok.lower()
        if low in ("--profile", "-p") and i + 1 < len(argv):
            nxt = argv[i + 1]
            if str(nxt).strip().lower() == _LEGACY_BUTLER_PROFILE:
                out.extend([tok, "default"])
            else:
                out.extend([tok, nxt])
            i += 2
            continue
        if low.startswith("--profile="):
            _, _, val = tok.partition("=")
            if val.strip().lower() == _LEGACY_BUTLER_PROFILE:
                out.append("--profile=default")
            else:
                out.append(tok)
            i += 1
            continue
        if low.startswith("-p=") and len(tok) > 3:
            val = tok[3:]
            if val.strip().lower() == _LEGACY_BUTLER_PROFILE:
                out.append("-p=default")
            else:
                out.append(tok)
            i += 1
            continue
        if len(tok) > 2 and low.startswith("-p") and tok[2] not in ("=", "-"):
            rest = tok[2:]
            if rest.strip().lower() == _LEGACY_BUTLER_PROFILE:
                out.append("-pdefault")
            else:
                out.append(tok)
            i += 1
            continue
        out.append(tok)
        i += 1
    return out


@dataclass(slots=True)
class HermesCommandPlan:
    argv: list[str]
    cwd: str | None
    env: dict[str, str]
    timeout_seconds: int
    effective_metadata: dict[str, Any]
    safety_flags: dict[str, Any] = field(default_factory=dict)
    summary_inputs: dict[str, Any] = field(default_factory=dict)

    def to_command_projection(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv),
            "cwd": self.cwd,
            "timeout_seconds": self.timeout_seconds,
            "mapped_fields": list(self.safety_flags.get("mapped_fields", [])),
            "unmapped_fields": list(self.safety_flags.get("unmapped_fields", [])),
            "blocked_cli_args": list(self.safety_flags.get("blocked_cli_args", [])),
        }


def build_hermes_command_plan(
    request: RuntimeRunRequest,
    hermes_meta: HermesRuntimeMetadata,
) -> HermesCommandPlan:
    raw_command = os.getenv("AUTORESEARCH_HERMES_COMMAND", "hermes")
    try:
        base_command = shlex.split(raw_command or "hermes")
    except ValueError as exc:
        raise HermesRuntimeFailure(
            kind=HermesRuntimeErrorKind.COMMAND_BUILD_FAILED,
            message=f"AUTORESEARCH_HERMES_COMMAND could not be parsed: {exc}",
            failed_stage="command_build",
            details={"raw_command": raw_command},
        ) from exc

    if not base_command:
        raise HermesRuntimeFailure(
            kind=HermesRuntimeErrorKind.COMMAND_BUILD_FAILED,
            message="AUTORESEARCH_HERMES_COMMAND resolved to an empty command",
            failed_stage="command_build",
            details={"raw_command": raw_command},
        )

    base_command = _remap_legacy_butler_profile_argv(list(base_command))

    global_flags: list[str] = []
    chat_flags: list[str] = []
    mapped_fields: list[str] = []
    unmapped_fields: list[str] = []

    if hermes_meta.profile:
        global_flags.extend(["--profile", hermes_meta.profile])
        mapped_fields.append("profile")
    if hermes_meta.provider:
        chat_flags.extend(["--provider", hermes_meta.provider])
        mapped_fields.append("provider")
    if hermes_meta.model:
        chat_flags.extend(["--model", hermes_meta.model])
        mapped_fields.append("model")
    if hermes_meta.toolsets:
        chat_flags.extend(["--toolsets", ",".join(hermes_meta.toolsets)])
        mapped_fields.append("toolsets")
    if hermes_meta.approval_mode:
        unmapped_fields.append("approval_mode")
    if hermes_meta.session_mode:
        unmapped_fields.append("session_mode")

    # Telegram queues `telegram_settings.claude_args` into `cli_args` for every runtime; a mistaken
    # `--profile butler` there must not override Hermes (common mis-copy from old examples).
    sanitized_cli_args = _remap_legacy_butler_profile_argv(list(request.cli_args))
    argv = [*base_command, *global_flags, "chat", "-Q", "-q", request.prompt, *chat_flags, *sanitized_cli_args]
    effective_metadata = hermes_meta.model_dump(mode="json")
    safety_flags = {
        "approval_mode": hermes_meta.approval_mode,
        "oneshot_only": True,
        "cli_args_escape_hatch_used": bool(sanitized_cli_args),
        "blocked_cli_args": [],
        "mapped_fields": mapped_fields,
        "unmapped_fields": unmapped_fields,
    }
    summary_inputs = {
        "prompt_head": _prompt_head(request.prompt),
        "profile": hermes_meta.profile,
        "provider": hermes_meta.provider,
        "model": hermes_meta.model,
        "timeout_seconds": request.timeout_seconds,
    }
    return HermesCommandPlan(
        argv=argv,
        cwd=request.work_dir,
        env=dict(request.env),
        timeout_seconds=request.timeout_seconds,
        effective_metadata=effective_metadata,
        safety_flags=safety_flags,
        summary_inputs=summary_inputs,
    )


def _prompt_head(prompt: str, limit: int = 80) -> str:
    compact = " ".join(prompt.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
