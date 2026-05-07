from __future__ import annotations

import os
from typing import Any, Literal

os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "__all__")

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Mood = Literal["relax", "funny", "exciting", "learning", "companion", "mixed"]
FocusLevel = Literal["low", "medium", "high"]
Company = Literal["solo", "friends", "boss", "family"]


class EntertainmentCuratorRequest(StrictModel):
    mood: Mood = "relax"
    time_available: str = "1小时"
    interest: list[str] = Field(default_factory=lambda: ["电影", "音乐"])
    focus_level: FocusLevel = "medium"
    company: Company = "solo"
    channel: Literal["telegram"] = "telegram"
    raw_text: str = ""
    requested_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("time_available", "raw_text", "requested_by", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None

    @field_validator("interest", mode="before")
    @classmethod
    def _normalize_interest(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = value.replace("、", ",").replace("，", ",").split(",")
            return [item.strip() for item in parts if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]

    @model_validator(mode="after")
    def _default_interest(self) -> EntertainmentCuratorRequest:
        if not self.interest:
            self.interest = ["电影", "音乐"]
        return self


class EntertainmentRecommendation(StrictModel):
    title: str
    type: str
    platform: str
    search_query: str
    reason: str
    alternative: str
    estimated_time: str


class NotebookLMPack(StrictModel):
    enabled: bool = False
    title: str = ""
    sources_to_collect: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    workflow: list[str] = Field(default_factory=list)


class EntertainmentCuratorResult(StrictModel):
    title: str
    mood: Mood
    time_available: str
    company: Company
    recommendations: list[EntertainmentRecommendation]
    notebooklm_pack: NotebookLMPack
    copyright_boundary: str
    channel: Literal["telegram"] = "telegram"
    account_profile: dict[str, Any] = Field(default_factory=dict)
    status: Literal["completed", "rejected"] = "completed"
    summary: str = ""
