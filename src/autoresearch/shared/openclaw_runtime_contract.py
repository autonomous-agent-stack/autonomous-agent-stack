from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from autoresearch.shared.models import StrictModel


class OpenClawRuntimeJobSpec(StrictModel):
    protocol_version: Literal["openclaw-runtime/v1"] = "openclaw-runtime/v1"
    job_id: str = Field(..., min_length=1)
    action: Literal["send_message", "run_skill"]
    session_id: str = Field(..., min_length=1)
    role: Literal["system", "user", "assistant", "tool", "status"] = "assistant"
    content: str | None = None
    skill_id: str | None = None
    input: Any = None
    credentials: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_action_fields(self) -> "OpenClawRuntimeJobSpec":
        self.job_id = self.job_id.strip()
        self.session_id = self.session_id.strip()
        if not self.job_id:
            raise ValueError("job_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")

        if self.action == "send_message":
            content = (self.content or "").strip()
            if not content:
                raise ValueError("send_message requires non-empty content")
            self.content = content
            return self

        selector = (self.skill_id or "").strip()
        if not selector:
            raise ValueError("run_skill requires skill_id")
        self.skill_id = selector
        return self


class OpenClawRuntimeResult(StrictModel):
    job_id: str
    action: Literal["send_message", "run_skill"]
    session_id: str
    success: bool = True
    summary: str
    error: str | None = None
    event_id: str | None = None
    skill_id: str | None = None
    result: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
