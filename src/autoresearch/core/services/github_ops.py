from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from autoresearch.core.services.approval_policy import ApprovalPolicyDecision, ApprovalPolicyService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.github_assistant.gh import GhCliGateway
from autoresearch.github_assistant.models import GitHubIssue, GitHubPullRequest
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    SessionEventRead,
    StrictModel,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


GITHUB_OPS_APPROVAL_ACTION = "github_ops"
_READ_ACTIONS = {"read_issue", "read_pr", "read_checks", "summarize_pr"}
_WRITE_ACTIONS = {"add_comment", "add_label"}
_BLOCKED_ACTIONS = {"merge_pr", "push_commit", "delete_branch", "repo_settings", "close_issue"}


class GitHubOpsRequest(StrictModel):
    action: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=3)
    issue_number: int | None = Field(default=None, ge=1)
    pr_number: int | None = Field(default=None, ge=1)
    comment: str | None = None
    labels: list[str] = Field(default_factory=list)
    account_profile: str = "accountA"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", "repo", "account_profile", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("comment", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return [str(item).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def _normalize_action(self) -> GitHubOpsRequest:
        aliases = {
            "github_ops.issue_ops": "read_issue",
            "github.issue_ops": "read_issue",
            "github_ops.pr_ops": "summarize_pr",
            "github.pr_ops": "summarize_pr",
            "github_ops.checks": "read_checks",
        }
        normalized = aliases.get(self.action.strip().lower(), self.action.strip().lower())
        self.action = normalized
        return self


class GitHubOpsResult(StrictModel):
    status: Literal["completed", "approval_required", "blocked", "failed"]
    account_profile: str
    action: str
    repo: str
    issue_number: int | None = None
    pr_number: int | None = None
    approval_id: str | None = None
    approval_policy: str = "auto"
    risk: str = "read"
    summary: str = ""
    reason: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubOpsGateway(Protocol):
    def is_installed(self) -> bool: ...
    def auth_status(self) -> bool: ...
    def current_login(self) -> str | None: ...
    def repo_accessible(self, repo: str) -> bool: ...
    def fetch_issue(self, repo: str, issue_number: int) -> GitHubIssue: ...
    def fetch_pull_request(self, repo: str, pr_number: int) -> GitHubPullRequest: ...
    def fetch_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, Any]]: ...
    def comment_issue(self, repo: str, issue_number: int, body: str) -> None: ...
    def comment_pr(self, repo: str, pr_number: int, body: str) -> None: ...
    def add_labels(self, repo: str, issue_number: int, labels: list[str]) -> None: ...


