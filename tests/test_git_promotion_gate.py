from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from autoresearch.core.services.git_promotion_gate import (
    GitPromotionCreateRequest,
    GitPromotionGateService,
    GitPromotionService,
)
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    GitPromotionMode,
    GitRemoteProbe,
    PromotionActorRole,
    PromotionIntent,
)


class FakeGitPromotionProvider:
    def __init__(self, probe: GitRemoteProbe) -> None:
        self.probe = probe
        self.branch_calls: list[tuple[str, str]] = []
        self.commit_calls: list[tuple[str, str, tuple[str, ...]]] = []
        self.push_calls: list[str] = []
        self.pr_calls: list[tuple[str, str, str]] = []

    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe:
        _ = repo_root, base_branch
        return self.probe

    def create_branch(
        self,
        repo_root: Path,
        *,
        branch_name: str,
        base_branch: str,
        workspace_dir: Path,
    ) -> None:
        _ = repo_root
        workspace_dir.mkdir(parents=True, exist_ok=True)
        self.branch_calls.append((branch_name, base_branch))

    def commit_changes(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        patch_uri: Path,
        changed_files: list[str],
        commit_message: str,
        validator_commands: list[str] | None = None,
        validator_log_dir: Path | None = None,
    ) -> str:
        _ = repo_root, workspace_dir, patch_uri, changed_files, validator_log_dir
        self.commit_calls.append((branch_name, commit_message, tuple(validator_commands or [])))
        return "abc123def456"

    def push_branch(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
    ) -> None:
        _ = repo_root, workspace_dir
        self.push_calls.append(branch_name)

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str:
        _ = repo_root, workspace_dir
        self.pr_calls.append((branch_name, base_branch, title))
        return f"https://example.invalid/{branch_name}?base={base_branch}&body={body}"


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def _init_repo(repo_root: Path) -> None:
    _git(repo_root, "init", "-b", "main")
    _git(repo_root, "config", "user.email", "tests@example.com")
    _git(repo_root, "config", "user.name", "Tests")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "initial")


