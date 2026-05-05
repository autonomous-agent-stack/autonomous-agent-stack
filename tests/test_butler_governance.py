from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_security_audit_service
from autoresearch.api.main import app
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalDecisionRequest,
    ControlPlaneApprovalRead,
    ControlPlaneApprovalStatus,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneSessionRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
from autoresearch.core.services.butler_tool_broker import ButlerToolBroker, ButlerToolResolveRequest
from autoresearch.core.services.security_audit import SecurityAuditQuickScanRequest, SecurityAuditService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    ApprovalStatus,
    JobStatus,
    SessionEventRead,
    WorkerLeaseRead,
    WorkerQueueName,
    WorkerQueueItemRead,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import InMemoryRepository
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.executor import MacWorkerExecutor


ROOT = Path(__file__).resolve().parents[1]


def _build_control_plane() -> tuple[ControlPlaneService, WorkerSchedulerService]:
    session_events = SessionEventService(InMemoryRepository[SessionEventRead]())
    worker_registry = WorkerRegistryService(repository=InMemoryRepository())
    worker_scheduler = WorkerSchedulerService(
        worker_registry=worker_registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        session_events=session_events,
    )
    return (
        ControlPlaneService(
            repositories=ControlPlaneRepositories(
                sessions=InMemoryRepository[ControlPlaneSessionRead](),
                tasks=InMemoryRepository[ControlPlaneTaskRead](),
                runs=InMemoryRepository[ControlPlaneRunRead](),
                approvals=InMemoryRepository[ControlPlaneApprovalRead](),
                artifacts=InMemoryRepository[ControlPlaneArtifactRead](),
                audit_events=InMemoryRepository[ControlPlaneAuditEventRead](),
                promotions=InMemoryRepository[ControlPlanePromotionRead](),
            ),
            worker_scheduler=worker_scheduler,
            session_events=session_events,
            tool_broker=ButlerToolBroker(repo_root=ROOT),
        ),
        worker_scheduler,
    )


def test_butler_tool_broker_grants_amap_weather_to_any_agent() -> None:
    broker = ButlerToolBroker(repo_root=ROOT)

    resolved = broker.resolve(
        ButlerToolResolveRequest(
            actor_role="member",
            target_agent="youtube_ops",
            tool_requirements=["location.weather.read"],
            parameters={"city": "Shanghai"},
        )
    )

    assert resolved.status == "granted"
    assert [grant.tool_id for grant in resolved.grants] == ["amap.weather"]
    assert resolved.grants[0].tier == "common_read"
    assert "pii_location" not in resolved.risk_tags


def test_butler_tool_broker_redacts_private_location_in_audit() -> None:
    broker = ButlerToolBroker(repo_root=ROOT)

    resolved = broker.resolve(
        ButlerToolResolveRequest(
            actor_role="operator",
            target_agent="content_kb",
            tool_requirements=[
                {
                    "capability": "location.geocode.read",
                    "input_text": "北京市朝阳区建国路88号2单元1201室",
                }
            ],
        )
    )

    assert resolved.status == "granted"
    assert "pii_location" in resolved.risk_tags
    assert resolved.grants[0].audit_summary == "北京市朝阳区建国路##号#单元####室"
    assert "88" not in resolved.grants[0].audit_summary
    assert "1201" not in resolved.grants[0].audit_summary


def test_github_write_tool_grant_requires_control_plane_approval() -> None:
    service, _ = _build_control_plane()

    task = service.create_task(
        ControlPlaneTaskCreateRequest(
            name="push docs update",
            capability_id="echo",
            requested_by="owner-user",
            metadata={"actor_role": "owner"},
            parameters={
                "target_agent": "github_ops_accountA",
                "tool_requirements": ["github.repo.push"],
            },
        )
    )

    assert task.status == ControlPlaneTaskStatus.AWAITING_APPROVAL
    assert task.approval_id
    assert "external_api" in task.risk_tags
    assert "external_write" in task.risk_tags
    assert task.metadata["tool_grants"][0]["tool_id"] == "github.push"
    assert task.metadata["tool_grants"][0]["metadata"]["requires_approval"] is True


def test_youtube_task_receives_scoped_common_grant_before_specialized_worker_dispatch() -> None:
    service, worker_scheduler = _build_control_plane()

    task = service.create_task(
        ControlPlaneTaskCreateRequest(
            name="organize watch later",
            capability_id="youtube_autoflow",
            requested_by="operator-user",
            parameters={
                "source_url": "https://www.youtube.com/watch?v=video-001",
                "target_agent": "youtube_ops",
                "tool_requirements": ["location.weather.read"],
            },
        )
    )
    assert task.status == ControlPlaneTaskStatus.AWAITING_APPROVAL
    assert task.metadata["tool_grants"][0]["tool_id"] == "amap.weather"

    approved = service.decide_task(
        task.task_id,
        ControlPlaneApprovalDecisionRequest(decision="approved", decided_by="owner-user"),
    )

    assert approved.status == ControlPlaneTaskStatus.QUEUED
    assert approved.run_id is not None
    worker_run = worker_scheduler.get_run(approved.run_id)
    assert worker_run is not None
    assert worker_run.task_type == WorkerTaskType.YOUTUBE_AUTOFLOW
    assert worker_run.payload["metadata"]["target_agent"] == "youtube_ops"
    assert worker_run.payload["metadata"]["tool_grants"][0]["tool_id"] == "amap.weather"


