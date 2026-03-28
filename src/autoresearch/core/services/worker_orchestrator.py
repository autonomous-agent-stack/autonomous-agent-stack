from __future__ import annotations

from pathlib import Path
import re
import shlex
import sys
import time
from typing import Any

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_controlled_backend import AutoResearchControlledBackendService
from autoresearch.core.services.autoresearch_worker import AutoResearchWorkerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openhands_controlled_backend import OpenHandsControlledBackendService
from autoresearch.core.services.openhands_worker import OpenHandsWorkerService
from autoresearch.shared.autoresearch_controlled_contract import AutoResearchExecutionRead
from autoresearch.shared.autoresearch_worker_contract import AutoResearchWorkerJobSpec
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalRisk,
    ApprovalStatus,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    GitPromotionMode,
    JobStatus,
    utc_now,
)
from autoresearch.shared.openhands_controlled_contract import ControlledExecutionRead
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec
from autoresearch.shared.store import create_resource_id
from autoresearch.shared.worker_orchestration_contract import (
    WorkerApprovalResumeRead,
    WorkerExecutionSummary,
    WorkerOrchestrationReplayPayload,
    WorkerRoute,
    WorkerRoutingDecision,
)

_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:src|tests|docs|configs|scripts|panel|dashboard)/[A-Za-z0-9_./-]+)"
)
_ANALYSIS_HINTS = (
    "analyze",
    "analysis",
    "research",
    "investigate",
    "review",
    "plan",
    "risk",
    "方案",
    "分析",
    "研究",
    "调研",
    "审查",
    "风险",
    "总结",
    "设计",
)
_EXECUTION_HINTS = (
    "fix",
    "implement",
    "patch",
    "bug",
    "refactor",
    "update",
    "edit",
    "change",
    "write code",
    "test",
    "修复",
    "修改",
    "实现",
    "补测试",
    "写代码",
    "重构",
    "改一下",
)
_APPROVAL_HINTS = (
    "main",
    "merge",
    "delete",
    "remove",
    "reset",
    "rebase",
    "drop",
    "force",
    "destructive",
    "生产",
    "删除",
    "主分支",
    "合并",
    "上线",
)


