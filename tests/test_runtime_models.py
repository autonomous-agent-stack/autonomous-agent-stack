from __future__ import annotations

import pytest
from pydantic import ValidationError

from autoresearch.agent_protocol.runtime_models import HermesRuntimeMetadata


def test_hermes_runtime_metadata_normalizes_supported_fields() -> None:
    metadata = HermesRuntimeMetadata.model_validate(
        {
            "provider": " openai ",
            "model": " gpt-5.1 ",
            "profile": " local ",
            "toolsets": ["shell", "shell", "git", " "],
            "approval_mode": "manual",
            "session_mode": "oneshot",
        }
    )

    assert metadata.provider == "openai"
    assert metadata.model == "gpt-5.1"
    assert metadata.profile == "local"
    assert metadata.toolsets == ["shell", "git"]
    assert metadata.approval_mode == "manual"
    assert metadata.session_mode == "oneshot"


@pytest.mark.parametrize(
    "payload",
    [
        {"provider": 123},
        {"toolsets": "shell"},
        {"toolsets": ["shell", 3]},
        {"approval_mode": "always_yes"},
        {"session_mode": "resume"},
        {"unexpected": True},
    ],
)
def test_hermes_runtime_metadata_rejects_invalid_payload(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HermesRuntimeMetadata.model_validate(payload)
