from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.control_plane_service import (
    ControlPlaneClarificationRequired,
    ControlPlaneService,
)
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperApprovalRequest,
    HousekeeperDispatchRequest,
    HousekeeperTaskDraftRead,
    HousekeeperTaskRead,
    HousekeeperTaskStatus,
)
from autoresearch.shared.models import (
    OpenClawMemoryBundleRead,
    OpenClawSessionEventAppendRequest,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


@dataclass(frozen=True, slots=True)
class _RoutingDecision:
    candidate_package_ids: list[str]
    normalized_intent: str
    routing_reason: str
    error: str | None = None
    clarification_reason_code: str | None = None
    clarification_questions: list[str] | None = None


class PersonalHousekeeperService:
    """Translate OpenClaw session messages into bounded control-plane tasks."""

    _MEMORY_BOUNDARY = {
        "allowed_scopes": ["session", "personal", "shared"],
        "shared_policy": "explicit_only",
        "backend_selection_cannot_expand_scope": True,
    }

    def __init__(
        self,
        repository: Repository[HousekeeperTaskRead],
        *,
        openclaw_service: OpenClawCompatService,
        openclaw_memory_service: OpenClawMemoryService,
        package_registry: AgentPackageRegistryService,
        control_plane_service: ControlPlaneService,
    ) -> None:
        self._repository = repository
        self._openclaw_service = openclaw_service
        self._openclaw_memory_service = openclaw_memory_service
        self._package_registry = package_registry
        self._control_plane_service = control_plane_service

    def list_tasks(self, *, session_id: str | None = None, limit: int = 100) -> list[HousekeeperTaskRead]:
        normalized_session_id = (session_id or "").strip() or None
        tasks = self._repository.list()
        if normalized_session_id is not None:
            tasks = [task for task in tasks if task.session_id == normalized_session_id]
        tasks.sort(key=lambda item: item.updated_at, reverse=True)
        return tasks[: max(1, limit)]

    def get_task(self, task_id: str) -> HousekeeperTaskRead | None:
        return self._repository.get(task_id)

    def dispatch(self, request: HousekeeperDispatchRequest) -> HousekeeperTaskRead:
        session = self._openclaw_service.get_session(request.session_id)
        if session is None:
            raise KeyError(f"OpenClaw session not found: {request.session_id}")

        self._openclaw_service.append_event(
            session.session_id,
            request=OpenClawSessionEventAppendRequest(
                role="user",
                content=request.message,
                metadata={"source": "housekeeper.dispatch"},
            ),
        )
        memory_bundle = self._openclaw_memory_service.bundle_for_session(session.session_id)
        routing_bundle = self._bounded_memory_bundle(memory_bundle)
        decision = self._select_package(request.message, routing_bundle)
        now = utc_now()
        draft = HousekeeperTaskDraftRead(
            draft_id=create_resource_id("hkdraft"),
            session_id=session.session_id,
            source_message=request.message,
            normalized_intent=decision.normalized_intent,
            candidate_package_ids=decision.candidate_package_ids,
            candidate_backend_kinds=[
                item.execution_backend
                for item in self._candidate_packages(decision.candidate_package_ids)
            ],
            routing_reason=decision.routing_reason,
            clarification_reason_code=decision.clarification_reason_code,
            clarification_questions=list(decision.clarification_questions or []),
            memory_scope={
                **self._MEMORY_BOUNDARY,
                "session_event_count": len(routing_bundle.session_events),
                "personal_memory_count": len(routing_bundle.personal_memories),
                "shared_memory_count": len(routing_bundle.shared_memories),
            },
            created_at=now,
        )
        task = HousekeeperTaskRead(
            task_id=create_resource_id("hktask"),
            session_id=session.session_id,
            draft_id=draft.draft_id,
            control_plane_task_id=None,
            source_message=request.message,
            normalized_intent=decision.normalized_intent,
            routing_reason=decision.routing_reason,
            status=HousekeeperTaskStatus.CREATED,
            clarification_reason_code=decision.clarification_reason_code,
            clarification_questions=list(decision.clarification_questions or []),
            approval_status=None,
            approval_id=None,
            agent_package_id=decision.candidate_package_ids[0] if decision.candidate_package_ids else None,
            selected_worker_id=None,
            backend_kind=None,
            backend_ref=None,
            result_summary=None,
            result_payload={},
            memory_snapshot=self._memory_snapshot(routing_bundle),
            metadata={"dry_run": request.dry_run},
            created_at=now,
            updated_at=now,
            error=decision.error,
        )

        if not decision.candidate_package_ids:
            failed = task.model_copy(
                update={
                    "status": HousekeeperTaskStatus.CLARIFICATION_REQUIRED,
                    "result_summary": "Housekeeper needs clarification before a control-plane task can be created.",
                }
            )
            saved = self._repository.save(failed.task_id, failed)
            self._append_status_event(saved)
            return saved
        saved = self._repository.save(task.task_id, task)
        try:
            control_task = self._control_plane_service.submit_housekeeper_draft(
                draft,
                housekeeper_task_id=saved.task_id,
                dry_run=request.dry_run,
            )
        except ControlPlaneClarificationRequired as exc:
            failed = saved.model_copy(
                update={
                    "status": HousekeeperTaskStatus.CLARIFICATION_REQUIRED,
                    "clarification_reason_code": exc.reason_code,
                    "clarification_questions": list(exc.questions),
                    "error": str(exc),
                    "result_summary": str(exc),
                    "updated_at": utc_now(),
                }
            )
            failed = self._repository.save(failed.task_id, failed)
            self._append_status_event(failed)
            return failed
        except ValueError as exc:
            failed = saved.model_copy(
                update={
                    "status": HousekeeperTaskStatus.FAILED,
                    "error": str(exc),
                    "result_summary": "Housekeeper draft failed during control-plane submission.",
                    "updated_at": utc_now(),
                }
            )
            failed = self._repository.save(failed.task_id, failed)
            self._append_status_event(failed)
            return failed
        mirrored = self._mirror_control_plane_task(saved, control_task)
        mirrored = self._repository.save(mirrored.task_id, mirrored)
        self._append_status_event(mirrored)
        return mirrored

    def approve_task(self, task_id: str, request: HousekeeperApprovalRequest) -> HousekeeperTaskRead:
        task = self._require_task(task_id)
        if task.control_plane_task_id is None:
            raise ValueError("housekeeper task does not reference a control-plane task")
        control_task = self._control_plane_service.approve_task(task.control_plane_task_id, request)
        mirrored = self._mirror_control_plane_task(task, control_task)
        mirrored = self._repository.save(mirrored.task_id, mirrored)
        self._append_status_event(mirrored)
        return mirrored

    def reject_task(self, task_id: str, request: HousekeeperApprovalRequest) -> HousekeeperTaskRead:
        task = self._require_task(task_id)
        if task.control_plane_task_id is None:
            raise ValueError("housekeeper task does not reference a control-plane task")
        control_task = self._control_plane_service.reject_task(task.control_plane_task_id, request)
        mirrored = self._mirror_control_plane_task(task, control_task)
        mirrored = self._repository.save(mirrored.task_id, mirrored)
        self._append_status_event(mirrored)
        return mirrored

    def _select_package(
        self,
        message: str,
        memory_bundle: OpenClawMemoryBundleRead,
    ) -> _RoutingDecision:
        normalized = message.strip().lower()
        packages = {item.package_id: item for item in self._package_registry.list_packages()}
        memory_hints = " ".join(
            record.content.lower()
            for record in [*memory_bundle.personal_memories, *memory_bundle.shared_memories]
        )

        linux_markers = (
            "linux",
            "shell",
            "bash",
            "script",
            "脚本",
            "巡检",
            "日志",
            "log",
            "systemctl",
            "journalctl",
            "cpu",
            "memory",
            "磁盘",
            "process",
            "进程",
            "服务状态",
        )
        software_markers = (
            "fix",
            "bug",
            "页面",
            "page",
            "ui",
            "frontend",
            "backend",
            "api",
            "测试",
            "test",
            "feature",
            "功能",
            "landing",
            "落地页",
            "code",
            "代码",
            "refactor",
        )
        yingdao_markers = ("影刀", "yingdao", "erp", "录入", "表单")

        if any(marker in normalized for marker in linux_markers) or any(marker in memory_hints for marker in linux_markers):
            package = packages.get("linux_housekeeping_agent_v0")
            if package is not None:
                return _RoutingDecision(
                    candidate_package_ids=[package.package_id],
                    normalized_intent="linux_housekeeping",
                    routing_reason="Matched Linux ops/shell markers.",
                )
        if any(marker in message for marker in yingdao_markers) or any(marker in normalized for marker in yingdao_markers):
            package = packages.get("yingdao_form_fill_agent_v0")
            if package is not None:
                return _RoutingDecision(
                    candidate_package_ids=[package.package_id],
                    normalized_intent="yingdao_structured_task",
                    routing_reason="Matched Yingdao/ERP markers.",
                )
        if any(marker in normalized for marker in software_markers) or any(marker in memory_hints for marker in software_markers):
            package = packages.get("software_change_agent_v0")
            if package is not None:
                return _RoutingDecision(
                    candidate_package_ids=[package.package_id],
                    normalized_intent="software_change",
                    routing_reason="Matched software/product build markers.",
                )
        return _RoutingDecision(
            candidate_package_ids=[],
            normalized_intent="unsupported",
            routing_reason="No stable package matched the request.",
            error="unsupported request; needs clarification or a new agent package",
            clarification_reason_code="no_matching_package",
            clarification_questions=[
                "这是代码改动、Linux 运维巡检，还是影刀/ERP 录入类任务？",
                "如果是代码任务，请说明目标页面/模块和期望改动边界。",
            ],
        )

    def _memory_snapshot(self, memory_bundle: OpenClawMemoryBundleRead) -> dict[str, Any]:
        return {
            **self._MEMORY_BOUNDARY,
            "session_event_count": len(memory_bundle.session_events),
            "personal_memory_count": len(memory_bundle.personal_memories),
            "shared_memory_count": len(memory_bundle.shared_memories),
            "personal_memory_preview": [item.content for item in memory_bundle.personal_memories[:2]],
            "shared_memory_preview": [item.content for item in memory_bundle.shared_memories[:2]],
        }

    def _append_status_event(self, task: HousekeeperTaskRead) -> None:
        content = task.result_summary or task.error or f"task {task.status.value}"
        self._openclaw_service.append_event(
            task.session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=content,
                metadata={
                    "source": "housekeeper",
                    "housekeeper_task_id": task.task_id,
                    "status": task.status.value,
                    "agent_package_id": task.agent_package_id,
                    "backend_kind": task.backend_kind.value if task.backend_kind is not None else None,
                },
            ),
        )

    def _require_task(self, task_id: str) -> HousekeeperTaskRead:
        task = self._repository.get(task_id)
        if task is None:
            raise KeyError(f"housekeeper task not found: {task_id}")
        return task

    def _candidate_packages(self, package_ids: list[str]):
        candidates = []
        for package_id in package_ids:
            package = self._package_registry.get_package(package_id)
            if package is not None:
                candidates.append(package)
        return candidates

    def _bounded_memory_bundle(self, memory_bundle: OpenClawMemoryBundleRead) -> OpenClawMemoryBundleRead:
        allowed_shared = [
            record
            for record in memory_bundle.shared_memories
            if bool(record.metadata.get("housekeeper_shared")) or "housekeeper_shared" in set(record.tags)
        ]
        return memory_bundle.model_copy(update={"shared_memories": allowed_shared})

    def _mirror_control_plane_task(
        self,
        front_task: HousekeeperTaskRead,
        control_task,
    ) -> HousekeeperTaskRead:
        return front_task.model_copy(
            update={
                "control_plane_task_id": control_task.task_id,
                "agent_package_id": control_task.agent_package_id,
                "selected_worker_id": control_task.selected_worker_id,
                "backend_kind": control_task.backend_kind,
                "backend_ref": control_task.backend_ref,
                "status": control_task.status,
                "approval_status": control_task.approval_status,
                "approval_id": control_task.approval_id,
                "result_summary": control_task.summary,
                "result_payload": control_task.result_payload,
                "updated_at": utc_now(),
                "error": control_task.error,
            }
        )
