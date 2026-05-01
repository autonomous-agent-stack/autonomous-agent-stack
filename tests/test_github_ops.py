from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_github_ops_service
from autoresearch.api.main import app
from autoresearch.core.services.approval_decisions import ApprovalDecisionService
from autoresearch.core.services.approval_policy import ApprovalPolicyService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.github_ops import GitHubOpsRequest, GitHubOpsService
from autoresearch.github_assistant.models import GitHubIssue, GitHubPullRequest, GitHubPullRequestFile
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    JobStatus,
    WorkerQueueItemRead,
    WorkerQueueName,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import InMemoryRepository
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.executor import MacWorkerExecutor


class _FakeGitHubOpsGateway:
    def __init__(self) -> None:
        self.issue_comments: list[tuple[str, int, str]] = []
        self.pr_comments: list[tuple[str, int, str]] = []
        self.labels: list[tuple[str, int, tuple[str, ...]]] = []

    def is_installed(self) -> bool:
        return True

    def auth_status(self) -> bool:
        return True

    def current_login(self) -> str:
        return "ops-bot"

    def repo_accessible(self, repo: str) -> bool:
        return repo == "acme/demo"

    def fetch_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        return GitHubIssue(
            repo=repo,
            number=issue_number,
            title="Fix flaky worker",
            body="Worker reports twice.",
            url=f"https://github.com/{repo}/issues/{issue_number}",
            state="OPEN",
            author="alice",
            labels=["bug"],
        )

    def fetch_pull_request(self, repo: str, pr_number: int) -> GitHubPullRequest:
        return GitHubPullRequest(
            repo=repo,
            number=pr_number,
            title="Add GitHub ops",
            body="Adds safe ops.",
            url=f"https://github.com/{repo}/pull/{pr_number}",
            state="OPEN",
            author="bob",
            base_ref="main",
            head_ref="feature/github-ops",
            labels=["enhancement"],
            files=[GitHubPullRequestFile(path="src/app.py", additions=12, deletions=3)],
        )

    def fetch_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, object]]:
        return [{"name": "tests", "state": "COMPLETED", "conclusion": "SUCCESS"}]

    def comment_issue(self, repo: str, issue_number: int, body: str) -> None:
        self.issue_comments.append((repo, issue_number, body))

    def comment_pr(self, repo: str, pr_number: int, body: str) -> None:
        self.pr_comments.append((repo, pr_number, body))

    def add_labels(self, repo: str, issue_number: int, labels: list[str]) -> None:
        self.labels.append((repo, issue_number, tuple(labels)))


def _write_configs(root: Path) -> None:
    account_dir = root / "configs" / "github_accounts"
    account_dir.mkdir(parents=True)
    (account_dir / "accountA.yaml").write_text(
        """
profile_id: "github_accountA"
auth:
  token_env: "GITHUB_TOKEN_ACCOUNT_A"
  fallback_token_env: "GITHUB_TOKEN"
defaults:
  allowed_repos: ["acme/demo"]
  allowed_owners: []
""".strip(),
        encoding="utf-8",
    )
    (root / "approval_policy.yaml").write_text(
        """
actions:
  github.pr_ops:summarize_pr:
    decision: "auto"
    risk: "read"
    reason: "read-only"
  github.issue_ops:add_comment:
    decision: "approval_required"
    risk: "external"
    required_role: "supervisor"
    reason: "comment write"
  github.pr_ops:add_label:
    decision: "approval_required"
    risk: "external"
    required_role: "supervisor"
    reason: "label write"
  github.pr_ops:merge_pr:
    decision: "blocked"
    risk: "destructive"
    reason: "merge blocked"
""".strip(),
        encoding="utf-8",
    )


def _build_service(root: Path, gateway: _FakeGitHubOpsGateway, approval_store: ApprovalStoreService | None = None) -> GitHubOpsService:
    _write_configs(root)
    return GitHubOpsService(
        repo_root=root,
        approval_policy=ApprovalPolicyService(policy_path=root / "approval_policy.yaml"),
        approval_store=approval_store or ApprovalStoreService(repository=InMemoryRepository()),
        gateway_factory=lambda _profile: gateway,
    )


def test_github_ops_summarizes_pr_and_writes_artifacts(tmp_path: Path) -> None:
    gateway = _FakeGitHubOpsGateway()
    service = _build_service(tmp_path, gateway)

    result = service.execute(GitHubOpsRequest(action="summarize_pr", repo="acme/demo", pr_number=7))

    assert result.status == "completed"
    assert result.approval_policy == "auto"
    assert "PR #7" in result.summary
    assert result.artifacts
    assert Path(result.artifacts[0]).exists()


def test_github_ops_comment_waits_for_approval_then_executes(tmp_path: Path) -> None:
    gateway = _FakeGitHubOpsGateway()
    approval_store = ApprovalStoreService(repository=InMemoryRepository())
    service = _build_service(tmp_path, gateway, approval_store)

    result = service.execute(
        GitHubOpsRequest(
            action="add_comment",
            repo="acme/demo",
            issue_number=9,
            comment="Looks scoped.",
            metadata={"telegram_uid": "9527"},
        )
    )

    assert result.status == "approval_required"
    assert result.approval_id
    assert gateway.issue_comments == []

    approval = approval_store.get_request(result.approval_id)
    assert approval is not None
    decision_service = ApprovalDecisionService(
        approval_store=approval_store,
        github_ops_service=service,
    )
    resolved = decision_service.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(decision="approved", decided_by="9527"),
    )

    assert resolved.status.value == "approved"
    assert gateway.issue_comments == [("acme/demo", 9, "Looks scoped.")]
    assert resolved.metadata["github_ops_executed"] is True


def test_github_ops_blocks_unsupported_write_actions(tmp_path: Path) -> None:
    gateway = _FakeGitHubOpsGateway()
    service = _build_service(tmp_path, gateway)

    result = service.execute(GitHubOpsRequest(action="merge_pr", repo="acme/demo", pr_number=7))

    assert result.status == "blocked"
    assert result.risk == "destructive"


def test_github_ops_api_execute_route(tmp_path: Path) -> None:
    gateway = _FakeGitHubOpsGateway()
    service = _build_service(tmp_path, gateway)
    app.dependency_overrides[get_github_ops_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/github-ops/execute",
                json={"action": "read_issue", "repo": "acme/demo", "issue_number": 3},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["data"]["issue"]["number"] == 3
    finally:
        app.dependency_overrides.pop(get_github_ops_service, None)


def test_mac_executor_runs_github_ops_task(tmp_path: Path) -> None:
    gateway = _FakeGitHubOpsGateway()
    service = _build_service(tmp_path, gateway)
    config = MacWorkerConfig(
        worker_id="mac-test",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Mac Test",
        host="localhost",
        housekeeping_root=tmp_path,
    )
    executor = MacWorkerExecutor(config, github_ops=service)
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="wr_github_ops_1",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="github_ops",
        task_type=WorkerTaskType.GITHUB_OPS,
        payload={"action": "read_pr", "repo": "acme/demo", "pr_number": 7},
        status=JobStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )

    result = executor.execute(run)

    assert result.status == JobStatus.COMPLETED
    assert result.result["status"] == "completed"
    assert result.metrics["github_ops_status"] == "completed"
