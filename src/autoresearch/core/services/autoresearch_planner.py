from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.core.services.openhands_worker import OpenHandsWorkerService
from autoresearch.core.services.upstream_watcher import UpstreamWatcherService
from autoresearch.shared.autoresearch_planner_contract import (
    AutoResearchPlanRead,
    AutoResearchPlanDispatchStatus,
    AutoResearchPlannerCandidateRead,
    AutoResearchPlannerEvidenceRead,
    AutoResearchPlannerRequest,
    UpstreamWatchDecision,
    UpstreamWatchRead,
)
from autoresearch.shared.models import JobStatus, utc_now
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec
from autoresearch.shared.store import Repository, create_resource_id


_IGNORED_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".masfactory_runtime",
    "node_modules",
    "panel",
    "dashboard",
    "memory",
    "logs",
}
_MARKER_WEIGHTS = {
    "BUG": 65.0,
    "FIXME": 60.0,
    "XXX": 50.0,
    "HACK": 45.0,
    "TODO": 35.0,
}
_MARKER_PATTERN = re.compile(r"\b(BUG|FIXME|XXX|HACK|TODO)\b[:\s-]*(.*)")
_CRITICAL_PREFIXES = (
    "src/autoresearch/core/services/",
    "src/autoresearch/executions/",
    "src/autoresearch/api/",
    "scripts/",
)


@dataclass(slots=True)
class _MarkerOccurrence:
    marker: str
    line: int
    detail: str
    weight: float


