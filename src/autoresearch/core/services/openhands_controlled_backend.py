from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from autoresearch.core.services.git_promotion_gate import GitPromotionGateService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    GitPromotionMode,
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
    FailureStrategy,
    ValidationStatus,
)
from autoresearch.shared.store import create_resource_id


class OpenHandsControlledBackendService:
    """Run a minimal controlled AAS -> OpenHands -> AAS execution loop."""

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

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._sync_directory(source=self._repo_root, target=baseline, apply_excludes=True)

        created_at = utc_now()
        backend = request.backend
        retries_used = 0
        attempts = 0
        fallback_budget = 0
        if (
            request.failure_strategy is FailureStrategy.FALLBACK
            and request.fallback_backend is not None
            and request.fallback_backend != request.backend
        ):
            fallback_budget = 1
        max_attempts = request.max_retries + 1 + fallback_budget

        exit_code = 1
        validation_exit_code: int | None = None
        validation_status = ValidationStatus.PENDING
        status = ControlledRunStatus.REJECTED
        error: str | None = None

        while attempts < max_attempts:
            attempts += 1
            self._sync_directory(source=baseline, target=workspace, apply_excludes=False)
            self._append_log(log_file, f"\n=== attempt {attempts} backend={backend.value} ===\n")

            exit_code, execution_error = self._execute_backend(
                backend=backend,
                prompt=request.prompt,
                workspace=workspace,
                artifacts_dir=artifacts_dir,
                log_file=log_file,
            )

            validation_exit_code, validation_status = self._run_validation(
                command=request.validation_command,
                workspace=workspace,
                log_file=log_file,
            )

            if exit_code == 0 and validation_status in {ValidationStatus.PASSED, ValidationStatus.SKIPPED}:
                status = ControlledRunStatus.READY_FOR_PROMOTION
                error = None
                break

            error = execution_error or f"validation failed with status={validation_status.value}"

            if request.failure_strategy is FailureStrategy.RETRY and attempts < max_attempts:
                retries_used += 1
                continue

            if (
                request.failure_strategy is FailureStrategy.FALLBACK
                and request.fallback_backend is not None
                and request.fallback_backend != backend
            ):
                backend = request.fallback_backend
                retries_used += 1
                continue

            if request.failure_strategy is FailureStrategy.HUMAN_IN_LOOP:
                status = ControlledRunStatus.NEEDS_HUMAN_REVIEW
            else:
                status = ControlledRunStatus.REJECTED
            break

        changed_files = self._collect_changed_files(base=baseline, workspace=workspace)
        self._write_patch(base=baseline, workspace=workspace, patch_file=patch_file)
        promotion_preflight, promotion = self._finalize_promotion(
            run_id=run_id,
            patch_file=patch_file,
            changed_files=changed_files,
            request=request,
            validation_status=validation_status,
            exit_code=exit_code,
            artifacts_dir=artifacts_dir,
        )
        if status is ControlledRunStatus.READY_FOR_PROMOTION and not promotion.success:
            status = ControlledRunStatus.NEEDS_HUMAN_REVIEW
            error = promotion.reason or error

        workspace_retained = True
        if status is ControlledRunStatus.READY_FOR_PROMOTION and request.cleanup_workspace_on_success:
            shutil.rmtree(workspace, ignore_errors=True)
            workspace_retained = False
        elif status is not ControlledRunStatus.READY_FOR_PROMOTION and not request.keep_workspace_on_failure:
            shutil.rmtree(workspace, ignore_errors=True)
            workspace_retained = False

        artifacts = [
            ControlledExecutionArtifact(kind="log", path=str(log_file)),
            ControlledExecutionArtifact(kind="patch", path=str(patch_file)),
        ]
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
            retries_used=retries_used,
            backend_used=backend,
            created_at=created_at,
            updated_at=now,
            metadata=request.metadata,
            error=error,
            promotion_preflight=promotion_preflight,
            promotion=promotion,
        )

        summary_payload = result.model_dump(mode="json")
        summary_file.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

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
        preferred_mode = GitPromotionMode(
            str(request.metadata.get("promotion_mode") or GitPromotionMode.PATCH.value)
        )
        checks = [
            PromotionGateCheck(
                id="controlled.exit_code",
                passed=exit_code == 0,
                detail=f"exit_code={exit_code}",
            ),
            PromotionGateCheck(
                id="controlled.validation_status",
                passed=validation_status in {ValidationStatus.PASSED, ValidationStatus.SKIPPED},
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
            preferred_mode=preferred_mode,
            target_base_branch=str(request.metadata.get("base_branch") or "main"),
            approval_granted=bool(request.metadata.get("approval_granted", False)),
            metadata={
                "branch_name": str(request.metadata.get("branch_name") or f"autoprom/{run_id}"),
                "commit_message": str(request.metadata.get("commit_message") or f"Promotion for {run_id}"),
                "pr_title": str(request.metadata.get("pr_title") or f"Promotion for {run_id}"),
                "pr_body": str(request.metadata.get("pr_body") or "Automated promotion draft PR."),
                "validator_commands": [shlex.join(request.validation_command)]
                if request.validation_command
                else [],
            },
        )
        return self._promotion_gate.finalize(
            intent=intent,
            artifacts_dir=artifacts_dir,
            validation_checks=checks,
        )

    def _sync_directory(self, *, source: Path, target: Path, apply_excludes: bool) -> None:
        if target.exists():
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
    ) -> tuple[int, str | None]:
        if backend is ControlledBackend.MOCK:
            return self._run_mock_backend(prompt=prompt, workspace=workspace, log_file=log_file)

        return self._run_openhands_cli(
            prompt=prompt,
            workspace=workspace,
            artifacts_dir=artifacts_dir,
            log_file=log_file,
        )

    def _run_mock_backend(self, *, prompt: str, workspace: Path, log_file: Path) -> tuple[int, str | None]:
        demo_file = workspace / "src" / "openhands_demo_task.py"
        demo_file.parent.mkdir(parents=True, exist_ok=True)
        safe_prompt = prompt.strip().replace('"""', "'''")
        content = (
            '"""Autogenerated by controlled OpenHands demo backend."""\n\n'
            "def run() -> dict[str, str]:\n"
            f'    return {{"task": "{safe_prompt}", "status": "completed"}}\n'
        )
        demo_file.write_text(content, encoding="utf-8")
        self._append_log(log_file, f"[mock-backend] wrote {demo_file}\n")
        return 0, None

    def _run_openhands_cli(
        self,
        *,
        prompt: str,
        workspace: Path,
        artifacts_dir: Path,
        log_file: Path,
    ) -> tuple[int, str | None]:
        launcher = self._repo_root / "scripts" / "openhands_start.sh"
        if not launcher.exists():
            return 127, f"launcher not found: {launcher}"

        guarded_prompt = (
            f"{prompt}\n\n"
            "Execution contract:\n"
            "- Single task execution only. Do not start autonomous loops.\n"
            "- Do not commit, push, or edit git config.\n"
            "- Modify files only under /opt/workspace.\n"
            "- Return changed files and executed commands in final summary.\n"
        )

        env = dict(os.environ)
        env["OPENHANDS_WORKSPACE"] = str(workspace)
        env["OPENHANDS_AUDIT_DIR"] = str(artifacts_dir)
        env["OPENHANDS_AUDIT_FILE"] = str(artifacts_dir / "openhands_compliance.json")

        completed = subprocess.run(
            ["bash", str(launcher), guarded_prompt],
            cwd=self._repo_root,
            env=env,
            capture_output=True,
            text=True,
        )

        output = (
            "[openhands-cli] stdout:\n"
            f"{completed.stdout}\n"
            "[openhands-cli] stderr:\n"
            f"{completed.stderr}\n"
        )
        self._append_log(log_file, output)

        if completed.returncode != 0:
            return completed.returncode, f"openhands_cli exited with code {completed.returncode}"

        return 0, None

    def _run_validation(
        self,
        *,
        command: list[str],
        workspace: Path,
        log_file: Path,
    ) -> tuple[int | None, ValidationStatus]:
        if not command:
            self._append_log(log_file, "[validation] skipped (empty command)\n")
            return None, ValidationStatus.SKIPPED

        validation_dir = workspace.parent / "artifacts" / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)

        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
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
        completed = subprocess.run(cmd, capture_output=True, text=True)
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
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode not in {0, 1}:
            patch_file.write_text("", encoding="utf-8")
            return
        patch_file.write_text(completed.stdout, encoding="utf-8")

    @staticmethod
    def _append_log(log_file: Path, text: str) -> None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(text)

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
