from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalRead,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneSessionRead,
    ControlPlaneTaskRead,
)
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
from autoresearch.core.services.federation import (
    FederationLeaseCreateRequest,
    FederationLeaseRead,
    FederationService,
    FederationTaskCreateRequest,
    FederationTaskRead,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.usage_quota import UsageLedgerEntryRead, UsageQuotaService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    SessionEventRead,
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
)
from autoresearch.shared.store import InMemoryRepository


def _write_peer_policy(root: Path, *, peer_quota: int = 10) -> tuple[Path, Path]:
    peers = root / "federation_peers.yaml"
    quota = root / "quota_policy.yaml"
    peers.write_text(
        """
peers:
  - peer_id: demo-peer
    display_name: Demo peer
    trust_level: L1
    status: active
    allowed_capabilities: [echo]
    max_units_per_period: 10
published_capabilities:
  - capability_id: echo
    name: Echo
    lease_required: true
    risk_tags: []
    max_duration_seconds: 3600
""",
        encoding="utf-8",
    )
    quota.write_text(
        f"""
defaults:
  period_seconds: 86400
  max_units_per_period: {peer_quota}
roles:
  peer:
    max_units_per_period: {peer_quota}
peers:
  demo-peer:
    max_units_per_period: {peer_quota}
""",
        encoding="utf-8",
    )
    return peers, quota


def _build_control_plane() -> tuple[ControlPlaneService, SessionEventService]:
    session_events = SessionEventService(InMemoryRepository[SessionEventRead]())
    worker_registry = WorkerRegistryService(repository=InMemoryRepository[WorkerRegistrationRead]())
    worker_scheduler = WorkerSchedulerService(
        worker_registry=worker_registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        session_events=session_events,
    )
    service = ControlPlaneService(
        repositories=ControlPlaneRepositories(
            sessions=InMemoryRepository[ControlPlaneSessionRead](),
            tasks=InMemoryRepository[ControlPlaneTaskRead](),
            runs=InMemoryRepository[ControlPlaneRunRead](),
            approvals=InMemoryRepository[ControlPlaneApprovalRead](),
            approval_grants=InMemoryRepository[ControlPlaneApprovalGrantRead](),
            artifacts=InMemoryRepository[ControlPlaneArtifactRead](),
            audit_events=InMemoryRepository[ControlPlaneAuditEventRead](),
            promotions=InMemoryRepository[ControlPlanePromotionRead](),
        ),
        worker_scheduler=worker_scheduler,
        session_events=session_events,
    )
    return service, session_events


def _build_service(root: Path, *, peer_quota: int = 10) -> tuple[FederationService, UsageQuotaService]:
    peers, quota = _write_peer_policy(root, peer_quota=peer_quota)
    control_plane, session_events = _build_control_plane()
    quota_service = UsageQuotaService(
        repository=InMemoryRepository[UsageLedgerEntryRead](),
        policy_path=quota,
        session_events=session_events,
    )
    return (
        FederationService(
            peers_path=peers,
            lease_repository=InMemoryRepository[FederationLeaseRead](),
            task_repository=InMemoryRepository[FederationTaskRead](),
            control_plane=control_plane,
            quota_service=quota_service,
            session_events=session_events,
        ),
        quota_service,
    )


def test_peer_lease_can_submit_local_governed_task_and_commit_quota(tmp_path: Path) -> None:
    service, quota = _build_service(tmp_path)
    lease = service.create_lease(
        FederationLeaseCreateRequest(
            peer_id="demo-peer",
            capability_id="echo",
            max_tasks=2,
            quota_units=3,
        )
    )

    task = service.submit_task(
        FederationTaskCreateRequest(
            peer_id="demo-peer",
            lease_id=lease.lease_id,
            capability_id="echo",
            task_name="leased echo",
            quota_units=1,
        )
    )

    assert task.status == "queued"
    assert task.local_task_id is not None
    assert task.metadata["usage_entry_id"] is not None
    assert [entry.status for entry in quota.list_entries(subject_id="demo-peer")] == ["committed"]
    assert service.list_leases(peer_id="demo-peer")[0].quota_units == 2


def test_revoked_lease_blocks_later_peer_task(tmp_path: Path) -> None:
    service, _quota = _build_service(tmp_path)
    lease = service.create_lease(
        FederationLeaseCreateRequest(
            peer_id="demo-peer",
            capability_id="echo",
            max_tasks=2,
            quota_units=3,
        )
    )
    service.revoke_lease(lease.lease_id)

    with pytest.raises(PermissionError):
        service.submit_task(
            FederationTaskCreateRequest(
                peer_id="demo-peer",
                lease_id=lease.lease_id,
                capability_id="echo",
                task_name="blocked echo",
                quota_units=1,
            )
        )


def test_federation_task_rejects_when_peer_quota_is_exhausted(tmp_path: Path) -> None:
    service, quota = _build_service(tmp_path, peer_quota=1)
    lease = service.create_lease(
        FederationLeaseCreateRequest(
            peer_id="demo-peer",
            capability_id="echo",
            max_tasks=2,
            quota_units=3,
        )
    )

    rejected = service.submit_task(
        FederationTaskCreateRequest(
            peer_id="demo-peer",
            lease_id=lease.lease_id,
            capability_id="echo",
            task_name="over quota",
            quota_units=2,
        )
    )

    assert rejected.status == "rejected"
    assert rejected.error == "quota exceeded"
    assert [entry.status for entry in quota.list_entries(subject_id="demo-peer")] == ["rejected"]
