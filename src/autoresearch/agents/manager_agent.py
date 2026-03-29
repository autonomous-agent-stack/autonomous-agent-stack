from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Iterable

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.core.services.openhands_worker import OpenHandsWorkerService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.shared.manager_agent_contract import (
    ManagerDispatchRead,
    ManagerDispatchRequest,
    ManagerExecutionPlanRead,
    ManagerIntentRead,
    ManagerPlanStrategy,
    ManagerPlanTaskRead,
    ManagerTaskStage,
)
from autoresearch.shared.models import JobStatus, utc_now
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec
from autoresearch.shared.store import Repository, create_resource_id


_COMPLEXITY_MARKERS = (
    "完整",
    "全套",
    "系统",
    "平台",
    "dashboard",
    "大屏",
    "监控",
    "实时",
    "图表",
    "电商",
    "小程序",
    "frontend",
    "backend",
    "前端",
    "后端",
    "端到端",
)


@dataclass(frozen=True, slots=True)
class _IntentRule:
    intent_id: str
    label: str
    summary: str
    keywords: tuple[str, ...]
    preferred_paths: tuple[str, ...]
    preferred_tests: tuple[str, ...]
    goal_template: str


_INTENT_RULES = (
    _IntentRule(
        intent_id="admin_dashboard",
        label="admin_dashboard",
        summary="Build an admin/panel dashboard feature across API, tests, and UI.",
        keywords=("dashboard", "大屏", "监控", "图表", "admin panel", "实时"),
        preferred_paths=(
            "src/autoresearch/api/routers/admin.py",
            "src/autoresearch/api/routers/panel.py",
            "src/autoresearch/core/services/**",
            "panel/**",
            "tests/test_panel_security.py",
            "tests/test_admin_managed_skills.py",
        ),
        preferred_tests=("tests/test_panel_security.py", "tests/test_admin_managed_skills.py"),
        goal_template="Build an admin dashboard style feature for: {prompt}",
    ),
    _IntentRule(
        intent_id="game_prototype",
        label="game_prototype",
        summary="Prototype an interactive experience on the existing panel surface.",
        keywords=("小游戏", "游戏", "game", "gameplay", "demo"),
        preferred_paths=(
            "panel/**",
            "src/autoresearch/api/routers/panel.py",
            "src/autoresearch/api/routers/openclaw.py",
            "tests/test_panel_security.py",
        ),
        preferred_tests=("tests/test_panel_security.py",),
        goal_template="Prototype a lightweight interactive feature on the existing panel surface for: {prompt}",
    ),
    _IntentRule(
        intent_id="telegram_surface",
        label="telegram_surface",
        summary="Extend Telegram and Mini App control surfaces.",
        keywords=("telegram", "mini app", "miniapp", "通知", "提醒"),
        preferred_paths=(
            "src/autoresearch/api/routers/autoresearch_plans.py",
            "src/autoresearch/api/routers/panel.py",
            "src/autoresearch/core/services/telegram_notify.py",
            "tests/test_autoresearch_planner.py",
            "tests/test_panel_security.py",
        ),
        preferred_tests=("tests/test_autoresearch_planner.py", "tests/test_panel_security.py"),
        goal_template="Improve Telegram/Mini App workflow support for: {prompt}",
    ),
    _IntentRule(
        intent_id="approval_surface",
        label="approval_surface",
        summary="Improve approval, admin, or review surfaces without changing safety policy.",
        keywords=("审批", "审核", "admin", "panel", "管理"),
        preferred_paths=(
            "src/autoresearch/api/routers/admin.py",
            "src/autoresearch/api/routers/panel.py",
            "tests/test_admin_managed_skills.py",
            "tests/test_panel_security.py",
        ),
        preferred_tests=("tests/test_admin_managed_skills.py", "tests/test_panel_security.py"),
        goal_template="Improve operator approval workflows for: {prompt}",
    ),
    _IntentRule(
        intent_id="worker_execution",
        label="worker_execution",
        summary="Improve planner, worker, or execution infrastructure.",
        keywords=("openhands", "worker", "patch", "修复", "自动化"),
        preferred_paths=(
            "src/autoresearch/core/services/openhands_worker.py",
            "src/autoresearch/core/services/autoresearch_planner.py",
            "tests/test_openhands_worker.py",
            "tests/test_autoresearch_planner.py",
        ),
        preferred_tests=("tests/test_openhands_worker.py", "tests/test_autoresearch_planner.py"),
        goal_template="Improve the execution pipeline for: {prompt}",
    ),
    _IntentRule(
        intent_id="generic_product",
        label="generic_product",
        summary="Ship a bounded product improvement through existing API/core surfaces.",
        keywords=(),
        preferred_paths=(
            "src/autoresearch/api/**",
            "src/autoresearch/core/services/**",
            "panel/**",
            "tests/**",
        ),
        preferred_tests=("tests/test_autoresearch_planner.py",),
        goal_template="Design and implement a bounded product increment for: {prompt}",
    ),
)


