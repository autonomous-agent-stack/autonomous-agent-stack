from __future__ import annotations

from typing import Any

from pydantic import Field

from autoresearch.shared.models import ApprovalRisk, GitPromotionMode, StrictModel


class WorkerRoute(str):
    CLAUDE_DIRECT = "claude_direct"
    AUTORESEARCH = "autoresearch"
    OPENHANDS = "openhands"
    AUTORESEARCH_THEN_OPENHANDS = "autoresearch_then_openhands"


class WorkerRoutingDecision(StrictModel):
    route: str
    selected_worker: str
    worker_chain: list[str] = Field(default_factory=list)
    selection_reason: str
    requires_approval: bool = False
    approval_risk: ApprovalRisk | None = None
    approval_reason: str | None = None
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    test_command: str
    pipeline_target: GitPromotionMode = GitPromotionMode.PATCH
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerExecutionSummary(StrictModel):
    route: str
    selected_worker: str
    worker_chain: list[str] = Field(default_factory=list)
    status: str
    summary_text: str
    error_text: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    promotion_mode: str | None = None
    promotion_success: bool | None = None
    promotion_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
