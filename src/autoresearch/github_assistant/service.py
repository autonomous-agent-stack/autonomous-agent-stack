from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable

from autoresearch.core.services.git_promotion_gate import (
    CliGitPromotionProvider,
    GitPromotionGateService,
    GitPromotionProvider,
)
from autoresearch.github_assistant.config import (
    ResolvedGitHubAssistantProfile,
    load_assistant_config,
    load_policy,
    load_repo_catalog,
    list_resolved_profiles,
    resolve_repo,
    resolve_profile,
    resolve_repo_relative_path,
)
from autoresearch.github_assistant.executors import AssistantExecutorRunner
from autoresearch.github_assistant.gh import GhCliGateway
from autoresearch.github_assistant.models import (
    AssistantConfig,
    AssistantPolicy,
    DoctorCheck,
    DoctorStatus,
    ExecutionPlan,
    GitHubAssistantDoctorRead,
    GitHubAssistantHealthRead,
    GitHubIssue,
    GitHubAssistantYouTubePublishRequest,
    GitHubAssistantYouTubePublishResult,
    GitHubPullRequest,
    ManagedRepoConfig,
    PreparedWorkspace,
    PullRequestReviewResult,
    RepoCatalog,
    ReleasePlanResult,
    RunSummary,
    ScheduleSummary,
    TriageIssueType,
    TriagePriority,
    TriageResult,
)
from autoresearch.github_assistant.prompts import PromptCatalog
from autoresearch.github_assistant.workspace import LocalWorkspaceManager
from autoresearch.shared.models import GitPromotionMode, PromotionIntent

_PR_URL_RE = re.compile(r"/pull/(?P<number>\d+)(?:$|[/?#])")


@dataclass(frozen=True, slots=True)
class LoadedAssistantContext:
    profile: ResolvedGitHubAssistantProfile
    assistant: AssistantConfig
    repos: RepoCatalog
    policy: AssistantPolicy
    prompts: PromptCatalog


class GitHubAssistantServiceRegistry:
    def __init__(self, *, repo_root: Path | None = None) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._services: dict[str, GitHubAssistantService] = {}
        self._signatures: dict[str, tuple[object, ...]] = {}

    def list_profiles(self) -> list[ResolvedGitHubAssistantProfile]:
        return list_resolved_profiles(self._repo_root)

    def default_profile_id(self) -> str | None:
        for profile in self.list_profiles():
            if profile.is_default:
                return profile.id
        return None

    def get(self, profile_id: str | None = None) -> GitHubAssistantService:
        profile = resolve_profile(self._repo_root, profile_id)
        signature = (
            profile.id,
            str(profile.root),
            profile.display_name,
            profile.github_host,
            str(profile.gh_config_dir),
            profile.explicit,
            profile.is_default,
        )
        cached = self._services.get(profile.id)
        if cached is not None and self._signatures.get(profile.id) == signature:
            return cached
        service = GitHubAssistantService(repo_root=self._repo_root, profile=profile)
        self._services[profile.id] = service
        self._signatures[profile.id] = signature
        return service


