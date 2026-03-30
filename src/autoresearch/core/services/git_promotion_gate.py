from __future__ import annotations

from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from autoresearch.agent_protocol.models import ExecutionPolicy, RunSummary, ValidationCheck
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    GitPromotionMode,
    GitRemoteProbe,
    JobStatus,
    PromotionActorRole,
    PromotionDiffStats,
    PromotionGateCheck,
    PromotionIntent,
    PromotionPreflight,
    PromotionResult,
    StrictModel,
    utc_now,
)
from autoresearch.shared.store import Repository, SQLiteModelRepository, create_resource_id

_RUNTIME_DENY_PREFIXES = (
    "logs/",
    ".masfactory_runtime/",
    "memory/",
    ".git/",
)

_TRACE_STDIO_TAIL_CHARS = 4000


def _is_benign_runtime_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    if not normalized:
        return False
    if normalized.startswith(".pytest_cache/") or "/.pytest_cache/" in f"/{normalized}":
        return True
    if "/__pycache__/" in f"/{normalized}":
        return True
    if normalized.startswith("apps/") and normalized.endswith("/README.md"):
        return True
    return False


class GitPromotionProvider(Protocol):
    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe: ...

    def create_branch(
        self,
        repo_root: Path,
        *,
        branch_name: str,
        base_branch: str,
        workspace_dir: Path,
    ) -> None: ...

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
    ) -> str: ...

    def push_branch(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
    ) -> None: ...

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str: ...