class WorkerOrchestratorService:
    """Deterministic worker routing over existing strict workers."""

    def __init__(
        self,
        *,
        agent_service: ClaudeAgentService,
        approval_service: ApprovalStoreService,
        openhands_worker: OpenHandsWorkerService | None = None,
        autoresearch_worker: AutoResearchWorkerService | None = None,
        openhands_backend: OpenHandsControlledBackendService | None = None,
        autoresearch_backend: AutoResearchControlledBackendService | None = None,
    ) -> None:
        self._agent_service = agent_service
        self._approval_service = approval_service
        self._openhands_worker = openhands_worker or OpenHandsWorkerService()
        self._autoresearch_worker = autoresearch_worker or AutoResearchWorkerService()
        self._openhands_backend = openhands_backend or OpenHandsControlledBackendService()
        self._autoresearch_backend = autoresearch_backend or AutoResearchControlledBackendService()

    def decide(
        self,
        *,
        prompt: str,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerRoutingDecision:
        raw_metadata = dict(metadata or {})
        normalized = prompt.strip().lower()
        explicit_paths = self._extract_paths(prompt)
        analysis = any(token in normalized for token in _ANALYSIS_HINTS)
        execution = bool(explicit_paths) or any(token in normalized for token in _EXECUTION_HINTS)
        pipeline_target = self._resolve_pipeline_target(normalized, raw_metadata)
        requires_approval = bool(
            execution
            and (
                pipeline_target is GitPromotionMode.DRAFT_PR
                or any(token in normalized for token in _APPROVAL_HINTS)
            )
        )

        if analysis and execution:
            route = WorkerRoute.AUTORESEARCH_THEN_OPENHANDS
            selected_worker = "autoresearch"
            worker_chain = ["autoresearch", "openhands"]
            reason = "task mixes analysis/planning language with concrete code-change intent"
            allowed_paths = explicit_paths or ["src/worker_patch.py"]
        elif execution:
            route = WorkerRoute.OPENHANDS
            selected_worker = "openhands"
            worker_chain = ["openhands"]
            reason = "task asks for concrete code changes or tests"
            allowed_paths = explicit_paths or ["src/worker_patch.py"]
        elif analysis:
            route = WorkerRoute.AUTORESEARCH
            selected_worker = "autoresearch"
            worker_chain = ["autoresearch"]
            reason = "task asks for analysis, research, planning, or risk framing"
            allowed_paths = explicit_paths or ["docs/worker_notes.md"]
        else:
            route = WorkerRoute.CLAUDE_DIRECT
            selected_worker = "claude_direct"
            worker_chain = ["claude_direct"]
            reason = "message looks conversational and does not require a strict execution worker"
            allowed_paths = []

        approval_risk = ApprovalRisk.DESTRUCTIVE if requires_approval else None
        approval_reason = (
            "high-risk write intent detected; approval is required before entering an execution worker"
            if requires_approval
            else None
        )
        test_command = self._build_test_command(allowed_paths)
        forbidden_paths = [
            ".git/**",
            "logs/**",
            ".masfactory_runtime/**",
            "memory/**",
            "**/*.key",
            "**/*.pem",
        ]
        return WorkerRoutingDecision(
            route=route,
            selected_worker=selected_worker,
            worker_chain=worker_chain,
            selection_reason=reason,
            requires_approval=requires_approval,
            approval_risk=approval_risk,
            approval_reason=approval_reason,
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths,
            test_command=test_command,
            pipeline_target=pipeline_target,
            metadata={
                "explicit_paths": explicit_paths,
            },
        )

    def queue_for_telegram(
        self,
        *,
        request: ClaudeAgentCreateRequest,
    ) -> tuple[WorkerRoutingDecision, ClaudeAgentRunRead | None, ApprovalRequestRead | None]:
        decision = self.decide(prompt=request.prompt, metadata=request.metadata)
        if decision.route == WorkerRoute.CLAUDE_DIRECT:
            return decision, None, None
        if decision.requires_approval:
            approval = self._approval_service.create_request(
                ApprovalRequestCreateRequest(
                    title=f"Approve {decision.selected_worker} run",
                    summary=request.task_name,
                    risk=decision.approval_risk or ApprovalRisk.WRITE,
                    source="worker_orchestration",
                    telegram_uid=str(
                        request.metadata.get("actor_user_id") or request.metadata.get("chat_id") or ""
                    ),
                    session_id=request.session_id,
                    assistant_scope=None,
                    metadata=self._build_approval_metadata(request=request, decision=decision),
                )
            )
            return decision, None, approval

        worker_request = self._build_worker_request(request=request, decision=decision)
        run = self._agent_service.create(worker_request)
        return decision, run, None

    def resume_approved_telegram_run(
        self,
        *,
        approval_id: str,
    ) -> WorkerApprovalResumeRead | None:
        approval = self._approval_service.get_request(approval_id)
        if approval is None:
            raise KeyError(f"approval not found: {approval_id}")
        if approval.source != "worker_orchestration" or approval.status is not ApprovalStatus.APPROVED:
            return None

        orchestration = dict(approval.metadata.get("orchestration") or {})
        if orchestration.get("resume_agent_run_id"):
            return None

        replay_raw = approval.metadata.get("worker_orchestration_replay")
        if not isinstance(replay_raw, dict):
            self._mark_resume_failure(
                approval=approval,
                orchestration=orchestration,
                error="worker orchestration replay payload missing",
            )
            return None

        try:
            replay = WorkerOrchestrationReplayPayload.model_validate(replay_raw)
        except Exception as exc:  # pragma: no cover - defensive
            self._mark_resume_failure(
                approval=approval,
                orchestration=orchestration,
                error=f"invalid worker orchestration replay payload: {exc}",
            )
            return None

        request_metadata = dict(replay.request.metadata)
        request_metadata["orchestration"] = {
            **orchestration,
            "approval_id": approval.approval_id,
            "approval_status": approval.status.value,
            "approval_decided_by": approval.decided_by,
            "approval_resolved_via": approval.metadata.get("resolved_via"),
            "resume_state": "queued",
        }

        worker_request = self._build_worker_request(
            request=replay.request,
            decision=replay.decision,
            metadata=request_metadata,
        )
        try:
            run = self._agent_service.create(worker_request)
        except Exception as exc:  # pragma: no cover - defensive
            self._mark_resume_failure(
                approval=approval,
                orchestration=orchestration,
                error=f"failed to queue resumed worker run: {exc}",
            )
            return None

        self._approval_service.update_request_metadata(
            approval.approval_id,
            {
                "orchestration": {
                    **orchestration,
                    "approval_id": approval.approval_id,
                    "approval_status": approval.status.value,
                    "approval_decided_by": approval.decided_by,
                    "approval_resolved_via": approval.metadata.get("resolved_via"),
                    "resume_state": "queued",
                    "resume_agent_run_id": run.agent_run_id,
                    "resumed_at": utc_now().isoformat(),
                }
            },
            require_status=ApprovalStatus.APPROVED,
        )
        chat_id = str(replay.request.metadata.get("chat_id") or approval.telegram_uid or "").strip() or None
        return WorkerApprovalResumeRead(
            approval_id=approval.approval_id,
            chat_id=chat_id,
            agent_run_id=run.agent_run_id,
            request=worker_request,
            decision=replay.decision,
        )

    def execute_telegram_run(
        self,
        *,
        agent_run_id: str,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        started = time.perf_counter()
        running_orchestration = self._orchestration_metadata(decision=decision, extra=request.metadata)[
            "orchestration"
        ]
        if running_orchestration.get("approval_id") or running_orchestration.get("resume_state"):
            running_orchestration["resume_state"] = "running"
        self._agent_service.mark_running(
            agent_run_id,
            metadata_updates={
                "orchestration": {**running_orchestration, "state": "running"}
            },
        )

        try:
            if decision.route == WorkerRoute.AUTORESEARCH:
                summary = self._run_autoresearch(request=request, decision=decision)
            elif decision.route == WorkerRoute.OPENHANDS:
                summary = self._run_openhands(request=request, decision=decision)
            elif decision.route == WorkerRoute.AUTORESEARCH_THEN_OPENHANDS:
                summary = self._run_chain(request=request, decision=decision)
            else:
                raise ValueError(f"unsupported orchestration route: {decision.route}")
        except Exception as exc:  # pragma: no cover - defensive
            summary = WorkerExecutionSummary(
                route=decision.route,
                selected_worker=decision.selected_worker,
                worker_chain=list(decision.worker_chain),
                status="failed",
                summary_text="worker orchestration failed",
                error_text=str(exc),
                metadata={},
            )

        duration_seconds = time.perf_counter() - started
        final_status = JobStatus.COMPLETED if summary.status == "completed" else JobStatus.FAILED
        metadata_updates = {
            "orchestration": {
                **self._orchestration_metadata(decision=decision, extra=request.metadata)["orchestration"],
                **summary.metadata,
                "state": summary.status,
                "resume_state": "completed" if summary.status == "completed" else "failed",
                "changed_files": summary.changed_files,
                "promotion_mode": summary.promotion_mode,
                "promotion_success": summary.promotion_success,
                "promotion_reason": summary.promotion_reason,
                "artifacts": summary.artifacts,
            }
        }
        self._agent_service.finalize_external_run(
            agent_run_id,
            status=final_status,
            returncode=0 if final_status is JobStatus.COMPLETED else 1,
            stdout_preview=summary.summary_text,
            stderr_preview=summary.error_text,
            duration_seconds=duration_seconds,
            error=summary.error_text if final_status is JobStatus.FAILED else None,
            metadata_updates=metadata_updates,
        )
        self._sync_approval_resume_state(
            agent_run_id=agent_run_id,
            request=request,
            orchestration=metadata_updates["orchestration"],
            summary=summary,
        )
        return summary

    def _run_autoresearch(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        spec = AutoResearchWorkerJobSpec(
            job_id=create_resource_id("orx"),
            research_task=request.prompt,
            allowed_paths=list(decision.allowed_paths),
            forbidden_paths=list(decision.forbidden_paths),
            test_command=decision.test_command,
            pipeline_target=decision.pipeline_target.value,
            metadata={
                "approval_granted": False,
                "orchestration_stage": "analysis_only",
            },
        )
        result = self._autoresearch_backend.run(self._autoresearch_worker.build_controlled_request(spec))
        return self._summarize_autoresearch(result=result, decision=decision)

    def _run_openhands(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        spec = OpenHandsWorkerJobSpec(
            job_id=create_resource_id("orx"),
            problem_statement=request.prompt,
            allowed_paths=list(decision.allowed_paths),
            forbidden_paths=list(decision.forbidden_paths),
            test_command=decision.test_command,
            pipeline_target=decision.pipeline_target.value,
            metadata={
                "approval_granted": True,
                "branch_name": f"codex/{create_resource_id('worker')}",
                "pr_title": request.task_name,
                "pr_body": "Orchestrated via Telegram worker selection.",
            },
        )
        result = self._openhands_backend.run(self._openhands_worker.build_controlled_request(spec))
        return self._summarize_openhands(result=result, decision=decision)

    def _run_chain(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        analysis_spec = AutoResearchWorkerJobSpec(
            job_id=create_resource_id("orx"),
            research_task=request.prompt,
            allowed_paths=["docs/worker_notes.md"],
            forbidden_paths=list(decision.forbidden_paths),
            test_command=self._python_inline_command("print('autoresearch-ok')"),
            pipeline_target="patch",
            metadata={
                "approval_granted": False,
                "orchestration_stage": "analysis_only",
                "skip_promotion_finalize": True,
            },
        )
        analysis_result = self._autoresearch_backend.run(
            self._autoresearch_worker.build_controlled_request(analysis_spec)
        )
        if analysis_result.status.value not in {"ready_for_promotion", "needs_human_review"}:
            return self._summarize_autoresearch(result=analysis_result, decision=decision)

        execution_prompt = self._build_chained_prompt(
            original_prompt=request.prompt,
            analysis_result=analysis_result,
        )
        openhands_spec = OpenHandsWorkerJobSpec(
            job_id=create_resource_id("orx"),
            problem_statement=execution_prompt,
            allowed_paths=list(decision.allowed_paths),
            forbidden_paths=list(decision.forbidden_paths),
            test_command=decision.test_command,
            pipeline_target=decision.pipeline_target.value,
            metadata={
                "approval_granted": True,
                "branch_name": f"codex/{create_resource_id('worker')}",
                "pr_title": request.task_name,
                "pr_body": "Orchestrated via AutoResearch -> OpenHands chain.",
            },
        )
        execution_result = self._openhands_backend.run(
            self._openhands_worker.build_controlled_request(openhands_spec)
        )
        summary = self._summarize_openhands(result=execution_result, decision=decision)
        analysis_deliverables = list(analysis_result.deliverable_artifacts.keys())
        summary.metadata.update(
            {
                "analysis_run_id": analysis_result.run_id,
                "analysis_status": analysis_result.status.value,
                "analysis_deliverables": analysis_deliverables,
                "analysis_promotion_finalize_skipped": bool(
                    analysis_result.metadata.get("skip_promotion_finalize", False)
                ),
                "execution_run_id": execution_result.run_id,
            }
        )
        summary.summary_text = "\n".join(
            [
                f"analysis_status: {analysis_result.status.value}",
                f"analysis_deliverables: {', '.join(analysis_deliverables) if analysis_deliverables else '-'}",
                summary.summary_text,
            ]
        )
        summary.artifacts = list(
            dict.fromkeys([*analysis_result.deliverable_artifacts.values(), *summary.artifacts])
        )
        return summary

    def _summarize_autoresearch(
        self,
        *,
        result: AutoResearchExecutionRead,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        success = result.status.value in {"ready_for_promotion", "needs_human_review"}
        lines = [
            f"worker: autoresearch",
            f"route: {decision.route}",
            f"status: {result.status.value}",
        ]
        if result.deliverable_artifacts:
            lines.append(f"deliverables: {', '.join(sorted(result.deliverable_artifacts.keys()))}")
        promotion_metadata = self._build_promotion_metadata(
            requested_mode=decision.pipeline_target,
            promotion_preflight=result.promotion_preflight,
            promotion=result.promotion,
        )
        if promotion_metadata["promotion_requested_mode"] is not None:
            lines.append(f"promotion_requested: {promotion_metadata['promotion_requested_mode']}")
        if promotion_metadata["promotion_effective_mode"] is not None:
            lines.append(f"promotion_effective: {promotion_metadata['promotion_effective_mode']}")
        if promotion_metadata["promotion_preflight_reason"]:
            lines.append(f"promotion_gate: {promotion_metadata['promotion_preflight_reason']}")
        if result.error:
            lines.append(f"error: {result.error}")
        return WorkerExecutionSummary(
            route=decision.route,
            selected_worker=decision.selected_worker,
            worker_chain=list(decision.worker_chain),
            status="completed" if success else "failed",
            summary_text="\n".join(lines),
            error_text=result.error,
            changed_files=list(result.changed_files),
            artifacts=list(result.deliverable_artifacts.values()),
            promotion_mode=result.promotion.mode.value if result.promotion and result.promotion.mode else None,
            promotion_success=result.promotion.success if result.promotion is not None else None,
            promotion_reason=result.promotion.reason if result.promotion is not None else None,
            metadata={
                "worker_run_id": result.run_id,
                "deliverables": list(result.deliverable_artifacts.keys()),
                "promotion_finalize_skipped": bool(result.metadata.get("skip_promotion_finalize", False)),
                **promotion_metadata,
            },
        )

    def _summarize_openhands(
        self,
        *,
        result: ControlledExecutionRead,
        decision: WorkerRoutingDecision,
    ) -> WorkerExecutionSummary:
        success = result.status.value in {"ready_for_promotion", "needs_human_review"}
        lines = [
            f"worker: openhands",
            f"route: {decision.route}",
            f"status: {result.status.value}",
        ]
        if result.changed_files:
            lines.append(f"changed_files: {', '.join(result.changed_files[:8])}")
        promotion_metadata = self._build_promotion_metadata(
            requested_mode=decision.pipeline_target,
            promotion_preflight=result.promotion_preflight,
            promotion=result.promotion,
        )
        if promotion_metadata["promotion_requested_mode"] is not None:
            lines.append(f"promotion_requested: {promotion_metadata['promotion_requested_mode']}")
        if promotion_metadata["promotion_effective_mode"] is not None:
            lines.append(f"promotion_effective: {promotion_metadata['promotion_effective_mode']}")
        if promotion_metadata["promotion_preflight_reason"]:
            lines.append(f"promotion_gate: {promotion_metadata['promotion_preflight_reason']}")
        if result.error:
            lines.append(f"error: {result.error}")
        return WorkerExecutionSummary(
            route=decision.route,
            selected_worker=decision.selected_worker,
            worker_chain=list(decision.worker_chain),
            status="completed" if success else "failed",
            summary_text="\n".join(lines),
            error_text=result.error,
            changed_files=list(result.changed_files),
            artifacts=[artifact.path for artifact in result.artifacts],
            promotion_mode=result.promotion.mode.value if result.promotion and result.promotion.mode else None,
            promotion_success=result.promotion.success if result.promotion is not None else None,
            promotion_reason=result.promotion.reason if result.promotion is not None else None,
            metadata={
                "worker_run_id": result.run_id,
                **promotion_metadata,
            },
        )

    def _build_chained_prompt(
        self,
        *,
        original_prompt: str,
        analysis_result: AutoResearchExecutionRead,
    ) -> str:
        sections: list[str] = [original_prompt]
        for key in ("execution_plan", "test_plan", "risk_summary"):
            path = analysis_result.deliverable_artifacts.get(key)
            if not path:
                continue
            artifact_path = Path(path)
            if not artifact_path.exists():
                continue
            content = artifact_path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            sections.append(f"{key}:\n{content[:1200]}")
        return "\n\n".join(sections)

    def _extract_paths(self, prompt: str) -> list[str]:
        matches: list[str] = []
        seen: set[str] = set()
        for candidate in _PATH_RE.findall(prompt):
            normalized = candidate.strip().strip("`'\",.:;()[]{}").replace("\\", "/")
            if not normalized or normalized.startswith("../") or normalized.startswith("/"):
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            matches.append(normalized if Path(normalized).suffix else f"{normalized}/**")
        return matches

    def _build_test_command(self, allowed_paths: list[str]) -> str:
        concrete = [item for item in allowed_paths if Path(item).suffix == ".py" and "*" not in item]
        if concrete:
            joined = " ".join(concrete)
            return f"{shlex.quote(sys.executable)} -m py_compile {joined}"
        return self._python_inline_command("print('worker-ok')")

    @staticmethod
    def _python_inline_command(statement: str) -> str:
        return f"{shlex.quote(sys.executable)} -c {shlex.quote(statement)}"

    def _resolve_pipeline_target(
        self,
        normalized_prompt: str,
        metadata: dict[str, Any],
    ) -> GitPromotionMode:
        explicit = str(metadata.get("pipeline_target") or "").strip().lower()
        if explicit == "draft_pr":
            return GitPromotionMode.DRAFT_PR
        if "draft pr" in normalized_prompt or "pull request" in normalized_prompt or "pr" in normalized_prompt:
            return GitPromotionMode.DRAFT_PR
        return GitPromotionMode.PATCH

    def _build_worker_request(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
        metadata: dict[str, Any] | None = None,
    ) -> ClaudeAgentCreateRequest:
        return request.model_copy(
            update={
                "agent_name": decision.selected_worker,
                "command_override": ["orchestrated-worker", decision.selected_worker],
                "append_prompt": False,
                "metadata": self._orchestration_metadata(
                    decision=decision,
                    extra=metadata if metadata is not None else request.metadata,
                ),
            }
        )

    def _build_approval_metadata(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        decision: WorkerRoutingDecision,
    ) -> dict[str, Any]:
        payload = self._orchestration_metadata(decision=decision, extra=request.metadata)
        payload["orchestration"] = {
            **dict(payload.get("orchestration") or {}),
            "state": "awaiting_approval",
            "approval_status": ApprovalStatus.PENDING.value,
            "resume_state": "pending_approval",
        }
        payload["worker_orchestration_replay"] = WorkerOrchestrationReplayPayload(
            request=request,
            decision=decision,
        ).model_dump(mode="json")
        return payload

    def _mark_resume_failure(
        self,
        *,
        approval: ApprovalRequestRead,
        orchestration: dict[str, Any],
        error: str,
    ) -> None:
        try:
            self._approval_service.update_request_metadata(
                approval.approval_id,
                {
                    "orchestration": {
                        **orchestration,
                        "approval_id": approval.approval_id,
                        "approval_status": approval.status.value,
                        "resume_state": "resume_failed",
                        "resume_error": error,
                        "resume_failed_at": utc_now().isoformat(),
                    }
                },
                require_status=ApprovalStatus.APPROVED,
            )
        except (KeyError, ValueError):  # pragma: no cover - defensive
            return

    def _sync_approval_resume_state(
        self,
        *,
        agent_run_id: str,
        request: ClaudeAgentCreateRequest,
        orchestration: dict[str, Any],
        summary: WorkerExecutionSummary,
    ) -> None:
        approval_id = str(orchestration.get("approval_id") or "").strip()
        if not approval_id:
            return
        try:
            self._approval_service.update_request_metadata(
                approval_id,
                {
                    "orchestration": {
                        **dict(orchestration),
                        "resume_agent_run_id": agent_run_id,
                        "resume_state": "completed" if summary.status == "completed" else "failed",
                        "resume_finished_at": utc_now().isoformat(),
                        "resume_error": summary.error_text,
                        "resume_summary": summary.summary_text,
                    }
                },
                require_status=ApprovalStatus.APPROVED,
            )
        except (KeyError, ValueError):  # pragma: no cover - defensive
            return

    def _build_promotion_metadata(
        self,
        *,
        requested_mode: GitPromotionMode,
        promotion_preflight: Any,
        promotion: Any,
    ) -> dict[str, Any]:
        requested = requested_mode.value if requested_mode is not None else None
        effective = None
        reason = None
        failed_checks: list[str] = []
        if promotion_preflight is not None:
            effective = (
                promotion_preflight.effective_mode.value
                if promotion_preflight.effective_mode is not None
                else None
            )
            reason = promotion_preflight.reason
            failed_checks = [check.id for check in promotion_preflight.checks if not check.passed]
        elif promotion is not None:
            effective = promotion.mode.value if promotion.mode is not None else None
            reason = promotion.reason
            failed_checks = [check.id for check in promotion.checks if not check.passed]
        return {
            "promotion_requested_mode": requested,
            "promotion_effective_mode": effective,
            "promotion_preflight_reason": reason,
            "promotion_failed_checks": failed_checks,
        }

    def _orchestration_metadata(
        self,
        *,
        decision: WorkerRoutingDecision,
        extra: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = dict(extra or {})
        existing_orchestration = dict(payload.get("orchestration") or {})
        payload["orchestration"] = {
            **existing_orchestration,
            "route": decision.route,
            "selected_worker": decision.selected_worker,
            "worker_chain": list(decision.worker_chain),
            "selection_reason": decision.selection_reason,
            "requires_approval": decision.requires_approval,
            "approval_reason": decision.approval_reason,
            "allowed_paths": list(decision.allowed_paths),
            "test_command": decision.test_command,
            "pipeline_target": decision.pipeline_target.value,
        }
        return payload