def _write_patch(root: Path, *, filename: str = "src/demo.py") -> Path:
    patch_path = root / "promotion.patch"
    patch_path.write_text(
        "\n".join(
            [
                f"diff --git a/{filename} b/{filename}",
                "new file mode 100644",
                "index 0000000..1111111",
                "--- /dev/null",
                f"+++ b/{filename}",
                "@@ -0,0 +1 @@",
                '+print("hello")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return patch_path


def _intent(
    patch_path: Path,
    *,
    run_id: str = "run-demo",
    preferred_mode: GitPromotionMode = GitPromotionMode.PATCH,
    actor_role: PromotionActorRole = PromotionActorRole.AGGREGATOR,
    approval_granted: bool = False,
    branch_name: str = "codex/demo",
    writer_lease_key: str | None = None,
    validator_commands: list[str] | None = None,
) -> PromotionIntent:
    return PromotionIntent(
        run_id=run_id,
        actor_role=actor_role,
        actor_id="aggregator-1",
        writer_id="worker-1",
        writer_lease_key=writer_lease_key or f"writer:{run_id}",
        patch_uri=str(patch_path),
        changed_files=["src/demo.py"],
        base_ref="HEAD",
        preferred_mode=preferred_mode,
        target_base_branch="main",
        approval_granted=approval_granted,
        metadata={
            "branch_name": branch_name,
            "commit_message": f"Promote {run_id}",
            "pr_title": f"Promote {run_id}",
            "pr_body": "Automated promotion draft PR.",
            "validator_commands": validator_commands or [],
        },
    )


def _prepare_promotion_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    source = repo_root / "src" / "base.py"
    source.write_text("value = 1\n", encoding="utf-8")
    _init_repo(repo_root)

    source.write_text("value = 2\n", encoding="utf-8")
    patch_text = _git(repo_root, "diff", "--", "src/base.py")
    _git(repo_root, "checkout", "--", "src/base.py")

    runtime_root = tmp_path / ".masfactory_runtime"
    run_dir = runtime_root / "runs" / "run_promotion"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "promotion.patch").write_text(patch_text, encoding="utf-8")
    (run_dir / "summary.json").write_text(
        """
{
  "run_id": "run_promotion",
  "final_status": "ready_for_promotion",
  "driver_result": {
    "protocol_version": "aep/v0",
    "run_id": "run_promotion",
    "agent_id": "mock",
    "attempt": 1,
    "status": "succeeded",
    "summary": "ok",
    "changed_paths": ["src/base.py"],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": 1, "commands": 0, "prompt_tokens": null, "completion_tokens": null},
    "recommended_action": "promote",
    "error": null
  },
  "validation": {
    "run_id": "run_promotion",
    "passed": true,
    "checks": []
  },
  "promotion_patch_uri": "artifacts/promotion.patch",
  "promotion_preflight": null,
  "promotion": null
}
        """.strip(),
        encoding="utf-8",
    )
    (run_dir / "job.json").write_text(
        '{"run_id":"run_promotion","agent_id":"mock","task":"Update base value"}',
        encoding="utf-8",
    )
    return repo_root, runtime_root


def test_finalize_defaults_to_patch_when_patch_gates_pass(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"

    service = GitPromotionGateService(repo_root=tmp_path)
    preflight, result = service.finalize(
        intent=_intent(patch_path),
        artifacts_dir=artifacts_dir,
    )

    assert preflight.allowed is True
    assert preflight.requested_mode is GitPromotionMode.PATCH
    assert preflight.effective_mode is GitPromotionMode.PATCH
    assert result.success is True
    assert result.mode is GitPromotionMode.PATCH
    assert result.pr_url is None
    assert (artifacts_dir / "promotion_preflight.json").exists()
    assert (artifacts_dir / "promotion_result.json").exists()


def test_finalize_upgrades_patch_to_draft_pr_when_all_preconditions_pass(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    provider = FakeGitPromotionProvider(
        GitRemoteProbe(
            remote_name="origin",
            remote_url="git@example.invalid/repo.git",
            healthy=True,
            credentials_available=True,
            base_branch_exists=True,
        )
    )
    service = GitPromotionGateService(repo_root=tmp_path, provider=provider)

    preflight, result = service.finalize(
        intent=_intent(
            patch_path,
            preferred_mode=GitPromotionMode.DRAFT_PR,
            approval_granted=True,
            branch_name="codex/demo-upgrade",
            validator_commands=["pytest -q tests/test_demo.py"],
        ),
        artifacts_dir=artifacts_dir,
    )

    assert preflight.allowed is True
    assert preflight.effective_mode is GitPromotionMode.DRAFT_PR
    assert result.success is True
    assert result.mode is GitPromotionMode.DRAFT_PR
    assert result.branch_name == "codex/demo-upgrade"
    assert result.commit_sha == "abc123def456"
    assert result.pr_url is not None
    assert provider.branch_calls == [("codex/demo-upgrade", "main")]
    assert provider.commit_calls == [
        ("codex/demo-upgrade", "Promote run-demo", ("pytest -q tests/test_demo.py",))
    ]
    assert provider.pr_calls == [("codex/demo-upgrade", "main", "Promote run-demo")]


def test_finalize_falls_back_to_patch_when_draft_pr_preconditions_are_unmet(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    provider = FakeGitPromotionProvider(
        GitRemoteProbe(
            remote_name="origin",
            remote_url="git@example.invalid/repo.git",
            healthy=True,
            credentials_available=False,
            base_branch_exists=True,
            reason="gh auth status failed",
        )
    )
    service = GitPromotionGateService(repo_root=tmp_path, provider=provider)

    preflight, result = service.finalize(
        intent=_intent(
            patch_path,
            preferred_mode=GitPromotionMode.DRAFT_PR,
            approval_granted=True,
        ),
        artifacts_dir=artifacts_dir,
    )

    assert preflight.allowed is True
    assert preflight.effective_mode is GitPromotionMode.PATCH
    assert "credentials available" in (preflight.reason or "")
    assert result.success is True
    assert result.mode is GitPromotionMode.PATCH
    assert result.pr_url is None
    assert provider.branch_calls == []
    assert provider.commit_calls == []
    assert provider.pr_calls == []


def test_finalize_falls_back_to_patch_when_base_repo_is_dirty(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "base.py").write_text("value = 1\n", encoding="utf-8")
    _init_repo(repo_root)
    (repo_root / "README.md").write_text("dirty\n", encoding="utf-8")

    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    provider = FakeGitPromotionProvider(
        GitRemoteProbe(
            remote_name="origin",
            remote_url="git@example.invalid/repo.git",
            healthy=True,
            credentials_available=True,
            base_branch_exists=True,
        )
    )
    service = GitPromotionGateService(repo_root=repo_root, provider=provider)

    preflight, result = service.finalize(
        intent=_intent(
            patch_path,
            preferred_mode=GitPromotionMode.DRAFT_PR,
            approval_granted=True,
        ),
        artifacts_dir=artifacts_dir,
    )

    checks = {item.id: item for item in preflight.checks}
    assert preflight.allowed is True
    assert preflight.effective_mode is GitPromotionMode.PATCH
    assert "clean base repository" in (preflight.reason or "")
    assert checks["draft_pr.clean_base_repo"].passed is False
    assert result.success is True
    assert result.mode is GitPromotionMode.PATCH
    assert provider.branch_calls == []


def test_finalize_rejects_non_aggregator_actor(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    service = GitPromotionGateService(repo_root=tmp_path)

    with pytest.raises(PermissionError, match="only aggregator can finalize"):
        service.finalize(
            intent=_intent(patch_path, actor_role=PromotionActorRole.WORKER),
            artifacts_dir=tmp_path / "artifacts",
        )


def test_finalize_blocks_when_writer_lease_is_already_held(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    writer_lease = WriterLeaseService()
    service = GitPromotionGateService(repo_root=tmp_path, writer_lease=writer_lease)
    intent = _intent(patch_path, run_id="run-held")

    with writer_lease.acquire("writer:run-held"):
        preflight, result = service.finalize(
            intent=intent,
            artifacts_dir=artifacts_dir,
        )

    checks = {item.id: item for item in preflight.checks}
    assert preflight.allowed is False
    assert result.success is False
    assert result.mode is None
    assert checks["gate.writer_lease_available"].passed is False


def test_finalize_rejects_main_branch_as_promotion_target(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    service = GitPromotionGateService(repo_root=tmp_path)

    preflight, result = service.finalize(
        intent=_intent(patch_path, branch_name="main"),
        artifacts_dir=artifacts_dir,
    )

    checks = {item.id: item for item in preflight.checks}
    assert preflight.allowed is False
    assert result.success is False
    assert result.mode is None
    assert checks["gate.no_main_write"].passed is False


def test_finalize_allows_only_one_result_per_run(tmp_path: Path) -> None:
    patch_path = _write_patch(tmp_path)
    artifacts_dir = tmp_path / "artifacts"
    service = GitPromotionGateService(repo_root=tmp_path)
    intent = _intent(patch_path, run_id="run-once")

    _, result = service.finalize(intent=intent, artifacts_dir=artifacts_dir)

    assert result.success is True
    with pytest.raises(ValueError, match="already finalized"):
        service.finalize(intent=intent, artifacts_dir=artifacts_dir)


def test_worktree_paths_include_repo_hash_salt_for_same_named_repositories(tmp_path: Path) -> None:
    repo_root_a = tmp_path / "alpha" / "repo"
    repo_root_b = tmp_path / "beta" / "repo"
    repo_root_a.mkdir(parents=True)
    repo_root_b.mkdir(parents=True)

    gate_a = GitPromotionGateService(repo_root=repo_root_a)
    gate_b = GitPromotionGateService(repo_root=repo_root_b)
    promotion_a = GitPromotionService(repo_root=repo_root_a, runtime_root=tmp_path / "runtime-a")
    promotion_b = GitPromotionService(repo_root=repo_root_b, runtime_root=tmp_path / "runtime-b")

    expected_hash_a = hashlib.sha256(str(repo_root_a.resolve()).encode("utf-8")).hexdigest()[:8]
    expected_hash_b = hashlib.sha256(str(repo_root_b.resolve()).encode("utf-8")).hexdigest()[:8]

    gate_path_a = gate_a._worktree_path("run-demo")
    gate_path_b = gate_b._worktree_path("run-demo")
    assert gate_path_a != gate_path_b
    assert gate_path_a.parts[:4] == ("/", "tmp", f"repo-{expected_hash_a}", "promotion-worktrees")
    assert gate_path_b.parts[:4] == ("/", "tmp", f"repo-{expected_hash_b}", "promotion-worktrees")

    promotion_path_a = promotion_a._promotion_worktree_path("promotion-1")
    promotion_path_b = promotion_b._promotion_worktree_path("promotion-1")
    assert promotion_path_a != promotion_path_b
    assert promotion_path_a.parts[:4] == ("/", "tmp", f"repo-{expected_hash_a}", "promotions")
    assert promotion_path_b.parts[:4] == ("/", "tmp", f"repo-{expected_hash_b}", "promotions")


def test_git_promotion_service_creates_branch_commit_and_draft_pr_payload(tmp_path: Path) -> None:
    repo_root, runtime_root = _prepare_promotion_repo(tmp_path)
    service = GitPromotionService(repo_root=repo_root, runtime_root=runtime_root)

    record = service.promote(
        GitPromotionCreateRequest(
            run_id="run_promotion",
            base_ref="main",
            validator_commands=[
                "python -c \"from pathlib import Path; assert 'value = 2' in Path('src/base.py').read_text()\""
            ],
            push_branch=False,
            open_draft_pr=False,
        )
    )

    assert record.status == "completed"
    assert record.branch_name is not None
    assert record.branch_name.startswith("codex/auto-upgrade/")
    assert record.commit_sha
    assert "gh pr create --draft" in record.draft_pr_command

    promoted = _git(repo_root, "show", f"{record.branch_name}:src/base.py")
    assert promoted.strip() == "value = 2"


def test_git_promotion_service_rejects_dirty_repository(tmp_path: Path) -> None:
    repo_root, runtime_root = _prepare_promotion_repo(tmp_path)
    (repo_root / "README.md").write_text("dirty\n", encoding="utf-8")
    service = GitPromotionService(repo_root=repo_root, runtime_root=runtime_root)

    with pytest.raises(ValueError, match="worktree is not clean"):
        service.promote(GitPromotionCreateRequest(run_id="run_promotion"))
