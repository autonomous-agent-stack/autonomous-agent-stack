from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from autoresearch.core.services.git_promotion_gate import GitPromotionGateService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.autoresearch_controlled_contract import (
    AutoResearchBackend,
    AutoResearchExecutionArtifact,
    AutoResearchExecutionRead,
    AutoResearchExecutionRequest,
    AutoResearchPatchResult,
    AutoResearchRunStatus,
    AutoResearchValidationStatus,
)
from autoresearch.shared.models import PromotionActorRole, PromotionGateCheck, PromotionIntent, utc_now
from autoresearch.shared.store import create_resource_id


@dataclass(slots=True)
class _AutoResearchOutcome:
    exit_code: int
    error: str | None = None
    stdout: str = ""
    stderr: str = ""


class AutoResearchControlledBackendService:
    """Emit constrained analysis artifacts plus an optional patch candidate inside allowed_paths."""

    _SYNC_EXCLUDES = (
        ".git",
        ".venv",
        "node_modules",
        "panel/out",
        "dashboard/.next",
        ".pytest_cache",
        ".ruff_cache",
        ".masfactory_runtime",
        "logs/audit/autoresearch/jobs",
    )

    def __init__(
        self,
        repo_root: Path | None = None,
        run_root: Path | None = None,
        promotion_gate: GitPromotionGateService | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        default_run_root = Path("/tmp") / "autonomous-agent-stack" / "autoresearch-controlled"
        self._run_root = (run_root or default_run_root).resolve()
        self._promotion_gate = promotion_gate or GitPromotionGateService(
            self._repo_root,
            writer_lease=WriterLeaseService(),
        )

    def run(self, request: AutoResearchExecutionRequest) -> AutoResearchExecutionRead:
        run_id = create_resource_id("arrun")
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

        changed_files: list[str] = []
        deliverable_paths: dict[str, str] = {}
        patch_result: AutoResearchPatchResult | None = None
        exit_code = 1
        validation_exit_code: int | None = None
        validation_status = AutoResearchValidationStatus.PENDING
        status = AutoResearchRunStatus.FAILED
        error: str | None = "worker did not execute"
        promotion_preflight = None
        promotion = None
        attempts_used = 0

        for attempt in range(1, request.max_iterations + 1):
            attempts_used = attempt
            self._sync_directory(source=baseline, target=workspace, apply_excludes=False)
            self._append_log(log_file, f"\n=== attempt {attempt}/{request.max_iterations} ===\n")

            outcome, deliverable_paths = self._run_mock_backend(
                prompt=request.prompt,
                workspace=workspace,
                artifacts_dir=artifacts_dir,
                log_file=log_file,
                allowed_paths=request.allowed_paths,
                deliverables=request.deliverables,
                test_command=request.test_command,
            )
            exit_code = outcome.exit_code

            changed_files = self._collect_changed_files(base=baseline, workspace=workspace)
            self._write_patch(base=baseline, workspace=workspace, patch_file=patch_file)
            patch_result = AutoResearchPatchResult(
                patch_path=str(patch_file),
                patch_text=patch_file.read_text(encoding="utf-8") if patch_file.exists() else "",
                changed_files=changed_files,
            )

            scope_error = self._detect_scope_violation(
                changed_files=changed_files,
                allowed_paths=request.allowed_paths,
                forbidden_paths=request.forbidden_paths,
            )
            if scope_error is not None:
                status = AutoResearchRunStatus.POLICY_BLOCKED
                error = scope_error
                validation_status = AutoResearchValidationStatus.SKIPPED
                validation_exit_code = None
                break

            if not changed_files:
                error = outcome.error or "worker did not produce a patch candidate"
                validation_status = AutoResearchValidationStatus.SKIPPED
                validation_exit_code = None
            else:
                validation_exit_code, validation_status = self._run_validation(
                    command=request.test_command,
                    workspace=workspace,
                    log_file=log_file,
                )
                error = outcome.error or (
                    None
                    if validation_status is AutoResearchValidationStatus.PASSED
                    else f"test_command failed with status={validation_status.value}"
                )

            if exit_code == 0 and validation_status is AutoResearchValidationStatus.PASSED:
                status = AutoResearchRunStatus.READY_FOR_PROMOTION
                error = None
                break

        if status is AutoResearchRunStatus.READY_FOR_PROMOTION and patch_result is not None:
            if bool(request.metadata.get("skip_promotion_finalize", False)):
                self._append_log(log_file, "[promotion] finalize skipped; analysis stage is artifact-only\n")
            else:
                promotion_preflight, promotion = self._finalize_promotion(
                    run_id=run_id,
                    patch_file=Path(patch_result.patch_path),
                    changed_files=changed_files,
                    request=request,
                    validation_status=validation_status,
                    exit_code=exit_code,
                    artifacts_dir=artifacts_dir,
                )
                if not promotion.success:
                    status = AutoResearchRunStatus.NEEDS_HUMAN_REVIEW
                    error = promotion.reason or "promotion gate rejected the patch candidate"

        workspace_retained = True
        if status is AutoResearchRunStatus.READY_FOR_PROMOTION and request.cleanup_workspace_on_success:
            shutil.rmtree(workspace, ignore_errors=True)
            workspace_retained = False
        elif status is not AutoResearchRunStatus.READY_FOR_PROMOTION and not request.keep_workspace_on_failure:
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
            deliverable_paths=deliverable_paths,
            exit_code=exit_code,
            validation_status=validation_status,
            validation_exit_code=validation_exit_code,
            status=status,
            iterations_used=max(attempts_used - 1, 0),
            backend_used=request.backend,
            error=error,
            patch_result=patch_result,
            promotion_preflight=promotion_preflight,
            promotion=promotion,
        )

    def _build_result(
        self,
        *,
        run_id: str,
        request: AutoResearchExecutionRequest,
        workspace: Path,
        workspace_retained: bool,
        log_file: Path,
        artifacts_dir: Path,
        summary_file: Path,
        created_at,
        changed_files: list[str],
        deliverable_paths: dict[str, str],
        exit_code: int,
        validation_status: AutoResearchValidationStatus,
        validation_exit_code: int | None,
        status: AutoResearchRunStatus,
        iterations_used: int,
        backend_used: AutoResearchBackend,
        error: str | None,
        patch_result: AutoResearchPatchResult | None,
        promotion_preflight,
        promotion,
    ) -> AutoResearchExecutionRead:
        artifacts = [AutoResearchExecutionArtifact(kind="log", path=str(log_file))]
        if patch_result is not None:
            artifacts.append(AutoResearchExecutionArtifact(kind="patch", path=patch_result.patch_path))
        for kind, path in deliverable_paths.items():
            artifacts.append(AutoResearchExecutionArtifact(kind=kind, path=path))
        validation_dir = artifacts_dir / "validation"
        if validation_dir.exists():
            artifacts.append(AutoResearchExecutionArtifact(kind="validation", path=str(validation_dir)))
        artifacts.append(AutoResearchExecutionArtifact(kind="summary", path=str(summary_file)))

        now = utc_now()
        result = AutoResearchExecutionRead(
            run_id=run_id,
            task_id=request.task_id,
            input=request.model_dump(mode="json"),
            workspace=str(workspace),
            workspace_retained=workspace_retained,
            execution_log=str(log_file),
            artifacts=artifacts,
            deliverable_artifacts=deliverable_paths,
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

    def _finalize_promotion(
        self,
        *,
        run_id: str,
        patch_file: Path,
        changed_files: list[str],
        request: AutoResearchExecutionRequest,
        validation_status: AutoResearchValidationStatus,
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
                passed=validation_status is AutoResearchValidationStatus.PASSED,
                detail=validation_status.value,
            ),
        ]
        intent = PromotionIntent(
            run_id=run_id,
            actor_role=PromotionActorRole.AGGREGATOR,
            actor_id="aggregator",
            writer_id="autoresearch",
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

    def _run_mock_backend(
        self,
        *,
        prompt: str,
        workspace: Path,
        artifacts_dir: Path,
        log_file: Path,
        allowed_paths: list[str],
        deliverables: list[str],
        test_command: list[str],
    ) -> tuple[_AutoResearchOutcome, dict[str, str]]:
        target = self._select_target(workspace=workspace, allowed_paths=allowed_paths)
        target.parent.mkdir(parents=True, exist_ok=True)
        safe_prompt = prompt.strip().replace('"""', "'''")
        if target.suffix == ".py":
            target.write_text(
                (
                    '"""Autogenerated by the constrained AutoResearch worker."""\n\n'
                    "def plan() -> dict[str, str]:\n"
                    f'    return {{"task": "{safe_prompt}", "status": "suggested"}}\n'
                ),
                encoding="utf-8",
            )
        else:
            target.write_text(
                f"AutoResearch patch candidate\n\nTask: {safe_prompt}\n",
                encoding="utf-8",
            )

        deliverable_paths = self._write_deliverables(
            artifacts_dir=artifacts_dir,
            prompt=prompt,
            target=target.relative_to(workspace).as_posix(),
            test_command=shlex.join(test_command),
            deliverables=deliverables,
        )
        stdout = f"[autoresearch-mock] wrote patch candidate {target}\n"
        self._append_log(log_file, stdout)
        return _AutoResearchOutcome(exit_code=0, stdout=stdout), deliverable_paths

    def _write_deliverables(
        self,
        *,
        artifacts_dir: Path,
        prompt: str,
        target: str,
        test_command: str,
        deliverables: list[str],
    ) -> dict[str, str]:
        outputs: dict[str, str] = {}
        for deliverable in deliverables:
            path = artifacts_dir / f"{deliverable}.md"
            if deliverable == "execution_plan":
                content = (
                    "# Execution Plan\n\n"
                    f"- Scope target: `{target}`\n"
                    f"- Research task: {prompt}\n"
                    "- Produce the narrowest patch candidate that stays inside allowed_paths.\n"
                )
            elif deliverable == "test_plan":
                content = (
                    "# Test Plan\n\n"
                    f"- Validate with: `{test_command}`\n"
                    "- Fail closed if the suggested patch does not satisfy the validator.\n"
                )
            elif deliverable == "risk_summary":
                content = (
                    "# Risk Summary\n\n"
                    "- Keep scope limited to the requested path.\n"
                    "- Do not mutate git state, approval state, or managed skills.\n"
                    "- Promotion remains gated by aggregator and promotion gate.\n"
                )
            else:
                content = (
                    "# Patch Suggestion\n\n"
                    f"- Candidate target: `{target}`\n"
                    "- Suggested change is emitted as a patch artifact, not directly committed.\n"
                )
            path.write_text(content, encoding="utf-8")
            outputs[deliverable] = str(path)
        return outputs

    def _run_validation(
        self,
        *,
        command: list[str],
        workspace: Path,
        log_file: Path,
    ) -> tuple[int | None, AutoResearchValidationStatus]:
        validation_dir = workspace.parent / "artifacts" / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)

        completed = subprocess.run(
            command,
            cwd=workspace,
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
            return 0, AutoResearchValidationStatus.PASSED
        return completed.returncode, AutoResearchValidationStatus.FAILED

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

    def _select_target(self, *, workspace: Path, allowed_paths: list[str]) -> Path:
        for pattern in allowed_paths:
            if not any(char in pattern for char in "*?["):
                return workspace / pattern

        for pattern in allowed_paths:
            prefix = pattern.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0].rstrip("/")
            if prefix:
                if "." in Path(prefix).name:
                    return workspace / prefix
                return workspace / prefix / "autoresearch_worker_output.py"

        return workspace / "src" / "autoresearch_worker_output.py"

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
        return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)

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
            changed.add(relative.as_posix())
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