class AutoResearchPlannerService:
    """Scan the repository for bounded patch-only work and emit worker-ready specs."""

    def __init__(
        self,
        repository: Repository[AutoResearchPlanRead],
        *,
        repo_root: Path | None = None,
        worker_service: OpenHandsWorkerService | None = None,
        dispatch_runner: Callable[[JobSpec], RunSummary] | None = None,
        writer_lease: WriterLeaseService | None = None,
        upstream_watcher: UpstreamWatcherService | None = None,
    ) -> None:
        self._repository = repository
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        self._worker_service = worker_service or OpenHandsWorkerService()
        self._dispatch_runner = dispatch_runner or self._default_dispatch_runner
        self._writer_lease = writer_lease or WriterLeaseService()
        self._upstream_watcher = upstream_watcher

    def create(self, request: AutoResearchPlannerRequest) -> AutoResearchPlanRead:
        now = utc_now()
        plan_id = create_resource_id("plan")
        upstream_watch = self._inspect_upstream(request)
        try:
            candidates = self._scan_candidates(limit=request.max_candidates)
            selected = candidates[0] if candidates else None

            worker_spec = None
            controlled_request = None
            agent_job = None
            summary = "Planner scanned the repo but did not find a safe patch-only candidate."
            if selected is not None:
                worker_spec = self._build_worker_spec(
                    plan_id=plan_id,
                    candidate=selected,
                    request=request,
                )
                controlled_request = self._worker_service.build_controlled_request(worker_spec)
                agent_job = self._worker_service.build_agent_job_spec(worker_spec)
                summary = (
                    f"Selected {selected.title} from {len(candidates)} candidate(s); "
                    f"score={selected.priority_score:.1f}."
                )
            summary = self._augment_summary_with_upstream_watch(summary, upstream_watch)

            plan = AutoResearchPlanRead(
                plan_id=plan_id,
                goal=request.goal,
                status=JobStatus.COMPLETED,
                summary=summary,
                created_at=now,
                updated_at=now,
                selected_candidate=selected,
                candidates=candidates,
                worker_spec=worker_spec,
                controlled_request=controlled_request,
                agent_job=agent_job,
                upstream_watch=upstream_watch,
                telegram_uid=request.telegram_uid,
                panel_action_url=None,
                notification_sent=False,
                dispatch_status=AutoResearchPlanDispatchStatus.PENDING,
                dispatch_requested_at=None,
                dispatch_completed_at=None,
                dispatch_requested_by=None,
                run_summary=None,
                dispatch_error=None,
                metadata={
                    **request.metadata,
                    "repo_root": str(self._repo_root),
                    "pipeline_target": request.pipeline_target,
                    "target_base_branch": request.target_base_branch,
                },
                error=None,
            )
        except Exception as exc:
            plan = AutoResearchPlanRead(
                plan_id=plan_id,
                goal=request.goal,
                status=JobStatus.FAILED,
                summary="Planner scan failed.",
                created_at=now,
                updated_at=now,
                selected_candidate=None,
                candidates=[],
                worker_spec=None,
                controlled_request=None,
                agent_job=None,
                upstream_watch=upstream_watch,
                telegram_uid=request.telegram_uid,
                panel_action_url=None,
                notification_sent=False,
                dispatch_status=AutoResearchPlanDispatchStatus.FAILED,
                dispatch_requested_at=None,
                dispatch_completed_at=None,
                dispatch_requested_by=None,
                run_summary=None,
                dispatch_error=None,
                metadata={
                    **request.metadata,
                    "repo_root": str(self._repo_root),
                    "pipeline_target": request.pipeline_target,
                    "target_base_branch": request.target_base_branch,
                },
                error=str(exc),
            )

        return self._repository.save(plan.plan_id, plan)

    def list(self) -> list[AutoResearchPlanRead]:
        return self._repository.list()

    def get(self, plan_id: str) -> AutoResearchPlanRead | None:
        return self._repository.get(plan_id)

    def list_pending(self, *, telegram_uid: str | None = None, limit: int = 20) -> list[AutoResearchPlanRead]:
        normalized_uid = (telegram_uid or "").strip() or None
        items: list[AutoResearchPlanRead] = []
        for item in self._repository.list():
            if item.dispatch_status is not AutoResearchPlanDispatchStatus.PENDING:
                continue
            if normalized_uid is not None and item.telegram_uid not in {None, normalized_uid}:
                continue
            items.append(item)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[: max(1, limit)]

    def update_delivery(
        self,
        plan_id: str,
        *,
        telegram_uid: str | None,
        panel_action_url: str | None,
        notification_sent: bool,
    ) -> AutoResearchPlanRead:
        with self._writer_lease.acquire(f"autoresearch-plan:{plan_id}"):
            plan = self._require_plan(plan_id)
            updated = plan.model_copy(
                update={
                    "telegram_uid": (telegram_uid or "").strip() or plan.telegram_uid,
                    "panel_action_url": panel_action_url,
                    "notification_sent": notification_sent,
                    "updated_at": utc_now(),
                }
            )
            return self._repository.save(updated.plan_id, updated)

    def request_dispatch(
        self,
        plan_id: str,
        *,
        requested_by: str,
    ) -> AutoResearchPlanRead:
        with self._writer_lease.acquire(f"autoresearch-plan:{plan_id}"):
            plan = self._require_plan(plan_id)
            if plan.worker_spec is None or plan.agent_job is None:
                raise ValueError("plan does not have a dispatchable worker contract")
            if plan.dispatch_status is AutoResearchPlanDispatchStatus.DISPATCHING:
                raise ValueError("plan is already dispatching")
            if plan.dispatch_status is AutoResearchPlanDispatchStatus.DISPATCHED:
                raise ValueError("plan has already been dispatched")

            now = utc_now()
            updated = plan.model_copy(
                update={
                    "dispatch_status": AutoResearchPlanDispatchStatus.DISPATCHING,
                    "dispatch_requested_at": now,
                    "dispatch_requested_by": requested_by.strip(),
                    "dispatch_completed_at": None,
                    "dispatch_error": None,
                    "updated_at": now,
                    "metadata": {
                        **plan.metadata,
                        "dispatch_requested_by": requested_by.strip(),
                    },
                }
            )
            return self._repository.save(updated.plan_id, updated)

    def execute_dispatch(self, plan_id: str) -> AutoResearchPlanRead:
        plan = self._require_plan(plan_id)
        if plan.worker_spec is None:
            raise ValueError("plan does not have a worker spec")

        job = self._worker_service.build_agent_job_spec(plan.worker_spec)
        try:
            summary = self._dispatch_runner(job)
        except Exception as exc:
            with self._writer_lease.acquire(f"autoresearch-plan:{plan_id}"):
                current = self._require_plan(plan_id)
                updated = current.model_copy(
                    update={
                        "dispatch_status": AutoResearchPlanDispatchStatus.FAILED,
                        "dispatch_completed_at": utc_now(),
                        "dispatch_error": str(exc),
                        "updated_at": utc_now(),
                    }
                )
                return self._repository.save(updated.plan_id, updated)

        dispatch_status = (
            AutoResearchPlanDispatchStatus.DISPATCHED
            if summary.final_status in {"ready_for_promotion", "promoted"}
            else AutoResearchPlanDispatchStatus.FAILED
        )
        dispatch_error = None
        if dispatch_status is AutoResearchPlanDispatchStatus.FAILED:
            dispatch_error = summary.driver_result.error or summary.final_status

        with self._writer_lease.acquire(f"autoresearch-plan:{plan_id}"):
            current = self._require_plan(plan_id)
            updated = current.model_copy(
                update={
                    "agent_job": job,
                    "dispatch_status": dispatch_status,
                    "dispatch_completed_at": utc_now(),
                    "run_summary": summary,
                    "dispatch_error": dispatch_error,
                    "updated_at": utc_now(),
                }
            )
            return self._repository.save(updated.plan_id, updated)

    def _scan_candidates(self, *, limit: int) -> list[AutoResearchPlannerCandidateRead]:
        candidates: list[AutoResearchPlannerCandidateRead] = []
        marker_candidates = self._marker_candidates()
        candidate_index = {
            (candidate.category, candidate.source_path): candidate for candidate in marker_candidates
        }
        candidates.extend(marker_candidates)

        for candidate in self._test_gap_candidates():
            key = (candidate.category, candidate.source_path)
            if key in candidate_index:
                continue
            candidates.append(candidate)
            candidate_index[key] = candidate

        candidates.sort(
            key=lambda item: (
                -item.priority_score,
                item.category,
                item.source_path,
            )
        )
        return candidates[:limit]

    def _marker_candidates(self) -> list[AutoResearchPlannerCandidateRead]:
        candidates: list[AutoResearchPlannerCandidateRead] = []
        for rel_path in self._iter_python_files():
            occurrences = self._find_markers(rel_path)
            if not occurrences:
                continue
            suggested_tests = self._infer_test_paths(rel_path)
            score = max(item.weight for item in occurrences)
            score += min(18.0, (len(occurrences) - 1) * 6.0)
            score += self._criticality_bonus(rel_path)
            if not self._has_existing_test(suggested_tests):
                score += 15.0

            first = occurrences[0]
            marker_list = ", ".join(item.marker for item in occurrences[:3])
            evidence = [
                AutoResearchPlannerEvidenceRead(
                    kind="marker",
                    path=rel_path,
                    line=item.line,
                    detail=f"{item.marker}: {item.detail}".strip(),
                    weight=item.weight,
                )
                for item in occurrences[:5]
            ]
            if self._criticality_bonus(rel_path) > 0:
                evidence.append(
                    AutoResearchPlannerEvidenceRead(
                        kind="hotspot",
                        path=rel_path,
                        detail="critical control-plane hotspot",
                        weight=self._criticality_bonus(rel_path),
                    )
                )
            if not self._has_existing_test(suggested_tests):
                evidence.append(
                    AutoResearchPlannerEvidenceRead(
                        kind="test_gap",
                        path=suggested_tests[0],
                        detail="direct regression test is missing and should be added",
                        weight=15.0,
                    )
                )

            candidates.append(
                AutoResearchPlannerCandidateRead(
                    candidate_id=create_resource_id("candidate"),
                    title=f"Resolve {first.marker} backlog in {rel_path}",
                    summary=(
                        f"Address {marker_list} markers in {rel_path} and keep the patch focused "
                        f"to the source file plus a targeted regression test."
                    ),
                    category="marker_backlog",
                    priority_score=round(score, 1),
                    source_path=rel_path,
                    allowed_paths=[rel_path, *suggested_tests],
                    suggested_test_paths=suggested_tests,
                    test_command=self._build_test_command(rel_path, suggested_tests),
                    evidence=evidence,
                    metadata={
                        "marker_count": len(occurrences),
                        "primary_marker": first.marker,
                    },
                )
            )
        return candidates

    def _test_gap_candidates(self) -> list[AutoResearchPlannerCandidateRead]:
        candidates: list[AutoResearchPlannerCandidateRead] = []
        for rel_path in self._iter_python_files():
            if rel_path.startswith("tests/"):
                continue
            if Path(rel_path).name == "__init__.py":
                continue
            line_count = self._count_lines(rel_path)
            if line_count < 120:
                continue

            suggested_tests = self._infer_test_paths(rel_path)
            if self._has_existing_test(suggested_tests):
                continue

            score = 40.0 + min(20.0, line_count / 20.0)
            score += self._criticality_bonus(rel_path)
            candidates.append(
                AutoResearchPlannerCandidateRead(
                    candidate_id=create_resource_id("candidate"),
                    title=f"Add focused regression coverage for {rel_path}",
                    summary=(
                        f"{rel_path} is relatively large and lacks a direct regression test. "
                        "Add a focused test while keeping source changes minimal."
                    ),
                    category="test_gap",
                    priority_score=round(score, 1),
                    source_path=rel_path,
                    allowed_paths=[rel_path, *suggested_tests],
                    suggested_test_paths=suggested_tests,
                    test_command=self._build_test_command(rel_path, suggested_tests),
                    evidence=[
                        AutoResearchPlannerEvidenceRead(
                            kind="test_gap",
                            path=suggested_tests[0],
                            detail="no direct test file found for this source hotspot",
                            weight=25.0,
                        ),
                        AutoResearchPlannerEvidenceRead(
                            kind="hotspot",
                            path=rel_path,
                            detail=f"file has {line_count} lines",
                            weight=min(20.0, line_count / 20.0),
                        ),
                    ],
                    metadata={
                        "line_count": line_count,
                    },
                )
            )
        return candidates

    def _build_worker_spec(
        self,
        *,
        plan_id: str,
        candidate: AutoResearchPlannerCandidateRead,
        request: AutoResearchPlannerRequest,
    ) -> OpenHandsWorkerJobSpec:
        slug = self._slugify(candidate.source_path)
        branch_suffix = candidate.candidate_id.split("_")[-1]
        problem_statement = (
            f"{candidate.summary}\n\n"
            f"Goal: {request.goal}\n"
            f"Selected source: {candidate.source_path}\n"
            f"Primary evidence: {candidate.evidence[0].detail if candidate.evidence else 'n/a'}"
        )
        return OpenHandsWorkerJobSpec(
            job_id=f"{plan_id}-{branch_suffix}",
            problem_statement=problem_statement,
            allowed_paths=list(candidate.allowed_paths),
            test_command=candidate.test_command,
            pipeline_target=request.pipeline_target,
            target_base_branch=request.target_base_branch,
            max_iterations=request.max_iterations,
            metadata={
                **request.metadata,
                "planner_plan_id": plan_id,
                "planner_candidate_id": candidate.candidate_id,
                "planner_score": candidate.priority_score,
                "planner_category": candidate.category,
                "approval_granted": request.approval_granted,
                "branch_name": f"codex/autoresearch/{slug}-{branch_suffix[:6]}",
                "commit_message": f"AutoResearch: {candidate.title}",
                "pr_title": f"AutoResearch: {candidate.title}",
                "pr_body": candidate.summary,
                "base_branch": request.target_base_branch,
            },
        )

    def _default_dispatch_runner(self, job: JobSpec) -> RunSummary:
        runner = AgentExecutionRunner(repo_root=self._repo_root)
        return runner.run_job(job)

    def _inspect_upstream(self, request: AutoResearchPlannerRequest) -> UpstreamWatchRead | None:
        if not request.include_upstream_watch or self._upstream_watcher is None:
            return None
        return self._upstream_watcher.inspect()

    def _augment_summary_with_upstream_watch(
        self,
        summary: str,
        upstream_watch: UpstreamWatchRead | None,
    ) -> str:
        if upstream_watch is None or not upstream_watch.summary:
            return summary
        if upstream_watch.decision is UpstreamWatchDecision.SKIP:
            return f"{summary} Upstream watcher auto-skipped merge noise: {upstream_watch.summary}"
        if upstream_watch.decision is UpstreamWatchDecision.REVIEW:
            return f"{summary} Upstream watcher flagged review-required changes: {upstream_watch.summary}"
        return f"{summary} Upstream watcher failed: {upstream_watch.error or upstream_watch.summary}"

    def _require_plan(self, plan_id: str) -> AutoResearchPlanRead:
        plan = self._repository.get(plan_id)
        if plan is None:
            raise KeyError(f"autoresearch plan not found: {plan_id}")
        return plan

    def _iter_python_files(self) -> list[str]:
        files: list[str] = []
        for root_name in ("src", "scripts", "tests"):
            root = self._repo_root / root_name
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                rel_path = path.relative_to(self._repo_root).as_posix()
                if self._is_ignored(rel_path):
                    continue
                files.append(rel_path)
        return sorted(set(files))

    def _find_markers(self, rel_path: str) -> list[_MarkerOccurrence]:
        path = self._repo_root / rel_path
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            return []
        occurrences: list[_MarkerOccurrence] = []
        for line_number, line in enumerate(lines, start=1):
            match = _MARKER_PATTERN.search(line)
            if match is None:
                continue
            marker = match.group(1)
            detail = match.group(2).strip() or line.strip()
            occurrences.append(
                _MarkerOccurrence(
                    marker=marker,
                    line=line_number,
                    detail=detail[:180],
                    weight=_MARKER_WEIGHTS[marker],
                )
            )
        return occurrences

    def _count_lines(self, rel_path: str) -> int:
        try:
            return len((self._repo_root / rel_path).read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            return 0

    def _infer_test_paths(self, rel_path: str) -> list[str]:
        if rel_path.startswith("tests/"):
            return [rel_path]

        tests_root = self._repo_root / "tests"
        stem = Path(rel_path).stem
        existing: list[str] = []
        if tests_root.exists():
            for path in tests_root.rglob(f"test_{stem}.py"):
                candidate = path.relative_to(self._repo_root).as_posix()
                if self._is_ignored(candidate):
                    continue
                existing.append(candidate)
        if existing:
            return sorted(existing)[:2]
        return [f"tests/test_{stem}.py"]

    def _build_test_command(self, source_path: str, test_paths: list[str]) -> str:
        if source_path.startswith("tests/"):
            return "pytest -q " + " ".join(test_paths)
        if test_paths:
            return "pytest -q " + " ".join(test_paths)
        return f"python -m py_compile {source_path}"

    def _has_existing_test(self, test_paths: list[str]) -> bool:
        return any((self._repo_root / test_path).exists() for test_path in test_paths)

    def _criticality_bonus(self, rel_path: str) -> float:
        for prefix in _CRITICAL_PREFIXES:
            if rel_path.startswith(prefix):
                return 18.0
        return 0.0

    @staticmethod
    def _is_ignored(rel_path: str) -> bool:
        return any(part in _IGNORED_PATH_PARTS for part in Path(rel_path).parts)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "plan"