class CliGitPromotionProvider:
    def _record_step(
        self,
        *,
        trace: list[dict[str, Any]] | None,
        step: str,
        started_at: datetime,
        completed_at: datetime,
        ok: bool,
        stdout: str | None = None,
        stderr: str | None = None,
        exit_code: int | None = None,
        error_type: str | None = None,
        error: str | None = None,
        **metadata: Any,
    ) -> None:
        if trace is None:
            return
        record: dict[str, Any] = {
            "step": step,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": int((completed_at - started_at).total_seconds() * 1000),
            "ok": ok,
            "exit_code": exit_code,
            "stdout_tail": (stdout or "")[-_TRACE_STDIO_TAIL_CHARS:] or None,
            "stderr_tail": (stderr or "")[-_TRACE_STDIO_TAIL_CHARS:] or None,
            "error_type": error_type,
            "error": error,
        }
        for key, value in metadata.items():
            if value is not None:
                record[key] = value
        trace.append(record)

    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe:
        if not (repo_root / ".git").exists():
            return GitRemoteProbe(reason="repository is not a git checkout")

        remote = self._run_git(repo_root, ["remote", "get-url", "origin"], check=False)
        if remote.returncode != 0:
            return GitRemoteProbe(reason="origin remote is not configured")

        base_branch_exists = (
            self._run_git(repo_root, ["show-ref", "--verify", f"refs/heads/{base_branch}"], check=False).returncode
            == 0
        )
        credentials_available = False
        gh_path = shutil.which("gh")
        if gh_path is not None:
            auth = subprocess.run(
                [gh_path, "auth", "status"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            credentials_available = auth.returncode == 0

        return GitRemoteProbe(
            remote_name="origin",
            remote_url=(remote.stdout or "").strip() or None,
            healthy=True,
            credentials_available=credentials_available,
            base_branch_exists=base_branch_exists,
            reason=None if base_branch_exists else f"base branch {base_branch} is missing locally",
        )

    def create_branch(
        self,
        repo_root: Path,
        *,
        branch_name: str,
        base_branch: str,
        workspace_dir: Path,
        trace: list[dict[str, Any]] | None = None,
    ) -> None:
        workspace_dir.parent.mkdir(parents=True, exist_ok=True)
        if workspace_dir.exists():
            self._run_git(repo_root, ["worktree", "remove", "--force", str(workspace_dir)], check=False)
        started_at = utc_now()
        completed = self._run_git(
            repo_root,
            ["worktree", "add", "-B", branch_name, str(workspace_dir), base_branch],
            check=False,
        )
        completed_at = utc_now()
        self._record_step(
            trace=trace,
            step="create_branch",
            started_at=started_at,
            completed_at=completed_at,
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            branch_name=branch_name,
            base_branch=base_branch,
            workspace_dir=str(workspace_dir),
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "git command failed").strip())

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
        trace: list[dict[str, Any]] | None = None,
    ) -> str:
        _ = repo_root, branch_name, changed_files
        apply_started_at = utc_now()
        applied = self._run_git(
            workspace_dir,
            ["apply", "--index", "--whitespace=nowarn", str(patch_uri)],
            check=False,
        )
        apply_completed_at = utc_now()
        self._record_step(
            trace=trace,
            step="apply_patch",
            started_at=apply_started_at,
            completed_at=apply_completed_at,
            ok=applied.returncode == 0,
            stdout=applied.stdout,
            stderr=applied.stderr,
            exit_code=applied.returncode,
            patch_uri=str(patch_uri),
        )
        if applied.returncode != 0:
            raise RuntimeError((applied.stderr or applied.stdout or "git command failed").strip())

        validator_log_dir.mkdir(parents=True, exist_ok=True) if validator_log_dir is not None else None
        for index, command in enumerate(validator_commands or [], start=1):
            validator_started_at = utc_now()
            completed = subprocess.run(
                command,
                cwd=workspace_dir,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
            validator_completed_at = utc_now()
            self._record_step(
                trace=trace,
                step="validator",
                started_at=validator_started_at,
                completed_at=validator_completed_at,
                ok=completed.returncode == 0,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                validator_index=index,
                command=command,
            )
            if validator_log_dir is not None:
                (validator_log_dir / f"validator_{index}.log").write_text(
                    "\n".join(
                        [
                            f"$ {command}",
                            "",
                            "[stdout]",
                            completed.stdout,
                            "",
                            "[stderr]",
                            completed.stderr,
                        ]
                    ),
                    encoding="utf-8",
                )
            if completed.returncode != 0:
                raise RuntimeError(f"validator failed: {command}")

        if not self._git_status(workspace_dir):
            raise RuntimeError("promotion patch did not produce any source changes")

        commit_started_at = utc_now()
        commit = self._run_git(
            workspace_dir,
            [
                "-c",
                "user.name=Autoresearch Promotion",
                "-c",
                "user.email=autoresearch@example.local",
                "commit",
                "-m",
                commit_message,
            ],
            check=False,
        )
        commit_completed_at = utc_now()
        self._record_step(
            trace=trace,
            step="commit",
            started_at=commit_started_at,
            completed_at=commit_completed_at,
            ok=commit.returncode == 0,
            stdout=commit.stdout,
            stderr=commit.stderr,
            exit_code=commit.returncode,
            commit_message=commit_message,
        )
        if commit.returncode != 0:
            raise RuntimeError((commit.stderr or commit.stdout or "git command failed").strip())
        completed = self._run_git(workspace_dir, ["rev-parse", "HEAD"])
        return (completed.stdout or "").strip()

    def push_branch(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        trace: list[dict[str, Any]] | None = None,
    ) -> None:
        _ = repo_root
        started_at = utc_now()
        completed = self._run_git(workspace_dir, ["push", "-u", "origin", branch_name], check=False)
        completed_at = utc_now()
        self._record_step(
            trace=trace,
            step="push",
            started_at=started_at,
            completed_at=completed_at,
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            branch_name=branch_name,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "git command failed").strip())

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
        trace: list[dict[str, Any]] | None = None,
    ) -> str:
        _ = repo_root
        gh_path = shutil.which("gh")
        if gh_path is None:
            raise RuntimeError("gh CLI is not available")
        self.push_branch(repo_root, workspace_dir=workspace_dir, branch_name=branch_name, trace=trace)
        started_at = utc_now()
        completed = subprocess.run(
            [
                gh_path,
                "pr",
                "create",
                "--draft",
                "--base",
                base_branch,
                "--head",
                branch_name,
                "--title",
                title,
                "--body",
                body,
            ],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        completed_at = utc_now()
        self._record_step(
            trace=trace,
            step="create_pr",
            started_at=started_at,
            completed_at=completed_at,
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            branch_name=branch_name,
            base_branch=base_branch,
            title=title,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "gh pr create failed").strip())
        return (completed.stdout or "").strip().splitlines()[-1].strip()

    @staticmethod
    def draft_pr_command(
        *,
        base_ref: str,
        branch_name: str,
        title: str,
        body_file: Path,
    ) -> str:
        return shlex.join(
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--base",
                base_ref,
                "--head",
                branch_name,
                "--title",
                title,
                "--body-file",
                str(body_file),
            ]
        )

    def _git_status(self, cwd: Path) -> list[str]:
        completed = self._run_git(cwd, ["status", "--porcelain"])
        return [line for line in (completed.stdout or "").splitlines() if line.strip()]

    def _run_git(
        self,
        cwd: Path,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "git command failed").strip())
        return completed


