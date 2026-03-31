from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
import hashlib
import math
from typing import Any
from zoneinfo import ZoneInfo

from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.autoresearch_planner_contract import AutoResearchPlannerRequest
from autoresearch.shared.housekeeper_contract import (
    AdmissionRiskLevel,
    CircuitBreakerStateRead,
    CircuitBreakerStatus,
    DeferredReason,
    ExecutionProfileRead,
    ExplorationBlockerReason,
    ExplorationDedupKeyRead,
    ExplorationRecordRead,
    HousekeeperChangeReason,
    HousekeeperMode,
    HousekeeperModeUpdateRequest,
    HousekeeperMorningSummaryRead,
    HousekeeperStateRead,
    HousekeeperTickRead,
    NightBudgetStateRead,
    TaskAdmissionAssessmentRead,
)
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead, ManagerDispatchRequest, ManagerPlanStrategy
from autoresearch.shared.media_job_contract import MediaJobRead, MediaJobStatus
from autoresearch.shared.models import ApprovalStatus, JobStatus, utc_now
from autoresearch.shared.store import Repository, create_resource_id


@dataclass(frozen=True, slots=True)
class _NightWindow:
    start: datetime
    end: datetime


class ExecutionProfileResolver:
    _PROFILES = {
        HousekeeperMode.DAY_SAFE: ExecutionProfileRead(
            profile_name=HousekeeperMode.DAY_SAFE,
            pipeline_target="patch",
            max_iterations=1,
            auto_dispatch_allowed=False,
            parallelism=1,
            allow_draft_pr=False,
            allow_repo_write=True,
            allow_network=False,
            allow_long_task_minutes=15,
        ),
        HousekeeperMode.NIGHT_READONLY_EXPLORE: ExecutionProfileRead(
            profile_name=HousekeeperMode.NIGHT_READONLY_EXPLORE,
            pipeline_target="patch",
            max_iterations=2,
            auto_dispatch_allowed=True,
            parallelism=2,
            allow_draft_pr=False,
            allow_repo_write=True,
            allow_network=False,
            allow_long_task_minutes=90,
        ),
        HousekeeperMode.NIGHT_EXPLORE: ExecutionProfileRead(
            profile_name=HousekeeperMode.NIGHT_EXPLORE,
            pipeline_target="draft_pr",
            max_iterations=2,
            auto_dispatch_allowed=True,
            parallelism=3,
            allow_draft_pr=True,
            allow_repo_write=True,
            allow_network=False,
            allow_long_task_minutes=120,
        ),
    }

    def resolve(self, mode: HousekeeperMode) -> ExecutionProfileRead:
        return self._PROFILES[mode].model_copy(deep=True)