def test_security_audit_quick_scan_blocks_dangerous_diff() -> None:
    service = SecurityAuditService(repo_root=ROOT)

    scan = service.quick_scan(
        SecurityAuditQuickScanRequest(diff="+import os\n+os.system('rm -rf /')\n")
    )

    assert scan.status == "fail"
    assert "security_high" in scan.risk_tags
    assert any(finding.severity in {"high", "critical"} for finding in scan.findings)


def test_mac_worker_executor_runs_security_audit_quick_scan() -> None:
    executor = MacWorkerExecutor(
        MacWorkerConfig(
            worker_id="security-worker",
            control_plane_base_url="http://127.0.0.1:8001",
            worker_name="Security Worker",
            host="localhost",
            housekeeping_root=ROOT,
            dry_run=True,
        )
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run-security-audit",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="security quick scan",
        task_type=WorkerTaskType.SECURITY_AUDIT,
        payload={"diff": "+import os\n+os.system('rm -rf /')\n"},
        status=JobStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )

    result = executor.execute(run)

    assert result.status == JobStatus.FAILED
    assert result.metrics["security_audit_status"] == "fail"
    assert "security_high" in result.result["risk_tags"]


def test_security_audit_rule_candidate_promotion_requires_audit() -> None:
    service = SecurityAuditService(repo_root=ROOT)

    scan = service.quick_scan(
        SecurityAuditQuickScanRequest(
            rule_candidate={
                "id": "promote-github-write",
                "writes": ["configs/butler/rules.yaml"],
                "tool_requirements": ["github.repo.push"],
            }
        )
    )

    assert scan.status == "fail"
    assert {"external_api", "external_write", "rule_promotion"}.issubset(set(scan.risk_tags))
    assert any(finding.category == "rule_candidate" for finding in scan.findings)


def test_security_audit_daily_report_aggregates_governance_state(tmp_path: Path) -> None:
    control_plane = SimpleNamespace(
        list_tasks=lambda: [
            SimpleNamespace(capability_id="hermes_openclaw", risk_tags=[], metadata={})
            for _ in range(5)
        ]
        + [
            SimpleNamespace(
                capability_id="github_assistant",
                risk_tags=["external_api"],
                metadata={},
            )
        ],
        list_approvals=lambda: [
            SimpleNamespace(status=ControlPlaneApprovalStatus.PENDING),
        ],
    )
    worker_scheduler = SimpleNamespace(
        list_queue=lambda: [
            SimpleNamespace(status=JobStatus.FAILED),
            SimpleNamespace(status=JobStatus.COMPLETED),
        ]
    )
    approval_store = SimpleNamespace(
        list_requests=lambda status=ApprovalStatus.PENDING, limit=200: [
            SimpleNamespace(status=status, limit=limit)
        ]
    )
    service = SecurityAuditService(
        repo_root=ROOT,
        artifact_root=tmp_path / "security-audit",
        control_plane=control_plane,
        worker_scheduler=worker_scheduler,
        approval_store=approval_store,
    )

    report = service.generate_daily_report()

    assert report.status == "warn"
    assert report.counts["failed_worker_runs"] == 1
    assert report.counts["hermes_fallback_tasks"] == 5
    assert report.counts["external_risk_tasks"] == 1
    assert report.artifact_path is not None
    assert Path(report.artifact_path).exists()


def test_butler_governance_api_smoke(tmp_path: Path) -> None:
    app.dependency_overrides[get_security_audit_service] = lambda: SecurityAuditService(
        repo_root=ROOT,
        artifact_root=tmp_path / "api-security-audit",
    )
    try:
        with TestClient(app) as client:
            registry = client.get("/api/v2/butler/registry")
            assert registry.status_code == 200
            assert any(tool["tool_id"] == "amap.weather" for tool in registry.json()["tools"])
            assert "mcp_tools" in registry.json()

            resolved = client.post(
                "/api/v2/butler/tools/resolve",
                json={
                    "actor_role": "member",
                    "target_agent": "x_ops",
                    "tool_requirements": ["location.weather.read"],
                },
            )
            assert resolved.status_code == 200
            assert resolved.json()["status"] == "granted"

            daily = client.get("/api/v2/security-audit/daily")
            assert daily.status_code == 200
            assert daily.json()["artifact_path"]
    finally:
        app.dependency_overrides.pop(get_security_audit_service, None)