class GitHubOpsService:
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        approval_policy: ApprovalPolicyService | None = None,
        approval_store: ApprovalStoreService | None = None,
        gateway_factory: Any | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        self._approval_policy = approval_policy or ApprovalPolicyService(
            policy_path=self._repo_root / "configs" / "approval_policy.yaml"
        )
        self._approval_store = approval_store
        self._gateway_factory = gateway_factory

    def doctor(self, *, account_profile: str = "accountA") -> dict[str, Any]:
        try:
            gateway = self._build_gateway(account_profile)
            gh_installed = gateway.is_installed()
            auth_ok = gateway.auth_status() if gh_installed else False
            active_login = gateway.current_login() if auth_ok else None
            return {
                "status": "ok" if gh_installed and auth_ok else "degraded",
                "account_profile": account_profile,
                "gh_installed": gh_installed,
                "gh_auth_ok": auth_ok,
                "active_login": active_login,
                "approval_policy": self._approval_policy.doctor(),
            }
        except Exception as exc:
            return {
                "status": "fail",
                "account_profile": account_profile,
                "error": str(exc).strip() or exc.__class__.__name__,
            }

    def execute(self, request: GitHubOpsRequest) -> GitHubOpsResult:
        request = GitHubOpsRequest.model_validate(request.model_dump(mode="json"))
        policy = self._approval_policy.decide(
            task_type=self._canonical_task_type(request),
            action=request.action,
            metadata=request.metadata,
        )
        if request.action in _BLOCKED_ACTIONS or policy.decision == "blocked":
            return self._result(
                request,
                status="blocked",
                policy=policy,
                summary="GitHub action blocked by policy.",
                reason=policy.reason,
            )
        if request.action not in _READ_ACTIONS | _WRITE_ACTIONS:
            return self._result(
                request,
                status="blocked",
                policy=policy,
                summary="Unsupported GitHub ops action.",
                reason=f"unsupported action: {request.action}",
            )
        if policy.decision == "approval_required" and not request.metadata.get("approval_granted"):
            approval = self._create_approval(request, policy)
            return self._write_artifacts(
                self._result(
                    request,
                    status="approval_required",
                    policy=policy,
                    approval_id=approval.approval_id,
                    summary="GitHub action is waiting for approval.",
                    reason=policy.reason,
                    metadata={"approval_id": approval.approval_id},
                )
            )

        try:
            result = self._execute_allowed(request, policy)
        except Exception as exc:
            result = self._result(
                request,
                status="failed",
                policy=policy,
                summary="GitHub ops action failed.",
                reason=str(exc).strip() or exc.__class__.__name__,
            )
        return self._write_artifacts(result)

    def execute_approved_approval(self, approval: ApprovalRequestRead) -> GitHubOpsResult:
        payload = approval.metadata.get("github_ops_payload")
        if not isinstance(payload, dict):
            raise ValueError("approval is missing github_ops_payload")
        request = GitHubOpsRequest.model_validate(
            {
                **payload,
                "metadata": {
                    **dict(payload.get("metadata") or {}),
                    "approval_granted": True,
                    "approval_id": approval.approval_id,
                    "approved_by": approval.decided_by,
                },
            }
        )
        return self.execute(request)

    def _execute_allowed(self, request: GitHubOpsRequest, policy: ApprovalPolicyDecision) -> GitHubOpsResult:
        self._validate_account_scope(request)
        gateway = self._build_gateway(request.account_profile)
        if not gateway.repo_accessible(request.repo):
            raise RuntimeError(f"GitHub repo is not accessible: {request.repo}")

        if request.action == "read_issue":
            issue_number = self._require_issue_number(request)
            issue = gateway.fetch_issue(request.repo, issue_number)
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=f"Read GitHub issue #{issue.number}: {issue.title}",
                data={"issue": issue.model_dump(mode="json")},
            )
        if request.action == "read_pr":
            pr_number = self._require_pr_number(request)
            pr = gateway.fetch_pull_request(request.repo, pr_number)
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=f"Read GitHub PR #{pr.number}: {pr.title}",
                data={"pull_request": pr.model_dump(mode="json")},
            )
        if request.action == "read_checks":
            pr_number = self._require_pr_number(request)
            checks = gateway.fetch_pr_checks(request.repo, pr_number)
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=f"Read GitHub PR checks for #{pr_number}.",
                data={"checks": checks},
            )
        if request.action == "summarize_pr":
            pr_number = self._require_pr_number(request)
            pr = gateway.fetch_pull_request(request.repo, pr_number)
            checks = gateway.fetch_pr_checks(request.repo, pr_number)
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=self._summarize_pr(pr, checks),
                data={"pull_request": pr.model_dump(mode="json"), "checks": checks},
            )
        if request.action == "add_comment":
            comment = (request.comment or "").strip()
            if not comment:
                raise ValueError("comment is required")
            if request.pr_number is not None:
                gateway.comment_pr(request.repo, request.pr_number, comment)
                target = f"PR #{request.pr_number}"
            else:
                issue_number = self._require_issue_number(request)
                gateway.comment_issue(request.repo, issue_number, comment)
                target = f"issue #{issue_number}"
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=f"Posted GitHub comment to {target}.",
                data={"comment_posted": True, "target": target},
            )
        if request.action == "add_label":
            labels = list(request.labels)
            if not labels:
                raise ValueError("labels are required")
            target_number = request.pr_number or self._require_issue_number(request)
            gateway.add_labels(request.repo, target_number, labels)
            return self._result(
                request,
                status="completed",
                policy=policy,
                summary=f"Added GitHub labels to #{target_number}: {', '.join(labels)}",
                data={"labels_added": labels, "target_number": target_number},
            )
        raise ValueError(f"unsupported action: {request.action}")

    def _create_approval(self, request: GitHubOpsRequest, policy: ApprovalPolicyDecision) -> ApprovalRequestRead:
        if self._approval_store is None:
            raise RuntimeError("ApprovalStoreService is required for approval-gated GitHub ops")
        telegram_uid = str(
            request.metadata.get("telegram_uid")
            or request.metadata.get("actor_user_id")
            or request.metadata.get("chat_id")
            or ""
        ).strip() or None
        title = f"审批 GitHub 操作 / Approve GitHub action: {request.action}"
        summary = "\n".join(
            [
                f"仓库 / Repo: {request.repo}",
                f"操作 / Action: {request.action}",
                f"原因 / Reason: {policy.reason}",
            ]
        )
        return self._approval_store.create_request(
            ApprovalRequestCreateRequest(
                title=title,
                summary=summary,
                risk=policy.risk,
                source="github_ops",
                telegram_uid=telegram_uid,
                session_id=str(request.metadata.get("session_id") or "").strip() or None,
                agent_run_id=str(request.metadata.get("run_id") or "").strip() or None,
                metadata={
                    "action_type": GITHUB_OPS_APPROVAL_ACTION,
                    "approval_policy": policy.decision,
                    "required_role": policy.required_role,
                    "canonical_task_type": self._canonical_task_type(request),
                    "github_ops_payload": request.model_dump(mode="json"),
                },
            )
        )

    def _build_gateway(self, account_profile: str) -> GitHubOpsGateway:
        if self._gateway_factory is not None:
            return self._gateway_factory(account_profile)
        account = self._load_account_config(account_profile)
        auth = dict(account.get("auth") or {})
        env: dict[str, str] = {}
        token_env = str(auth.get("token_env") or "").strip()
        fallback_token_env = str(auth.get("fallback_token_env") or "").strip()
        token = os.getenv(token_env) if token_env else None
        token = token or (os.getenv(fallback_token_env) if fallback_token_env else None)
        if token:
            env["GITHUB_TOKEN"] = token
            env["GH_TOKEN"] = token
        return GhCliGateway(repo_root=self._repo_root, env=env)

    def _load_account_config(self, account_profile: str) -> dict[str, Any]:
        profile = account_profile.strip()
        candidates = [profile]
        if profile.startswith("github_"):
            candidates.append(profile.removeprefix("github_"))
        for candidate in candidates:
            path = self._repo_root / "configs" / "github_accounts" / f"{candidate}.yaml"
            if path.exists():
                return load_yaml_object(path)
        raise FileNotFoundError(f"github account config not found: {account_profile}")

    def _validate_account_scope(self, request: GitHubOpsRequest) -> None:
        account = self._load_account_config(request.account_profile)
        defaults = dict(account.get("defaults") or {})
        allowed_repos = [str(item).strip() for item in defaults.get("allowed_repos") or [] if str(item).strip()]
        allowed_owners = [str(item).strip() for item in defaults.get("allowed_owners") or [] if str(item).strip()]
        if allowed_repos and request.repo not in allowed_repos:
            raise PermissionError(f"repo is not allowlisted for {request.account_profile}: {request.repo}")
        owner = request.repo.split("/", 1)[0]
        if allowed_owners and owner not in allowed_owners:
            raise PermissionError(f"owner is not allowlisted for {request.account_profile}: {owner}")

    def _write_artifacts(self, result: GitHubOpsResult) -> GitHubOpsResult:
        run_dir = self._repo_root / "artifacts" / "github_ops" / f"{utc_now().strftime('%Y%m%dT%H%M%SZ')}-{result.action}"
        run_dir.mkdir(parents=True, exist_ok=True)
        result_path = run_dir / "github_ops_result.json"
        summary_path = run_dir / "github_ops_summary.md"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        summary_path.write_text(self._render_summary(result), encoding="utf-8")
        return result.model_copy(
            update={
                "artifacts": [str(result_path), str(summary_path)],
                "metadata": {**result.metadata, "run_dir": str(run_dir)},
            }
        )

    @staticmethod
    def _render_summary(result: GitHubOpsResult) -> str:
        lines = [
            "# GitHub Ops Summary",
            "",
            f"- status: {result.status}",
            f"- account_profile: {result.account_profile}",
            f"- repo: {result.repo}",
            f"- action: {result.action}",
            f"- approval_policy: {result.approval_policy}",
            f"- summary: {result.summary}",
        ]
        if result.reason:
            lines.append(f"- reason: {result.reason}")
        if result.approval_id:
            lines.append(f"- approval_id: {result.approval_id}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _summarize_pr(pr: GitHubPullRequest, checks: list[dict[str, Any]]) -> str:
        changed = len(pr.files)
        additions = sum(item.additions for item in pr.files)
        deletions = sum(item.deletions for item in pr.files)
        failed_checks = [
            str(item.get("name") or item.get("context") or "unknown")
            for item in checks
            if str(item.get("conclusion") or item.get("state") or "").lower() in {"failure", "failed", "error"}
        ]
        check_text = "all checks passing or unavailable" if not failed_checks else f"failing checks: {', '.join(failed_checks)}"
        return (
            f"PR #{pr.number} {pr.title} changes {changed} files "
            f"(+{additions}/-{deletions}); {check_text}."
        )

    @staticmethod
    def _canonical_task_type(request: GitHubOpsRequest) -> str:
        if request.pr_number is not None or request.action in {"read_pr", "read_checks", "summarize_pr"}:
            return "github.pr_ops"
        return "github.issue_ops"

    @staticmethod
    def _require_issue_number(request: GitHubOpsRequest) -> int:
        if request.issue_number is None:
            raise ValueError("issue_number is required")
        return request.issue_number

    @staticmethod
    def _require_pr_number(request: GitHubOpsRequest) -> int:
        if request.pr_number is None:
            raise ValueError("pr_number is required")
        return request.pr_number

    @staticmethod
    def _result(
        request: GitHubOpsRequest,
        *,
        status: Literal["completed", "approval_required", "blocked", "failed"],
        policy: ApprovalPolicyDecision,
        summary: str,
        reason: str | None = None,
        approval_id: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GitHubOpsResult:
        return GitHubOpsResult(
            status=status,
            account_profile=request.account_profile,
            action=request.action,
            repo=request.repo,
            issue_number=request.issue_number,
            pr_number=request.pr_number,
            approval_id=approval_id,
            approval_policy=policy.decision,
            risk=policy.risk.value,
            summary=summary,
            reason=reason,
            data=data or {},
            metadata={**request.metadata, **dict(metadata or {})},
        )


def build_default_github_ops_service(*, repo_root: Path | None = None) -> GitHubOpsService:
    from autoresearch.api.settings import get_runtime_settings
    from autoresearch.core.services.session_events import SessionEventService

    root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
    db_path = get_runtime_settings().api_db_path
    approval_store = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests",
            model_cls=ApprovalRequestRead,
        ),
        session_events=SessionEventService(
            repository=SQLiteModelRepository(
                db_path=db_path,
                table_name="session_events",
                model_cls=SessionEventRead,
            )
        ),
    )
    return GitHubOpsService(repo_root=root, approval_store=approval_store)