class HousekeeperService:
    def __init__(
        self,
        *,
        state_repository: Repository[HousekeeperStateRead],
        budget_repository: Repository[NightBudgetStateRead],
        exploration_repository: Repository[ExplorationRecordRead],
        timezone_name: str = "Asia/Shanghai",
        summary_chat_id: str | None = None,
        profile_resolver: ExecutionProfileResolver | None = None,
    ) -> None:
        self._state_repository = state_repository
        self._budget_repository = budget_repository
        self._exploration_repository = exploration_repository
        self._timezone = ZoneInfo(timezone_name)
        self._summary_chat_id = (summary_chat_id or "").strip() or None
        self._profile_resolver = profile_resolver or ExecutionProfileResolver()

    def get_state(self, *, now: datetime | None = None) -> HousekeeperStateRead:
        current = self._state_repository.get("housekeeper")
        resolved_now = self._normalize_now(now)
        if current is None:
            scheduled = self._scheduled_mode_for(resolved_now)
            current = HousekeeperStateRead(
                scheduled_mode=scheduled,
                effective_mode=scheduled,
                reason=HousekeeperChangeReason.SCHEDULE,
                changed_by="system",
                last_changed_at=resolved_now,
            )
            return self._state_repository.save(current.state_id, current)

        updated = self._refresh_state(current=current, now=resolved_now)
        if updated != current:
            return self._state_repository.save(updated.state_id, updated)
        return updated

    def update_mode(self, request: HousekeeperModeUpdateRequest, *, now: datetime | None = None) -> HousekeeperStateRead:
        current = self.get_state(now=now)
        resolved_now = self._normalize_now(now)
        if request.action == "set_manual_override":
            if request.target_mode is None:
                raise ValueError("target_mode is required for set_manual_override")
            updated = current.model_copy(
                update={
                    "manual_override_mode": request.target_mode,
                    "effective_until": request.effective_until or self._next_boundary(resolved_now),
                    "reason": request.reason,
                    "changed_by": request.changed_by.strip(),
                    "last_changed_at": resolved_now,
                    "metadata": {**current.metadata, **request.metadata},
                }
            )
        elif request.action == "clear_manual_override":
            updated = current.model_copy(
                update={
                    "manual_override_mode": None,
                    "effective_until": None,
                    "reason": request.reason,
                    "changed_by": request.changed_by.strip(),
                    "last_changed_at": resolved_now,
                    "metadata": {**current.metadata, **request.metadata},
                }
            )
        elif request.action == "ack_circuit_breaker":
            breaker = current.circuit_breaker_state.model_copy(
                update={
                    "status": CircuitBreakerStatus.CLOSED,
                    "acknowledged_at": resolved_now,
                    "reason": None,
                    "metadata": {**current.circuit_breaker_state.metadata, **request.metadata},
                }
            )
            updated = current.model_copy(
                update={
                    "circuit_breaker_state": breaker,
                    "reason": request.reason,
                    "changed_by": request.changed_by.strip(),
                    "last_changed_at": resolved_now,
                }
            )
        else:
            if request.target_mode is None:
                raise ValueError("target_mode is required for apply_schedule")
            updated = current.model_copy(
                update={
                    "scheduled_mode": request.target_mode,
                    "reason": request.reason,
                    "changed_by": request.changed_by.strip(),
                    "last_changed_at": resolved_now,
                    "metadata": {**current.metadata, **request.metadata},
                }
            )

        refreshed = self._refresh_state(current=updated, now=resolved_now)
        return self._state_repository.save(refreshed.state_id, refreshed)

    def prepare_manager_request(
        self,
        request: ManagerDispatchRequest,
        *,
        manager_service: ManagerAgentService,
        trigger_source: str,
        now: datetime | None = None,
    ) -> tuple[ManagerDispatchRequest, TaskAdmissionAssessmentRead, HousekeeperStateRead]:
        state = self.get_state(now=now)
        profile = self._profile_resolver.resolve(state.effective_mode)
        assessment = manager_service.assess_request(request)
        auto_dispatch = bool(request.auto_dispatch and profile.auto_dispatch_allowed)
        deferred_reason: DeferredReason | None = None

        if state.circuit_breaker_state.status is CircuitBreakerStatus.OPEN:
            auto_dispatch = False
            deferred_reason = DeferredReason.CIRCUIT_BREAKER_OPEN
        elif request.auto_dispatch and not profile.auto_dispatch_allowed:
            auto_dispatch = False
            deferred_reason = DeferredReason.DEFERRED_TO_NIGHT
        elif auto_dispatch and not self._admission_allows(profile=profile, assessment=assessment):
            auto_dispatch = False
            deferred_reason = (
                DeferredReason.APPROVAL_REQUIRED
                if assessment.risk_level is AdmissionRiskLevel.HIGH
                else DeferredReason.DEFERRED_TO_NIGHT
            )

        updated = request.model_copy(
            update={
                "pipeline_target": profile.pipeline_target,
                "max_iterations": profile.max_iterations,
                "auto_dispatch": auto_dispatch,
                "metadata": {
                    **request.metadata,
                    "execution_profile": profile.model_dump(mode="json"),
                    "trigger_source": trigger_source,
                    "scheduled_window": state.effective_mode.value,
                    "admission_assessment": assessment.model_dump(mode="json"),
                    "deferred_reason": deferred_reason.value if deferred_reason is not None else None,
                },
            }
        )
        return updated, assessment, state

    def prepare_planner_request(
        self,
        request: AutoResearchPlannerRequest,
        *,
        trigger_source: str,
        now: datetime | None = None,
    ) -> tuple[AutoResearchPlannerRequest, TaskAdmissionAssessmentRead, HousekeeperStateRead]:
        state = self.get_state(now=now)
        profile = self._profile_resolver.resolve(state.effective_mode)
        assessment = self.assess_planner_request(request)
        deferred_reason: DeferredReason | None = None
        if state.circuit_breaker_state.status is CircuitBreakerStatus.OPEN:
            deferred_reason = DeferredReason.CIRCUIT_BREAKER_OPEN

        updated = request.model_copy(
            update={
                "pipeline_target": profile.pipeline_target,
                "max_iterations": profile.max_iterations,
                "metadata": {
                    **request.metadata,
                    "execution_profile": profile.model_dump(mode="json"),
                    "trigger_source": trigger_source,
                    "scheduled_window": state.effective_mode.value,
                    "admission_assessment": assessment.model_dump(mode="json"),
                    "deferred_reason": deferred_reason.value if deferred_reason is not None else None,
                },
            }
        )
        return updated, assessment, state

    def assess_planner_request(self, request: AutoResearchPlannerRequest) -> TaskAdmissionAssessmentRead:
        estimated_runtime = 12 if request.pipeline_target == "patch" else 20
        if request.max_candidates > 5:
            estimated_runtime += 10
        if request.include_upstream_watch:
            estimated_runtime += 10
        risk = AdmissionRiskLevel.LOW if estimated_runtime <= 15 else AdmissionRiskLevel.MEDIUM
        return TaskAdmissionAssessmentRead(
            plan_shape="planner_candidate",
            estimated_runtime_minutes=estimated_runtime,
            requires_repo_write=True,
            requires_network=False,
            fanout_count=1,
            risk_level=risk,
        )

    def create_morning_summary(
        self,
        *,
        manager_service: ManagerAgentService,
        planner_service: AutoResearchPlannerService,
        approval_service: ApprovalStoreService,
        notifier: TelegramNotifierService,
        media_jobs: list[MediaJobRead] | None = None,
        now: datetime | None = None,
    ) -> HousekeeperMorningSummaryRead:
        state = self.get_state(now=now)
        resolved_now = self._normalize_now(now)
        window = self._previous_night_window(resolved_now)

        completed_items: list[str] = []
        blocked_items: list[str] = []
        decision_items: list[str] = []
        queue_items: list[str] = []

        for dispatch in manager_service.list_dispatches():
            if not self._within_window(dispatch.updated_at, window):
                continue
            line = f"{dispatch.dispatch_id}: {dispatch.summary}"
            if dispatch.status is JobStatus.COMPLETED:
                completed_items.append(line)
            elif dispatch.status is JobStatus.FAILED:
                blocked_items.append(line)

        for plan in planner_service.list():
            if not self._within_window(plan.updated_at, window):
                continue
            line = f"{plan.plan_id}: {plan.summary}"
            if plan.dispatch_status.value == "dispatched" and plan.run_summary is not None:
                completed_items.append(line)
            elif plan.dispatch_status.value == "failed":
                blocked_items.append(line)

        for job in media_jobs or []:
            if not self._within_window(job.updated_at, window):
                continue
            line = f"{job.job_id}: {job.mode.value} -> {job.status.value}"
            if job.status is MediaJobStatus.COMPLETED:
                completed_items.append(line)
            elif job.status is MediaJobStatus.FAILED:
                blocked_items.append(line)

        for approval in approval_service.list_requests(status=ApprovalStatus.PENDING, limit=20):
            decision_items.append(f"{approval.approval_id}: {approval.title}")

        for dispatch in manager_service.list_dispatches():
            if dispatch.status in {JobStatus.CREATED, JobStatus.QUEUED}:
                queue_items.append(f"manager {dispatch.dispatch_id}: {dispatch.summary}")
        for plan in planner_service.list_pending(limit=20):
            queue_items.append(f"plan {plan.plan_id}: {plan.summary}")

        summary_text = "\n".join(
            [
                "昨夜完成了什么",
                *(f"- {item}" for item in (completed_items or ["无"])),
                "",
                "失败/阻塞了什么",
                *(f"- {item}" for item in (blocked_items or ["无"])),
                "",
                "今天需要你决定什么",
                *(f"- {item}" for item in (decision_items or ["无"])),
                "",
                "系统当前模式与待执行队列",
                f"- mode: {state.effective_mode.value}",
                *(f"- {item}" for item in (queue_items or ["无"])),
            ]
        )

        sent = bool(self._summary_chat_id and notifier.enabled and notifier.send_message(chat_id=self._summary_chat_id, text=summary_text))
        updated_state = state.model_copy(update={"last_summary_at": resolved_now})
        self._state_repository.save(updated_state.state_id, updated_state)
        return HousekeeperMorningSummaryRead(
            sent=sent,
            summary_text=summary_text,
            completed_items=completed_items,
            blocked_items=blocked_items,
            decision_items=decision_items,
            queue_items=queue_items,
            state=updated_state,
        )

    def execute_night_explore_tick(
        self,
        *,
        manager_service: ManagerAgentService,
        planner_service: AutoResearchPlannerService,
        notifier: TelegramNotifierService,
        media_jobs: list[MediaJobRead] | None = None,
        now: datetime | None = None,
    ) -> HousekeeperTickRead:
        state = self.get_state(now=now)
        resolved_now = self._normalize_now(now)
        budget = self._get_or_create_budget(resolved_now)

        if state.circuit_breaker_state.status is CircuitBreakerStatus.OPEN:
            return HousekeeperTickRead(
                executed=False,
                skipped_reason="circuit_breaker_open",
                blocker_reason=ExplorationBlockerReason.BUDGET_EXHAUSTED,
                summary="Night explore skipped because the circuit breaker is open.",
                state=state,
                budget=budget,
            )
        if state.effective_mode not in {HousekeeperMode.NIGHT_READONLY_EXPLORE, HousekeeperMode.NIGHT_EXPLORE}:
            return HousekeeperTickRead(
                executed=False,
                skipped_reason="not_in_night_mode",
                summary="Night explore skipped because the effective mode is not a night mode.",
                state=state,
                budget=budget,
            )
        if self._budget_exhausted(budget):
            self._record_budget_blocker(now=resolved_now)
            return HousekeeperTickRead(
                executed=False,
                skipped_reason="budget_exhausted",
                blocker_reason=ExplorationBlockerReason.BUDGET_EXHAUSTED,
                summary="Night explore skipped because the nightly budget is exhausted.",
                state=state,
                budget=budget,
            )

        pending_dispatch = self._pick_pending_manager_dispatch(manager_service=manager_service)
        if pending_dispatch is not None:
            dedup_key = self._build_dispatch_dedup_key(pending_dispatch)
            if self._is_dedup_blocked(dedup_key=dedup_key, blocker_reason=None, now=resolved_now):
                return HousekeeperTickRead(
                    executed=False,
                    skipped_reason="dedup_blocked",
                    target_kind="manager_dispatch",
                    target_id=pending_dispatch.dispatch_id,
                    blocker_reason=ExplorationBlockerReason.UNKNOWN,
                    summary="Night explore skipped a deferred manager dispatch because an equivalent attempt ran recently.",
                    state=state,
                    budget=budget,
                )
            result = manager_service.execute_dispatch(pending_dispatch.dispatch_id)
            blocker = self._blocker_from_dispatch(result)
            budget = self._consume_budget(budget=budget, dispatch=result)
            self._record_exploration_attempt(
                dedup_key=dedup_key,
                target_kind="manager_dispatch",
                target_id=result.dispatch_id,
                blocker_reason=blocker,
                final_status=result.status.value,
                metadata={"summary": result.summary},
                now=resolved_now,
            )
            state = self._update_circuit_breaker_state(notifier=notifier, media_jobs=media_jobs, now=resolved_now)
            return HousekeeperTickRead(
                executed=True,
                target_kind="manager_dispatch",
                target_id=result.dispatch_id,
                blocker_reason=blocker,
                summary=result.summary,
                state=state,
                budget=budget,
            )

        profile = self._profile_resolver.resolve(state.effective_mode)
        planner_request = AutoResearchPlannerRequest(
            goal="Scan the repo for the next safe patch-only improvement.",
            pipeline_target=profile.pipeline_target,
            max_iterations=profile.max_iterations,
            include_upstream_watch=True,
            metadata={"trigger_source": "night_explore_tick"},
        )
        planner_request, _, _ = self.prepare_planner_request(
            planner_request,
            trigger_source="night_explore_tick",
            now=resolved_now,
        )
        plan = planner_service.create(planner_request)
        if plan.selected_candidate is None:
            return HousekeeperTickRead(
                executed=False,
                skipped_reason="no_candidate",
                summary="Night explore did not find a new planner candidate.",
                state=state,
                budget=budget,
            )

        dedup_key = self._build_plan_dedup_key(plan)
        if self._is_dedup_blocked(dedup_key=dedup_key, blocker_reason=None, now=resolved_now):
            return HousekeeperTickRead(
                executed=False,
                skipped_reason="dedup_blocked",
                target_kind="planner_dispatch",
                target_id=plan.plan_id,
                blocker_reason=ExplorationBlockerReason.UNKNOWN,
                summary="Night explore skipped a planner candidate because an equivalent attempt ran recently.",
                state=state,
                budget=budget,
            )

        queued = planner_service.request_dispatch(plan.plan_id, requested_by="housekeeper")
        result = planner_service.execute_dispatch(queued.plan_id)
        blocker = self._blocker_from_plan(result)
        budget = self._consume_budget(budget=budget, plan=result)
        self._record_exploration_attempt(
            dedup_key=dedup_key,
            target_kind="planner_dispatch",
            target_id=result.plan_id,
            blocker_reason=blocker,
            final_status=result.dispatch_status.value,
            metadata={"summary": result.summary},
            now=resolved_now,
        )
        state = self._update_circuit_breaker_state(notifier=notifier, media_jobs=media_jobs, now=resolved_now)
        return HousekeeperTickRead(
            executed=True,
            target_kind="planner_dispatch",
            target_id=result.plan_id,
            blocker_reason=blocker,
            summary=result.summary,
            state=state,
            budget=budget,
        )

    def record_media_job_outcome(
        self,
        *,
        job: MediaJobRead,
        notifier: TelegramNotifierService,
        media_jobs: list[MediaJobRead] | None = None,
        now: datetime | None = None,
    ) -> HousekeeperStateRead:
        resolved_now = self._normalize_now(now)
        blocker = None if job.status is MediaJobStatus.COMPLETED else ExplorationBlockerReason.UNKNOWN
        dedup = ExplorationDedupKeyRead(
            repo_id="media",
            target_scope_hash=self._hash_text(job.target_bucket.value),
            intent_id=job.mode.value,
            normalized_goal_hash=self._hash_text(job.url),
        )
        self._record_exploration_attempt(
            dedup_key=dedup,
            target_kind="media_job",
            target_id=job.job_id,
            blocker_reason=blocker,
            final_status=job.status.value,
            metadata={"url": job.url},
            now=resolved_now,
        )
        return self._update_circuit_breaker_state(notifier=notifier, media_jobs=media_jobs, now=resolved_now)

    def _refresh_state(self, *, current: HousekeeperStateRead, now: datetime) -> HousekeeperStateRead:
        scheduled_mode = self._scheduled_mode_for(now)
        manual_mode = current.manual_override_mode
        effective_until = current.effective_until
        if manual_mode is not None and effective_until is not None and effective_until <= now:
            manual_mode = None
            effective_until = None

        effective_mode = scheduled_mode
        if current.circuit_breaker_state.status is CircuitBreakerStatus.OPEN:
            effective_mode = HousekeeperMode.DAY_SAFE
        elif manual_mode is not None and effective_until is not None and effective_until > now:
            effective_mode = manual_mode

        return current.model_copy(
            update={
                "scheduled_mode": scheduled_mode,
                "manual_override_mode": manual_mode,
                "effective_until": effective_until,
                "effective_mode": effective_mode,
            }
        )

    def _admission_allows(self, *, profile: ExecutionProfileRead, assessment: TaskAdmissionAssessmentRead) -> bool:
        if not profile.auto_dispatch_allowed:
            return False
        if profile.profile_name is not HousekeeperMode.DAY_SAFE:
            return True
        return (
            assessment.estimated_runtime_minutes <= 15
            and assessment.fanout_count <= 1
            and assessment.risk_level in {AdmissionRiskLevel.LOW, AdmissionRiskLevel.MEDIUM}
            and not profile.allow_draft_pr
        )

    def _pick_pending_manager_dispatch(self, *, manager_service: ManagerAgentService) -> ManagerDispatchRead | None:
        candidates: list[ManagerDispatchRead] = []
        for dispatch in manager_service.list_dispatches():
            deferred = str(dispatch.metadata.get("deferred_reason") or "").strip()
            if dispatch.status in {JobStatus.CREATED, JobStatus.QUEUED} and deferred in {"", DeferredReason.DEFERRED_TO_NIGHT.value}:
                candidates.append(dispatch)
        candidates.sort(key=lambda item: item.updated_at)
        return candidates[0] if candidates else None

    def _build_dispatch_dedup_key(self, dispatch: ManagerDispatchRead) -> ExplorationDedupKeyRead:
        scope = "|".join(dispatch.selected_intent.allowed_paths if dispatch.selected_intent is not None else [])
        return ExplorationDedupKeyRead(
            repo_id="repo",
            target_scope_hash=self._hash_text(scope),
            intent_id=dispatch.selected_intent.intent_id if dispatch.selected_intent is not None else "unknown",
            normalized_goal_hash=self._hash_text(dispatch.normalized_goal),
        )

    def _build_plan_dedup_key(self, plan) -> ExplorationDedupKeyRead:
        candidate = plan.selected_candidate
        scope = "|".join(candidate.allowed_paths if candidate is not None else [])
        return ExplorationDedupKeyRead(
            repo_id="repo",
            target_scope_hash=self._hash_text(scope),
            intent_id=(candidate.category if candidate is not None else "planner"),
            normalized_goal_hash=self._hash_text(plan.goal),
        )

    def _is_dedup_blocked(
        self,
        *,
        dedup_key: ExplorationDedupKeyRead,
        blocker_reason: ExplorationBlockerReason | None,
        now: datetime,
    ) -> bool:
        cutoff = now - timedelta(hours=24)
        for record in self._exploration_repository.list():
            if record.created_at < cutoff:
                continue
            if record.dedup_key != dedup_key:
                continue
            if record.blocker_reason == blocker_reason:
                return True
        return False

    def _record_exploration_attempt(
        self,
        *,
        dedup_key: ExplorationDedupKeyRead,
        target_kind: str,
        target_id: str,
        blocker_reason: ExplorationBlockerReason | None,
        final_status: str | None,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        record = ExplorationRecordRead(
            record_id=create_resource_id("explore"),
            dedup_key=dedup_key,
            target_kind=target_kind,
            target_id=target_id,
            blocker_reason=blocker_reason,
            final_status=final_status,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )
        self._exploration_repository.save(record.record_id, record)

    def _update_circuit_breaker_state(
        self,
        *,
        notifier: TelegramNotifierService,
        media_jobs: list[MediaJobRead] | None,
        now: datetime,
    ) -> HousekeeperStateRead:
        state = self.get_state(now=now)
        recent_records = [
            record
            for record in self._exploration_repository.list()
            if record.updated_at >= now - timedelta(hours=2)
        ]
        recent_records.sort(key=lambda item: item.updated_at, reverse=True)
        failures = 0
        consecutive_failures = 0
        for index, record in enumerate(recent_records):
            failed = record.blocker_reason is not None or str(record.final_status or "").lower() in {"failed", "human_review"}
            if failed:
                failures += 1
            if index == consecutive_failures and failed:
                consecutive_failures += 1
            elif index == consecutive_failures:
                break
        media_failures = 0
        for job in sorted(media_jobs or [], key=lambda item: item.updated_at, reverse=True):
            if job.updated_at < now - timedelta(hours=2):
                continue
            if job.status is MediaJobStatus.FAILED:
                media_failures += 1
            else:
                break

        total = len(recent_records)
        failure_rate = failures / total if total else 0.0
        should_open = consecutive_failures >= 3 or (total >= 3 and failure_rate >= 0.7) or media_failures >= 3
        if not should_open:
            return state
        if state.circuit_breaker_state.status is CircuitBreakerStatus.OPEN:
            return state

        breaker = CircuitBreakerStateRead(
            status=CircuitBreakerStatus.OPEN,
            triggered_at=now,
            reason="automatic failure threshold exceeded",
            consecutive_failures=consecutive_failures,
            recent_failure_rate=failure_rate,
            metadata={"media_consecutive_failures": media_failures},
        )
        updated = state.model_copy(
            update={
                "circuit_breaker_state": breaker,
                "effective_mode": HousekeeperMode.DAY_SAFE,
                "reason": HousekeeperChangeReason.CIRCUIT_BREAKER,
                "changed_by": "system",
                "last_changed_at": now,
            }
        )
        self._state_repository.save(updated.state_id, updated)
        if self._summary_chat_id and notifier.enabled:
            notifier.send_message(
                chat_id=self._summary_chat_id,
                text=(
                    "[housekeeper] circuit breaker opened\n"
                    f"- consecutive_failures: {consecutive_failures}\n"
                    f"- failure_rate_2h: {failure_rate:.2f}\n"
                    f"- media_consecutive_failures: {media_failures}"
                ),
            )
        return updated

    def _get_or_create_budget(self, now: datetime) -> NightBudgetStateRead:
        current = self._budget_repository.get("night_budget")
        window = self._current_night_window(now)
        if current is not None and current.window_start == window.start and current.window_end == window.end:
            return current
        budget = NightBudgetStateRead(
            window_start=window.start,
            window_end=window.end,
            updated_at=now,
        )
        return self._budget_repository.save(budget.budget_id, budget)

    def _consume_budget(self, *, budget: NightBudgetStateRead, dispatch=None, plan=None) -> NightBudgetStateRead:
        duration_ms = 0
        draft_prs = budget.draft_prs_used
        if dispatch is not None and dispatch.run_summary is not None:
            duration_ms = dispatch.run_summary.driver_result.metrics.duration_ms or 0
            if dispatch.run_summary.promotion is not None and dispatch.run_summary.promotion.pr_url:
                draft_prs += 1
        if plan is not None and plan.run_summary is not None:
            duration_ms = plan.run_summary.driver_result.metrics.duration_ms or 0
            if plan.run_summary.promotion is not None and plan.run_summary.promotion.pr_url:
                draft_prs += 1
        updated = budget.model_copy(
            update={
                "dispatches_used": budget.dispatches_used + 1,
                "draft_prs_used": draft_prs,
                "worker_minutes_used": budget.worker_minutes_used + math.ceil(duration_ms / 60000) if duration_ms else budget.worker_minutes_used,
                "updated_at": utc_now(),
            }
        )
        return self._budget_repository.save(updated.budget_id, updated)

    def _budget_exhausted(self, budget: NightBudgetStateRead) -> bool:
        return (
            budget.dispatches_used >= budget.max_dispatches_per_night
            or budget.draft_prs_used >= budget.max_draft_pr_per_night
            or budget.worker_minutes_used >= budget.max_worker_minutes_per_night
        )

    def _record_budget_blocker(self, *, now: datetime) -> None:
        dedup_key = ExplorationDedupKeyRead(
            repo_id="repo",
            target_scope_hash=self._hash_text("night_budget"),
            intent_id="night_budget",
            normalized_goal_hash=self._hash_text("night_budget"),
        )
        self._record_exploration_attempt(
            dedup_key=dedup_key,
            target_kind="planner_dispatch",
            target_id="night_budget",
            blocker_reason=ExplorationBlockerReason.BUDGET_EXHAUSTED,
            final_status="skipped",
            metadata={},
            now=now,
        )

    def _blocker_from_dispatch(self, dispatch: ManagerDispatchRead) -> ExplorationBlockerReason | None:
        if dispatch.run_summary is None:
            return ExplorationBlockerReason.UNKNOWN
        return self._blocker_from_run_summary(
            final_status=dispatch.run_summary.final_status,
            error=dispatch.run_summary.driver_result.error,
        )

    def _blocker_from_plan(self, plan) -> ExplorationBlockerReason | None:
        if plan.run_summary is None:
            if plan.dispatch_status.value == "failed":
                return ExplorationBlockerReason.UNKNOWN
            return None
        return self._blocker_from_run_summary(
            final_status=plan.run_summary.final_status,
            error=plan.run_summary.driver_result.error,
        )

    def _blocker_from_run_summary(self, *, final_status: str, error: str | None) -> ExplorationBlockerReason | None:
        message = str(error or "").lower()
        if not message and final_status in {"ready_for_promotion", "promoted"}:
            return None
        if "permission" in message:
            return ExplorationBlockerReason.PERMISSION_DENIED
        if "environmentcheckfailed" in message or "missing" in message:
            return ExplorationBlockerReason.ENV_MISSING
        if "dirty" in message:
            return ExplorationBlockerReason.DIRTY_REPO
        if final_status == "human_review":
            return ExplorationBlockerReason.APPROVAL_PENDING
        if "stalled" in message or "stalled_no_progress" in message:
            return ExplorationBlockerReason.STALLED_NO_PROGRESS
        if "validation" in message:
            return ExplorationBlockerReason.VALIDATION_FAILED
        return ExplorationBlockerReason.UNKNOWN

    def _scheduled_mode_for(self, now: datetime) -> HousekeeperMode:
        local_now = now.astimezone(self._timezone)
        local_time = local_now.timetz().replace(tzinfo=None)
        if time(9, 0) <= local_time < time(23, 0):
            return HousekeeperMode.DAY_SAFE
        return HousekeeperMode.NIGHT_READONLY_EXPLORE

    def _next_boundary(self, now: datetime) -> datetime:
        local_now = now.astimezone(self._timezone)
        day_boundary = datetime.combine(local_now.date(), time(9, 0), tzinfo=self._timezone)
        night_boundary = datetime.combine(local_now.date(), time(23, 0), tzinfo=self._timezone)
        if local_now < day_boundary:
            return day_boundary.astimezone(now.tzinfo)
        if local_now < night_boundary:
            return night_boundary.astimezone(now.tzinfo)
        next_day = local_now.date() + timedelta(days=1)
        return datetime.combine(next_day, time(9, 0), tzinfo=self._timezone).astimezone(now.tzinfo)

    def _current_night_window(self, now: datetime) -> _NightWindow:
        local_now = now.astimezone(self._timezone)
        today_23 = datetime.combine(local_now.date(), time(23, 0), tzinfo=self._timezone)
        today_9 = datetime.combine(local_now.date(), time(9, 0), tzinfo=self._timezone)
        if local_now < today_9:
            start = today_23 - timedelta(days=1)
            end = today_9
        elif local_now >= today_23:
            start = today_23
            end = today_9 + timedelta(days=1)
        else:
            start = today_23
            end = today_9 + timedelta(days=1)
        return _NightWindow(start=start.astimezone(now.tzinfo), end=end.astimezone(now.tzinfo))

    def _previous_night_window(self, now: datetime) -> _NightWindow:
        local_now = now.astimezone(self._timezone)
        today_9 = datetime.combine(local_now.date(), time(9, 0), tzinfo=self._timezone)
        end = today_9 if local_now >= today_9 else today_9 - timedelta(days=1)
        start = end - timedelta(hours=10)
        return _NightWindow(start=start.astimezone(now.tzinfo), end=end.astimezone(now.tzinfo))

    @staticmethod
    def _within_window(value: datetime, window: _NightWindow) -> bool:
        return window.start <= value <= window.end

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_now(now: datetime | None) -> datetime:
        return now or utc_now()
