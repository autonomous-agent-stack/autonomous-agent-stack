from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from autoresearch.agent_protocol.capability_models import CapabilityManifest
from autoresearch.core.services.capability_manifest_service import CapabilityManifestService
from autoresearch.shared.models import StrictModel, utc_now
from autoresearch.shared.store import Repository, create_resource_id


class A2ACapabilityCard(StrictModel):
    capability_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    lease_required: bool = True
    risk_tier: str = "common_read"
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2AAgentCard(StrictModel):
    name: str = "AAS Evergreen Agent Control Plane"
    version: str = "1.0"
    capabilities: list[A2ACapabilityCard] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATaskCreateRequest(StrictModel):
    capability_id: str
    task: str
    endpoint: str | None = None
    peer_id: str | None = None
    lease_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATaskRead(StrictModel):
    task_id: str
    capability_id: str
    status: Literal["accepted", "succeeded", "failed", "rejected"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2AGatewayService:
    def __init__(
        self,
        *,
        capability_service: CapabilityManifestService,
        task_repository: Repository[A2ATaskRead],
    ) -> None:
        self._capability_service = capability_service
        self._task_repository = task_repository

    def agent_card(self) -> A2AAgentCard:
        capabilities = [
            self._card_from_manifest(item)
            for item in self._capability_service.list_manifests()
            if item.enabled and item.lease_enabled
        ]
        return A2AAgentCard(
            capabilities=capabilities,
            metadata={
                "control_plane": "aas",
                "ledger": "federation",
                "credential_policy": "credentials_do_not_leave_provider_node",
            },
        )

    def submit_task(self, request: A2ATaskCreateRequest) -> A2ATaskRead:
        try:
            capability = self._capability_service.get(request.capability_id)
        except FileNotFoundError:
            return self._save_task(request, status="rejected", error="capability not found")
        if not capability.enabled or not capability.lease_enabled:
            return self._save_task(request, status="rejected", error="capability is not published for A2A")
        return self._save_task(
            request,
            status="succeeded",
            result={
                "message": "A2A task accepted by local AAS demo bridge",
                "capability_id": capability.capability_id,
                "task": request.task,
            },
        )

    def get_task(self, task_id: str) -> A2ATaskRead | None:
        return self._task_repository.get(task_id)

    def _save_task(
        self,
        request: A2ATaskCreateRequest,
        *,
        status: Literal["accepted", "succeeded", "failed", "rejected"],
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> A2ATaskRead:
        current = utc_now()
        task = A2ATaskRead(
            task_id=create_resource_id("a2a_task"),
            capability_id=request.capability_id,
            status=status,
            result=dict(result or {}),
            error=error,
            created_at=current,
            updated_at=current,
            metadata={
                **request.metadata,
                "endpoint": request.endpoint,
                "peer_id": request.peer_id,
                "lease_id": request.lease_id,
            },
        )
        return self._task_repository.save(task.task_id, task)

    @staticmethod
    def _card_from_manifest(manifest: CapabilityManifest) -> A2ACapabilityCard:
        return A2ACapabilityCard(
            capability_id=manifest.capability_id,
            name=manifest.display_name or manifest.capability_id,
            description=manifest.description,
            input_schema=manifest.input_schema,
            output_schema=manifest.output_schema,
            lease_required=manifest.lease_enabled,
            risk_tier=manifest.risk_tier,
            metadata={
                **manifest.metadata,
                "provided_by": manifest.provided_by,
                "kind": manifest.kind,
            },
        )
