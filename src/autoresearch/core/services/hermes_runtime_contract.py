from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from autoresearch.agent_protocol.runtime_models import HermesRuntimeMetadata, RuntimeRunRequest

BLOCKED_HERMES_CLI_ARGS = (
    "--yolo",
    "--resume",
    "-r",
    "--continue",
    "-c",
    "--pass-session-id",
    "--image",
    "--skills",
    "-s",
    "--worktree",
    "-w",
)


def reject_unsupported_request_surface(request: RuntimeRunRequest) -> None:
    unsupported_fields: list[str] = []
    if request.images:
        unsupported_fields.append("images")
    if request.skill_names:
        unsupported_fields.append("skill_names")
    if request.command_override is not None:
        unsupported_fields.append("command_override")
    if unsupported_fields:
        joined = ", ".join(unsupported_fields)
        raise ValueError(f"Hermes runtime v1 does not support: {joined}")


def reject_unsupported_cli_args(cli_args: list[str]) -> list[str]:
    blocked = [
        arg
        for arg in cli_args
        if any(arg == flag or arg.startswith(f"{flag}=") for flag in BLOCKED_HERMES_CLI_ARGS)
    ]
    if blocked:
        joined = ", ".join(blocked)
        raise ValueError(f"Hermes runtime v1 does not support cli_args: {joined}")
    return list(cli_args)


def normalize_hermes_metadata(
    metadata: Mapping[str, object],
    *,
    contract_version: str,
    runtime_id: str = "hermes",
) -> tuple[dict[str, object], HermesRuntimeMetadata, HermesRuntimeMetadata]:
    normalized = dict(metadata)
    raw_hermes = _mapping_value(metadata.get("hermes"))
    requested_model = _parse_hermes_metadata(raw_hermes)
    if requested_model.approval_mode == "off":
        raise ValueError("Hermes runtime v1 does not support metadata.hermes.approval_mode=off")

    effective_model = requested_model.model_copy(
        update={
            "session_mode": requested_model.session_mode or "oneshot",
        }
    )

    normalized["runtime_adapter"] = runtime_id
    normalized["hermes"] = {
        "contract_version": contract_version,
        "requested": requested_model.model_dump(
            mode="json",
            exclude_defaults=True,
            exclude_none=True,
        ),
        "effective": effective_model.model_dump(mode="json"),
    }
    return normalized, requested_model, effective_model


def _parse_hermes_metadata(payload: Mapping[str, object]) -> HermesRuntimeMetadata:
    try:
        return HermesRuntimeMetadata.model_validate(dict(payload))
    except ValidationError as exc:
        raise ValueError(f"invalid metadata.hermes: {exc}") from exc


def _mapping_value(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("invalid metadata.hermes: value must be an object")
    return {str(key): item for key, item in value.items()}
