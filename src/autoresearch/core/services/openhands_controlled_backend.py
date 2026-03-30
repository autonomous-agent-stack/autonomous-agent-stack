from __future__ import annotations

import ast
from dataclasses import dataclass
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from autoresearch.core.services.git_promotion_gate import GitPromotionGateService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    PromotionActorRole,
    PromotionGateCheck,
    PromotionIntent,
    utc_now,
)
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionArtifact,
    ControlledExecutionRead,
    ControlledExecutionRequest,
    ControlledRunStatus,
    PatchResult,
    ValidationStatus,
)
from autoresearch.shared.store import create_resource_id


@dataclass(slots=True)
class _BackendExecutionOutcome:
    exit_code: int
    error: str | None = None
    stdout: str = ""
    stderr: str = ""


class OpenHandsControlledBackendService:
    """Run a constrained OpenHands worker and hand patch results to the promotion gate."""

    _SYNC_EXCLUDES = (
        ".git",
        ".venv",
        "node_modules",
        "panel/out",
        "dashboard/.next",
        ".pytest_cache",
        ".ruff_cache",
        ".masfactory_runtime",
        "logs/audit/openhands/jobs",
    )
    _GIT_ENV_KEYS = {
        "GIT_ASKPASS",
        "GIT_AUTHOR_EMAIL",
        "GIT_AUTHOR_NAME",
        "GIT_COMMITTER_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_SSH_VARIANT",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "SSH_AGENT_PID",
        "SSH_AUTH_SOCK",
        "SSH_ASKPASS",
    }
    _GIT_ENV_PREFIXES = ("GITHUB_", "GH_", "GIT_AUTHOR_", "GIT_COMMITTER_", "SSH_")
    _FAST_FAIL_PATTERNS = (
        re.compile(r"\bSyntaxError\b"),
        re.compile(r"\bModuleNotFoundError\b"),
        re.compile(r"\bImportError\b"),
        re.compile(r"\bPermission denied\b", re.IGNORECASE),
    )

    def __init__(
        self,
        repo_root: Path | None = None,
        run_root: Path | None = None,
        promotion_gate: GitPromotionGateService | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        default_run_root = Path("/tmp") / "autonomous-agent-stack" / "openhands-controlled"
        self._run_root = (run_root or default_run_root).resolve()
        self._promotion_gate = promotion_gate or GitPromotionGateService(
            self._repo_root,
            writer_lease=WriterLeaseService(),
        )

    def run(self, request: ControlledExecutionRequest) -> ControlledExecutionRead:
        run_id = create_resource_id("ohrun")
        run_dir = self._run_root / run_id
        baseline = run_dir / "baseline"
        workspace = run_dir / "workspace"
        artifacts_dir = run_dir / "artifacts"
        log_file = artifacts_dir / "execution.log"
        patch_file = artifacts_dir / "promotion.patch"
        summary_file = artifacts_dir / "summary.json"
        overlay = run_dir / "overlay"

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        created_at = utc_now()

        if request.backend is ControlledBackend.OPENHANDS_CLI and self._repo_has_uncommitted_changes():
            result = self._build_result(
                run_id=run_id,
                request=request,
                workspace=workspace,
                workspace_retained=False,
                log_file=log_file,
                artifacts_dir=artifacts_dir,
                summary_file=summary_file,
                created_at=created_at,
                changed_files=[],
                exit_code=1,
                validation_status=ValidationStatus.SKIPPED,
                validation_exit_code=None,
                status=ControlledRunStatus.POLICY_BLOCKED,
                iterations_used=0,
                backend_used=request.backend,
                error="repo root has uncommitted changes; controlled worker requires a clean git checkout",
                patch_result=None,
                promotion_preflight=None,
                promotion=None,
            )
            return result

        self._sync_directory(source=self._repo_root, target=baseline, apply_excludes=True)

        backend = request.backend
        fallback_used = False
        current_backend_attempts = 0
        total_attempts = 0

        changed_files: list[str] = []
        exit_code = 1
        validation_exit_code: int | None = None
        validation_status = ValidationStatus.PENDING
        status = ControlledRunStatus.FAILED
        error: str | None = "worker did not execute"
        patch_result: PatchResult | None = None
        execution_outcome = _BackendExecutionOutcome(exit_code=1, error=error)
        promotion_preflight = None
        promotion = None

        while True:
            backend_limit = request.max_iterations if backend is request.backend else 1
            if current_backend_attempts >= backend_limit:
                if self._can_fallback(request=request, backend=backend, fallback_used=fallback_used):
                    backend = request.fallback_backend or backend
                    fallback_used = True
                    current_backend_attempts = 0
                    continue
                break

            current_backend_attempts += 1
            total_attempts += 1
            self._sync_directory(source=baseline, target=workspace, apply_excludes=False)
            self._prepare_strict_workspace(
                workspace=workspace,
                overlay_root=overlay,
                allowed_paths=request.allowed_paths,
            )
            self._append_log(
                log_file,
                f"\n=== attempt {total_attempts} backend={backend.value} iteration={current_backend_attempts}/{backend_limit} ===\n",
            )

            execution_outcome = self._execute_backend(
                backend=backend,
                prompt=request.prompt,
                workspace=workspace,
                artifacts_dir=artifacts_dir,
                log_file=log_file,
                allowed_paths=request.allowed_paths,
            )
            exit_code = execution_outcome.exit_code

            changed_files = self._collect_changed_files(base=baseline, workspace=workspace)
            self._write_patch(base=baseline, workspace=workspace, patch_file=patch_file)
            patch_result = PatchResult(
                patch_path=str(patch_file),
                patch_text=patch_file.read_text(encoding="utf-8") if patch_file.exists() else "",
                changed_files=changed_files,
                stdout=execution_outcome.stdout,
                stderr=execution_outcome.stderr,
            )

            scope_error = self._detect_scope_violation(
                changed_files=changed_files,
                allowed_paths=request.allowed_paths,
                forbidden_paths=request.forbidden_paths,
            )
            if scope_error is not None:
                status = ControlledRunStatus.POLICY_BLOCKED
                error = scope_error
                self._append_log(log_file, f"[policy] blocked: {scope_error}\n")
                validation_status = ValidationStatus.SKIPPED
                validation_exit_code = None
                break

            if not changed_files:
                error = execution_outcome.error or "worker did not produce a patch candidate"
                validation_status = ValidationStatus.SKIPPED
                validation_exit_code = None
            else:
                validation_exit_code, validation_status = self._run_validation(
                    command=request.test_command,
                    workspace=workspace,
                    log_file=log_file,
                )
                error = execution_outcome.error or (
                    None
                    if validation_status is ValidationStatus.PASSED
                    else f"test_command failed with status={validation_status.value}"
                )

            fail_fast_reason = self._detect_fail_fast_reason(
                execution_outcome=execution_outcome,
                changed_files=changed_files,
                workspace=workspace,
                log_file=log_file,
            )
            if fail_fast_reason is not None:
                status = ControlledRunStatus.FAILED
                error = fail_fast_reason
                validation_status = ValidationStatus.FAILED
                if validation_exit_code is None:
                    validation_exit_code = 2
                break

            if exit_code == 0 and validation_status is ValidationStatus.PASSED and changed_files:
                status = ControlledRunStatus.READY_FOR_PROMOTION
                error = None
                break

            if current_backend_attempts < backend_limit:
                continue

            if self._can_fallback(request=request, backend=backend, fallback_used=fallback_used):
                backend = request.fallback_backend or backend
                fallback_used = True
                current_backend_attempts = 0
                continue
            break

        if status is ControlledRunStatus.READY_FOR_PROMOTION and patch_result is not None:
            promotion_preflight, promotion = self._finalize_promotion(
                run_id=run_id,
                patch_file=patch_file,
                changed_files=changed_files,
                request=request,
                validation_status=validation_status,
                exit_code=exit_code,
                artifacts_dir=artifacts_dir,
            )
            if not promotion.success:
                status = ControlledRunStatus.NEEDS_HUMAN_REVIEW
                error = promotion.reason or "promotion gate rejected the patch candidate"

        workspace_retained = True
        if status is ControlledRunStatus.READY_FOR_PROMOTION and request.cleanup_workspace_on_success:
            shutil.rmtree(workspace, ignore_errors=True)
            workspace_retained = False
        elif status is not ControlledRunStatus.READY_FOR_PROMOTION and not request.keep_workspace_on_failure:
            shutil.rmtree(workspace, ignore_errors=True)
            workspace_retained = False

        return self._build_result(
            run_id=run_id,
            request=request,
            workspace=workspace,
            workspace_retained=workspace_retained,
            log_file=log_file,
            artifacts_dir=artifacts_dir,
            summary_file=summary_file,
            created_at=created_at,
            changed_files=changed_files,
            exit_code=exit_code,
            validation_status=validation_status,
            validation_exit_code=validation_exit_code,
            status=status,
            iterations_used=max(total_attempts - 1, 0),
            backend_used=backend,
            error=error,
            patch_result=patch_result,
            promotion_preflight=promotion_preflight,
            promotion=promotion,
        )

    def _build_result(
        self,
        *,
        run_id: str,
        request: ControlledExecutionRequest,
        workspace: Path,
        workspace_retained: bool,
        log_file: Path,
        artifacts_dir: Path,
        summary_file: Path,
        created_at,
        changed_files: list[str],
        exit_code: int,
        validation_status: ValidationStatus,
        validation_exit_code: int | None,
        status: ControlledRunStatus,
        iterations_used: int,
        backend_used: ControlledBackend,
        error: str | None,
        patch_result: PatchResult | None,
        promotion_preflight,
        promotion,
    ) -> ControlledExecutionRead:
        artifacts = [ControlledExecutionArtifact(kind="log", path=str(log_file))]
        if patch_result is not None:
            artifacts.append(ControlledExecutionArtifact(kind="patch", path=patch_result.patch_path))
        compliance_file = artifacts_dir / "openhands_compliance.json"
        if compliance_file.exists():
            artifacts.append(ControlledExecutionArtifact(kind="compliance", path=str(compliance_file)))
        validation_dir = artifacts_dir / "validation"
        if validation_dir.exists():
            artifacts.append(ControlledExecutionArtifact(kind="validation", path=str(validation_dir)))
        artifacts.append(ControlledExecutionArtifact(kind="summary", path=str(summary_file)))

        now = utc_now()
        result = ControlledExecutionRead(
            run_id=run_id,
            task_id=request.task_id,
            input=request.model_dump(mode="json"),
            workspace=str(workspace),
            workspace_retained=workspace_retained,
            execution_log=str(log_file),
            artifacts=artifacts,
            changed_files=changed_files,
            exit_code=exit_code,
            validation_status=validation_status,
            validation_exit_code=validation_exit_code,
            status=status,
            iterations_used=iterations_used,
            backend_used=backend_used,
            created_at=created_at,
            updated_at=now,
            metadata=request.metadata,
            error=error,
            patch_result=patch_result,
            promotion_preflight=promotion_preflight,
            promotion=promotion,
        )
        summary_file.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    @staticmethod
    def _can_fallback(
        *,
        request: ControlledExecutionRequest,
        backend: ControlledBackend,
        fallback_used: bool,
    ) -> bool:
        return (
            not fallback_used
            and request.fallback_backend is not None
            and request.fallback_backend != backend
        )

    def _finalize_promotion(
        self,
        *,
        run_id: str,
        patch_file: Path,
        changed_files: list[str],
        request: ControlledExecutionRequest,
        validation_status: ValidationStatus,
        exit_code: int,
        artifacts_dir: Path,
    ):
        checks = [
            PromotionGateCheck(
                id="controlled.exit_code",
                passed=exit_code == 0,
                detail=f"exit_code={exit_code}",
            ),
            PromotionGateCheck(
                id="controlled.validation_status",
                passed=validation_status is ValidationStatus.PASSED,
                detail=validation_status.value,
            ),
        ]
        intent = PromotionIntent(
            run_id=run_id,
            actor_role=PromotionActorRole.AGGREGATOR,
            actor_id="aggregator",
            writer_id=request.backend.value,
            writer_lease_key=f"writer:{run_id}",
            patch_uri=str(patch_file),
            changed_files=changed_files,
            base_ref=self._git_ref(["rev-parse", "HEAD"], default="nogit"),
            preferred_mode=request.pipeline_target,
            target_base_branch=str(request.metadata.get("base_branch") or "main"),
            approval_granted=bool(request.metadata.get("approval_granted", False)),
            metadata={
                "branch_name": str(request.metadata.get("branch_name") or f"autoprom/{run_id}"),
                "commit_message": str(request.metadata.get("commit_message") or f"Promotion for {run_id}"),
                "pr_title": str(request.metadata.get("pr_title") or f"Promotion for {run_id}"),
                "pr_body": str(request.metadata.get("pr_body") or "Automated promotion draft PR."),
                "worker_output_mode": request.worker_output_mode,
                "pipeline_target": request.pipeline_target.value,
                "validator_commands": [shlex.join(request.test_command)],
                "allowed_paths": list(request.allowed_paths),
                "forbidden_paths": list(request.forbidden_paths),
            },
        )
        return self._promotion_gate.finalize(
            intent=intent,
            artifacts_dir=artifacts_dir,
            validation_checks=checks,
        )

    def _sync_directory(self, *, source: Path, target: Path, apply_excludes: bool) -> None:
        if target.exists():
            self._make_tree_writable(target)
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        rsync_path = shutil.which("rsync")
        if rsync_path:
            cmd = [rsync_path, "-a", "--delete"]
            if apply_excludes:
                for item in self._SYNC_EXCLUDES:
                    cmd.extend(["--exclude", item])
            cmd.extend([f"{source}/", f"{target}/"])
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return

        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*self._SYNC_EXCLUDES) if apply_excludes else None,
        )

    def _execute_backend(
        self,
        *,
        backend: ControlledBackend,
        prompt: str,
        workspace: Path,
        artifacts_dir: Path,
        log_file: Path,
        allowed_paths: list[str],
    ) -> _BackendExecutionOutcome:
        try:
            if backend is ControlledBackend.MOCK:
                return self._run_mock_backend(
                    prompt=prompt,
                    workspace=workspace,
                    log_file=log_file,
                    allowed_paths=allowed_paths,
                )

            return self._run_openhands_cli(
                prompt=prompt,
                workspace=workspace,
                artifacts_dir=artifacts_dir,
                log_file=log_file,
                allowed_paths=allowed_paths,
            )
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            self._append_log(log_file, f"[backend-exception] {exc.__class__.__name__}: {message}\n")
            return _BackendExecutionOutcome(
                exit_code=1,
                error=message,
                stderr=f"{exc.__class__.__name__}: {message}\n",
            )

    def _run_mock_backend(
        self,
        *,
        prompt: str,
        workspace: Path,
        log_file: Path,
        allowed_paths: list[str],
    ) -> _BackendExecutionOutcome:
        demo_file = self._materialize_mock_patch(
            workspace=workspace,
            allowed_paths=allowed_paths,
            prompt=prompt,
        )
        stdout = f"[mock-backend] wrote {demo_file}\n"
        self._append_log(log_file, stdout)
        return _BackendExecutionOutcome(exit_code=0, stdout=stdout, stderr="")

    def _run_openhands_cli(
        self,
        *,
        prompt: str,
        workspace: Path,
        artifacts_dir: Path,
        log_file: Path,
        allowed_paths: list[str],
    ) -> _BackendExecutionOutcome:
        launcher = self._repo_root / "scripts" / "openhands_start.sh"
        if not launcher.exists():
            return _BackendExecutionOutcome(
                exit_code=127,
                error=f"launcher not found: {launcher}",
                stderr=f"launcher not found: {launcher}\n",
            )

        guarded_prompt = (
            f"{prompt}\n\n"
            "Execution contract:\n"
            "- Single task execution only. Do not start autonomous loops.\n"
            "- Do not commit, push, or edit git config.\n"
            "- Modify files only inside the provided workspace root.\n"
            "- Return changed files and executed commands in final summary.\n"
        )

        env = self._build_openhands_env(workspace=workspace, artifacts_dir=artifacts_dir)
        completed = subprocess.run(
            ["bash", str(launcher), guarded_prompt],
            cwd=self._repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        self._append_log(
            log_file,
            "[openhands-cli] stdout:\n"
            f"{stdout}\n"
            "[openhands-cli] stderr:\n"
            f"{stderr}\n",
        )

        if completed.returncode != 0:
            return _BackendExecutionOutcome(
                exit_code=completed.returncode,
                error=f"openhands_cli exited with code {completed.returncode}",
                stdout=stdout,
                stderr=stderr,
            )

        if env.get("OPENHANDS_DRY_RUN") == "1":
            demo_file = self._materialize_mock_patch(
                workspace=workspace,
                allowed_paths=allowed_paths,
                prompt=prompt,
            )
            self._append_log(log_file, f"[openhands-cli] dry-run materialized {demo_file}\n")

        return _BackendExecutionOutcome(exit_code=0, stdout=stdout, stderr=stderr)

    def _build_openhands_env(self, *, workspace: Path, artifacts_dir: Path) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in self._GIT_ENV_KEYS
            and not any(key.startswith(prefix) for prefix in self._GIT_ENV_PREFIXES)
        }
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["OPENHANDS_WORKSPACE"] = str(workspace)
        env["OPENHANDS_AUDIT_DIR"] = str(artifacts_dir)
        env["OPENHANDS_AUDIT_FILE"] = str(artifacts_dir / "openhands_compliance.json")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = str(artifacts_dir / "pycache")
        if env.get("OPENHANDS_DRY_RUN") == "1" and "OPENHANDS_RUNTIME" not in env:
            env["OPENHANDS_RUNTIME"] = "host"
        return env

    def _materialize_mock_patch(
        self,
        *,
        workspace: Path,
        allowed_paths: list[str],
        prompt: str,
    ) -> Path:
        target = self._select_mock_target(workspace=workspace, allowed_paths=allowed_paths)
        target.parent.mkdir(parents=True, exist_ok=True)
        safe_prompt = prompt.strip().replace('"""', "'''")
        target.write_text(
            (
                '"""Autogenerated by constrained OpenHands worker."""\n\n'
                "def run() -> dict[str, str]:\n"
                f'    return {{"task": "{safe_prompt}", "status": "completed"}}\n'
            ),
            encoding="utf-8",
        )
        return target

    def _select_mock_target(self, *, workspace: Path, allowed_paths: list[str]) -> Path:
        for pattern in allowed_paths:
            if not any(char in pattern for char in "*?["):
                return workspace / pattern

        for pattern in allowed_paths:
            prefix = pattern.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0].rstrip("/")
            if prefix:
                if "." in Path(prefix).name:
                    return workspace / prefix
                return workspace / prefix / "openhands_mock_worker.py"

        return workspace / "src" / "openhands_mock_worker.py"

    def _run_validation(
        self,
        *,
        command: list[str],
        workspace: Path,
        log_file: Path,
    ) -> tuple[int | None, ValidationStatus]:
        validation_dir = workspace.parent / "artifacts" / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)

        completed = subprocess.run(
            command,
            cwd=workspace,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPYCACHEPREFIX": str(validation_dir / "pycache"),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        validation_log = validation_dir / "validation.log"
        validation_log.write_text(
            (
                f"command: {command}\n"
                f"returncode: {completed.returncode}\n"
                "stdout:\n"
                f"{completed.stdout}\n"
                "stderr:\n"
                f"{completed.stderr}\n"
            ),
            encoding="utf-8",
        )
        self._append_log(log_file, f"[validation] returncode={completed.returncode} log={validation_log}\n")

        if completed.returncode == 0:
            return 0, ValidationStatus.PASSED
        return completed.returncode, ValidationStatus.FAILED

    def _prepare_strict_workspace(
        self,
        *,
        workspace: Path,
        overlay_root: Path,
        allowed_paths: list[str],
    ) -> None:
        if overlay_root.exists():
            shutil.rmtree(overlay_root)
        overlay_root.mkdir(parents=True, exist_ok=True)

        file_paths: list[str] = []
        directory_paths: list[str] = []
        wildcard_paths: list[str] = []

        for pattern in allowed_paths:
            normalized = pattern.strip().replace("\\", "/").rstrip("/")
            if not normalized:
                continue
            if any(char in normalized for char in "*?["):
                wildcard_paths.append(normalized)
                continue
            target = workspace / normalized
            if target.exists() and target.is_dir():
                directory_paths.append(normalized)
                continue
            if "." in Path(normalized).name:
                file_paths.append(normalized)
            else:
                directory_paths.append(normalized)

        for rel_path in file_paths:
            self._materialize_overlay_file(
                workspace=workspace,
                overlay_root=overlay_root,
                relative_path=rel_path,
            )

        self._apply_readonly_tree(workspace=workspace)

        for rel_path in directory_paths:
            self._make_path_tree_writable(workspace / rel_path)

        for pattern in wildcard_paths:
            self._make_matching_paths_writable(workspace=workspace, pattern=pattern)

        for rel_path in file_paths:
            self._make_overlay_target_writable(overlay_root=overlay_root, relative_path=rel_path)

    def _materialize_overlay_file(
        self,
        *,
        workspace: Path,
        overlay_root: Path,
        relative_path: str,
    ) -> None:
        source = workspace / relative_path
        overlay_target = overlay_root / relative_path
        overlay_target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            if source.is_dir():
                return
            shutil.copy2(source, overlay_target)
            source.unlink()
        else:
            overlay_target.touch()
        source.parent.mkdir(parents=True, exist_ok=True)
        source.symlink_to(overlay_target)

    def _apply_readonly_tree(self, *, workspace: Path) -> None:
        for root, dirnames, filenames in os.walk(workspace):
            root_path = Path(root)
            os.chmod(root_path, 0o555)
            for dirname in dirnames:
                os.chmod(root_path / dirname, 0o555)
            for filename in filenames:
                path = root_path / filename
                if path.is_symlink():
                    continue
                os.chmod(path, 0o444)

    def _make_path_tree_writable(self, path: Path) -> None:
        if not path.exists():
            return
        if path.is_file():
            os.chmod(path, 0o644)
            return
        for root, dirnames, filenames in os.walk(path):
            root_path = Path(root)
            os.chmod(root_path, 0o755)
            for dirname in dirnames:
                os.chmod(root_path / dirname, 0o755)
            for filename in filenames:
                candidate = root_path / filename
                if candidate.is_symlink():
                    continue
                os.chmod(candidate, 0o644)

    def _make_matching_paths_writable(self, *, workspace: Path, pattern: str) -> None:
        for candidate in workspace.rglob("*"):
            relative = candidate.relative_to(workspace).as_posix()
            if fnmatch.fnmatch(relative, pattern):
                self._make_path_tree_writable(candidate)

    def _make_tree_writable(self, path: Path) -> None:
        if not path.exists():
            return
        for root, dirnames, filenames in os.walk(path):
            root_path = Path(root)
            os.chmod(root_path, 0o755)
            for dirname in dirnames:
                os.chmod(root_path / dirname, 0o755)
            for filename in filenames:
                candidate = root_path / filename
                if candidate.is_symlink():
                    continue
                os.chmod(candidate, 0o644)

    def _make_overlay_target_writable(self, *, overlay_root: Path, relative_path: str) -> None:
        target = overlay_root / relative_path
        parent = target.parent
        while True:
            os.chmod(parent, 0o755)
            if parent == overlay_root:
                break
            parent = parent.parent
        if target.exists():
            os.chmod(target, 0o644)

    def _detect_fail_fast_reason(
        self,
        *,
        execution_outcome: _BackendExecutionOutcome,
        changed_files: list[str],
        workspace: Path,
        log_file: Path,
    ) -> str | None:
        combined_output = "\n".join(
            part for part in (execution_outcome.error, execution_outcome.stdout, execution_outcome.stderr) if part
        )
        for pattern in self._FAST_FAIL_PATTERNS:
            if pattern.search(combined_output):
                reason = f"fail-fast probe tripped on backend output: {pattern.pattern}"
                self._append_log(log_file, f"[fail-fast] {reason}\n")
                return reason

        python_changes = [path for path in changed_files if path.endswith(".py")]
        if not python_changes:
            return None

        for rel_path in python_changes:
            target = workspace / rel_path
            try:
                source = target.read_text(encoding="utf-8")
                ast.parse(source, filename=rel_path)
            except SyntaxError as exc:
                reason = f"fail-fast probe detected broken python artifacts: SyntaxError in {rel_path}:{exc.lineno}"
                self._append_log(log_file, f"[fail-fast] {reason}\n")
                return reason
            except OSError as exc:
                reason = f"fail-fast probe could not read changed file {rel_path}: {exc}"
                self._append_log(log_file, f"[fail-fast] {reason}\n")
                return reason
        return None

    def _detect_scope_violation(
        self,
        *,
        changed_files: list[str],
        allowed_paths: list[str],
        forbidden_paths: list[str],
    ) -> str | None:
        blocked: list[str] = []
        for path in changed_files:
            if self._matches_any(path, forbidden_paths):
                blocked.append(f"{path} (forbidden)")
                continue
            if not self._matches_any(path, allowed_paths):
                blocked.append(f"{path} (outside allowed_paths)")
        if blocked:
            return "patch touched disallowed files: " + "; ".join(blocked)
        return None

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        normalized = path.replace("\\", "/")
        pure = Path(normalized).as_posix()
        return any(fnmatch.fnmatch(pure, pattern) for pattern in patterns)

    def _collect_changed_files(self, *, base: Path, workspace: Path) -> list[str]:
        cmd = [
            "git",
            "--no-pager",
            "diff",
            "--no-index",
            "--name-only",
            "--",
            str(base),
            str(workspace),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode not in {0, 1}:
            return []

        changed: set[str] = set()
        for raw in completed.stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            path = Path(line)
            relative: Path | None = None
            if path.is_absolute():
                if path.is_relative_to(workspace):
                    relative = path.relative_to(workspace)
                elif path.is_relative_to(base):
                    relative = path.relative_to(base)
            if relative is None:
                continue
            rel_str = str(relative)
            if rel_str.startswith("logs/audit/openhands/jobs"):
                continue
            changed.add(rel_str)

        return sorted(changed)

    def _write_patch(self, *, base: Path, workspace: Path, patch_file: Path) -> None:
        cmd = [
            "git",
            "--no-pager",
            "diff",
            "--no-index",
            "--",
            str(base),
            str(workspace),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode not in {0, 1}:
            patch_file.write_text("", encoding="utf-8")
            return
        patch_file.write_text(completed.stdout, encoding="utf-8")

    @staticmethod
    def _append_log(log_file: Path, text: str) -> None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def _repo_has_uncommitted_changes(self) -> bool:
        if not (self._repo_root / ".git").exists():
            return False
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return False
        return bool((completed.stdout or "").strip())

    def _git_ref(self, args: list[str], *, default: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return default
        return (completed.stdout or "").strip() or default
