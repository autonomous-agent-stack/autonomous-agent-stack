from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any

from autoresearch.agent_protocol.models import (
    DriverResult,
    JobSpec,
    RunSummary,
    ValidationCheck,
    ValidationReport,
)
from autoresearch.agent_protocol.decision import attempt_succeeded, derive_terminal_status
from autoresearch.agent_protocol.policy import EffectivePolicy, build_effective_policy
from autoresearch.agent_protocol.registry import AgentRegistry
from autoresearch.core.services.git_promotion_gate import GitPromotionGateService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import GitPromotionMode, PromotionActorRole, PromotionIntent

_RUNTIME_DENY_PREFIXES = (
    "logs/",
    ".masfactory_runtime/",
    "memory/",
    ".git/",
)


class AgentExecutionRunner:
    def __init__(
        self,
        repo_root: Path | None = None,
        runtime_root: Path | None = None,
        manifests_dir: Path | None = None,
        promotion_gate: GitPromotionGateService | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._runtime_root = (
            runtime_root or (self._repo_root / ".masfactory_runtime" / "runs")
        ).resolve()
        self._manifests_dir = (manifests_dir or (self._repo_root / "configs" / "agents")).resolve()
        self._registry = AgentRegistry(self._manifests_dir)
        self._promotion_gate = promotion_gate or GitPromotionGateService(
            self._repo_root,
            writer_lease=WriterLeaseService(),
        )

    def run_job(self, job: JobSpec) -> RunSummary:
        manifest = self._registry.load(job.agent_id)
        effective_policy = build_effective_policy(manifest.policy_defaults, job.policy)

        run_dir = self._runtime_root / job.run_id
        baseline_dir = run_dir / "baseline"
        workspace_dir = run_dir / "workspace"
        artifacts_dir = run_dir / "artifacts"
        job_path = run_dir / "job.json"
        policy_path = run_dir / "effective_policy.json"
        result_path = run_dir / "driver_result.json"
        summary_path = run_dir / "summary.json"
        events_path = run_dir / "events.ndjson"
        patch_path = artifacts_dir / "promotion.patch"

        if run_dir.exists():
            shutil.rmtree(run_dir)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        job_path.write_text(
            json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        policy_payload = {
            "hard": effective_policy.hard.model_dump(mode="json"),
            "manifest_default": effective_policy.manifest_default.model_dump(mode="json"),
            "job": effective_policy.job.model_dump(mode="json"),
            "merged": effective_policy.merged.model_dump(mode="json"),
        }
        policy_path.write_text(
            json.dumps(policy_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self._snapshot_repo_to_baseline(baseline_dir)

        current_agent = job.agent_id
        fallback_index = 0
        pending_attempts = 1
        attempt = 0
        forced_final_status: str | None = None

        last_result = self._contract_error_result(
            run_id=job.run_id,
            agent_id=current_agent,
            attempt=0,
            message="no attempt executed",
        )
        last_validation = ValidationReport(run_id=job.run_id, passed=False, checks=[])
        last_patch_filtered_paths: list[str] = []

        while True:
            if pending_attempts <= 0:
                if fallback_index >= len(job.fallback):
                    break
                step = job.fallback[fallback_index]
                fallback_index += 1

                if step.action == "retry":
                    pending_attempts = step.max_attempts
                    continue
                if step.action == "fallback_agent":
                    if step.agent_id:
                        current_agent = step.agent_id
                    pending_attempts = step.max_attempts
                    continue
                if step.action == "human_review":
                    forced_final_status = "human_review"
                    break
                if step.action == "reject":
                    forced_final_status = "blocked"
                    break

            attempt += 1
            pending_attempts -= 1

            self._snapshot_baseline_to_workspace(baseline_dir, workspace_dir)
            self._append_event(
                events_path,
                {
                    "type": "attempt_started",
                    "attempt": attempt,
                    "agent_id": current_agent,
                },
            )

            active_manifest = self._registry.load(current_agent)
            driver_result = self._invoke_adapter(
                manifest_entrypoint=active_manifest.entrypoint,
                run_dir=run_dir,
                workspace_dir=workspace_dir,
                artifacts_dir=artifacts_dir,
                job_path=job_path,
                result_path=result_path,
                events_path=events_path,
                baseline_dir=baseline_dir,
                run_id=job.run_id,
                agent_id=current_agent,
                attempt=attempt,
                timeout_sec=effective_policy.merged.timeout_sec,
            )
            result_path.write_text(
                json.dumps(driver_result.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            changed_paths = self._collect_changed_paths(baseline_dir, workspace_dir)
            patch_text, patch_filtered_paths, builtin_checks = self._build_filtered_patch(
                baseline_dir=baseline_dir,
                workspace_dir=workspace_dir,
                changed_paths=changed_paths,
                driver_result=driver_result,
                policy=effective_policy,
            )
            patch_path.write_text(patch_text, encoding="utf-8")

            validation = self._run_validators(
                run_id=job.run_id,
                workspace_dir=workspace_dir,
                patch_path=patch_path,
                builtin_checks=builtin_checks,
                validator_specs=job.validators,
                timeout_sec=effective_policy.merged.timeout_sec,
            )

            if not driver_result.changed_paths:
                driver_result = driver_result.model_copy(
                    update={"changed_paths": patch_filtered_paths}
                )
            last_patch_filtered_paths = patch_filtered_paths

            if self._has_policy_violation(validation):
                driver_result = driver_result.model_copy(
                    update={
                        "status": "policy_blocked",
                        "recommended_action": "reject",
                        "error": "execution produced out-of-scope or forbidden changes",
                    }
                )

            last_result = driver_result
            last_validation = validation

            self._append_event(
                events_path,
                {
                    "type": "attempt_completed",
                    "attempt": attempt,
                    "agent_id": current_agent,
                    "driver_status": driver_result.status,
                    "validation_passed": validation.passed,
                },
            )

            if attempt_succeeded(driver_result=driver_result, validation=validation):
                promotion_preflight, promotion = self._finalize_promotion(
                    job=job,
                    agent_id=current_agent,
                    patch_path=patch_path,
                    changed_files=patch_filtered_paths,
                    validation=validation,
                    policy=effective_policy,
                    artifacts_dir=artifacts_dir,
                )
                final_status = "promoted" if promotion.mode is GitPromotionMode.DRAFT_PR else "ready_for_promotion"
                if not promotion.success:
                    final_status = "blocked"
                summary = RunSummary(
                    run_id=job.run_id,
                    final_status=final_status,
                    driver_result=driver_result,
                    validation=validation,
                    promotion_patch_uri=str(patch_path),
                    promotion_preflight=promotion_preflight,
                    promotion=promotion,
                )
                summary_path.write_text(
                    json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                self._cleanup_workspace(
                    workspace_dir=workspace_dir,
                    success=True,
                    policy=effective_policy,
                )
                return summary

            if driver_result.status == "policy_blocked":
                break

        final_status = forced_final_status or derive_terminal_status(last_result, last_validation)
        summary = RunSummary(
            run_id=job.run_id,
            final_status=final_status,
            driver_result=last_result,
            validation=last_validation,
            promotion_patch_uri=str(patch_path) if patch_path.exists() else None,
            promotion_preflight=None,
            promotion=None,
        )
        summary_path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._cleanup_workspace(
            workspace_dir=workspace_dir,
            success=False,
            policy=effective_policy,
        )
        return summary

    @staticmethod
    def _has_policy_violation(validation: ValidationReport) -> bool:
        blocked_checks = {
            "builtin.allowed_paths",
            "builtin.forbidden_paths",
            "builtin.no_runtime_artifacts",
        }
        return any(check.id in blocked_checks and not check.passed for check in validation.checks)

    def _snapshot_repo_to_baseline(self, baseline_dir: Path) -> None:
        ignore = shutil.ignore_patterns(
            ".git",
            ".venv",
            "node_modules",
            ".pytest_cache",
            ".ruff_cache",
            "panel/out",
            "dashboard/.next",
            ".masfactory_runtime",
        )
        shutil.copytree(self._repo_root, baseline_dir, dirs_exist_ok=True, ignore=ignore)

    def _snapshot_baseline_to_workspace(self, baseline_dir: Path, workspace_dir: Path) -> None:
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        shutil.copytree(baseline_dir, workspace_dir, dirs_exist_ok=True)

    def _invoke_adapter(
        self,
        *,
        manifest_entrypoint: str,
        run_dir: Path,
        workspace_dir: Path,
        artifacts_dir: Path,
        job_path: Path,
        result_path: Path,
        events_path: Path,
        baseline_dir: Path,
        run_id: str,
        agent_id: str,
        attempt: int,
        timeout_sec: int,
    ) -> DriverResult:
        if result_path.exists():
            result_path.unlink()

        entrypoint = (self._repo_root / manifest_entrypoint).resolve()
        if not entrypoint.exists():
            return self._contract_error_result(
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                message=f"adapter entrypoint not found: {entrypoint}",
            )

        env = dict(os.environ)
        env.update(
            {
                "AEP_RUN_DIR": str(run_dir),
                "AEP_WORKSPACE": str(workspace_dir),
                "AEP_ARTIFACT_DIR": str(artifacts_dir),
                "AEP_JOB_SPEC": str(job_path),
                "AEP_RESULT_PATH": str(result_path),
                "AEP_EVENT_LOG": str(events_path),
                "AEP_BASELINE": str(baseline_dir),
                "AEP_ATTEMPT": str(attempt),
            }
        )

        stdout_log = artifacts_dir / "stdout.log"
        stderr_log = artifacts_dir / "stderr.log"

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                [str(entrypoint)],
                cwd=self._repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
        except subprocess.TimeoutExpired:
            return DriverResult(
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                status="timed_out",
                summary=f"adapter timed out after {timeout_sec}s",
                recommended_action="fallback",
                error=f"timeout after {timeout_sec}s",
            )

        with stdout_log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== attempt {attempt} ({agent_id}) ===\n")
            handle.write(completed.stdout or "")
        with stderr_log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== attempt {attempt} ({agent_id}) ===\n")
            handle.write(completed.stderr or "")

        if not result_path.exists():
            return self._contract_error_result(
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                message="driver_result.json missing after adapter execution",
            )

        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            result = DriverResult.model_validate(payload)
        except Exception as exc:
            return self._contract_error_result(
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                message=f"invalid driver_result.json: {exc}",
            )

        merged_metrics = result.metrics.model_copy(update={"duration_ms": duration_ms})
        result = result.model_copy(
            update={"metrics": merged_metrics, "attempt": attempt, "agent_id": agent_id}
        )

        if completed.returncode == 10 and result.status not in {"policy_blocked", "contract_error"}:
            result = result.model_copy(update={"status": "policy_blocked"})
        if completed.returncode == 30 and result.status == "succeeded":
            result = result.model_copy(update={"status": "timed_out"})
        if completed.returncode == 40:
            result = result.model_copy(update={"status": "contract_error"})

        return result

    def _collect_changed_paths(self, baseline_dir: Path, workspace_dir: Path) -> list[str]:
        base_files = self._collect_files(baseline_dir)
        workspace_files = self._collect_files(workspace_dir)
        all_paths = sorted(set(base_files) | set(workspace_files))

        changed: list[str] = []
        for rel in all_paths:
            base_path = baseline_dir / rel
            ws_path = workspace_dir / rel
            if not base_path.exists() or not ws_path.exists():
                changed.append(rel)
                continue
            if base_path.read_bytes() != ws_path.read_bytes():
                changed.append(rel)
        return changed

    def _build_filtered_patch(
        self,
        *,
        baseline_dir: Path,
        workspace_dir: Path,
        changed_paths: list[str],
        driver_result: DriverResult,
        policy: EffectivePolicy,
    ) -> tuple[str, list[str], list[ValidationCheck]]:
        checks: list[ValidationCheck] = []
        driver_succeeded = driver_result.status in {"succeeded", "partial"}
        checks.append(
            ValidationCheck(
                id="builtin.driver_success",
                passed=driver_succeeded,
                detail=driver_result.status,
            )
        )

        forbidden_changed = [
            path for path in changed_paths if self._matches_any(path, policy.merged.forbidden_paths)
        ]
        runtime_changed = [
            path for path in changed_paths if path.startswith(_RUNTIME_DENY_PREFIXES)
        ]

        allowed_changed = [
            path
            for path in changed_paths
            if self._matches_any(path, policy.merged.allowed_paths)
            and not self._matches_any(path, policy.merged.forbidden_paths)
            and not path.startswith(_RUNTIME_DENY_PREFIXES)
        ]

        checks.append(
            ValidationCheck(
                id="builtin.allowed_paths",
                passed=len(
                    [
                        p
                        for p in changed_paths
                        if p not in allowed_changed
                        and p not in forbidden_changed
                        and p not in runtime_changed
                    ]
                )
                == 0,
                detail="all changed files must be inside allowed_paths",
            )
        )
        checks.append(
            ValidationCheck(
                id="builtin.forbidden_paths",
                passed=not forbidden_changed,
                detail="; ".join(forbidden_changed) if forbidden_changed else "ok",
            )
        )
        checks.append(
            ValidationCheck(
                id="builtin.no_runtime_artifacts",
                passed=not runtime_changed,
                detail="; ".join(runtime_changed) if runtime_changed else "ok",
            )
        )
        checks.append(
            ValidationCheck(
                id="builtin.max_changed_files",
                passed=len(changed_paths) <= policy.merged.max_changed_files,
                detail=f"changed={len(changed_paths)} limit={policy.merged.max_changed_files}",
            )
        )

        binary_changed: list[str] = []
        patch_chunks: list[str] = []
        patch_line_count = 0

        for rel in allowed_changed:
            diff_text, is_binary = self._diff_single_path(
                baseline_dir / rel, workspace_dir / rel, rel
            )
            if is_binary:
                binary_changed.append(rel)
                continue
            if diff_text:
                patch_chunks.append(diff_text)
                patch_line_count += sum(
                    1
                    for line in diff_text.splitlines()
                    if line.startswith("+") or line.startswith("-")
                )

        checks.append(
            ValidationCheck(
                id="builtin.no_binary_changes",
                passed=(not binary_changed) or policy.merged.allow_binary_changes,
                detail="; ".join(binary_changed) if binary_changed else "ok",
            )
        )
        checks.append(
            ValidationCheck(
                id="builtin.max_patch_lines",
                passed=patch_line_count <= policy.merged.max_patch_lines,
                detail=f"patch_lines={patch_line_count} limit={policy.merged.max_patch_lines}",
            )
        )

        patch_text = "".join(patch_chunks)
        requires_source_change = driver_succeeded and driver_result.recommended_action == "promote"
        has_source_change = bool(patch_text.strip())
        checks.append(
            ValidationCheck(
                id="builtin.nonempty_change_for_promote",
                passed=(not requires_source_change) or has_source_change,
                detail=(
                    "ok"
                    if (not requires_source_change) or has_source_change
                    else "driver requested promotion without source changes"
                ),
            )
        )
        return patch_text, allowed_changed, checks

    def _run_validators(
        self,
        *,
        run_id: str,
        workspace_dir: Path,
        patch_path: Path,
        builtin_checks: list[ValidationCheck],
        validator_specs: list[Any],
        timeout_sec: int,
    ) -> ValidationReport:
        checks = list(builtin_checks)

        for spec in validator_specs:
            if spec.kind == "builtin":
                if not any(item.id == spec.id for item in checks):
                    checks.append(
                        ValidationCheck(
                            id=spec.id,
                            passed=False,
                            detail="unknown builtin validator id",
                        )
                    )
                continue

            if spec.kind == "human":
                checks.append(
                    ValidationCheck(
                        id=spec.id,
                        passed=False,
                        detail="requires human review",
                    )
                )
                continue

            command = (spec.command or "").strip()
            if not command:
                checks.append(
                    ValidationCheck(
                        id=spec.id,
                        passed=False,
                        detail="empty command validator",
                    )
                )
                continue

            try:
                completed = subprocess.run(
                    command,
                    cwd=workspace_dir,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                passed = completed.returncode == 0
                detail = (completed.stdout or completed.stderr or "").strip()
                checks.append(
                    ValidationCheck(
                        id=spec.id,
                        passed=passed,
                        detail=detail[:1000],
                    )
                )
            except subprocess.TimeoutExpired:
                checks.append(
                    ValidationCheck(
                        id=spec.id,
                        passed=False,
                        detail=f"validator timed out after {timeout_sec}s",
                    )
                )

        passed = all(check.passed for check in checks)
        return ValidationReport(run_id=run_id, passed=passed, checks=checks)

    @staticmethod
    def _contract_error_result(
        *,
        run_id: str,
        agent_id: str,
        attempt: int,
        message: str,
    ) -> DriverResult:
        return DriverResult(
            run_id=run_id,
            agent_id=agent_id,
            attempt=attempt,
            status="contract_error",
            summary=message,
            recommended_action="reject",
            error=message,
        )

    def _finalize_promotion(
        self,
        *,
        job: JobSpec,
        agent_id: str,
        patch_path: Path,
        changed_files: list[str],
        validation: ValidationReport,
        policy: EffectivePolicy,
        artifacts_dir: Path,
    ):
        preferred_mode = GitPromotionMode(
            str(
                job.metadata.get("pipeline_target")
                or job.metadata.get("promotion_mode")
                or GitPromotionMode.PATCH.value
            )
        )
        base_branch = str(job.metadata.get("base_branch") or "main")
        intent = PromotionIntent(
            run_id=job.run_id,
            actor_role=PromotionActorRole.AGGREGATOR,
            actor_id="aggregator",
            writer_id=agent_id,
            writer_lease_key=f"writer:{job.run_id}",
            patch_uri=str(patch_path),
            changed_files=changed_files,
            base_ref=self._git_ref(["rev-parse", "HEAD"], default="nogit"),
            preferred_mode=preferred_mode,
            target_base_branch=base_branch,
            approval_granted=bool(job.metadata.get("approval_granted", False)),
            metadata={
                "branch_name": self._sanitize_branch_name(
                    str(job.metadata.get("branch_name") or f"autoprom/{job.run_id}")
                ),
                "commit_message": str(job.metadata.get("commit_message") or f"Promotion for {job.run_id}"),
                "pr_title": str(job.metadata.get("pr_title") or f"Promotion for {job.run_id}"),
                "pr_body": str(job.metadata.get("pr_body") or "Automated promotion draft PR."),
                "validator_commands": [
                    str(spec.command).strip()
                    for spec in job.validators
                    if getattr(spec, "kind", None) == "command" and (spec.command or "").strip()
                ],
                "allowed_paths": list(policy.merged.allowed_paths),
                "forbidden_paths": list(policy.merged.forbidden_paths),
                "max_changed_files": policy.merged.max_changed_files,
                "max_patch_lines": policy.merged.max_patch_lines,
                "allow_binary_changes": policy.merged.allow_binary_changes,
            },
        )
        return self._promotion_gate.finalize(
            intent=intent,
            artifacts_dir=artifacts_dir,
            validation_checks=validation.checks,
        )

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        normalized = path.replace("\\", "/")
        pure = PurePosixPath(normalized)
        for pattern in patterns:
            if pure.match(pattern) or fnmatch.fnmatch(normalized, pattern):
                return True
        return False

    @staticmethod
    def _collect_files(root: Path) -> list[str]:
        files: list[str] = []
        if not root.exists():
            return files
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            files.append(path.relative_to(root).as_posix())
        return files

    def _diff_single_path(
        self, base_path: Path, workspace_path: Path, rel_path: str
    ) -> tuple[str, bool]:
        base_lines, base_binary = self._read_text_lines(base_path)
        ws_lines, ws_binary = self._read_text_lines(workspace_path)

        if base_binary or ws_binary:
            return "", True

        diff = list(
            difflib.unified_diff(
                base_lines,
                ws_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm="",
            )
        )
        if not diff:
            return "", False
        return "\n".join(diff) + "\n", False

    @staticmethod
    def _read_text_lines(path: Path) -> tuple[list[str], bool]:
        if not path.exists():
            return [], False
        raw = path.read_bytes()
        if b"\x00" in raw:
            return [], True
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return [], True
        return text.splitlines(), False

    @staticmethod
    def _append_event(events_path: Path, payload: dict[str, Any]) -> None:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

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

    @staticmethod
    def _sanitize_branch_name(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9._/-]+", "-", value.strip()).strip("-./")
        return normalized or "autoprom/run"

    @staticmethod
    def _cleanup_workspace(*, workspace_dir: Path, success: bool, policy: EffectivePolicy) -> None:
        if success and policy.merged.cleanup_on_success:
            shutil.rmtree(workspace_dir, ignore_errors=True)
            return
        if not success and not policy.merged.retain_workspace_on_failure:
            shutil.rmtree(workspace_dir, ignore_errors=True)
