from __future__ import annotations

import json
from pathlib import Path

from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.housekeeper import HousekeeperDispatchRequest, PersonalHousekeeperService
from autoresearch.shared.housekeeper_contract import HousekeeperTaskStatus
from autoresearch.shared.models import (
    MemoryScope,
    OpenClawMemoryRecordCreateRequest,
    OpenClawSessionActorRead,
    OpenClawSessionCreateRequest,
)
from autoresearch.shared.store import InMemoryRepository


def _seed_agent_package_tree(repo_root: Path) -> None:
    manifests = {
        "software-change": {
            "id": "software_change_agent_v0",
            "name": "Software Change Agent",
            "description": "Software changes through manager agent",
            "version": "0.1.0",
            "execution_backend": "manager_agent",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_capabilities": {"platform": ["linux"], "tools": ["tests"], "min_versions": {}},
            "supported_worker_types": ["linux", "openclaw"],
            "governance": {
                "risk_level": "high",
                "approval_rules": {
                    "requires_approval_for_write": True,
                    "requires_approval_for_delete": True,
                    "approval_threshold": 1,
                },
            },
            "failure_handling": {"fallback_strategy": "manual"},
            "execution": {"timeout_ms": 1000},
        },
        "linux-housekeeping": {
            "id": "linux_housekeeping_agent_v0",
            "name": "Linux Housekeeping Agent",
            "description": "Linux housekeeping through supervisor",
            "version": "0.1.0",
            "execution_backend": "linux_supervisor",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_capabilities": {"platform": ["linux"], "tools": ["shell"], "min_versions": {}},
            "supported_worker_types": ["linux"],
            "governance": {
                "risk_level": "medium",
                "approval_rules": {
                    "requires_approval_for_write": False,
                    "requires_approval_for_delete": False,
                    "approval_threshold": 0,
                },
            },
            "failure_handling": {"fallback_strategy": "manual"},
            "execution": {"timeout_ms": 1000},
        },
    }
    for folder, manifest in manifests.items():
        path = repo_root / "agent-control-plane" / "packages" / "agent-packages" / folder / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_service(repo_root: Path) -> tuple[PersonalHousekeeperService, str]:
    openclaw_service = OpenClawCompatService(repository=InMemoryRepository())
    memory_service = OpenClawMemoryService(repository=InMemoryRepository(), openclaw_service=openclaw_service)
    package_registry = AgentPackageRegistryService(repo_root=repo_root)
    service = PersonalHousekeeperService(
        repository=InMemoryRepository(),
        openclaw_service=openclaw_service,
        openclaw_memory_service=memory_service,
        package_registry=package_registry,
    )
    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(
            channel="api",
            title="frontdesk",
            assistant_id="housekeeper",
            actor=OpenClawSessionActorRead(user_id="u-1", username="owner", role="owner"),
        )
    )
    memory_service.remember_for_session(
        session.session_id,
        OpenClawMemoryRecordCreateRequest(content="常见任务是修页面和补测试"),
    )
    return service, session.session_id


def test_frontdesk_dispatch_requires_approval_for_write_task(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_package_tree(repo_root)
    service, session_id = _build_service(repo_root)

    task = service.dispatch(
        HousekeeperDispatchRequest(
            session_id=session_id,
            message="请修改 landing page 文案并补一组测试。",
        )
    )

    assert task.agent_package_id == "software_change_agent_v0"
    assert task.backend_kind is not None
    assert task.status is HousekeeperTaskStatus.APPROVAL_REQUIRED
    assert task.approval_request is not None
    assert task.metadata["dispatch_authority"] == "control_plane"


def test_frontdesk_dispatch_returns_clarification_when_no_package_matches(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_package_tree(repo_root)
    service, session_id = _build_service(repo_root)

    task = service.dispatch(
        HousekeeperDispatchRequest(
            session_id=session_id,
            message="请帮我安排晚饭菜单并讲个睡前故事。",
            allowed_memory_scopes=[MemoryScope.SESSION],
        )
    )

    assert task.status is HousekeeperTaskStatus.CLARIFICATION_REQUIRED
    assert task.agent_package_id is None
    assert task.backend_kind is None
    assert task.clarification_reason_code == "no_matching_package"
    assert task.approval_request is None


def test_frontdesk_can_summarize_control_plane_result(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_package_tree(repo_root)
    service, session_id = _build_service(repo_root)
    task = service.dispatch(
        HousekeeperDispatchRequest(
            session_id=session_id,
            message="请巡检 Linux 服务状态并收集最近错误日志。",
        )
    )

    updated = service.summarize_result(
        task.task_id,
        control_plane_task_id="cptask_123",
        status=HousekeeperTaskStatus.COMPLETED,
        summary="Linux housekeeping completed successfully.",
        result_payload={"summary": "Linux housekeeping completed successfully.", "artifacts": ["syslog.txt"]},
    )

    assert updated.status is HousekeeperTaskStatus.COMPLETED
    assert updated.result_summary == "Linux housekeeping completed successfully."
    assert updated.result_payload["artifacts"] == ["syslog.txt"]
    assert updated.metadata["control_plane_task_id"] == "cptask_123"
