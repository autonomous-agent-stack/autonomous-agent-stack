from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import ApprovalRisk, StrictModel, WorkerQueueItemCreateRequest


class WorkerRoutingDecision(StrictModel):
    route: str
    selected_worker: str
    worker_chain: list[str] = Field(default_factory=list)
    selection_reason: str
    requires_approval: bool = False
    approval_risk: ApprovalRisk | None = None
    approval_reason: str | None = None
    approval_policy: Literal["auto", "approval_required", "blocked"] = "auto"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerOrchestrationReplayPayload(StrictModel):
    queue_request: WorkerQueueItemCreateRequest
    decision: WorkerRoutingDecision


class WorkerApprovalResumeRead(StrictModel):
    approval_id: str
    run_id: str
    queue_request: WorkerQueueItemCreateRequest
    decision: WorkerRoutingDecision