class GitHubAssistantService:
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        profile: ResolvedGitHubAssistantProfile | None = None,
        github: Any | None = None,
        workspace_manager: Any | None = None,
        promotion_provider: GitPromotionProvider | None = None,
        executor_runner: Callable[..., None] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._profile = profile or resolve_profile(self._repo_root)
        self._github_env = self._build_github_env(self._profile)
        self._github = github or GhCliGateway(
            repo_root=self._repo_root,
            env=self._github_env,
            github_host=self._profile.github_host,
        )
        self._workspace_manager = workspace_manager
        self._promotion_provider = promotion_provider or CliGitPromotionProvider(
            env=self._github_env,
            github_host=self._profile.github_host,
        )
        self._executor_runner = executor_runner
        self._now_factory = now_factory or (lambda: datetime.now(timezone.utc))
        self._executor_adapter = AssistantExecutorRunner(repo_root=self._repo_root)

    @property
    def profile(self) -> ResolvedGitHubAssistantProfile:
        return self._profile

    def load_context(self) -> LoadedAssistantContext:
        assistant = load_assistant_config(self._profile.root)
        repos = load_repo_catalog(self._profile.root)
        policy = load_policy(self._profile.root, assistant)
        prompts_root = resolve_repo_relative_path(self._profile.root, assistant.prompts_dir)
        prompts = PromptCatalog(prompts_root)
        return LoadedAssistantContext(
            profile=self._profile,
            assistant=assistant,
            repos=repos,
            policy=policy,
            prompts=prompts,
        )

    def doctor_report(self) -> GitHubAssistantDoctorRead:
        checks, ok = self.doctor()
        expected_bot_account = None
        managed_repo_count = 0
        try:
            context = self.load_context()
            expected_bot_account = context.assistant.bot_account
            managed_repo_count = len(context.repos.repos)
        except Exception:
            expected_bot_account = None
        try:
            active_login = getattr(self._github, "current_login", lambda: None)()
        except Exception:
            active_login = None
        return GitHubAssistantDoctorRead(
            ok=ok,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            github_host=self._profile.github_host,
            managed_repo_count=managed_repo_count,
            expected_bot_account=expected_bot_account,
            active_login=active_login,
            checks=checks,
        )

    def health_report(self) -> GitHubAssistantHealthRead:
        doctor = self.doctor_report()
        auth_check = next((item for item in doctor.checks if item.name == "gh auth"), None)
        gh_auth_ok = auth_check is not None and auth_check.status == DoctorStatus.PASS
        return GitHubAssistantHealthRead(
            status="ok" if doctor.ok else "degraded",
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            github_host=self._profile.github_host,
            managed_repo_count=doctor.managed_repo_count,
            doctor_ok=doctor.ok,
            gh_auth_ok=gh_auth_ok,
            expected_bot_account=doctor.expected_bot_account,
            active_login=doctor.active_login,
            checks=doctor.checks,
        )

    def read_summary(self, run_dir: Path) -> RunSummary:
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"run summary not found: {summary_path}")
        return RunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))

    def list_artifacts(self, run_dir: Path) -> list[str]:
        if not run_dir.exists():
            return []
        return sorted(item.name for item in run_dir.iterdir() if item.is_file())

    def doctor(self) -> tuple[list[DoctorCheck], bool]:
        checks: list[DoctorCheck] = []
        assistant_path = self._profile.root / "assistant.yaml"
        repos_path = self._profile.root / "repos.yaml"

        if self._profile.explicit:
            profiles_path = self._repo_root / "profiles.yaml"
            if profiles_path.exists():
                checks.append(
                    DoctorCheck(
                        name="profiles.yaml",
                        status=DoctorStatus.PASS,
                        detail=self._relative_to_template_root(profiles_path),
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        name="profiles.yaml",
                        status=DoctorStatus.FAIL,
                        detail="missing profiles.yaml",
                    )
                )

        if assistant_path.exists():
            checks.append(
                DoctorCheck(
                    name="assistant.yaml",
                    status=DoctorStatus.PASS,
                    detail=self._relative_to_template_root(assistant_path),
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="assistant.yaml",
                    status=DoctorStatus.FAIL,
                    detail="missing assistant.yaml",
                    hint="Copy the template file and set your bot account.",
                )
            )
        if repos_path.exists():
            checks.append(
                DoctorCheck(
                    name="repos.yaml",
                    status=DoctorStatus.PASS,
                    detail=self._relative_to_template_root(repos_path),
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="repos.yaml",
                    status=DoctorStatus.FAIL,
                    detail="missing repos.yaml",
                    hint="Add at least one managed repository.",
                )
            )

        try:
            context = self.load_context()
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name="config parse",
                    status=DoctorStatus.FAIL,
                    detail=str(exc),
                )
            )
            return checks, False

        if context.repos.repos:
            checks.append(
                DoctorCheck(
                    name="managed repos",
                    status=DoctorStatus.PASS,
                    detail=f"{len(context.repos.repos)} configured",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="managed repos",
                    status=DoctorStatus.FAIL,
                    detail="no managed repositories configured",
                    hint="Add at least one repo entry to repos.yaml.",
                )
            )
            return checks, False

        for filename in (
            "issue-triage.md",
            "issue-execution-plan.md",
            "draft-pr-summary.md",
            "pr-review.md",
            "release-ops.md",
        ):
            try:
                path = context.prompts.require(filename)
            except FileNotFoundError as exc:
                checks.append(DoctorCheck(name=f"prompt:{filename}", status=DoctorStatus.FAIL, detail=str(exc)))
            else:
                checks.append(
                    DoctorCheck(
                        name=f"prompt:{filename}",
                        status=DoctorStatus.PASS,
                        detail=self._relative_to_template_root(path),
                    )
                )

        policy_path = resolve_repo_relative_path(self._profile.root, context.assistant.policy_path)
        checks.append(
            DoctorCheck(
                name="profile",
                status=DoctorStatus.PASS,
                detail=f"{self._profile.id} ({self._profile.display_name})",
            )
        )
        checks.append(
            DoctorCheck(
                name="policy",
                status=DoctorStatus.PASS,
                detail=self._relative_to_template_root(policy_path),
            )
        )

        checks.append(self._directory_check(name="runs dir", path=self._runtime_runs_root(context.assistant)))
        checks.append(
            self._directory_check(
                name="workspace root",
                path=self._runtime_workspace_root(context.assistant),
            )
        )
        checks.append(self._executor_check(context.assistant))

        gh_installed = getattr(self._github, "is_installed", lambda: True)()
        if gh_installed:
            checks.append(DoctorCheck(name="gh binary", status=DoctorStatus.PASS, detail="gh is available"))
        else:
            checks.append(
                DoctorCheck(
                    name="gh binary",
                    status=DoctorStatus.FAIL,
                    detail="gh is not installed",
                    hint="Install GitHub CLI before using the assistant.",
                )
            )
            checks.append(
                DoctorCheck(
                    name="gh auth",
                    status=DoctorStatus.FAIL,
                    detail="skipped because gh binary is unavailable",
                    hint="Install GitHub CLI before checking auth.",
                )
            )
            ok = all(check.status != DoctorStatus.FAIL for check in checks)
            return checks, ok

        auth_probe = getattr(self._github, "auth_probe", None)
        if callable(auth_probe):
            auth_ok, auth_detail = auth_probe()
        else:
            auth_ok = getattr(self._github, "auth_status", lambda: False)()
            auth_detail = "authenticated" if auth_ok else "gh auth status failed"
        if auth_ok:
            checks.append(DoctorCheck(name="gh auth", status=DoctorStatus.PASS, detail=auth_detail))
        else:
            checks.append(
                DoctorCheck(
                    name="gh auth",
                    status=DoctorStatus.FAIL,
                    detail=auth_detail,
                    hint="Run `gh auth login` with the bot account.",
                )
            )
        try:
            current_login = getattr(self._github, "current_login", lambda: None)()
        except Exception:
            current_login = None
        if current_login and current_login != context.assistant.bot_account:
            checks.append(
                DoctorCheck(
                    name="gh bot account",
                    status=DoctorStatus.WARN,
                    detail=f"active gh login is {current_login}, config expects {context.assistant.bot_account}",
                    hint="Switch gh login or update assistant.yaml.",
                )
            )
        elif current_login:
            checks.append(
                DoctorCheck(
                    name="gh bot account",
                    status=DoctorStatus.PASS,
                    detail=current_login,
                )
            )

        for repo_config in context.repos.repos:
            if not auth_ok:
                checks.append(
                    DoctorCheck(
                        name=f"repo:{repo_config.repo}",
                        status=DoctorStatus.WARN,
                        detail="skipped because gh auth is failing",
                        hint="Re-authenticate first, then rerun doctor.",
                    )
                )
                continue
            repo_probe = getattr(self._github, "repo_probe", None)
            if callable(repo_probe):
                accessible, repo_detail = repo_probe(repo_config.repo)
            else:
                accessible = getattr(self._github, "repo_accessible", lambda _repo: False)(repo_config.repo)
                repo_detail = "authorized" if accessible else "not accessible"
            status = DoctorStatus.PASS if accessible else DoctorStatus.FAIL
            hint = None if accessible else f"Verify the bot account can access {repo_config.repo}."
            checks.append(
                DoctorCheck(
                    name=f"repo:{repo_config.repo}",
                    status=status,
                    detail=repo_detail,
                    hint=hint,
                )
            )

        ok = all(check.status != DoctorStatus.FAIL for check in checks)
        return checks, ok

    def review_pr(self, repo_name: str, pr_number: int) -> tuple[Path, PullRequestReviewResult]:
        context = self.load_context()
        repo_config = resolve_repo(context.repos, repo_name)
        pr = self._github.fetch_pull_request(repo_config.repo, pr_number)
        run_id = self._build_run_id()
        run_dir = self._build_named_run_dir(context.assistant, run_id, repo_config.repo, f"pr-{pr.number}")
        run_dir.mkdir(parents=True, exist_ok=True)
        review = self._review_pull_request(
            pr=pr,
            repo_config=repo_config,
            assistant=context.assistant,
        )
        review_text = context.prompts.render(
            "pr-review.md",
            {
                "repo": repo_config.repo,
                "pr_number": pr.number,
                "pr_title": pr.title or "(untitled)",
                "pr_url": pr.url,
                "base_ref": pr.base_ref,
                "head_ref": pr.head_ref,
                "summary": review.summary,
                "risk_level": review.risk_level,
                "suggested_checks": review.suggested_checks or ["(none)"],
                "blocked_files": review.blocked_files or ["(none)"],
                "changed_files": review.changed_files or ["(none)"],
            },
        )
        (run_dir / "review.md").write_text(review_text, encoding="utf-8")
        (run_dir / "review.json").write_text(
            json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = RunSummary(
            run_id=run_id,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            repo=repo_config.repo,
            status="reviewed_pr",
            started_at=self._now_factory(),
            updated_at=self._now_factory(),
            metadata={"pr_number": pr.number, "pr_url": pr.url, "review": review.model_dump(mode="json")},
        )
        self._write_summary(run_dir, summary)
        return run_dir, review

    def release_plan(
        self,
        repo_name: str,
        *,
        version: str | None = None,
        limit: int = 10,
    ) -> tuple[Path, ReleasePlanResult]:
        context = self.load_context()
        repo_config = resolve_repo(context.repos, repo_name)
        merged_prs = self._github.list_merged_pull_requests(repo_config.repo, limit=limit)
        run_id = self._build_run_id()
        run_dir = self._build_named_run_dir(context.assistant, run_id, repo_config.repo, "release-plan")
        run_dir.mkdir(parents=True, exist_ok=True)
        release_plan = self._build_release_plan(repo=repo_config.repo, merged_prs=merged_prs, version=version)
        release_text = context.prompts.render(
            "release-ops.md",
            {
                "repo": repo_config.repo,
                "target_version": version or "(unspecified)",
                "summary": release_plan.summary,
                "merged_prs": [
                    f"- #{item.number} {item.title} ({item.url})"
                    for item in release_plan.merged_prs
                ]
                or ["(none)"],
                "suggested_actions": release_plan.suggested_actions or ["(none)"],
            },
        )
        (run_dir / "release-plan.md").write_text(release_text, encoding="utf-8")
        (run_dir / "release-plan.json").write_text(
            json.dumps(release_plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = RunSummary(
            run_id=run_id,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            repo=repo_config.repo,
            status="release_planned",
            started_at=self._now_factory(),
            updated_at=self._now_factory(),
            metadata={"target_version": version, "merged_pr_count": len(merged_prs)},
        )
        self._write_summary(run_dir, summary)
        return run_dir, release_plan

    def triage(self, repo_name: str, issue_number: int) -> tuple[Path, TriageResult]:
        context = self.load_context()
        repo_config = resolve_repo(context.repos, repo_name)
        issue = self._github.fetch_issue(repo_config.repo, issue_number)
        triage = self._triage_issue(
            issue=issue,
            repo_config=repo_config,
            assistant=context.assistant,
        )

        run_id = self._build_run_id()
        run_dir = self._build_run_dir(context.assistant, run_id, repo_config.repo, issue.number)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_triage_artifacts(run_dir, context.prompts, repo_config, issue, triage)
        summary = RunSummary(
            run_id=run_id,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            repo=repo_config.repo,
            issue_number=issue.number,
            issue_url=issue.url,
            status="triaged",
            started_at=self._now_factory(),
            updated_at=self._now_factory(),
            triage=triage.model_dump(mode="json"),
        )
        self._write_summary(run_dir, summary)
        return run_dir, triage

    def execute(self, repo_name: str, issue_number: int) -> Path:
        context = self.load_context()
        repo_config = resolve_repo(context.repos, repo_name)
        issue = self._github.fetch_issue(repo_config.repo, issue_number)
        triage = self._triage_issue(
            issue=issue,
            repo_config=repo_config,
            assistant=context.assistant,
        )
        run_id = self._build_run_id()
        run_dir = self._build_run_dir(context.assistant, run_id, repo_config.repo, issue.number)
        run_dir.mkdir(parents=True, exist_ok=True)
        started_at = self._now_factory()
        self._write_triage_artifacts(run_dir, context.prompts, repo_config, issue, triage)

        plan = self._build_execution_plan(
            issue=issue,
            triage=triage,
            repo_config=repo_config,
            assistant=context.assistant,
            policy=context.policy,
            prompts=context.prompts,
            run_dir=run_dir,
        )

        summary = RunSummary(
            run_id=run_id,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            repo=repo_config.repo,
            issue_number=issue.number,
            issue_url=issue.url,
            status="planning",
            started_at=started_at,
            updated_at=self._now_factory(),
            triage=triage.model_dump(mode="json"),
            plan=plan.model_dump(mode="json"),
        )
        self._write_summary(run_dir, summary)

        if not triage.auto_executable:
            summary.status = "blocked"
            summary.warnings.append("issue is not safe for automatic execution")
            summary.updated_at = self._now_factory()
            self._write_summary(run_dir, summary)
            return run_dir

        workspace_manager = self._workspace_manager or LocalWorkspaceManager(
            github=self._github,
            workspace_root=self._runtime_workspace_root(context.assistant),
        )
        prepared = workspace_manager.prepare(repo=repo_config.repo, run_id=summary.run_id)
        warning_messages: list[str] = []
        try:
            self._run_executor(
                prepared=prepared,
                run_dir=run_dir,
                issue=issue,
                plan=plan,
                assistant=context.assistant,
            )
            changed_files = self._changed_files(prepared.execution_workspace_dir)
            summary.changed_files = changed_files
            if not changed_files:
                summary.status = "no_changes"
                warning_messages.append("executor completed without source changes")
                summary.warnings = warning_messages
                summary.updated_at = self._now_factory()
                self._write_summary(run_dir, summary)
                return run_dir

            disallowed = [
                path for path in changed_files if not self._matches_any(path, repo_config.allowed_paths)
            ]
            if disallowed:
                summary.status = "blocked"
                warning_messages.append(
                    "changed files outside allowed_paths: " + ", ".join(disallowed)
                )
                summary.warnings = warning_messages
                summary.updated_at = self._now_factory()
                self._write_summary(run_dir, summary)
                return run_dir

            patch_path = run_dir / "patch.diff"
            patch_path.write_text(
                self._build_patch(prepared.execution_workspace_dir),
                encoding="utf-8",
            )

            preflight, result = GitPromotionGateService(
                repo_root=prepared.source_repo_dir,
                provider=self._promotion_provider,
            ).finalize(
                intent=PromotionIntent(
                    run_id=summary.run_id,
                    actor_id=context.assistant.bot_account,
                    writer_id=context.assistant.bot_account,
                    writer_lease_key=f"github-assistant:{repo_config.repo}",
                    patch_uri=str(patch_path),
                    changed_files=changed_files,
                    base_ref=repo_config.default_branch,
                    preferred_mode=GitPromotionMode.DRAFT_PR,
                    target_base_branch=repo_config.default_branch,
                    approval_granted=True,
                    metadata={
                        "branch_name": plan.branch_name,
                        "commit_message": plan.commit_message,
                        "pr_title": plan.pr_title,
                        "pr_body": plan.pr_body,
                        "validator_commands": plan.validator_commands,
                        "forbidden_paths": plan.forbidden_paths,
                        "max_changed_files": plan.max_changed_files,
                        "max_patch_lines": plan.max_patch_lines,
                    },
                ),
                artifacts_dir=run_dir,
            )
            pr_payload = {
                "repo": repo_config.repo,
                "issue_number": issue.number,
                "issue_url": issue.url,
                "head_branch": plan.branch_name,
                "base_branch": repo_config.default_branch,
                "title": plan.pr_title,
                "body": plan.pr_body,
                "pr_url": result.pr_url,
                "promotion_preflight": preflight.model_dump(mode="json"),
                "promotion_result": result.model_dump(mode="json"),
            }
            (run_dir / "pr_payload.json").write_text(
                json.dumps(pr_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            summary.status = "draft_pr_opened" if result.pr_url else "promotion_complete"
            summary.pr_url = result.pr_url
            summary.warnings = warning_messages
            summary.updated_at = self._now_factory()
            if not result.success:
                summary.status = "promotion_failed"
                if result.reason:
                    summary.warnings.append(result.reason)
            self._maybe_apply_issue_metadata(
                repo=repo_config.repo,
                issue_number=issue.number,
                triage=triage,
                policy=context.policy,
                warnings=summary.warnings,
            )
            summary.comment_results = self._maybe_comment_links(
                repo=repo_config.repo,
                issue_number=issue.number,
                issue_url=issue.url,
                pr_url=result.pr_url,
                run_dir=run_dir,
                policy=context.policy,
            )
            self._write_summary(run_dir, summary)
            return run_dir
        except Exception as exc:
            summary.status = "failed"
            summary.warnings.append(str(exc))
            summary.updated_at = self._now_factory()
            self._write_summary(run_dir, summary)
            return run_dir
        finally:
            workspace_manager.cleanup(prepared)

    def publish_youtube(
        self,
        payload: GitHubAssistantYouTubePublishRequest,
    ) -> tuple[Path, GitHubAssistantYouTubePublishResult]:
        context = self.load_context()
        repo_config, route_reason = self._resolve_youtube_repo(context.repos, payload)
        run_id = self._build_run_id()
        run_dir = self._build_named_run_dir(context.assistant, run_id, repo_config.repo, f"youtube-{payload.video_id}")
        run_dir.mkdir(parents=True, exist_ok=True)
        started_at = self._now_factory()

        output_path = self._build_youtube_output_path(repo_config, payload)
        publish_payload = {
            "repo": repo_config.repo,
            "route_reason": route_reason,
            "output_path": output_path,
            "video_id": payload.video_id,
            "source_url": payload.source_url,
            "digest_id": payload.digest_id,
            "transcript_id": payload.transcript_id,
            "requested_by": payload.requested_by,
            "channel_id": payload.channel_id,
            "channel_title": payload.channel_title,
            "has_transcript_content": bool(payload.transcript_content and payload.transcript_content.strip()),
        }
        (run_dir / "publish_payload.json").write_text(
            json.dumps(publish_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary = RunSummary(
            run_id=run_id,
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            repo=repo_config.repo,
            status="planning",
            started_at=started_at,
            updated_at=self._now_factory(),
            metadata={
                **publish_payload,
                "content_source": "youtube",
            },
        )
        self._write_summary(run_dir, summary)

        workspace_manager = self._workspace_manager or LocalWorkspaceManager(
            github=self._github,
            workspace_root=self._runtime_workspace_root(context.assistant),
        )
        prepared = workspace_manager.prepare(repo=repo_config.repo, run_id=summary.run_id)
        warning_messages: list[str] = []
        try:
            relative_output = output_path.replace("\\", "/")
            if not self._matches_any(relative_output, repo_config.allowed_paths):
                summary.status = "blocked"
                summary.warnings = [f"output path outside allowed_paths: {relative_output}"]
                summary.updated_at = self._now_factory()
                self._write_summary(run_dir, summary)
                return run_dir, GitHubAssistantYouTubePublishResult(
                    repo=repo_config.repo,
                    output_path=relative_output,
                    route_reason=route_reason,
                )

            destination = (prepared.execution_workspace_dir / relative_output).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if prepared.execution_workspace_dir.resolve() not in destination.parents and destination != prepared.execution_workspace_dir.resolve():
                raise RuntimeError(f"refusing to write outside workspace: {relative_output}")

            destination.write_text(
                self._render_youtube_markdown(payload),
                encoding="utf-8",
            )
            (run_dir / "publish.md").write_text(destination.read_text(encoding="utf-8"), encoding="utf-8")

            changed_files = self._changed_files(prepared.execution_workspace_dir)
            summary.changed_files = changed_files
            if not changed_files:
                summary.status = "no_changes"
                summary.updated_at = self._now_factory()
                self._write_summary(run_dir, summary)
                return run_dir, GitHubAssistantYouTubePublishResult(
                    repo=repo_config.repo,
                    output_path=relative_output,
                    route_reason=route_reason,
                )

            disallowed = [
                path for path in changed_files if not self._matches_any(path, repo_config.allowed_paths)
            ]
            if disallowed:
                summary.status = "blocked"
                warning_messages.append("changed files outside allowed_paths: " + ", ".join(disallowed))
                summary.warnings = warning_messages
                summary.updated_at = self._now_factory()
                self._write_summary(run_dir, summary)
                return run_dir, GitHubAssistantYouTubePublishResult(
                    repo=repo_config.repo,
                    output_path=relative_output,
                    route_reason=route_reason,
                )

            patch_path = run_dir / "patch.diff"
            patch_path.write_text(
                self._build_patch(prepared.execution_workspace_dir),
                encoding="utf-8",
            )

            branch_name = self._build_youtube_branch_name(context.assistant, payload)
            pr_title = f"Ingest YouTube digest: {(payload.title or payload.video_id).strip()[:72]}"
            pr_body = "\n".join(
                [
                    f"Source URL: {payload.source_url}",
                    f"Video ID: {payload.video_id}",
                    f"Digest ID: {payload.digest_id}",
                    f"Transcript ID: {payload.transcript_id or '(none)'}",
                    f"Output path: `{relative_output}`",
                    f"Route reason: {route_reason}",
                ]
            )
            preflight, result = GitPromotionGateService(
                repo_root=prepared.source_repo_dir,
                provider=self._promotion_provider,
            ).finalize(
                intent=PromotionIntent(
                    run_id=summary.run_id,
                    actor_id=context.assistant.bot_account,
                    writer_id=context.assistant.bot_account,
                    writer_lease_key=f"github-assistant:{repo_config.repo}",
                    patch_uri=str(patch_path),
                    changed_files=changed_files,
                    base_ref=repo_config.default_branch,
                    preferred_mode=GitPromotionMode.DRAFT_PR,
                    target_base_branch=repo_config.default_branch,
                    approval_granted=True,
                    metadata={
                        "branch_name": branch_name,
                        "commit_message": f"docs(youtube): ingest {payload.video_id}",
                        "pr_title": pr_title,
                        "pr_body": pr_body,
                        "validator_commands": [
                            item for item in [repo_config.lint_command, repo_config.test_command] if item
                        ],
                        "forbidden_paths": context.policy.forbidden_paths,
                        "max_changed_files": context.assistant.max_changed_files,
                        "max_patch_lines": context.assistant.max_patch_lines,
                    },
                ),
                artifacts_dir=run_dir,
            )

            summary.status = "draft_pr_opened" if result.pr_url else "promotion_complete"
            summary.pr_url = result.pr_url
            summary.warnings = warning_messages
            summary.updated_at = self._now_factory()
            summary.metadata.update(
                {
                    "output_path": relative_output,
                    "route_reason": route_reason,
                    "promotion_preflight": preflight.model_dump(mode="json"),
                    "promotion_result": result.model_dump(mode="json"),
                }
            )
            if not result.success:
                summary.status = "promotion_failed"
                if result.reason:
                    summary.warnings.append(result.reason)
            self._write_summary(run_dir, summary)
            return run_dir, GitHubAssistantYouTubePublishResult(
                repo=repo_config.repo,
                output_path=relative_output,
                route_reason=route_reason,
                pr_url=result.pr_url,
                branch_name=result.branch_name,
            )
        except Exception as exc:
            summary.status = "failed"
            summary.warnings.append(str(exc))
            summary.updated_at = self._now_factory()
            self._write_summary(run_dir, summary)
            raise
        finally:
            workspace_manager.cleanup(prepared)

    def schedule_run(self) -> ScheduleSummary:
        context = self.load_context()
        summary = ScheduleSummary(
            profile_id=self._profile.id,
            profile_display_name=self._profile.display_name,
            scheduled_trigger_enabled=context.assistant.scheduled_trigger_enabled,
            issue_label=context.assistant.schedule.issue_label,
        )
        if not context.assistant.scheduled_trigger_enabled:
            return summary

        for repo_config in context.repos.repos:
            summary.repos_scanned += 1
            issue_numbers = self._github.list_open_issues(
                repo_config.repo,
                label=context.assistant.schedule.issue_label,
                limit=context.assistant.schedule.max_issues_per_repo,
            )
            summary.issues_selected += len(issue_numbers)
            for issue_number in issue_numbers:
                run_dir, _ = self.triage(repo_config.repo, issue_number)
                summary.triage_runs.append(str(run_dir))
        return summary

    def _build_execution_plan(
        self,
        *,
        issue: GitHubIssue,
        triage: TriageResult,
        repo_config: ManagedRepoConfig,
        assistant: AssistantConfig,
        policy: AssistantPolicy,
        prompts: PromptCatalog,
        run_dir: Path,
    ) -> ExecutionPlan:
        issue_slug = self._slugify(issue.title) or f"issue-{issue.number}"
        branch_name = f"{assistant.branch_prefix.rstrip('/')}/{issue.number}-{issue_slug}"
        commit_message = f"fix(issue-{issue.number}): {issue.title.strip()[:60]}"
        pr_title = f"{issue.title.strip()} (fixes #{issue.number})"
        validator_commands = [item for item in [repo_config.lint_command, repo_config.test_command] if item]
        plan = ExecutionPlan(
            repo=repo_config.repo,
            issue_number=issue.number,
            issue_url=issue.url,
            branch_name=branch_name,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=prompts.render(
                "draft-pr-summary.md",
                {
                    "repo": repo_config.repo,
                    "issue_number": issue.number,
                    "issue_title": issue.title or "(untitled)",
                    "issue_url": issue.url,
                    "summary": triage.summary,
                    "validator_commands": validator_commands or ["(none)"],
                    "allowed_paths": triage.allowed_paths or ["(none)"],
                    "branch_name": branch_name,
                },
            ),
            validator_commands=validator_commands,
            allowed_paths=list(repo_config.allowed_paths),
            forbidden_paths=list(policy.forbidden_paths),
            max_changed_files=assistant.max_changed_files,
            max_patch_lines=assistant.max_patch_lines,
        )
        plan_text = prompts.render(
            "issue-execution-plan.md",
            {
                "repo": repo_config.repo,
                "issue_number": issue.number,
                "issue_title": issue.title or "(untitled)",
                "issue_url": issue.url,
                "issue_type": triage.issue_type.value,
                "priority": triage.priority.value,
                "summary": triage.summary,
                "allowed_paths": plan.allowed_paths or ["(none)"],
                "forbidden_paths": plan.forbidden_paths or ["(none)"],
                "validator_commands": plan.validator_commands or ["(none)"],
                "branch_name": branch_name,
                "commit_message": commit_message,
            },
        )
        (run_dir / "plan.md").write_text(plan_text, encoding="utf-8")
        return plan

    def _triage_issue(
        self,
        *,
        issue: GitHubIssue,
        repo_config: ManagedRepoConfig,
        assistant: AssistantConfig,
    ) -> TriageResult:
        body = issue.body.strip()
        labels_lower = {label.lower() for label in issue.labels}
        text = f"{issue.title}\n{body}".lower()

        issue_type = TriageIssueType.TASK
        if "duplicate" in labels_lower or "duplicate of #" in text:
            issue_type = TriageIssueType.DUPLICATE
        elif any(label in labels_lower for label in ("bug", "type:bug", "regression")) or any(
            token in text for token in ("bug", "error", "traceback", "broken", "fail")
        ):
            issue_type = TriageIssueType.BUG
        elif any(label in labels_lower for label in ("feature", "enhancement", "type:feature")) or any(
            token in text for token in ("feature", "enhancement", "support", "add ")
        ):
            issue_type = TriageIssueType.FEATURE
        elif any(label in labels_lower for label in ("question", "help wanted")) or text.endswith("?"):
            issue_type = TriageIssueType.QUESTION

        priority = TriagePriority.MEDIUM
        if any(label in labels_lower for label in ("p0", "critical", "sev:critical")) or "security" in text:
            priority = TriagePriority.CRITICAL
        elif any(label in labels_lower for label in ("p1", "high", "sev:high")) or "urgent" in text:
            priority = TriagePriority.HIGH
        elif any(label in labels_lower for label in ("p3", "low", "sev:low")):
            priority = TriagePriority.LOW

        missing_context: list[str] = []
        if not body or len(body) < 24:
            missing_context.append("issue body is too short for safe automation")
        if issue_type is TriageIssueType.BUG and not any(
            token in text for token in ("steps", "expected", "actual", "repro", "traceback")
        ):
            missing_context.append("bug report is missing reproduction or expected/actual detail")
        if issue_type is TriageIssueType.FEATURE and not any(
            token in text for token in ("acceptance", "outcome", "user", "should")
        ):
            missing_context.append("feature request is missing acceptance detail")

        suggested_labels = []
        key_map = {
            TriageIssueType.BUG: "bug",
            TriageIssueType.FEATURE: "feature",
            TriageIssueType.DUPLICATE: "duplicate",
        }
        type_key = key_map.get(issue_type)
        if type_key and type_key in repo_config.labels_map:
            suggested_labels.extend(repo_config.labels_map[type_key])
        if missing_context and "info_needed" in repo_config.labels_map:
            suggested_labels.extend(repo_config.labels_map["info_needed"])
        if issue_type is not TriageIssueType.DUPLICATE and "auto_execute" in repo_config.labels_map:
            suggested_labels.extend(repo_config.labels_map["auto_execute"])
        suggested_labels = list(dict.fromkeys(suggested_labels))

        reasons = []
        auto_executable = True
        if issue.state.upper() != "OPEN":
            auto_executable = False
            reasons.append("issue is not open")
        if issue_type in (TriageIssueType.DUPLICATE, TriageIssueType.QUESTION):
            auto_executable = False
            reasons.append(f"{issue_type.value} issues are not auto-executed")
        if missing_context:
            auto_executable = False
            reasons.extend(missing_context)
        if not repo_config.allowed_paths:
            auto_executable = False
            reasons.append("managed repo has no allowed_paths")
        if not self._executor_available(assistant):
            auto_executable = False
            reasons.append("assistant executor is not configured")

        summary = issue.title.strip() or f"Issue #{issue.number}"
        if body:
            first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
            if first_line:
                summary = f"{summary}: {first_line[:120]}"

        validator_commands = [item for item in [repo_config.lint_command, repo_config.test_command] if item]

        return TriageResult(
            repo=repo_config.repo,
            issue_number=issue.number,
            issue_url=issue.url,
            issue_type=issue_type,
            priority=priority,
            summary=summary,
            suggested_labels=suggested_labels,
            suggested_assignees=[],
            missing_context=missing_context,
            auto_executable=auto_executable,
            reasons=reasons,
            allowed_paths=list(repo_config.allowed_paths),
            validator_commands=validator_commands,
        )

    def _run_executor(
        self,
        *,
        prepared: PreparedWorkspace,
        run_dir: Path,
        issue: GitHubIssue,
        plan: ExecutionPlan,
        assistant: AssistantConfig,
    ) -> None:
        if self._executor_runner is not None:
            self._executor_runner(
                workspace=prepared.execution_workspace_dir,
                run_dir=run_dir,
                issue=issue,
                plan=plan,
            )
            return
        self._executor_adapter.run(
            prepared=prepared,
            run_dir=run_dir,
            issue=issue,
            plan=plan,
            assistant=assistant,
        )

    def _build_run_id(self) -> str:
        now = self._now_factory()
        return now.strftime("%Y%m%dT%H%M%S%fZ")

    def _build_named_run_dir(
        self,
        assistant: AssistantConfig,
        run_id: str,
        repo: str,
        leaf_name: str,
    ) -> Path:
        owner, name = repo.split("/", 1)
        runs_root = self._runtime_runs_root(assistant)
        return runs_root / run_id / owner / name / leaf_name

    def _build_run_dir(
        self,
        assistant: AssistantConfig,
        run_id: str,
        repo: str,
        issue_number: int,
    ) -> Path:
        return self._build_named_run_dir(assistant, run_id, repo, f"issue-{issue_number}")

    def _runtime_runs_root(self, assistant: AssistantConfig) -> Path:
        return self._resolve_runtime_path(assistant.runs_dir)

    def _runtime_workspace_root(self, assistant: AssistantConfig) -> Path:
        return self._resolve_runtime_path(assistant.workspace_root)

    def _resolve_runtime_path(self, value: str) -> Path:
        root = resolve_repo_relative_path(self._repo_root, value)
        if not self._profile.explicit:
            return root
        if root.name == self._profile.id:
            return root
        return root / self._profile.id

    def _relative_to_template_root(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._repo_root))
        except ValueError:
            return str(path)

    def _write_summary(self, run_dir: Path, summary: RunSummary) -> None:
        (run_dir / "summary.json").write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_triage_artifacts(
        self,
        run_dir: Path,
        prompts: PromptCatalog,
        repo_config: ManagedRepoConfig,
        issue: GitHubIssue,
        triage: TriageResult,
    ) -> None:
        triage_text = prompts.render(
            "issue-triage.md",
            {
                "repo": repo_config.repo,
                "issue_number": issue.number,
                "issue_title": issue.title or "(untitled)",
                "issue_url": issue.url,
                "issue_body": issue.body.strip() or "(empty)",
                "issue_labels": ", ".join(issue.labels) or "(none)",
                "issue_type": triage.issue_type.value,
                "priority": triage.priority.value,
                "summary": triage.summary,
                "auto_executable": triage.auto_executable,
                "missing_context": triage.missing_context or ["(none)"],
                "suggested_labels": triage.suggested_labels or ["(none)"],
                "allowed_paths": triage.allowed_paths or ["(none)"],
                "reasons": triage.reasons or ["(none)"],
            },
        )
        (run_dir / "triage.md").write_text(triage_text, encoding="utf-8")
        (run_dir / "triage.json").write_text(
            json.dumps(triage.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _changed_files(self, workspace_dir: Path) -> list[str]:
        subprocess.run(
            ["git", "add", "-N", "."],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "git status failed").strip())
        changed: list[str] = []
        for line in (completed.stdout or "").splitlines():
            if len(line) < 4:
                continue
            raw_path = line[3:].strip()
            path = raw_path.split(" -> ")[-1].strip()
            if path:
                changed.append(path.replace("\\", "/"))
        return sorted(dict.fromkeys(changed))

    def _build_patch(self, workspace_dir: Path) -> str:
        completed = subprocess.run(
            ["git", "diff", "--binary"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "git diff failed").strip())
        return completed.stdout

    def _resolve_youtube_repo(
        self,
        repo_catalog: RepoCatalog,
        payload: GitHubAssistantYouTubePublishRequest,
    ) -> tuple[ManagedRepoConfig, str]:
        if payload.repo_hint and payload.repo_hint.strip():
            repo = resolve_repo(repo_catalog, payload.repo_hint)
            if not repo.youtube_ingest.enabled:
                raise ValueError(f"managed repo {repo.repo} does not enable youtube_ingest")
            return repo, f"repo_hint matched {repo.repo}"

        candidates: list[tuple[int, ManagedRepoConfig, str]] = []
        haystack = "\n".join(
            item.strip().lower()
            for item in (
                payload.title or "",
                payload.channel_title or "",
                payload.description or "",
                payload.digest_content or "",
            )
            if item and item.strip()
        )
        for repo in repo_catalog.repos:
            route = repo.youtube_ingest
            if not route.enabled:
                continue
            score = 0
            reasons: list[str] = []
            if payload.channel_id and payload.channel_id in route.channel_ids:
                score += 100
                reasons.append(f"channel_id={payload.channel_id}")
            if payload.channel_title:
                lowered_title = payload.channel_title.strip().lower()
                for candidate in route.channel_titles:
                    candidate_text = candidate.strip().lower()
                    if candidate_text and candidate_text in lowered_title:
                        score += 50
                        reasons.append(f"channel_title~={candidate}")
                        break
            matched_keywords = [keyword for keyword in route.keywords if keyword.lower() in haystack]
            if matched_keywords:
                score += len(matched_keywords) * 10
                reasons.append("keywords=" + ",".join(matched_keywords))
            if score > 0:
                candidates.append((score, repo, "; ".join(reasons)))

        if not candidates:
            raise ValueError("no youtube_ingest route matched any managed repo")

        candidates.sort(key=lambda item: item[0], reverse=True)
        top_score, top_repo, top_reason = candidates[0]
        if len(candidates) > 1 and candidates[1][0] == top_score:
            tied = ", ".join(candidate.repo for score, candidate, _reason in candidates if score == top_score)
            raise ValueError(f"ambiguous youtube_ingest route across managed repos: {tied}")
        return top_repo, top_reason

    def _build_youtube_output_path(
        self,
        repo_config: ManagedRepoConfig,
        payload: GitHubAssistantYouTubePublishRequest,
    ) -> str:
        route = repo_config.youtube_ingest
        published_date = payload.published_at.date().isoformat() if payload.published_at else "undated"
        slug = self._slugify(payload.title or payload.video_id) or payload.video_id
        relative = Path(route.output_dir) / route.filename_template.format(
            video_id=payload.video_id,
            slug=slug,
            published_date=published_date,
            channel_slug=self._slugify(payload.channel_title or payload.channel_id or "unknown"),
        )
        normalized = relative.as_posix().strip()
        if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
            raise ValueError(f"invalid youtube_ingest output path: {normalized or '<empty>'}")
        return normalized

    def _render_youtube_markdown(self, payload: GitHubAssistantYouTubePublishRequest) -> str:
        published_at = payload.published_at.isoformat() if payload.published_at else "unknown"
        lines = [
            "---",
            "source: youtube",
            f"video_id: {payload.video_id}",
            f"digest_id: {payload.digest_id}",
            f"transcript_id: {payload.transcript_id or ''}",
            f"transcript_language: {payload.transcript_language or ''}",
            f"source_url: {payload.source_url}",
            f"channel_id: {payload.channel_id or ''}",
            f"channel_title: {payload.channel_title or ''}",
            f"published_at: {published_at}",
            "---",
            "",
            f"# {payload.title or payload.video_id}",
            "",
            f"- Source URL: {payload.source_url}",
            f"- Channel: {payload.channel_title or payload.channel_id or 'unknown'}",
            f"- Published At: {published_at}",
            f"- Transcript Language: {payload.transcript_language or 'unknown'}",
            "",
            "## Digest",
            "",
            payload.digest_content.strip(),
            "",
        ]
        if payload.transcript_content and payload.transcript_content.strip():
            lines.extend(
                [
                    "## Transcript",
                    "",
                    payload.transcript_content.strip(),
                    "",
                ]
            )
        if payload.description and payload.description.strip():
            lines.extend(
                [
                    "## Video Description",
                    "",
                    payload.description.strip(),
                    "",
                ]
            )
        return "\n".join(lines)

    def _build_youtube_branch_name(
        self,
        assistant: AssistantConfig,
        payload: GitHubAssistantYouTubePublishRequest,
    ) -> str:
        prefix = assistant.branch_prefix.rstrip("/")
        if prefix.endswith("/issue"):
            prefix = prefix[: -len("/issue")] + "/youtube"
        elif prefix.endswith("issue"):
            prefix = prefix[: -len("issue")] + "youtube"
        else:
            prefix = f"{prefix}/youtube"
        slug = self._slugify(payload.title or payload.video_id) or payload.video_id
        return f"{prefix}/{payload.video_id}-{slug}"[:120]

    def _maybe_apply_issue_metadata(
        self,
        *,
        repo: str,
        issue_number: int,
        triage: TriageResult,
        policy: AssistantPolicy,
        warnings: list[str],
    ) -> None:
        if policy.allow_label and triage.suggested_labels:
            try:
                self._github.add_labels(repo, issue_number, triage.suggested_labels)
            except Exception as exc:
                warnings.append(f"failed to add labels: {exc}")
        if policy.allow_assign and triage.suggested_assignees:
            try:
                self._github.add_assignees(repo, issue_number, triage.suggested_assignees)
            except Exception as exc:
                warnings.append(f"failed to assign issue: {exc}")

    def _maybe_comment_links(
        self,
        *,
        repo: str,
        issue_number: int,
        issue_url: str,
        pr_url: str | None,
        run_dir: Path,
        policy: AssistantPolicy,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        if not policy.allow_comment:
            return results

        if pr_url:
            try:
                self._github.comment_issue(
                    repo,
                    issue_number,
                    "\n".join(
                        [
                            f"Draft PR opened: {pr_url}",
                            f"Run artifacts: `{self._relative_to_template_root(run_dir)}`",
                        ]
                    ),
                )
                results["issue_comment"] = "posted"
            except Exception as exc:
                results["issue_comment"] = f"failed: {exc}"

            pr_number = self._extract_pr_number(pr_url)
            if pr_number is not None:
                try:
                    self._github.comment_pr(
                        repo,
                        pr_number,
                        f"Linked issue: {issue_url}\nRun artifacts: `{self._relative_to_template_root(run_dir)}`",
                    )
                    results["pr_comment"] = "posted"
                except Exception as exc:
                    results["pr_comment"] = f"failed: {exc}"
        return results

    def _executor_available(self, assistant: AssistantConfig) -> bool:
        if self._executor_runner is not None:
            return True
        return self._executor_adapter.is_configured(assistant)

    def _review_pull_request(
        self,
        *,
        pr: GitHubPullRequest,
        repo_config: ManagedRepoConfig,
        assistant: AssistantConfig,
    ) -> PullRequestReviewResult:
        changed_files = [item.path for item in pr.files]
        blocked_files = [
            path for path in changed_files if not self._matches_any(path, repo_config.allowed_paths)
        ]
        risk_level: str = "low"
        if blocked_files or len(changed_files) > assistant.max_changed_files:
            risk_level = "high"
        elif len(changed_files) > max(3, assistant.max_changed_files // 2):
            risk_level = "medium"
        if any(path.startswith(".github/") or "security" in path.lower() for path in changed_files):
            risk_level = "high"
        summary = pr.title.strip() or f"PR #{pr.number}"
        if pr.body.strip():
            first_line = next((line.strip() for line in pr.body.splitlines() if line.strip()), "")
            if first_line:
                summary = f"{summary}: {first_line[:120]}"
        suggested_checks = [item for item in [repo_config.lint_command, repo_config.test_command] if item]
        return PullRequestReviewResult(
            repo=repo_config.repo,
            pr_number=pr.number,
            pr_url=pr.url,
            summary=summary,
            risk_level=risk_level,
            suggested_checks=suggested_checks,
            blocked_files=blocked_files,
            changed_files=changed_files,
        )

    def _build_release_plan(
        self,
        *,
        repo: str,
        merged_prs: list[Any],
        version: str | None,
    ) -> ReleasePlanResult:
        summary = f"{repo}: {len(merged_prs)} recently merged PRs ready for release planning."
        actions = [
            "Confirm the target version and tagging rule.",
            "Turn merged PR titles into release notes sections.",
            "Run the repo validation matrix before tagging.",
            "Publish the changelog and create the release entry.",
        ]
        return ReleasePlanResult(
            repo=repo,
            target_version=version,
            summary=summary,
            merged_prs=list(merged_prs),
            suggested_actions=actions,
        )

    def _directory_check(self, *, name: str, path: Path) -> DoctorCheck:
        if path.exists() and not path.is_dir():
            return DoctorCheck(
                name=name,
                status=DoctorStatus.FAIL,
                detail=f"{path} exists but is not a directory",
            )
        probe_root = path if path.exists() else path.parent
        while not probe_root.exists() and probe_root != probe_root.parent:
            probe_root = probe_root.parent
        try:
            writable = os.access(probe_root, os.W_OK)
        except Exception as exc:  # pragma: no cover - defensive
            return DoctorCheck(
                name=name,
                status=DoctorStatus.FAIL,
                detail=f"failed to probe {path}: {exc}",
            )
        if not writable:
            return DoctorCheck(
                name=name,
                status=DoctorStatus.FAIL,
                detail=f"{path} is not writable via {probe_root}",
            )
        return DoctorCheck(
            name=name,
            status=DoctorStatus.PASS,
            detail=str(path),
        )

    def _executor_check(self, assistant: AssistantConfig) -> DoctorCheck:
        if self._executor_runner is not None:
            return DoctorCheck(
                name="executor",
                status=DoctorStatus.PASS,
                detail="custom executor runner injected",
            )

        executor = assistant.executor
        if executor.command:
            return DoctorCheck(
                name="executor",
                status=DoctorStatus.PASS,
                detail=f"{executor.adapter} command configured",
            )

        if executor.adapter == "codex":
            binary = executor.binary or "codex"
            if self._binary_available(binary):
                return DoctorCheck(
                    name="executor",
                    status=DoctorStatus.PASS,
                    detail=f"codex binary available: {binary}",
                )
            return DoctorCheck(
                name="executor",
                status=DoctorStatus.FAIL,
                detail=f"codex binary not found: {binary}",
                hint="Install Codex CLI or set assistant.executor.command.",
            )

        if executor.adapter == "openhands":
            script = (self._repo_root / "scripts" / "openhands_start.sh").resolve()
            if script.exists():
                return DoctorCheck(
                    name="executor",
                    status=DoctorStatus.PASS,
                    detail=f"OpenHands launcher available: {script.relative_to(self._repo_root)}",
                )
            return DoctorCheck(
                name="executor",
                status=DoctorStatus.FAIL,
                detail=f"OpenHands launcher missing: {script}",
                hint="Restore scripts/openhands_start.sh or configure executor.command.",
            )

        return DoctorCheck(
            name="executor",
            status=DoctorStatus.FAIL,
            detail=f"{executor.adapter} executor requires assistant.executor.command",
            hint="Set assistant.executor.command or switch to codex/openhands.",
        )

    @staticmethod
    def _binary_available(binary: str) -> bool:
        candidate = binary.strip()
        if not candidate:
            return False
        if shutil.which(candidate):
            return True
        path = Path(candidate).expanduser()
        return path.exists() and os.access(path, os.X_OK)

    @staticmethod
    def _extract_pr_number(pr_url: str) -> int | None:
        matched = _PR_URL_RE.search(pr_url)
        if not matched:
            return None
        return int(matched.group("number"))

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        normalized = path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug[:48]

    @staticmethod
    def _build_github_env(profile: ResolvedGitHubAssistantProfile) -> dict[str, str]:
        if not profile.explicit:
            return {}
        return {
            "GH_CONFIG_DIR": str(profile.gh_config_dir),
        }