class GitPromotionGateService:
    def __init__(
        self,
        repo_root: Path,
        *,
        provider: GitPromotionProvider | None = None,
        writer_lease: WriterLeaseService | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._provider = provider or CliGitPromotionProvider()
        self._writer_lease = writer_lease or WriterLeaseService()
        defaults = ExecutionPolicy()
        self._default_forbidden_paths = list(defaults.forbidden_paths)
        self._default_max_changed_files = defaults.max_changed_files
        self._default_max_patch_lines = defaults.max_patch_lines
        self._default_allow_binary_changes = defaults.allow_binary_changes

    def finalize(
        self,
        *,
        intent: PromotionIntent,
        artifacts_dir: Path,
        validation_checks: list[ValidationCheck] | list[PromotionGateCheck] | None = None,
    ) -> tuple[PromotionPreflight, PromotionResult]:
        if intent.actor_role is not PromotionActorRole.AGGREGATOR:
            raise PermissionError("only aggregator can finalize promotion results")

        artifacts_dir = artifacts_dir.resolve()
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        result_path = artifacts_dir / "promotion_result.json"
        if result_path.exists():
            raise ValueError(f"promotion result already finalized for run {intent.run_id}")

        patch_path = Path(intent.patch_uri).resolve()
        patch_text = patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""
        diff_stats = self._build_diff_stats(patch_text=patch_text, changed_files=intent.changed_files)
        remote_probe = self._provider.probe_remote_health(
            self._repo_root,
            base_branch=intent.target_base_branch,
        )
        repo_dirty = self._git_status_lines(self._repo_root)
        checks = self._build_gate_checks(
            intent=intent,
            patch_exists=patch_path.exists(),
            patch_text=patch_text,
            diff_stats=diff_stats,
            validation_checks=validation_checks or [],
            remote_probe=remote_probe,
            repo_dirty=repo_dirty,
        )

        patch_allowed = all(not check.id.startswith("draft_pr.") and check.passed or check.id.startswith("draft_pr.") for check in checks)
        requested_mode = intent.preferred_mode
        effective_mode = GitPromotionMode.PATCH if patch_allowed else None
        reason: str | None = None

        if patch_allowed and requested_mode is GitPromotionMode.DRAFT_PR:
            unmet = [self._draft_pr_requirement_label(check.id) for check in checks if check.id.startswith("draft_pr.") and not check.passed]
            if unmet:
                reason = "draft_pr preconditions not satisfied: " + ", ".join(unmet)
            else:
                effective_mode = GitPromotionMode.DRAFT_PR
        elif not patch_allowed:
            reason = "promotion gate failed"

        preflight = PromotionPreflight(
            run_id=intent.run_id,
            requested_mode=requested_mode,
            effective_mode=effective_mode,
            allowed=patch_allowed,
            remote_probe=remote_probe,
            checks=checks,
            reason=reason,
        )
        (artifacts_dir / "promotion_preflight.json").write_text(
            json.dumps(preflight.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        now = utc_now()
        result = PromotionResult(
            run_id=intent.run_id,
            success=patch_allowed,
            mode=GitPromotionMode.PATCH if patch_allowed else None,
            patch_uri=str(patch_path) if patch_path.exists() else None,
            branch_name=None,
            commit_sha=None,
            pr_url=None,
            base_ref=intent.base_ref,
            target_base_branch=intent.target_base_branch,
            changed_files=list(intent.changed_files),
            diff_stats=diff_stats,
            finalized_by=intent.actor_id,
            checks=checks,
            created_at=now,
            updated_at=now,
            reason=reason,
            metadata={
                **intent.metadata,
                "writer_id": intent.writer_id,
            },
        )

        if patch_allowed and effective_mode is GitPromotionMode.DRAFT_PR:
            branch_name = self._sanitize_branch_name(
                str(intent.metadata.get("branch_name") or f"autoprom/{intent.run_id}")
            )
            workspace_dir = self._worktree_path(intent.run_id)
            validator_commands = self._metadata_list(intent.metadata, "validator_commands")
            commit_sha: str | None = None
            try:
                self._provider.create_branch(
                    self._repo_root,
                    branch_name=branch_name,
                    base_branch=intent.target_base_branch,
                    workspace_dir=workspace_dir,
                )
                commit_sha = self._provider.commit_changes(
                    self._repo_root,
                    workspace_dir=workspace_dir,
                    branch_name=branch_name,
                    patch_uri=patch_path,
                    changed_files=intent.changed_files,
                    commit_message=str(
                        intent.metadata.get("commit_message") or f"Promotion for {intent.run_id}"
                    ),
                    validator_commands=validator_commands,
                    validator_log_dir=artifacts_dir / "promotion-validation",
                )
            except Exception as exc:
                result = result.model_copy(
                    update={
                        "success": False,
                        "mode": None,
                        "branch_name": branch_name,
                        "updated_at": utc_now(),
                        "reason": f"draft_pr prepare failed: {exc}",
                        "metadata": {
                            **result.metadata,
                            "draft_pr_prepare_failed": str(exc),
                        },
                    }
                )
            else:
                try:
                    pr_url = self._provider.open_draft_pr(
                        self._repo_root,
                        workspace_dir=workspace_dir,
                        branch_name=branch_name,
                        base_branch=intent.target_base_branch,
                        title=str(intent.metadata.get("pr_title") or f"Promotion for {intent.run_id}"),
                        body=str(intent.metadata.get("pr_body") or "Automated promotion draft PR."),
                    )
                except Exception as exc:
                    result = result.model_copy(
                        update={
                            "mode": GitPromotionMode.PATCH,
                            "branch_name": branch_name,
                            "commit_sha": commit_sha,
                            "updated_at": utc_now(),
                            "reason": f"draft_pr upgrade failed: {exc}",
                            "metadata": {
                                **result.metadata,
                                "draft_pr_upgrade_failed": str(exc),
                                "fallback_mode": GitPromotionMode.PATCH.value,
                            },
                        }
                    )
                else:
                    result = result.model_copy(
                        update={
                            "mode": GitPromotionMode.DRAFT_PR,
                            "branch_name": branch_name,
                            "commit_sha": commit_sha,
                            "pr_url": pr_url,
                            "updated_at": utc_now(),
                            "reason": None,
                        }
                    )
            finally:
                self._cleanup_worktree(workspace_dir)

        result_path.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return preflight, result

    def _build_gate_checks(
        self,
        *,
        intent: PromotionIntent,
        patch_exists: bool,
        patch_text: str,
        diff_stats: PromotionDiffStats,
        validation_checks: list[ValidationCheck] | list[PromotionGateCheck],
        remote_probe: GitRemoteProbe,
        repo_dirty: list[str],
    ) -> list[PromotionGateCheck]:
        changed_files = [
            item.replace("\\", "/")
            for item in intent.changed_files
            if not _is_benign_runtime_artifact(item)
        ]
        forbidden_paths = self._metadata_list(intent.metadata, "forbidden_paths") or self._default_forbidden_paths
        max_changed_files = int(intent.metadata.get("max_changed_files", self._default_max_changed_files))
        max_patch_lines = int(intent.metadata.get("max_patch_lines", self._default_max_patch_lines))
        allow_binary_changes = bool(
            intent.metadata.get("allow_binary_changes", self._default_allow_binary_changes)
        )
        forbidden_changed = [
            path for path in changed_files if self._matches_any(path, forbidden_paths)
        ]
        runtime_changed = [path for path in changed_files if path.startswith(_RUNTIME_DENY_PREFIXES)]
        binary_patch = "GIT binary patch" in patch_text or "Binary files " in patch_text

        checks = [
            PromotionGateCheck(
                id="gate.patch_exists",
                passed=patch_exists and bool(patch_text.strip()),
                detail="promotion patch artifact is required" if not patch_text.strip() else "ok",
            ),
            PromotionGateCheck(
                id="gate.forbidden_paths",
                passed=not forbidden_changed,
                detail="; ".join(forbidden_changed) if forbidden_changed else "ok",
            ),
            PromotionGateCheck(
                id="gate.no_runtime_artifacts",
                passed=not runtime_changed,
                detail="; ".join(runtime_changed) if runtime_changed else "ok",
            ),
            PromotionGateCheck(
                id="gate.max_changed_files",
                passed=len(changed_files) <= max_changed_files,
                detail=f"changed={len(changed_files)} limit={max_changed_files}",
            ),
            PromotionGateCheck(
                id="gate.max_patch_lines",
                passed=diff_stats.patch_lines <= max_patch_lines,
                detail=f"patch_lines={diff_stats.patch_lines} limit={max_patch_lines}",
            ),
            PromotionGateCheck(
                id="gate.no_binary_changes",
                passed=(not binary_patch) or allow_binary_changes,
                detail="binary patch detected" if binary_patch else "ok",
            ),
            PromotionGateCheck(
                id="gate.no_main_write",
                passed=self._sanitize_branch_name(
                    str(intent.metadata.get("branch_name") or f"autoprom/{intent.run_id}")
                )
                != intent.target_base_branch,
                detail=f"target_base_branch={intent.target_base_branch}",
            ),
            self._build_writer_lease_check(intent.writer_lease_key),
        ]
        if intent.preferred_mode is GitPromotionMode.DRAFT_PR:
            checks.extend(
                [
                    PromotionGateCheck(
                        id="draft_pr.remote_probe",
                        passed=remote_probe.healthy,
                        detail=remote_probe.reason or "ok",
                    ),
                    PromotionGateCheck(
                        id="draft_pr.clean_base_repo",
                        passed=not repo_dirty,
                        detail="ok" if not repo_dirty else "; ".join(repo_dirty[:20]),
                    ),
                    PromotionGateCheck(
                        id="draft_pr.credentials_available",
                        passed=remote_probe.credentials_available,
                        detail="ok" if remote_probe.credentials_available else "gh auth status failed",
                    ),
                    PromotionGateCheck(
                        id="draft_pr.base_branch_exists",
                        passed=remote_probe.base_branch_exists,
                        detail="ok" if remote_probe.base_branch_exists else f"missing {intent.target_base_branch}",
                    ),
                    PromotionGateCheck(
                        id="draft_pr.approval_granted",
                        passed=intent.approval_granted,
                        detail="ok" if intent.approval_granted else "approval is required",
                    ),
                ]
            )

        for item in validation_checks:
            if isinstance(item, PromotionGateCheck):
                checks.append(item)
            else:
                checks.append(PromotionGateCheck(id=item.id, passed=item.passed, detail=item.detail))
        return checks

    def _build_writer_lease_check(self, writer_lease_key: str | None) -> PromotionGateCheck:
        if not writer_lease_key:
            return PromotionGateCheck(
                id="gate.writer_lease_available",
                passed=False,
                detail="writer lease key is required",
            )
        try:
            with self._writer_lease.acquire(writer_lease_key, blocking=False):
                return PromotionGateCheck(
                    id="gate.writer_lease_available",
                    passed=True,
                    detail="ok",
                )
        except TimeoutError:
            return PromotionGateCheck(
                id="gate.writer_lease_available",
                passed=False,
                detail="writer lease is currently held by another writer",
            )

    def _build_diff_stats(self, *, patch_text: str, changed_files: list[str]) -> PromotionDiffStats:
        insertions = 0
        deletions = 0
        patch_lines = 0
        for line in patch_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                insertions += 1
                patch_lines += 1
            elif line.startswith("-"):
                deletions += 1
                patch_lines += 1
        return PromotionDiffStats(
            files_changed=len(changed_files),
            insertions=insertions,
            deletions=deletions,
            patch_lines=patch_lines,
        )

    def _cleanup_worktree(self, workspace_dir: Path) -> None:
        if not workspace_dir.exists():
            return
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(workspace_dir)],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        shutil.rmtree(workspace_dir, ignore_errors=True)

    def _git_status_lines(self, cwd: Path) -> list[str]:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return []
        return [line for line in (completed.stdout or "").splitlines() if line.strip()]

    def _worktree_path(self, run_id: str) -> Path:
        base = Path("/tmp") / f"{self._repo_root.name}-{self._repo_root_hash()}" / "promotion-worktrees"
        return base / self._sanitize_branch_name(run_id)

    def _repo_root_hash(self) -> str:
        return hashlib.sha256(str(self._repo_root).encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def _draft_pr_requirement_label(check_id: str) -> str:
        labels = {
            "draft_pr.remote_probe": "remote healthy",
            "draft_pr.clean_base_repo": "clean base repository",
            "draft_pr.credentials_available": "credentials available",
            "draft_pr.base_branch_exists": "base branch exists",
            "draft_pr.approval_granted": "approval granted",
        }
        return labels.get(check_id, check_id)

    @staticmethod
    def _sanitize_branch_name(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9._/-]+", "-", value.strip()).strip("-./")
        return normalized or "autoprom/run"

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        normalized = path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)

    @staticmethod
    def _metadata_list(metadata: dict[str, object], key: str) -> list[str]:
        raw = metadata.get(key)
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]


class GitPromotionCreateRequest(StrictModel):
    run_id: str = Field(..., min_length=1)
    base_ref: str = "main"
    branch_prefix: str = "codex/auto-upgrade"
    title: str | None = None
    body: str = ""
    commit_message: str | None = None
    validator_commands: list[str] = Field(default_factory=list)
    remote_name: str = "origin"
    push_branch: bool = False
    open_draft_pr: bool = False
    keep_worktree: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitPromotionRead(StrictModel):
    promotion_id: str
    run_id: str
    status: JobStatus
    base_ref: str
    branch_name: str | None = None
    commit_sha: str | None = None
    patch_path: str
    worktree_path: str | None = None
    draft_pr_command: str
    pr_url: str | None = None
    validator_commands: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class GitPromotionService:
    def __init__(
        self,
        *,
        repo_root: Path,
        runtime_root: Path | None = None,
        repository: Repository[GitPromotionRead] | None = None,
        writer_lease: WriterLeaseService | None = None,
        provider: GitPromotionProvider | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._runtime_root = (runtime_root or (self._repo_root / ".masfactory_runtime")).resolve()
        self._runs_root = self._runtime_root / "runs"
        self._promotions_root = self._runtime_root / "promotions"
        self._promotions_root.mkdir(parents=True, exist_ok=True)
        self._repository = repository or SQLiteModelRepository(
            db_path=self._runtime_root / "promotions.sqlite3",
            table_name="git_promotions",
            model_cls=GitPromotionRead,
        )
        self._writer_lease = writer_lease or WriterLeaseService()
        self._provider = provider or CliGitPromotionProvider()

    def get_promotion(self, promotion_id: str) -> GitPromotionRead | None:
        return self._repository.get(promotion_id)

    def list_promotions(self) -> list[GitPromotionRead]:
        return self._repository.list()

    def find_latest_promotion_for_run(self, run_id: str) -> GitPromotionRead | None:
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            return None
        matches = [item for item in self._repository.list() if item.run_id == normalized_run_id]
        if not matches:
            return None
        matches.sort(key=lambda item: item.updated_at, reverse=True)
        return matches[0]

    def promote(self, request: GitPromotionCreateRequest) -> GitPromotionRead:
        run_dir = self._runs_root / request.run_id
        summary_path = run_dir / "summary.json"
        patch_path = run_dir / "artifacts" / "promotion.patch"
        job_path = run_dir / "job.json"

        if not summary_path.exists():
            raise FileNotFoundError(f"run summary not found: {summary_path}")
        if not patch_path.exists():
            raise FileNotFoundError(f"promotion patch not found: {patch_path}")

        summary = RunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
        if summary.final_status != "ready_for_promotion":
            raise ValueError(f"run is not ready for promotion: {summary.final_status}")

        dirty = self._git_status(self._repo_root)
        if dirty:
            raise ValueError("repository worktree is not clean; promotion requires a clean base")

        job_payload: dict[str, Any] = {}
        if job_path.exists():
            job_payload = json.loads(job_path.read_text(encoding="utf-8"))

        promotion_id = create_resource_id("gpr")
        now = utc_now()
        branch_name = self._branch_name(
            branch_prefix=request.branch_prefix,
            task=str(job_payload.get("task") or request.run_id),
            created_at=now,
        )
        commit_message = (request.commit_message or "").strip() or f"chore(promotion): apply {request.run_id}"
        title = (request.title or "").strip() or f"Promote AEP run {request.run_id}"

        promotion_dir = self._promotions_root / promotion_id
        workspace_dir = self._promotion_worktree_path(promotion_id)
        validator_dir = promotion_dir / "validators"
        body_file = promotion_dir / "draft_pr_body.md"
        promotion_dir.mkdir(parents=True, exist_ok=True)
        validator_dir.mkdir(parents=True, exist_ok=True)

        body = request.body.strip() or self._default_pr_body(
            run_id=request.run_id,
            patch_path=patch_path,
            validator_commands=request.validator_commands,
        )
        body_file.write_text(body + "\n", encoding="utf-8")
        trace_file = promotion_dir / "step_trace.json"
        step_trace: list[dict[str, Any]] = []

        draft_pr_command = CliGitPromotionProvider.draft_pr_command(
            base_ref=request.base_ref,
            branch_name=branch_name,
            title=title,
            body_file=body_file,
        )

        created = GitPromotionRead(
            promotion_id=promotion_id,
            run_id=request.run_id,
            status=JobStatus.CREATED,
            base_ref=request.base_ref,
            branch_name=branch_name,
            commit_sha=None,
            patch_path=str(patch_path),
            worktree_path=str(workspace_dir),
            draft_pr_command=draft_pr_command,
            pr_url=None,
            validator_commands=list(request.validator_commands),
            created_at=now,
            updated_at=now,
            metadata=dict(request.metadata),
            error=None,
        )
        self._repository.save(created.promotion_id, created)

        with self._writer_lease.acquire(f"promotion:{request.run_id}"):
            try:
                self._provider.create_branch(
                    self._repo_root,
                    branch_name=branch_name,
                    base_branch=request.base_ref,
                    workspace_dir=workspace_dir,
                    trace=step_trace,
                )
                commit_sha = self._provider.commit_changes(
                    self._repo_root,
                    workspace_dir=workspace_dir,
                    branch_name=branch_name,
                    patch_uri=patch_path,
                    changed_files=list(summary.driver_result.changed_paths),
                    commit_message=commit_message,
                    validator_commands=request.validator_commands,
                    validator_log_dir=validator_dir,
                    trace=step_trace,
                )

                if request.push_branch and not request.open_draft_pr:
                    self._provider.push_branch(
                        self._repo_root,
                        workspace_dir=workspace_dir,
                        branch_name=branch_name,
                        trace=step_trace,
                    )

                pr_url = None
                if request.open_draft_pr:
                    pr_url = self._provider.open_draft_pr(
                        self._repo_root,
                        workspace_dir=workspace_dir,
                        branch_name=branch_name,
                        base_branch=request.base_ref,
                        title=title,
                        body=body,
                        trace=step_trace,
                    )
                trace_file.write_text(json.dumps(step_trace, indent=2), encoding="utf-8")
                step_summary = self._build_step_summary(
                    step_trace=step_trace,
                    terminal_status=JobStatus.COMPLETED.value,
                    pr_url=pr_url,
                )

                completed_record = created.model_copy(
                    update={
                        "status": JobStatus.COMPLETED,
                        "commit_sha": commit_sha,
                        "pr_url": pr_url,
                        "updated_at": utc_now(),
                        "metadata": {
                            **created.metadata,
                            "validator_logs": [
                                str(path) for path in sorted(validator_dir.glob("validator_*.log"))
                            ],
                            "body_file": str(body_file),
                            "step_trace_file": str(trace_file),
                            "step_summary": step_summary,
                            "push_branch": request.push_branch,
                            "open_draft_pr": request.open_draft_pr,
                        },
                    }
                )
                self._repository.save(completed_record.promotion_id, completed_record)
                if not request.keep_worktree:
                    self._cleanup_worktree(workspace_dir)
                return completed_record
            except Exception as exc:
                trace_file.write_text(json.dumps(step_trace, indent=2), encoding="utf-8")
                step_summary = self._build_step_summary(
                    step_trace=step_trace,
                    terminal_status=JobStatus.FAILED.value,
                    error=str(exc),
                )
                failed = created.model_copy(
                    update={
                        "status": JobStatus.FAILED,
                        "updated_at": utc_now(),
                        "metadata": {
                            **created.metadata,
                            "validator_logs": [
                                str(path) for path in sorted(validator_dir.glob("validator_*.log"))
                            ],
                            "body_file": str(body_file),
                            "step_trace_file": str(trace_file),
                            "step_summary": step_summary,
                            "push_branch": request.push_branch,
                            "open_draft_pr": request.open_draft_pr,
                        },
                        "error": str(exc),
                    }
                )
                self._repository.save(failed.promotion_id, failed)
                if not request.keep_worktree:
                    self._cleanup_worktree(workspace_dir)
                raise

    def _build_step_summary(
        self,
        *,
        step_trace: list[dict[str, Any]],
        terminal_status: str,
        pr_url: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        last_step = step_trace[-1] if step_trace else None
        failed_step = next((step for step in reversed(step_trace) if not step.get("ok", False)), None)
        return {
            "terminal_status": terminal_status,
            "last_step": last_step.get("step") if last_step is not None else None,
            "failed_step": failed_step.get("step") if failed_step is not None else None,
            "failure_reason": (
                error
                or (failed_step.get("error") if failed_step is not None else None)
                or (failed_step.get("stderr_tail") if failed_step is not None else None)
            ),
            "retryable": bool(failed_step is not None and failed_step.get("step") in {"push", "create_pr"}),
            "pr_url": pr_url,
        }

    def _branch_name(self, *, branch_prefix: str, task: str, created_at: datetime) -> str:
        prefix = branch_prefix.rstrip("/")
        slug = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")[:40] or "run"
        timestamp = created_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{prefix}/{slug}-{timestamp}"

    def _default_pr_body(
        self,
        *,
        run_id: str,
        patch_path: Path,
        validator_commands: list[str],
    ) -> str:
        validators = "\n".join(f"- `{item}`" for item in validator_commands) or "- none"
        return "\n".join(
            [
                "## Automated Promotion",
                "",
                f"- Run ID: `{run_id}`",
                f"- Patch: `{patch_path}`",
                "- Mode: `draft_pr`",
                "",
                "## Validators",
                validators,
            ]
        )

    def _git_status(self, cwd: Path) -> list[str]:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return []
        return [line for line in (completed.stdout or "").splitlines() if line.strip()]

    def _promotion_worktree_path(self, promotion_id: str) -> Path:
        return (
            Path("/tmp")
            / f"{self._repo_root.name}-{self._repo_root_hash()}"
            / "promotions"
            / promotion_id
            / "worktree"
        )

    def _repo_root_hash(self) -> str:
        return hashlib.sha256(str(self._repo_root).encode("utf-8")).hexdigest()[:8]

    def _cleanup_worktree(self, worktree_dir: Path) -> None:
        if not worktree_dir.exists():
            return
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_dir)],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            shutil.rmtree(worktree_dir, ignore_errors=True)
