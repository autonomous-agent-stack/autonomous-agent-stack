from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.control_plane.contracts import ControlPlaneTaskCreateRequest
from autoresearch.control_plane.service import ControlPlaneService
from autoresearch.core.services.capability_manifest_service import CapabilityManifestService
from autoresearch.core.services.butler_failure_review import (
    ButlerFailureReviewRequest,
    ButlerFailureReviewService,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.usage_quota import (
    UsageQuotaCheckRequest,
    UsageQuotaService,
    UsageReserveRead,
)
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.shared.models import SessionEventCreateRequest, StrictModel, utc_now
from autoresearch.shared.store import Repository, create_resource_id


FederationTrustLevel = Literal["L0", "L1", "L2", "L3"]
FederationPeerStatus = Literal["active", "disabled", "revoked"]
FederationLeaseStatus = Literal["active", "revoked", "expired"]
FederationTaskStatus = Literal["accepted", "awaiting_approval", "queued", "running", "succeeded", "failed", "rejected", "cancelled"]


class FederationPeerRead(StrictModel):
    peer_id: str
    display_name: str
    endpoint: str | None = None
    trust_level: FederationTrustLevel = "L1"
    status: FederationPeerStatus = "disabled"
    allowed_capabilities: list[str] = Field(default_factory=list)
    max_units_per_period: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationCapabilityRead(StrictModel):
    capability_id: str
    name: str
    lease_required: bool = True
    risk_tags: list[str] = Field(default_factory=list)
    max_duration_seconds: int = 3600
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationLeaseCreateRequest(StrictModel):
    peer_id: str = Field(..., min_length=1)
    capability_id: str = Field(..., min_length=1)
    duration_seconds: int = Field(default=3600, ge=60, le=604800)
    max_tasks: int = Field(default=1, ge=1, le=1000)
    quota_units: int = Field(default=10, ge=0)
    requested_by: str = "local-admin"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("peer_id", "capability_id", "requested_by", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> str:
        return str(value or "").strip()


class FederationLeaseRead(StrictModel):
    lease_id: str
    peer_id: str
    capability_id: str
    status: FederationLeaseStatus
    max_tasks: int
    used_tasks: int = 0
    quota_units: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    requested_by: str = "local-admin"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationTaskCreateRequest(StrictModel):
    peer_id: str = Field(..., min_length=1)
    lease_id: str = Field(..., min_length=1)
    capability_id: str = Field(..., min_length=1)
    task_name: str = Field(..., min_length=1)
    intent: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[str] = Field(default_factory=list)
    quota_units: int = Field(default=1, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("peer_id", "lease_id", "capability_id", "task_name", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("intent", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class FederationTaskRead(StrictModel):
    federation_task_id: str
    peer_id: str
    lease_id: str
    capability_id: str
    status: FederationTaskStatus
    local_task_id: str | None = None
    local_run_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationService:
    """Static-peer federation gateway for bilateral AAS v1 task leases."""

    def __init__(
        self,
        *,
        peers_path: Path,
        lease_repository: Repository[FederationLeaseRead],
        task_repository: Repository[FederationTaskRead],
        control_plane: ControlPlaneService,
        capability_service: CapabilityManifestService | None = None,
        quota_service: UsageQuotaService | None = None,
        session_events: SessionEventService | None = None,
        failure_review_service: ButlerFailureReviewService | None = None,
    ) -> None:
        self._peers_path = peers_path
        self._lease_repository = lease_repository
        self._task_repository = task_repository
        self._control_plane = control_plane
        self._capability_service = capability_service
        self._quota_service = quota_service
        self._session_events = session_events
        self._failure_review_service = failure_review_service
        self._payload = self._load_payload()

    @property
    def peers_path(self) -> Path:
        return self._peers_path

    def list_peers(self) -> list[FederationPeerRead]:
        peers = [self._peer_from_payload(item) for item in self._peer_items()]
        return sorted(peers, key=lambda item: item.peer_id)

    def list_capabilities(self) -> list[FederationCapabilityRead]:
        raw = self._payload.get("published_capabilities")
        capabilities: list[FederationCapabilityRead] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    capabilities.append(FederationCapabilityRead.model_validate(item))
        if capabilities:
            configured = {item.capability_id for item in capabilities}
            capabilities.extend(
                self._federation_capability_from_manifest(item)
                for item in self._capability_manifests()
                if item.lease_enabled and item.enabled and item.capability_id not in configured
            )
            return sorted(capabilities, key=lambda item: item.capability_id)
        manifest_capabilities = [
            self._federation_capability_from_manifest(item)
            for item in self._capability_manifests()
            if item.lease_enabled and item.enabled
        ]
        if manifest_capabilities:
            return sorted(manifest_capabilities, key=lambda item: item.capability_id)
        return [
            FederationCapabilityRead(
                capability_id=item.capability_id,
                name=item.name,
                lease_required=True,
                risk_tags=item.risk_tags,
                metadata={"source": "control_plane_v2"},
            )
            for item in self._control_plane.list_capabilities()
            if item.enabled and not item.external_calls_enabled
        ]

    def _capability_manifests(self) -> list[Any]:
        if self._capability_service is None:
            return []
        return self._capability_service.list_manifests()

    @staticmethod
    def _federation_capability_from_manifest(manifest: Any) -> FederationCapabilityRead:
        return FederationCapabilityRead(
            capability_id=manifest.capability_id,
            name=manifest.display_name or manifest.capability_id,
            lease_required=manifest.lease_enabled,
            risk_tags=[manifest.risk_tier],
            max_duration_seconds=int(manifest.metadata.get("max_duration_seconds") or 3600),
            metadata={
                **manifest.metadata,
                "source": "capability_manifest",
                "provided_by": manifest.provided_by,
                "kind": manifest.kind,
            },
        )

    def list_leases(self, *, peer_id: str | None = None) -> list[FederationLeaseRead]:
        leases = [self._normalize_lease(item) for item in self._lease_repository.list()]
        if peer_id:
            leases = [item for item in leases if item.peer_id == peer_id]
        return sorted(leases, key=lambda item: item.updated_at, reverse=True)

    def create_lease(self, request: FederationLeaseCreateRequest) -> FederationLeaseRead:
        peer = self._require_active_peer(request.peer_id)
        capability = self._require_capability(request.capability_id)
        if request.capability_id not in peer.allowed_capabilities and "*" not in peer.allowed_capabilities:
            raise PermissionError(f"peer {peer.peer_id} is not allowed to lease {request.capability_id}")
        duration = min(request.duration_seconds, capability.max_duration_seconds)
        current = utc_now()
        lease = FederationLeaseRead(
            lease_id=create_resource_id("flease"),
            peer_id=peer.peer_id,
            capability_id=request.capability_id,
            status="active",
            max_tasks=request.max_tasks,
            used_tasks=0,
            quota_units=min(request.quota_units, peer.max_units_per_period) if peer.max_units_per_period else request.quota_units,
            created_at=current,
            updated_at=current,
            expires_at=current + timedelta(seconds=duration),
            requested_by=request.requested_by,
            metadata={
                **request.metadata,
                "trust_level": peer.trust_level,
                "risk_tags": capability.risk_tags,
            },
        )
        saved = self._lease_repository.save(lease.lease_id, lease)
        self._record_event("federation.lease.created", f"Federation lease created: {saved.lease_id}", saved.model_dump(mode="json"))
        return saved

    def revoke_lease(self, lease_id: str, *, requested_by: str = "local-admin", reason: str = "manual revoke") -> FederationLeaseRead:
        lease = self._lease_repository.get(lease_id)
        if lease is None:
            raise KeyError(lease_id)
        current = utc_now()
        revoked = lease.model_copy(
            update={
                "status": "revoked",
                "updated_at": current,
                "revoked_at": current,
                "metadata": {**lease.metadata, "revoked_by": requested_by, "revoke_reason": reason},
            }
        )
        saved = self._lease_repository.save(revoked.lease_id, revoked)
        self._record_event("federation.lease.revoked", f"Federation lease revoked: {saved.lease_id}", saved.model_dump(mode="json"))
        return saved

    def submit_task(self, request: FederationTaskCreateRequest) -> FederationTaskRead:
        peer = self._require_active_peer(request.peer_id)
        lease = self._require_active_lease(request.lease_id, peer_id=peer.peer_id, capability_id=request.capability_id)
        if lease.used_tasks >= lease.max_tasks:
            return self._reject_task(request, "lease task limit exhausted")
        if request.quota_units > lease.quota_units:
            return self._reject_task(request, "lease quota exhausted")

        session_id = str(request.metadata.get("session_id") or create_resource_id("federation_session"))
        reserve = self._reserve_peer_quota(request, peer_id=peer.peer_id, session_id=session_id)
        if reserve is not None and not reserve.allowed:
            usage_entry_id = reserve.entry.entry_id if reserve.entry else None
            return self._reject_task(request, reserve.reason, usage_entry_id=usage_entry_id)
        usage_entry_id = reserve.entry.entry_id if reserve is not None and reserve.entry else None

        try:
            cp_task = self._control_plane.create_task(
                ControlPlaneTaskCreateRequest(
                    name=request.task_name,
                    intent=request.intent or request.task_name,
                    session_id=session_id,
                    capability_id=request.capability_id,
                    parameters={
                        **request.parameters,
                        "federation_peer_id": peer.peer_id,
                        "federation_lease_id": lease.lease_id,
                        "actor_role": "peer",
                    },
                    risk_tags=sorted(set(request.risk_tags) | set(lease.metadata.get("risk_tags") or [])),
                    requested_by=f"peer:{peer.peer_id}",
                    priority=5,
                    metadata={
                        **request.metadata,
                        "federation": True,
                        "peer_id": peer.peer_id,
                        "trust_level": peer.trust_level,
                        "lease_id": lease.lease_id,
                        "quota_units": request.quota_units,
                        "usage_entry_id": usage_entry_id,
                    },
                )
            )
        except Exception:
            if usage_entry_id is not None and self._quota_service is not None:
                self._quota_service.release(
                    usage_entry_id,
                    metadata={"release_reason": "federation_task_create_failed"},
                )
            raise
        if usage_entry_id is not None and self._quota_service is not None:
            self._quota_service.commit(
                usage_entry_id,
                metadata={"commit_reason": "federation_task_accepted"},
            )
        current = utc_now()
        federation_task = FederationTaskRead(
            federation_task_id=create_resource_id("ftask"),
            peer_id=peer.peer_id,
            lease_id=lease.lease_id,
            capability_id=request.capability_id,
            status=_federation_status_from_cp(cp_task.status.value),
            local_task_id=cp_task.task_id,
            local_run_id=cp_task.run_id,
            result=cp_task.result,
            error=cp_task.error,
            created_at=current,
            updated_at=current,
            metadata={
                "control_plane_status": cp_task.status.value,
                "approval_id": cp_task.approval_id,
                "usage_entry_id": usage_entry_id,
            },
        )
        self._task_repository.save(federation_task.federation_task_id, federation_task)
        self._lease_repository.save(
            lease.lease_id,
            lease.model_copy(
                update={
                    "used_tasks": lease.used_tasks + 1,
                    "quota_units": max(0, lease.quota_units - request.quota_units),
                    "updated_at": current,
                }
            ),
        )
        self._record_event(
            "federation.task.accepted",
            f"Federation task accepted: {federation_task.federation_task_id}",
            federation_task.model_dump(mode="json"),
            session_id=session_id,
        )
        return federation_task

    def _reserve_peer_quota(
        self,
        request: FederationTaskCreateRequest,
        *,
        peer_id: str,
        session_id: str,
    ) -> UsageReserveRead | None:
        if self._quota_service is None:
            return None
        return self._quota_service.reserve(
            UsageQuotaCheckRequest(
                subject_id=peer_id,
                subject_type="peer",
                actor_role="peer",
                agent_name=request.capability_id,
                task_id=request.lease_id,
                quota_units=request.quota_units,
                session_id=session_id,
                metadata={
                    **request.metadata,
                    "session_id": session_id,
                    "federation_peer_id": peer_id,
                    "federation_lease_id": request.lease_id,
                    "federation_capability_id": request.capability_id,
                },
            )
        )

    def get_task(self, federation_task_id: str) -> FederationTaskRead | None:
        task = self._task_repository.get(federation_task_id)
        if task is None or task.local_task_id is None:
            return task
        cp_task = self._control_plane.get_task(task.local_task_id)
        if cp_task is None:
            return task
        projected = task.model_copy(
            update={
                "status": _federation_status_from_cp(cp_task.status.value),
                "local_run_id": cp_task.run_id,
                "result": cp_task.result,
                "error": cp_task.error,
                "updated_at": max(task.updated_at, cp_task.updated_at),
                "metadata": {
                    **task.metadata,
                    "control_plane_status": cp_task.status.value,
                    "approval_id": cp_task.approval_id,
                },
            }
        )
        if projected != task:
            self._task_repository.save(projected.federation_task_id, projected)
        return projected

    def doctor(self) -> dict[str, Any]:
        peers = self.list_peers()
        leases = self.list_leases()
        return {
            "status": "ok",
            "peers_path": str(self._peers_path),
            "peers_loaded": self._peers_path.exists(),
            "peer_count": len(peers),
            "active_peer_count": len([peer for peer in peers if peer.status == "active"]),
            "published_capability_count": len(self.list_capabilities()),
            "lease_count": len(leases),
            "active_lease_count": len([lease for lease in leases if lease.status == "active"]),
        }

    def _reject_task(
        self,
        request: FederationTaskCreateRequest,
        reason: str,
        *,
        usage_entry_id: str | None = None,
    ) -> FederationTaskRead:
        current = utc_now()
        review_metadata: dict[str, Any] = {}
        session_id = str(request.metadata.get("session_id") or "").strip() or None
        if self._failure_review_service is not None:
            review = self._failure_review_service.review(
                ButlerFailureReviewRequest(
                    message=request.intent or request.task_name,
                    task_id=request.lease_id,
                    run_id=None,
                    capability_id=request.capability_id,
                    worker_error=reason,
                    worker_message="Federation task rejected",
                    worker_metrics={"status": "rejected", "peer_id": request.peer_id},
                    session_id=session_id,
                    usage_entry_id=usage_entry_id,
                    metadata={
                        **request.metadata,
                        "federation_peer_id": request.peer_id,
                        "federation_lease_id": request.lease_id,
                    },
                )
            )
            review_metadata = {
                "failure_review_id": review.review_id,
                "failure_kind": review.failure_kind,
                "route_repair_suggestion": review.suggested_route,
                "candidate_skill_summary": review.candidate_skill_summary,
            }
        task = FederationTaskRead(
            federation_task_id=create_resource_id("ftask"),
            peer_id=request.peer_id,
            lease_id=request.lease_id,
            capability_id=request.capability_id,
            status="rejected",
            error=reason,
            created_at=current,
            updated_at=current,
            metadata={
                "reason": reason,
                "usage_entry_id": usage_entry_id,
                **review_metadata,
            },
        )
        saved = self._task_repository.save(task.federation_task_id, task)
        self._record_event("federation.task.rejected", reason, saved.model_dump(mode="json"))
        return saved

    def _require_active_peer(self, peer_id: str) -> FederationPeerRead:
        peer = next((item for item in self.list_peers() if item.peer_id == peer_id), None)
        if peer is None:
            raise KeyError(f"federation peer not found: {peer_id}")
        if peer.status != "active":
            raise PermissionError(f"federation peer is not active: {peer_id}")
        return peer

    def _require_capability(self, capability_id: str) -> FederationCapabilityRead:
        capability = next((item for item in self.list_capabilities() if item.capability_id == capability_id), None)
        if capability is None:
            raise KeyError(f"federation capability not published: {capability_id}")
        return capability

    def _require_active_lease(self, lease_id: str, *, peer_id: str, capability_id: str) -> FederationLeaseRead:
        lease = self._lease_repository.get(lease_id)
        if lease is None:
            raise KeyError(f"federation lease not found: {lease_id}")
        lease = self._normalize_lease(lease)
        if lease.status != "active":
            raise PermissionError(f"federation lease is not active: {lease_id}")
        if lease.peer_id != peer_id or lease.capability_id != capability_id:
            raise PermissionError("federation lease scope mismatch")
        return lease

    def _normalize_lease(self, lease: FederationLeaseRead) -> FederationLeaseRead:
        if lease.status != "active" or lease.expires_at > utc_now():
            return lease
        expired = lease.model_copy(update={"status": "expired", "updated_at": utc_now()})
        return self._lease_repository.save(expired.lease_id, expired)

    def _load_payload(self) -> dict[str, Any]:
        if not self._peers_path.exists():
            return {"peers": [], "published_capabilities": []}
        return load_yaml_object(self._peers_path)

    def _peer_items(self) -> list[dict[str, Any]]:
        raw = self._payload.get("peers")
        return [dict(item) for item in raw] if isinstance(raw, list) else []

    @staticmethod
    def _peer_from_payload(payload: dict[str, Any]) -> FederationPeerRead:
        return FederationPeerRead(
            peer_id=str(payload.get("peer_id") or payload.get("id") or "").strip(),
            display_name=str(payload.get("display_name") or payload.get("name") or payload.get("peer_id") or "").strip(),
            endpoint=_optional_string(payload.get("endpoint")),
            trust_level=str(payload.get("trust_level") or "L1").strip(),
            status=str(payload.get("status") or "disabled").strip().lower(),
            allowed_capabilities=[str(item).strip() for item in payload.get("allowed_capabilities") or [] if str(item).strip()],
            max_units_per_period=_int(payload.get("max_units_per_period"), default=0),
            metadata={k: v for k, v in payload.items() if k not in {"peer_id", "id", "display_name", "name", "endpoint", "trust_level", "status", "allowed_capabilities", "max_units_per_period"}},
        )

    def _record_event(
        self,
        event_type: str,
        content: str,
        metadata: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> None:
        if self._session_events is None:
            return
        resolved_session_id = session_id or str(metadata.get("session_id") or metadata.get("lease_id") or metadata.get("federation_task_id") or "federation")
        self._session_events.append(
            SessionEventCreateRequest(
                session_id=resolved_session_id,
                source="federation",
                event_type=event_type,
                role="status",
                content=content,
                status=str(metadata.get("status") or event_type.rsplit(".", 1)[-1]),
                idempotency_key=f"{event_type}:{metadata.get('lease_id') or metadata.get('federation_task_id') or create_resource_id('fed_evt')}",
                metadata=metadata,
            )
        )


def _federation_status_from_cp(status: str) -> FederationTaskStatus:
    return {
        "awaiting_approval": "awaiting_approval",
        "queued": "queued",
        "running": "running",
        "succeeded": "succeeded",
        "failed": "failed",
        "rejected": "rejected",
        "cancelled": "cancelled",
        "created": "accepted",
    }.get(status, "accepted")  # type: ignore[return-value]


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