class ManagerAgentService:
    """Translate ambiguous founder prompts into bounded patch-only execution plans."""

    def __init__(
        self,
        repository: Repository[ManagerDispatchRead],
        *,
        repo_root: Path | None = None,
        worker_service: OpenHandsWorkerService | None = None,
        dispatch_runner: Callable[[JobSpec], RunSummary] | None = None,
        writer_lease: WriterLeaseService | None = None,
    ) -> None:
        self._repository = repository
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._worker_service = worker_service or OpenHandsWorkerService()
        self._dispatch_runner = dispatch_runner or self._default_dispatch_runner
        self._writer_lease = writer_lease or WriterLeaseService()

    def create_dispatch(self, request: ManagerDispatchRequest) -> ManagerDispatchRead:
        now = utc_now()
        dispatch_id = create_resource_id("mgrdispatch")
        intent = self._select_intent(request.prompt)
        normalized_goal = str(intent.metadata["normalized_goal"])
        execution_plan = self._build_execution_plan(dispatch_id=dispatch_id, request=request, intent=intent)
        primary_task = execution_plan.tasks[0] if execution_plan.tasks else None
        status = JobStatus.QUEUED if request.auto_dispatch else JobStatus.CREATED

        dispatch = ManagerDispatchRead(
            dispatch_id=dispatch_id,
            prompt=request.prompt,
            normalized_goal=normalized_goal,
            status=status,
            summary=(
                f"Manager routed prompt to {intent.label} and produced "
                f"{len(execution_plan.tasks)} task(s)."
            ),
            created_at=now,
            updated_at=now,
            selected_intent=intent,
            execution_plan=execution_plan,
            worker_spec=primary_task.worker_spec if primary_task is not None else None,
            controlled_request=primary_task.controlled_request if primary_task is not None else None,
            agent_job=primary_task.agent_job if primary_task is not None else None,
            run_summary=None,
            metadata={
                **request.metadata,
                "pipeline_target": request.pipeline_target,
                "target_base_branch": request.target_base_branch,
                "plan_strategy": execution_plan.strategy.value,
            },
            error=None,
        )
        return self._repository.save(dispatch.dispatch_id, dispatch)

    def list_dispatches(self) -> list[ManagerDispatchRead]:
        return self._repository.list()

    def get_dispatch(self, dispatch_id: str) -> ManagerDispatchRead | None:
        return self._repository.get(dispatch_id)

    def execute_dispatch(self, dispatch_id: str) -> ManagerDispatchRead:
        dispatch = self._require_dispatch(dispatch_id)
        plan = dispatch.execution_plan
        if plan is None or not plan.tasks:
            raise ValueError("manager dispatch does not have an execution plan")

        last_summary: RunSummary | None = None
        for task in plan.tasks:
            current = self._require_dispatch(dispatch_id)
            current_task = self._require_plan_task(current, task.task_id)
            self._ensure_dependencies_completed(current=current, task=current_task)
            self._save_dispatch(
                current,
                task_id=task.task_id,
                task_status=JobStatus.RUNNING,
            )

            if current_task.agent_job is None:
                raise ValueError(f"manager task does not have a runnable job: {task.task_id}")

            try:
                run_summary = self._dispatch_runner(current_task.agent_job)
            except Exception as exc:
                failed = self._save_dispatch(
                    self._require_dispatch(dispatch_id),
                    status=JobStatus.FAILED,
                    task_id=task.task_id,
                    task_status=JobStatus.FAILED,
                    task_error=str(exc),
                    error=str(exc),
                    summary=(
                        f"Manager plan failed on {task.task_id} "
                        f"after routing {len(plan.tasks)} task(s)."
                    ),
                )
                return failed

            last_summary = run_summary
            task_status = (
                JobStatus.COMPLETED
                if run_summary.final_status in {"ready_for_promotion", "promoted"}
                else JobStatus.FAILED
            )
            if task_status is JobStatus.FAILED:
                failed = self._save_dispatch(
                    self._require_dispatch(dispatch_id),
                    status=JobStatus.FAILED,
                    task_id=task.task_id,
                    task_status=task_status,
                    task_run_summary=run_summary,
                    task_error=run_summary.driver_result.error,
                    run_summary=run_summary,
                    error=run_summary.driver_result.error,
                    summary=(
                        f"Manager plan stopped on {task.task_id} "
                        f"with {run_summary.final_status}."
                    ),
                )
                return failed

            self._save_dispatch(
                self._require_dispatch(dispatch_id),
                task_id=task.task_id,
                task_status=JobStatus.COMPLETED,
                task_run_summary=run_summary,
                run_summary=run_summary,
            )

        completed = self._save_dispatch(
            self._require_dispatch(dispatch_id),
            status=JobStatus.COMPLETED,
            run_summary=last_summary,
            summary=(
                f"Manager plan completed across {len(plan.tasks)} dependent task(s)."
            ),
            error=None,
        )
        return completed

    def _build_execution_plan(
        self,
        *,
        dispatch_id: str,
        request: ManagerDispatchRequest,
        intent: ManagerIntentRead,
    ) -> ManagerExecutionPlanRead:
        if self._should_decompose(request.prompt, intent):
            tasks = self._build_decomposed_tasks(dispatch_id=dispatch_id, request=request, intent=intent)
            return ManagerExecutionPlanRead(
                plan_id=f"{dispatch_id}-plan",
                strategy=ManagerPlanStrategy.TASK_DAG,
                summary="Manager decomposed the prompt into backend -> tests -> frontend stages.",
                tasks=tasks,
            )

        single_task = self._build_plan_task(
            dispatch_id=dispatch_id,
            request=request,
            intent=intent,
            task_suffix="primary",
            title=f"Implement {intent.label}",
            summary=intent.summary,
            stage=ManagerTaskStage.GENERIC,
            depends_on=[],
            allowed_paths=intent.allowed_paths,
            test_paths=intent.suggested_test_paths,
        )
        return ManagerExecutionPlanRead(
            plan_id=f"{dispatch_id}-plan",
            strategy=ManagerPlanStrategy.SINGLE_TASK,
            summary="Manager kept the prompt as a single bounded task.",
            tasks=[single_task],
        )

    def _build_decomposed_tasks(
        self,
        *,
        dispatch_id: str,
        request: ManagerDispatchRequest,
        intent: ManagerIntentRead,
    ) -> list[ManagerPlanTaskRead]:
        backend_paths = self._bucket_backend_paths(intent)
        test_paths = self._bucket_test_paths(intent)
        frontend_paths = self._bucket_frontend_paths(intent)

        backend_task = self._build_plan_task(
            dispatch_id=dispatch_id,
            request=request,
            intent=intent,
            task_suffix="backend",
            title=f"Backend foundation for {intent.label}",
            summary="Define or update service/API surfaces needed by the feature.",
            stage=ManagerTaskStage.BACKEND,
            depends_on=[],
            allowed_paths=backend_paths,
            test_paths=test_paths,
        )
        tests_task = self._build_plan_task(
            dispatch_id=dispatch_id,
            request=request,
            intent=intent,
            task_suffix="tests",
            title=f"Regression coverage for {intent.label}",
            summary="Lock the backend contract and edge cases with focused tests.",
            stage=ManagerTaskStage.TESTS,
            depends_on=[backend_task.task_id],
            allowed_paths=test_paths or ["tests/**"],
            test_paths=test_paths,
        )
        frontend_task = self._build_plan_task(
            dispatch_id=dispatch_id,
            request=request,
            intent=intent,
            task_suffix="frontend",
            title=f"Frontend integration for {intent.label}",
            summary="Connect the new capability to panel/admin surfaces without expanding the safety boundary.",
            stage=ManagerTaskStage.FRONTEND,
            depends_on=[backend_task.task_id, tests_task.task_id],
            allowed_paths=frontend_paths,
            test_paths=test_paths,
        )
        return [backend_task, tests_task, frontend_task]

    def _build_plan_task(
        self,
        *,
        dispatch_id: str,
        request: ManagerDispatchRequest,
        intent: ManagerIntentRead,
        task_suffix: str,
        title: str,
        summary: str,
        stage: ManagerTaskStage,
        depends_on: list[str],
        allowed_paths: list[str],
        test_paths: list[str],
    ) -> ManagerPlanTaskRead:
        task_id = f"{dispatch_id}-{task_suffix}"
        normalized_allowed_paths = self._normalize_scope(
            allowed_paths,
            fallback=["src/autoresearch/api/**", "src/autoresearch/core/services/**", "tests/**"],
        )
        normalized_test_paths = self._normalize_scope(
            test_paths,
            fallback=["tests/test_autoresearch_planner.py"],
        )
        worker_spec = self._build_worker_spec(
            dispatch_id=dispatch_id,
            request=request,
            intent=intent,
            task_id=task_id,
            task_title=title,
            task_summary=summary,
            task_stage=stage,
            depends_on=depends_on,
            allowed_paths=normalized_allowed_paths,
            test_paths=normalized_test_paths,
        )
        return ManagerPlanTaskRead(
            task_id=task_id,
            title=title,
            summary=summary,
            stage=stage,
            depends_on=depends_on,
            status=JobStatus.CREATED,
            worker_spec=worker_spec,
            controlled_request=self._worker_service.build_controlled_request(worker_spec),
            agent_job=self._worker_service.build_agent_job_spec(worker_spec),
            run_summary=None,
            metadata={
                "manager_intent_id": intent.intent_id,
                "manager_stage": stage.value,
                "dependency_count": len(depends_on),
            },
            error=None,
        )

    def _select_intent(self, prompt: str) -> ManagerIntentRead:
        normalized_prompt = prompt.strip()
        prompt_folded = normalized_prompt.casefold()
        best_rule = _INTENT_RULES[-1]
        best_keywords: list[str] = []
        best_score = -1
        for rule in _INTENT_RULES:
            matched = [keyword for keyword in rule.keywords if keyword.casefold() in prompt_folded]
            score = len(matched)
            if score > best_score:
                best_rule = rule
                best_keywords = matched
                best_score = score
        allowed_paths = self._resolve_existing_paths(best_rule.preferred_paths)
        suggested_tests = self._resolve_existing_paths(best_rule.preferred_tests)
        if not allowed_paths:
            allowed_paths = ["src/autoresearch/api/**", "src/autoresearch/core/services/**", "tests/**"]
        normalized_goal = best_rule.goal_template.format(prompt=normalized_prompt)
        return ManagerIntentRead(
            intent_id=best_rule.intent_id,
            label=best_rule.label,
            summary=best_rule.summary,
            matched_keywords=best_keywords,
            allowed_paths=allowed_paths,
            suggested_test_paths=suggested_tests,
            metadata={"normalized_goal": normalized_goal},
        )

    def _bucket_backend_paths(self, intent: ManagerIntentRead) -> list[str]:
        candidates = [
            path
            for path in intent.allowed_paths
            if path.startswith("src/")
            and not self._is_frontend_path(path)
            and not path.startswith("tests/")
        ]
        return self._normalize_scope(
            candidates,
            fallback=["src/autoresearch/api/**", "src/autoresearch/core/services/**"],
        )

    def _bucket_test_paths(self, intent: ManagerIntentRead) -> list[str]:
        candidates = [
            *intent.suggested_test_paths,
            *[path for path in intent.allowed_paths if path.startswith("tests/")],
        ]
        return self._normalize_scope(candidates, fallback=["tests/test_autoresearch_planner.py"])

    def _bucket_frontend_paths(self, intent: ManagerIntentRead) -> list[str]:
        candidates = [path for path in intent.allowed_paths if self._is_frontend_path(path)]
        return self._normalize_scope(
            candidates,
            fallback=["panel/**", "src/autoresearch/api/routers/panel.py"],
        )

    def _resolve_existing_paths(self, patterns: tuple[str, ...]) -> list[str]:
        resolved: list[str] = []
        for pattern in patterns:
            if pattern.endswith("/**"):
                relative_dir = pattern[:-3]
                if (self._repo_root / relative_dir).exists():
                    resolved.append(pattern)
                continue
            if (self._repo_root / pattern).exists():
                resolved.append(pattern)
        return resolved

    def _normalize_scope(self, values: Iterable[str], *, fallback: list[str]) -> list[str]:
        normalized = self._dedupe(values)
        if normalized:
            return normalized
        return self._dedupe(item for item in fallback if self._scope_exists(item))

    def _scope_exists(self, pattern: str) -> bool:
        if pattern.endswith("/**"):
            return (self._repo_root / pattern[:-3]).exists()
        return (self._repo_root / pattern).exists()

    def _should_decompose(self, prompt: str, intent: ManagerIntentRead) -> bool:
        prompt_folded = prompt.casefold()
        if intent.intent_id == "admin_dashboard":
            return True
        if any(marker.casefold() in prompt_folded for marker in _COMPLEXITY_MARKERS):
            return True
        return len(prompt.strip()) >= 40 and len(intent.matched_keywords) >= 2

    def _build_worker_spec(
        self,
        *,
        dispatch_id: str,
        request: ManagerDispatchRequest,
        intent: ManagerIntentRead,
        task_id: str,
        task_title: str,
        task_summary: str,
        task_stage: ManagerTaskStage,
        depends_on: list[str],
        allowed_paths: list[str],
        test_paths: list[str],
    ) -> OpenHandsWorkerJobSpec:
        slug = self._slugify(f"{intent.label}-{task_stage.value}")
        test_command = "pytest -q " + " ".join(test_paths) if test_paths else "pytest -q tests/test_autoresearch_planner.py"
        dependency_text = ", ".join(depends_on) if depends_on else "none"
        problem_statement = (
            "Manager agent execution plan task.\n\n"
            f"Founder prompt: {request.prompt}\n"
            f"Normalized goal: {intent.metadata['normalized_goal']}\n"
            f"Intent: {intent.label}\n"
            f"Task title: {task_title}\n"
            f"Task summary: {task_summary}\n"
            f"Task stage: {task_stage.value}\n"
            f"Dependencies: {dependency_text}\n"
            "Stay inside the scoped files and deliver the smallest useful patch for this stage only."
        )
        return OpenHandsWorkerJobSpec(
            job_id=task_id,
            problem_statement=problem_statement,
            allowed_paths=allowed_paths,
            test_command=test_command,
            pipeline_target=request.pipeline_target,
            target_base_branch=request.target_base_branch,
            max_iterations=request.max_iterations,
            metadata={
                **request.metadata,
                "manager_dispatch_id": dispatch_id,
                "manager_prompt": request.prompt,
                "manager_intent_id": intent.intent_id,
                "manager_intent_label": intent.label,
                "manager_goal": intent.metadata["normalized_goal"],
                "manager_task_id": task_id,
                "manager_task_title": task_title,
                "manager_task_stage": task_stage.value,
                "manager_dependencies": list(depends_on),
                "approval_granted": request.approval_granted,
                "branch_name": f"codex/manager/{slug}-{dispatch_id[-6:]}",
                "commit_message": f"Manager Agent [{task_stage.value}]: {intent.label}",
                "pr_title": f"Manager Agent [{task_stage.value}]: {intent.label}",
                "pr_body": f"{task_title}\n\n{request.prompt}",
                "base_branch": request.target_base_branch,
            },
        )

    def _save_dispatch(
        self,
        current: ManagerDispatchRead,
        *,
        status: JobStatus | None = None,
        task_id: str | None = None,
        task_status: JobStatus | None = None,
        task_run_summary: RunSummary | None = None,
        task_error: str | None = None,
        run_summary: RunSummary | None = None,
        summary: str | None = None,
        error: str | None = None,
    ) -> ManagerDispatchRead:
        execution_plan = current.execution_plan
        if execution_plan is not None and task_id is not None:
            updated_tasks: list[ManagerPlanTaskRead] = []
            for task in execution_plan.tasks:
                if task.task_id != task_id:
                    updated_tasks.append(task)
                    continue
                updated_tasks.append(
                    task.model_copy(
                        update={
                            "status": task_status or task.status,
                            "run_summary": task_run_summary if task_run_summary is not None else task.run_summary,
                            "error": task_error if task_error is not None else task.error,
                        }
                    )
                )
            execution_plan = execution_plan.model_copy(update={"tasks": updated_tasks})

        updated = current.model_copy(
            update={
                "status": status or current.status,
                "execution_plan": execution_plan,
                "run_summary": run_summary if run_summary is not None else current.run_summary,
                "summary": summary if summary is not None else current.summary,
                "error": error if error is not None else current.error,
                "updated_at": utc_now(),
            }
        )
        return self._repository.save(updated.dispatch_id, updated)

    def _ensure_dependencies_completed(self, *, current: ManagerDispatchRead, task: ManagerPlanTaskRead) -> None:
        if current.execution_plan is None:
            return
        dependency_statuses = {
            item.task_id: item.status
            for item in current.execution_plan.tasks
            if item.task_id in task.depends_on
        }
        missing = [dep for dep in task.depends_on if dependency_statuses.get(dep) is not JobStatus.COMPLETED]
        if missing:
            raise ValueError(f"task {task.task_id} is blocked by incomplete dependencies: {', '.join(missing)}")

    def _require_plan_task(self, current: ManagerDispatchRead, task_id: str) -> ManagerPlanTaskRead:
        if current.execution_plan is None:
            raise KeyError(f"manager execution plan missing for task: {task_id}")
        for task in current.execution_plan.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(f"manager task not found: {task_id}")

    def _default_dispatch_runner(self, job: JobSpec) -> RunSummary:
        runner = AgentExecutionRunner(repo_root=self._repo_root)
        return runner.run_job(job)

    def _require_dispatch(self, dispatch_id: str) -> ManagerDispatchRead:
        dispatch = self._repository.get(dispatch_id)
        if dispatch is None:
            raise KeyError(f"manager dispatch not found: {dispatch_id}")
        return dispatch

    @staticmethod
    def _is_frontend_path(path: str) -> bool:
        normalized = path.replace("\\", "/")
        return normalized.startswith("panel/") or normalized.endswith("/panel.py")

    @staticmethod
    def _dedupe(values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in values:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "dispatch"
