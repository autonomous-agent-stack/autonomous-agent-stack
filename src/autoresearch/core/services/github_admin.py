from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from github_admin.contracts import (
    GitHubAdminFailureRead,
    GitHubAdminInventoryRequest,
    GitHubAdminPlanDecisionRead,
    GitHubAdminProfileRead,
    GitHubAdminRunRead,
    GitHubAdminRunSummary,
    GitHubAdminRunType,
    GitHubAdminTransferPlanRequest,
)
from github_admin.inventory import GitHubApiInventoryGateway, InventoryGateway, collect_inventory
from github_admin.profiles import load_profiles
from github_admin.transfer import build_transfer_decisions, render_transfer_plan_markdown

from autoresearch.shared.models import JobStatus, utc_now
from autoresearch.shared.store import Repository, create_resource_id


logger = logging.getLogger(__name__)


class GitHubAdminService:
    def __init__(
        self,
        *,
        repository: Repository[GitHubAdminRunRead],
        repo_root: Path,
        gateway_factory: Callable[[GitHubAdminProfileRead | None], InventoryGateway] | None = None,
        now_factory=utc_now,
    ) -> None:
        self._repository = repository
        self._repo_root = repo_root
        self._profiles_dir = repo_root / "configs" / "github_profiles"
        self._gateway_factory = gateway_factory or self._default_gateway_factory
        self._now_factory = now_factory

    def inventory(self, request: GitHubAdminInventoryRequest) -> GitHubAdminRunRead:
        run_id = create_resource_id("ghadm")
        now = self._now_factory()
        profiles = self._load_profiles()
        collection = collect_inventory(
            owners=request.owners,
            visibility=request.visibility.value,
            include_archived=request.include_archived,
            profiles=profiles,
            gateway_factory=self._gateway_factory,
        )
        run_dir = self._prepare_run_dir(now)
        artifacts = self._write_inventory_artifacts(run_dir, collection.failures)
        summary = self._build_summary(
            owners_requested=request.owners,
            owners_scanned=collection.owners_scanned,
            repositories=collection.repositories,
            decisions=[],
            failures=collection.failures,
        )
        status = JobStatus.COMPLETED if collection.owners_scanned else JobStatus.FAILED
        record = GitHubAdminRunRead(
            run_id=run_id,
            run_type=GitHubAdminRunType.INVENTORY,
            status=status,
            dry_run=True,
            source_owners=request.owners,
            target_owner=request.target_owner,
            visibility=request.visibility,
            include_archived=request.include_archived,
            profiles=profiles,
            repositories=collection.repositories,
            decisions=[],
            failures=collection.failures,
            summary=summary,
            run_dir=str(run_dir),
            artifacts=artifacts,
            created_at=now,
            updated_at=self._now_factory(),
            error=None if collection.owners_scanned else "inventory failed for all requested owners",
        )
        self._write_json(run_dir / "inventory.json", record.model_dump(mode="json"))
        return self._repository.save(record.run_id, record)

    def transfer_plan(self, request: GitHubAdminTransferPlanRequest) -> GitHubAdminRunRead:
        run_id = create_resource_id("ghplan")
        now = self._now_factory()
        profiles = self._load_profiles()
        collection = collect_inventory(
            owners=request.source_owners,
            visibility=request.visibility.value,
            include_archived=request.include_archived,
            profiles=profiles,
            gateway_factory=self._gateway_factory,
        )
        decisions = build_transfer_decisions(
            repositories=collection.repositories,
            source_owners=request.source_owners,
            target_owner=request.target_owner,
            profiles=profiles,
            post_actions=request.post_actions,
        )
        plan_markdown = render_transfer_plan_markdown(
            run_id=run_id,
            source_owners=request.source_owners,
            target_owner=request.target_owner,
            decisions=decisions,
        )
        run_dir = self._prepare_run_dir(now)
        artifacts = self._write_plan_artifacts(run_dir, plan_markdown, collection.failures)
        summary = self._build_summary(
            owners_requested=request.source_owners,
            owners_scanned=collection.owners_scanned,
            repositories=collection.repositories,
            decisions=decisions,
            failures=collection.failures,
        )
        status = JobStatus.COMPLETED if collection.owners_scanned else JobStatus.FAILED
        record = GitHubAdminRunRead(
            run_id=run_id,
            run_type=GitHubAdminRunType.TRANSFER_PLAN,
            status=status,
            dry_run=True,
            source_owners=request.source_owners,
            target_owner=request.target_owner,
            visibility=request.visibility,
            include_archived=request.include_archived,
            profiles=profiles,
            repositories=collection.repositories,
            decisions=decisions,
            failures=collection.failures,
            summary=summary,
            run_dir=str(run_dir),
            artifacts=artifacts,
            plan_markdown=plan_markdown,
            created_at=now,
            updated_at=self._now_factory(),
            error=None if collection.owners_scanned else "inventory failed for all requested owners",
        )
        self._write_json(run_dir / "inventory.json", record.model_dump(mode="json"))
        return self._repository.save(record.run_id, record)

    def get(self, run_id: str) -> GitHubAdminRunRead | None:
        return self._repository.get(run_id)

    def list(self) -> list[GitHubAdminRunRead]:
        return self._repository.list()

    def _load_profiles(self) -> list[GitHubAdminProfileRead]:
        if not self._profiles_dir.exists():
            return []
        return load_profiles(self._profiles_dir)

    def _default_gateway_factory(self, profile: GitHubAdminProfileRead | None) -> InventoryGateway:
        return GitHubApiInventoryGateway(
            github_host=profile.github_host if profile else "github.com",
            token=profile.token if profile and profile.has_token and not profile.is_example else None,
        )

    def _prepare_run_dir(self, now) -> Path:
        day_dir = self._repo_root / "artifacts" / "github_admin" / now.date().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        index = 1
        while True:
            run_dir = day_dir / f"run_{index:03d}"
            if not run_dir.exists():
                run_dir.mkdir(parents=True, exist_ok=False)
                return run_dir
            index += 1

    def _write_inventory_artifacts(self, run_dir: Path, failures: list[GitHubAdminFailureRead]) -> list[str]:
        self._write_json(run_dir / "transfer_results.json", self._placeholder_results("dry_run_only", failures))
        self._write_json(run_dir / "invitation_results.json", self._placeholder_results("dry_run_only", failures))
        return ["inventory.json", "transfer_results.json", "invitation_results.json"]

    def _write_plan_artifacts(self, run_dir: Path, plan_markdown: str, failures: list[GitHubAdminFailureRead]) -> list[str]:
        (run_dir / "plan.md").write_text(plan_markdown, encoding="utf-8")
        self._write_json(run_dir / "transfer_results.json", self._placeholder_results("not_executed", failures))
        self._write_json(run_dir / "invitation_results.json", self._placeholder_results("not_executed", failures))
        return ["inventory.json", "plan.md", "transfer_results.json", "invitation_results.json"]

    def _placeholder_results(self, status_label: str, failures: list[GitHubAdminFailureRead]) -> dict[str, object]:
        return {
            "mode": "dry_run",
            "status": status_label,
            "executed": False,
            "reason": "real transfer not enabled",
            "failures": [failure.model_dump(mode="json") for failure in failures],
        }

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_summary(
        self,
        *,
        owners_requested: list[str],
        owners_scanned: list[str],
        repositories,
        decisions: list[GitHubAdminPlanDecisionRead],
        failures: list[GitHubAdminFailureRead],
    ) -> GitHubAdminRunSummary:
        excluded_repo_count = sum(1 for repository in repositories if repository.suggested_exclude)
        planned_transfer_count = sum(1 for decision in decisions if decision.action == "plan_transfer")
        manual_review_count = sum(1 for decision in decisions if decision.action == "review")
        candidate_repo_count = sum(
            1
            for repository in repositories
            if not repository.suggested_exclude or any("heuristic:" in item for item in repository.suggested_exclude_reasons)
        )
        return GitHubAdminRunSummary(
            owners_requested=owners_requested,
            owners_scanned=owners_scanned,
            repo_count=len(repositories),
            candidate_repo_count=candidate_repo_count,
            excluded_repo_count=excluded_repo_count,
            planned_transfer_count=planned_transfer_count,
            manual_review_count=manual_review_count,
            failure_count=len(failures),
        )
