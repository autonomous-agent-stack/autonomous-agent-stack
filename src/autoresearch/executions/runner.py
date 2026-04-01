from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

from autoresearch.agent_protocol.models import (
    DriverMetrics,
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
from autoresearch.executions.failure_classifier import classify_failure
from autoresearch.shared.models import GitPromotionMode, PromotionActorRole, PromotionIntent

_RUNTIME_DENY_PREFIXES = (
    "logs/",
    ".masfactory_runtime/",
    "memory/",
    ".git/",
)

_AI_LAB_ENV_OVERRIDE_KEYS = (
    "ENV_FILE",
    "OPENHANDS_ENV_FILE",
    "COMPOSE_DIR",
    "COMPOSE_FILE",
    "WORKSPACE_DIR",
    "LOG_DIR",
    "CACHE_DIR",
    "LAB_USER",
    "AUTO_OPEN_DOCKER",
    "AUTO_START_COLIMA",
    "AI_LAB_IMAGE_TAG",
    "AI_LAB_FORCE_DOCKER_RUN",
    "AI_LAB_HOST_MOUNT_ROOT",
    "OPENHANDS_HOME_DIR",
    "DOCKER_HOST_SOCKET_PATH",
    "DOCKER_HOST_IN_CONTAINER",
    "DOCKER_HOST_MOUNT_DIR",
    "AI_LAB_COLIMA_HELPER",
)


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

    def _uses_openhands_ai_lab_runtime(self, manifest_entrypoint: str) -> bool:
        if Path(manifest_entrypoint).name != "openhands_adapter.sh":
            return False
        runtime = str(os.environ.get("OPENHANDS_RUNTIME") or "ai-lab").strip().lower()
        return runtime == "ai-lab"

    def _build_openhands_ai_lab_env(self) -> dict[str, str]:
        env = dict(os.environ)
        for key in _AI_LAB_ENV_OVERRIDE_KEYS:
            env.pop(key, None)
        env_file = str(self._repo_root / "ai_lab.env")
        env["ENV_FILE"] = env_file
        env["OPENHANDS_ENV_FILE"] = env_file
        return env

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
        run_dir_created = time.time()

        if run_dir.exists():
            self._rmtree_force(run_dir)
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
        cleanup_success = False
        final_summary: RunSummary | None = None

        last_result = self._contract_error_result(
            run_id=job.run_id,
            agent_id=current_agent,
            attempt=0,
            message="no attempt executed",
        )
        last_validation = ValidationReport(run_id=job.run_id, passed=False, checks=[])
        last_patch_filtered_paths: list[str] = []

        try:
            while True:
                if pending_attempts <= 0:
                    if fallback_index >= len(job.fallback):
                        break
                    step = job.fallback[fallback_index]
                    fallback_index += 1

                    if step.action == "retry":
                        skip_retry_reason = self._retry_skip_reason(last_result)
                        if skip_retry_reason is not None:
                            self._append_event(
                                events_path,
                                {
                                    "type": "fallback_skipped",
                                    "attempt": attempt,
                                    "agent_id": current_agent,
                                    "action": "retry",
                                    "reason": skip_retry_reason,
                                },
                            )
                            continue
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

                active_manifest = self._registry.load(current_agent)
                preflight_error = self._preflight_agent_environment(
                    agent_id=current_agent,
                    manifest_entrypoint=active_manifest.entrypoint,
                )
                if preflight_error is not None:
                    driver_result = self._contract_error_result(
                        run_id=job.run_id,
                        agent_id=current_agent,
                        attempt=attempt,
                        message=preflight_error,
                        recommended_action="fallback",
                    )
                    last_result = driver_result
                    last_validation = ValidationReport(run_id=job.run_id, passed=False, checks=[])
                    self._append_event(
                        events_path,
                        {
                            "type": "attempt_blocked",
                            "attempt": attempt,
                            "agent_id": current_agent,
                            "reason": "environment_preflight_failed",
                            "detail": preflight_error,
                        },
                    )
                    self._append_event(
                        events_path,
                        {
                            "type": "attempt_completed",
                            "attempt": attempt,
                            "agent_id": current_agent,
                            "driver_status": driver_result.status,
                            "validation_passed": False,
                        },
                    )
                    continue

                attempt_job = self._job_for_attempt(
                    job=job,
                    agent_id=current_agent,
                    attempt=attempt,
                    last_result=last_result,
                    last_validation=last_validation,
                )
                job_path.write_text(
                    json.dumps(attempt_job.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                self._snapshot_baseline_to_workspace(baseline_dir, workspace_dir)
                self._prepare_shadow_workspace(workspace_dir, effective_policy)
                self._append_event(
                    events_path,
                    {
                        "type": "attempt_started",
                        "attempt": attempt,
                        "agent_id": current_agent,
                    },
                )

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
                    policy=effective_policy,
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
                    final_status = (
                        "promoted"
                        if promotion.mode is GitPromotionMode.DRAFT_PR
                        else "ready_for_promotion"
                    )
                    if not promotion.success:
                        final_status = "blocked"
                    final_summary = RunSummary(
                        run_id=job.run_id,
                        final_status=final_status,
                        driver_result=driver_result,
                        validation=validation,
                        promotion_patch_uri=str(patch_path),
                        promotion_preflight=promotion_preflight,
                        promotion=promotion,
                        failure_status=classify_failure(
                            driver_result=driver_result,
                            validation=validation,
                            metadata=job.metadata,
                        ).failure_status,
                        failure_layer=self._infer_failure_layer(final_status, driver_result, validation),
                        failure_stage=self._infer_failure_stage(driver_result, validation),
                        model_provider=self._infer_model_provider(job),
                        fallback_chain=self._build_fallback_chain(job),
                        first_progress_at=self._format_progress_at(run_dir_created, driver_result.metrics.first_progress_ms),
                        last_progress_at=self._format_progress_at(run_dir_created, driver_result.metrics.duration_ms),
                        run_dir_created=self._format_timestamp(run_dir_created),
                        artifacts_produced=self._build_artifacts_produced(
                            summary_path=summary_path,
                            job_path=job_path,
                            policy_path=policy_path,
                            result_path=result_path,
                            events_path=events_path,
                            patch_path=patch_path,
                        ),
                        business_assertion_status=self._build_business_assertion_status(validation),
                    )
                    cleanup_success = True
                    break

                if driver_result.status == "policy_blocked":
                    break

            if final_summary is None:
                final_status = forced_final_status or derive_terminal_status(last_result, last_validation)
                final_summary = RunSummary(
                    run_id=job.run_id,
                    final_status=final_status,
                    driver_result=last_result,
                    validation=last_validation,
                    promotion_patch_uri=str(patch_path) if patch_path.exists() else None,
                    promotion_preflight=None,
                    promotion=None,
                    failure_status=classify_failure(
                        driver_result=last_result,
                        validation=last_validation,
                        metadata=job.metadata,
                    ).failure_status,
                    failure_layer=self._infer_failure_layer(final_status, last_result, last_validation),
                    failure_stage=self._infer_failure_stage(last_result, last_validation),
                    model_provider=self._infer_model_provider(job),
                    fallback_chain=self._build_fallback_chain(job),
                    first_progress_at=self._format_progress_at(
                        run_dir_created, last_result.metrics.first_progress_ms
                    ),
                    last_progress_at=self._format_progress_at(
                        run_dir_created, last_result.metrics.duration_ms
                    ),
                    run_dir_created=self._format_timestamp(run_dir_created),
                    artifacts_produced=self._build_artifacts_produced(
                        summary_path=summary_path,
                        job_path=job_path,
                        policy_path=policy_path,
                        result_path=result_path,
                        events_path=events_path,
                        patch_path=patch_path if patch_path.exists() else None,
                    ),
                    business_assertion_status=self._build_business_assertion_status(last_validation),
                )
        except Exception as exc:
            error_message = f"runner crashed: {exc.__class__.__name__}: {exc}"
            last_result = self._contract_error_result(
                run_id=job.run_id,
                agent_id=current_agent,
                attempt=attempt or 1,
                message=error_message,
            )
            self._append_event(
                events_path,
                {
                    "type": "runner_exception",
                    "attempt": attempt,
                    "agent_id": current_agent,
                    "detail": error_message,
                },
            )
            final_summary = RunSummary(
                run_id=job.run_id,
                final_status="failed",
                driver_result=last_result,
                validation=last_validation,
                promotion_patch_uri=str(patch_path) if patch_path.exists() else None,
                promotion_preflight=None,
                promotion=None,
                failure_status=classify_failure(
                    driver_result=last_result,
                    validation=last_validation,
                    metadata=job.metadata,
                ).failure_status,
                failure_layer=self._infer_failure_layer("failed", last_result, last_validation),
                failure_stage=self._infer_failure_stage(last_result, last_validation),
                model_provider=self._infer_model_provider(job),
                fallback_chain=self._build_fallback_chain(job),
                first_progress_at=self._format_progress_at(
                    run_dir_created, last_result.metrics.first_progress_ms
                ),
                last_progress_at=self._format_progress_at(
                    run_dir_created, last_result.metrics.duration_ms
                ),
                run_dir_created=self._format_timestamp(run_dir_created),
                artifacts_produced=self._build_artifacts_produced(
                    summary_path=summary_path,
                    job_path=job_path,
                    policy_path=policy_path,
                    result_path=result_path,
                    events_path=events_path,
                    patch_path=patch_path if patch_path.exists() else None,
                ),
                business_assertion_status=self._build_business_assertion_status(last_validation),
            )
        finally:
            if final_summary is None:
                final_summary = RunSummary(
                    run_id=job.run_id,
                    final_status=forced_final_status or derive_terminal_status(last_result, last_validation),
                    driver_result=last_result,
                    validation=last_validation,
                    promotion_patch_uri=str(patch_path) if patch_path.exists() else None,
                    promotion_preflight=None,
                    promotion=None,
                    failure_status=classify_failure(
                        driver_result=last_result,
                        validation=last_validation,
                        metadata=job.metadata,
                    ).failure_status,
                    failure_layer=self._infer_failure_layer(
                        forced_final_status or derive_terminal_status(last_result, last_validation),
                        last_result,
                        last_validation,
                    ),
                    failure_stage=self._infer_failure_stage(last_result, last_validation),
                    model_provider=self._infer_model_provider(job),
                    fallback_chain=self._build_fallback_chain(job),
                    first_progress_at=self._format_progress_at(
                        run_dir_created, last_result.metrics.first_progress_ms
                    ),
                    last_progress_at=self._format_progress_at(
                        run_dir_created, last_result.metrics.duration_ms
                    ),
                    run_dir_created=self._format_timestamp(run_dir_created),
                    artifacts_produced=self._build_artifacts_produced(
                        summary_path=summary_path,
                        job_path=job_path,
                        policy_path=policy_path,
                        result_path=result_path,
                        events_path=events_path,
                        patch_path=patch_path if patch_path.exists() else None,
                    ),
                    business_assertion_status=self._build_business_assertion_status(last_validation),
                )
            self._write_summary(summary_path=summary_path, summary=final_summary)
            self._cleanup_workspace(
                workspace_dir=workspace_dir,
                success=cleanup_success,
                policy=effective_policy,
            )

        return final_summary

    @staticmethod
    def _write_summary(*, summary_path: Path, summary: RunSummary) -> None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _format_timestamp(epoch_seconds: float) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(epoch_seconds))

    def _format_progress_at(self, run_dir_created: float, progress_ms: int | None) -> str | None:
        if progress_ms is None:
            return None
        return self._format_timestamp(run_dir_created + (progress_ms / 1000.0))

    @staticmethod
    def _infer_model_provider(job: JobSpec) -> str | None:
        provider = str(job.metadata.get("model_provider") or "").strip()
        return provider or None

    @staticmethod
    def _build_fallback_chain(job: JobSpec) -> list[str]:
        chain = [job.agent_id]
        chain.extend(step.agent_id for step in job.fallback if step.agent_id)
        return chain

    @staticmethod
    def _build_business_assertion_status(validation: ValidationReport) -> str:
        return "passed" if validation.passed else "failed"

    @staticmethod
    def _infer_failure_stage(driver_result: DriverResult, validation: ValidationReport) -> str | None:
        if not validation.passed:
            for check in validation.checks:
                if not check.passed:
                    return check.id
            return "validation"
        if driver_result.status == "contract_error":
            return "adapter"
        if driver_result.status in {"timed_out", "stalled_no_progress"}:
            return driver_result.status
        if driver_result.status == "policy_blocked":
            return "policy"
        if driver_result.status == "failed":
            return "driver"
        return None

    @staticmethod
    def _infer_failure_layer(
        final_status: str,
        driver_result: DriverResult,
        validation: ValidationReport,
    ) -> str | None:
        if validation.checks and not validation.passed:
            return "business_validation"
        if final_status in {"blocked", "human_review"}:
            return "orchestration"
        if driver_result.status in {"contract_error", "timed_out", "stalled_no_progress"}:
            return "infra"
        if driver_result.status == "failed":
            return "model"
        return None

    @staticmethod
    def _build_artifacts_produced(
        *,
        summary_path: Path,
        job_path: Path,
        policy_path: Path,
        result_path: Path,
        events_path: Path,
        patch_path: Path | None,
    ) -> list[str]:
        produced = [str(path) for path in (summary_path, job_path, policy_path, result_path, events_path) if path.exists()]
        if patch_path is not None and patch_path.exists():
            produced.append(str(patch_path))
        return produced

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
            self._rmtree_force(workspace_dir)
        shutil.copytree(baseline_dir, workspace_dir, dirs_exist_ok=True)

    def _prepare_shadow_workspace(self, workspace_dir: Path, policy: EffectivePolicy) -> None:
        if not workspace_dir.exists():
            return

        self._apply_mode_tree(workspace_dir, file_mode=0o444, dir_mode=0o555)

        writable_paths: set[Path] = set()
        for pattern in policy.merged.allowed_paths:
            writable_paths.update(self._resolve_writable_targets(workspace_dir, pattern))

        for target in sorted(writable_paths, key=lambda item: (len(item.parts), str(item))):
            self._make_target_writable(workspace_dir, target)

        locked_paths: set[Path] = set()
        for pattern in policy.merged.forbidden_paths:
            locked_paths.update(self._resolve_matching_paths(workspace_dir, pattern))

        for target in sorted(locked_paths, key=lambda item: len(item.parts), reverse=True):
            self._make_target_read_only(target)

    def _resolve_writable_targets(self, workspace_dir: Path, pattern: str) -> set[Path]:
        normalized = pattern.replace("\\", "/").strip("/")
        if not normalized:
            return set()

        targets = self._resolve_matching_paths(workspace_dir, normalized)
        if targets:
            return targets

        prefix = self._glob_prefix(normalized)
        if prefix:
            candidate = workspace_dir / prefix
            if candidate.exists():
                return {candidate}
            return {candidate}

        candidate = workspace_dir / normalized
        if candidate.exists():
            return {candidate}
        return {candidate}

    def _resolve_matching_paths(self, workspace_dir: Path, pattern: str) -> set[Path]:
        normalized = pattern.replace("\\", "/").strip("/")
        if not normalized:
            return set()

        matched: set[Path] = set()
        for path in [workspace_dir, *workspace_dir.rglob("*")]:
            rel = path.relative_to(workspace_dir).as_posix() if path != workspace_dir else "."
            if rel == ".":
                continue
            if self._matches_any(rel, [normalized]):
                matched.add(path)
        return matched

    @staticmethod
    def _nearest_existing_ancestor(workspace_dir: Path, candidate: Path) -> Path:
        probe = candidate
        while probe != workspace_dir and not probe.exists():
            probe = probe.parent
        if probe.exists():
            return probe
        return workspace_dir

    def _make_target_writable(self, workspace_dir: Path, target: Path) -> None:
        for ancestor in reversed(target.parents):
            if ancestor == workspace_dir.parent or ancestor == target:
                continue
            if workspace_dir not in ancestor.parents and ancestor != workspace_dir:
                continue
            if ancestor.exists():
                self._chmod_path(ancestor, 0o777)

        if target.is_dir():
            self._apply_mode_tree(target, file_mode=0o666, dir_mode=0o777)
            return

        if target.exists():
            self._chmod_path(target, 0o666)
            if target.parent.exists():
                self._chmod_path(target.parent, 0o777)
            return

        self._ensure_writable_path_chain(workspace_dir=workspace_dir, target=target)
        if not target.suffix:
            try:
                target.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            if target.exists() and target.is_dir():
                self._apply_mode_tree(target, file_mode=0o666, dir_mode=0o777)
                return

        if target.parent.exists():
            self._chmod_path(target.parent, 0o777)

    def _ensure_writable_path_chain(self, *, workspace_dir: Path, target: Path) -> None:
        self._chmod_path(workspace_dir, 0o777)
        try:
            relative_target = target.relative_to(workspace_dir)
        except ValueError:
            return

        chain_parts = relative_target.parts if not target.suffix else relative_target.parts[:-1]
        current = workspace_dir
        for part in chain_parts:
            current = current / part
            if not current.exists():
                try:
                    current.mkdir(exist_ok=True)
                except OSError:
                    return
            self._chmod_path(current, 0o777)

    def _make_target_read_only(self, target: Path) -> None:
        if target.is_dir():
            self._apply_mode_tree(target, file_mode=0o444, dir_mode=0o555)
            return
        if target.exists():
            self._chmod_path(target, 0o444)
            if target.parent.exists():
                self._chmod_path(target.parent, 0o555)

    def _apply_mode_tree(self, root: Path, *, file_mode: int, dir_mode: int) -> None:
        if not root.exists():
            return
        if root.is_dir():
            self._chmod_path(root, dir_mode)
            for path in root.rglob("*"):
                if path.is_dir():
                    self._chmod_path(path, dir_mode)
                else:
                    self._chmod_path(path, file_mode)
            return
        self._chmod_path(root, file_mode)

    @staticmethod
    def _chmod_path(path: Path, mode: int) -> None:
        try:
            path.chmod(mode)
        except OSError:
            return

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
        policy: EffectivePolicy,
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

        if self._uses_openhands_ai_lab_runtime(manifest_entrypoint):
            env = self._build_openhands_ai_lab_env()
        else:
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
        completed: subprocess.CompletedProcess[str] | None = None
        probe_signature: tuple[tuple[str, int, int], ...] | None = None
        last_probed_signature: tuple[tuple[str, int, int], ...] | None = None
        stable_polls = 0
        stall_timeout_sec = self._stall_progress_timeout_sec(timeout_sec)
        last_scoped_progress_signature = self._scoped_progress_signature(
            baseline_dir=baseline_dir,
            workspace_dir=workspace_dir,
            allowed_paths=policy.merged.allowed_paths,
        )
        last_state_progress_signature = self._runtime_heartbeat_signature(workspace_dir=workspace_dir)
        last_log_progress_signature = self._log_progress_signature(
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        last_progress_at = started
        first_progress_ms: int | None = None
        first_scoped_write_ms: int | None = None
        first_state_heartbeat_ms: int | None = None
        first_log_progress_ms: int | None = None
        process_group_id: int | None = None

        with stdout_log.open("a", encoding="utf-8") as stdout_handle, stderr_log.open(
            "a", encoding="utf-8"
        ) as stderr_handle:
            stdout_handle.write(f"\n=== attempt {attempt} ({agent_id}) ===\n")
            stderr_handle.write(f"\n=== attempt {attempt} ({agent_id}) ===\n")
            stdout_handle.flush()
            stderr_handle.flush()

            process = subprocess.Popen(
                [str(entrypoint)],
                cwd=self._repo_root,
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                start_new_session=True,
            )
            if hasattr(os, "getpgid"):
                try:
                    process_group_id = os.getpgid(process.pid)
                except OSError:
                    process_group_id = None

            while True:
                returncode = process.poll()
                now = time.perf_counter()
                duration_ms = int((now - started) * 1000)
                if returncode is not None:
                    completed = subprocess.CompletedProcess(
                        args=[str(entrypoint)],
                        returncode=returncode,
                        stdout="",
                        stderr="",
                    )
                    break

                if duration_ms >= timeout_sec * 1000:
                    self._terminate_process(process, process_group_id=process_group_id)
                    return DriverResult(
                        run_id=run_id,
                        agent_id=agent_id,
                        attempt=attempt,
                        status="timed_out",
                        summary=f"adapter timed out after {timeout_sec}s",
                        metrics=DriverMetrics(
                            duration_ms=duration_ms,
                            first_progress_ms=first_progress_ms,
                            first_scoped_write_ms=first_scoped_write_ms,
                            first_state_heartbeat_ms=first_state_heartbeat_ms,
                        ),
                        recommended_action="fallback",
                        error=f"timeout after {timeout_sec}s",
                    )

                current_scoped_progress_signature = self._scoped_progress_signature(
                    baseline_dir=baseline_dir,
                    workspace_dir=workspace_dir,
                    allowed_paths=policy.merged.allowed_paths,
                )
                current_state_progress_signature = self._runtime_heartbeat_signature(
                    workspace_dir=workspace_dir,
                )
                current_log_progress_signature = self._log_progress_signature(
                    stdout_log=stdout_log,
                    stderr_log=stderr_log,
                )
                scoped_progress_changed = (
                    current_scoped_progress_signature != last_scoped_progress_signature
                )
                state_progress_changed = (
                    current_state_progress_signature != last_state_progress_signature
                )
                log_progress_changed = current_log_progress_signature != last_log_progress_signature
                if scoped_progress_changed or state_progress_changed or log_progress_changed:
                    if (
                        scoped_progress_changed
                        and first_scoped_write_ms is None
                        and current_scoped_progress_signature
                    ):
                        first_scoped_write_ms = duration_ms
                    if (
                        state_progress_changed
                        and first_state_heartbeat_ms is None
                        and current_state_progress_signature
                    ):
                        first_state_heartbeat_ms = duration_ms
                    if (
                        log_progress_changed
                        and first_log_progress_ms is None
                        and current_log_progress_signature
                    ):
                        first_log_progress_ms = duration_ms
                    if first_progress_ms is None:
                        first_candidates = [
                            value
                            for value in (
                                first_scoped_write_ms,
                                first_state_heartbeat_ms,
                                first_log_progress_ms,
                            )
                            if value is not None
                        ]
                        if first_candidates:
                            first_progress_ms = min(first_candidates)
                    last_scoped_progress_signature = current_scoped_progress_signature
                    last_state_progress_signature = current_state_progress_signature
                    last_log_progress_signature = current_log_progress_signature
                    last_progress_at = now
                elif (now - last_progress_at) >= stall_timeout_sec:
                    self._terminate_process(process, process_group_id=process_group_id)
                    stall_error = f"no workspace progress for {stall_timeout_sec}s"
                    return DriverResult(
                        run_id=run_id,
                        agent_id=agent_id,
                        attempt=attempt,
                        status="stalled_no_progress",
                        summary=f"adapter stalled after {stall_timeout_sec}s without workspace progress",
                        metrics=DriverMetrics(
                            duration_ms=duration_ms,
                            first_progress_ms=first_progress_ms,
                            first_scoped_write_ms=first_scoped_write_ms,
                            first_state_heartbeat_ms=first_state_heartbeat_ms,
                        ),
                        recommended_action="fallback",
                        error=stall_error,
                    )

                current_signature, current_paths = self._changed_python_signature(
                    baseline_dir=baseline_dir,
                    workspace_dir=workspace_dir,
                    allowed_paths=policy.merged.allowed_paths,
                )
                if current_signature and current_signature == probe_signature:
                    stable_polls += 1
                elif current_signature:
                    probe_signature = current_signature
                    stable_polls = 1
                else:
                    probe_signature = None
                    stable_polls = 0

                if (
                    current_signature
                    and stable_polls >= 2
                    and current_signature != last_probed_signature
                ):
                    probe_failure = self._run_fast_fail_probe(
                        workspace_dir=workspace_dir,
                        changed_python_paths=current_paths,
                    )
                    last_probed_signature = current_signature
                    if probe_failure is not None:
                        self._terminate_process(process, process_group_id=process_group_id)
                        return DriverResult(
                            run_id=run_id,
                            agent_id=agent_id,
                            attempt=attempt,
                            status="failed",
                            summary="adapter aborted by fast-fail probe",
                            changed_paths=self._collect_changed_paths(baseline_dir, workspace_dir),
                            metrics=DriverMetrics(
                                duration_ms=duration_ms,
                                first_progress_ms=first_progress_ms,
                                first_scoped_write_ms=first_scoped_write_ms,
                                first_state_heartbeat_ms=first_state_heartbeat_ms,
                            ),
                            recommended_action="fallback",
                            error=probe_failure,
                        )

                time.sleep(2)

        duration_ms = int((time.perf_counter() - started) * 1000)
        if completed is None:
            return self._contract_error_result(
                run_id=run_id,
                agent_id=agent_id,
                attempt=attempt,
                message="adapter process exited without completion record",
            )

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

        merged_metrics = result.metrics.model_copy(
            update={
                "duration_ms": duration_ms,
                "first_progress_ms": (
                    result.metrics.first_progress_ms
                    if result.metrics.first_progress_ms is not None
                    else first_progress_ms
                ),
                "first_scoped_write_ms": (
                    result.metrics.first_scoped_write_ms
                    if result.metrics.first_scoped_write_ms is not None
                    else first_scoped_write_ms
                ),
                "first_state_heartbeat_ms": (
                    result.metrics.first_state_heartbeat_ms
                    if result.metrics.first_state_heartbeat_ms is not None
                    else first_state_heartbeat_ms
                ),
            }
        )
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

        relevant_changed = [path for path in changed_paths if not _is_benign_runtime_artifact(path)]
        forbidden_changed = [
            path for path in relevant_changed if self._matches_any(path, policy.merged.forbidden_paths)
        ]
        runtime_changed = [
            path for path in relevant_changed if path.startswith(_RUNTIME_DENY_PREFIXES)
        ]

        allowed_changed = [
            path
            for path in relevant_changed
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
                        for p in relevant_changed
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
                passed=len(relevant_changed) <= policy.merged.max_changed_files,
                detail=f"changed={len(relevant_changed)} limit={policy.merged.max_changed_files}",
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

    def _meaningful_progress_signature(
        self,
        *,
        baseline_dir: Path,
        workspace_dir: Path,
        allowed_paths: list[str],
    ) -> tuple[tuple[str, int, int], ...]:
        return self._scoped_progress_signature(
            baseline_dir=baseline_dir,
            workspace_dir=workspace_dir,
            allowed_paths=allowed_paths,
        ) + self._state_heartbeat_signature(workspace_dir=workspace_dir)

    def _scoped_progress_signature(
        self,
        *,
        baseline_dir: Path,
        workspace_dir: Path,
        allowed_paths: list[str],
    ) -> tuple[tuple[str, int, int], ...]:
        items: list[tuple[str, int, int]] = []
        changed_paths = self._collect_changed_paths(baseline_dir, workspace_dir)
        for rel in sorted(changed_paths):
            if not self._matches_any(rel, allowed_paths):
                continue
            path = workspace_dir / rel
            if not path.exists():
                items.append((f"delete:{rel}", 0, 0))
                continue
            stat = path.stat()
            items.append((f"change:{rel}", stat.st_mtime_ns, stat.st_size))
        return tuple(items)

    def _state_heartbeat_signature(
        self,
        *,
        workspace_dir: Path,
    ) -> tuple[tuple[str, int, int], ...]:
        items: list[tuple[str, int, int]] = []
        state_root = workspace_dir / ".openhands-state"
        if state_root.exists():
            for path in sorted(candidate for candidate in state_root.rglob("*") if candidate.is_file()):
                stat = path.stat()
                items.append(
                    (
                        f"state:{path.relative_to(workspace_dir).as_posix()}",
                        stat.st_mtime_ns,
                        stat.st_size,
                    )
                )
        return tuple(items)

    def _runtime_heartbeat_signature(
        self,
        *,
        workspace_dir: Path,
    ) -> tuple[tuple[str, int, int], ...]:
        return self._state_heartbeat_signature(workspace_dir=workspace_dir)

    @staticmethod
    def _log_progress_signature(*, stdout_log: Path, stderr_log: Path) -> tuple[int, int, int, int]:
        def _stat(path: Path) -> tuple[int, int]:
            try:
                stat_result = path.stat()
            except FileNotFoundError:
                return (0, 0)
            return (int(stat_result.st_size), int(stat_result.st_mtime_ns))

        stdout_size, stdout_mtime = _stat(stdout_log)
        stderr_size, stderr_mtime = _stat(stderr_log)
        return (stdout_size, stdout_mtime, stderr_size, stderr_mtime)

    def _changed_python_signature(
        self,
        *,
        baseline_dir: Path,
        workspace_dir: Path,
        allowed_paths: list[str],
    ) -> tuple[tuple[tuple[str, int, int], ...] | None, list[str]]:
        changed_paths = self._collect_changed_paths(baseline_dir, workspace_dir)
        python_paths = [
            path
            for path in changed_paths
            if path.endswith(".py")
            and path.startswith(("src/", "tests/"))
            and self._matches_any(path, allowed_paths)
        ]
        if not python_paths:
            return None, []

        signature_items: list[tuple[str, int, int]] = []
        for rel in sorted(python_paths):
            path = workspace_dir / rel
            if not path.exists():
                continue
            stat = path.stat()
            signature_items.append((rel, stat.st_mtime_ns, stat.st_size))
        if not signature_items:
            return None, []
        return tuple(signature_items), [item[0] for item in signature_items]

    def _run_fast_fail_probe(
        self,
        *,
        workspace_dir: Path,
        changed_python_paths: list[str],
    ) -> str | None:
        if not changed_python_paths:
            return None

        compile_probe = subprocess.run(
            [sys.executable, "-m", "py_compile", *changed_python_paths],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        compile_detail = (compile_probe.stderr or compile_probe.stdout or "").strip()
        if compile_probe.returncode != 0 and "SyntaxError" in compile_detail:
            return compile_detail[:2000]

        importable_modules: list[str] = []
        for rel in changed_python_paths:
            if not rel.startswith("src/"):
                continue
            module_parts = list(Path(rel).with_suffix("").parts[1:])
            if module_parts and module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]
            if module_parts:
                importable_modules.append(".".join(module_parts))

        if not importable_modules:
            return None

        import_probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib, sys; "
                    "mods = sys.argv[1:]; "
                    "[(importlib.import_module(name), None) for name in mods]"
                ),
                *importable_modules,
            ],
            cwd=workspace_dir,
            env={
                **os.environ,
                "PYTHONPATH": str(workspace_dir / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True,
            text=True,
            check=False,
        )
        import_detail = (import_probe.stderr or import_probe.stdout or "").strip()
        if import_probe.returncode != 0 and any(
            token in import_detail for token in ("ModuleNotFoundError", "ImportError", "SyntaxError")
        ):
            return import_detail[:2000]
        return None

    @staticmethod
    def _stall_progress_timeout_sec(timeout_sec: int) -> int:
        return min(timeout_sec, min(180, max(60, max(1, timeout_sec // 4))))

    def _preflight_agent_environment(self, *, agent_id: str, manifest_entrypoint: str) -> str | None:
        if agent_id != "openhands":
            return None
        if Path(manifest_entrypoint).name != "openhands_adapter.sh":
            return None
        if str(os.environ.get("OPENHANDS_DRY_RUN") or "0").strip() == "1":
            return None

        if not self._uses_openhands_ai_lab_runtime(manifest_entrypoint):
            return None
        preflight_env = self._build_openhands_ai_lab_env()

        override_command = str(os.environ.get("OPENHANDS_PREFLIGHT_CMD") or "").strip()
        if override_command:
            completed = subprocess.run(
                override_command,
                cwd=self._repo_root,
                env=preflight_env,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            script = self._repo_root / "scripts" / "launch_ai_lab.sh"
            if not script.exists():
                return f"EnvironmentCheckFailed: launch_ai_lab.sh not found at {script}"
            completed = subprocess.run(
                ["bash", str(script), "status"],
                cwd=self._repo_root,
                env=preflight_env,
                capture_output=True,
                text=True,
                check=False,
            )

        if completed.returncode == 0:
            return None

        detail = (completed.stderr or completed.stdout or "").strip()
        if not detail:
            detail = f"preflight exited with code {completed.returncode}"
        collapsed = re.sub(r"\s+", " ", detail)[:400]
        return f"EnvironmentCheckFailed: {collapsed}"

    def _job_for_attempt(
        self,
        *,
        job: JobSpec,
        agent_id: str,
        attempt: int,
        last_result: DriverResult,
        last_validation: ValidationReport,
    ) -> JobSpec:
        if attempt <= 1 or agent_id != job.agent_id:
            return job

        feedback = self._build_retry_feedback(last_result=last_result, last_validation=last_validation)
        if feedback is None:
            return job

        metadata = dict(job.metadata)
        metadata["retry_feedback"] = feedback
        metadata["retry_attempt"] = attempt
        metadata["retry_source_status"] = last_result.status
        return job.model_copy(
            update={
                "task": (
                    f"{job.task.rstrip()}\n\n"
                    "Retry feedback from the previous attempt. Fix these exact failures before making any new changes:\n"
                    f"{feedback}\n"
                ),
                "metadata": metadata,
            }
        )

    @staticmethod
    def _build_retry_feedback(
        *,
        last_result: DriverResult,
        last_validation: ValidationReport,
    ) -> str | None:
        if last_validation.passed:
            return None

        failed_checks = [check for check in last_validation.checks if not check.passed and check.detail.strip()]
        error_text = str(last_result.error or "").strip()
        if not failed_checks and not error_text:
            return None

        parts = [
            f"Previous driver status: {last_result.status}",
            f"Previous driver summary: {last_result.summary}",
        ]
        if last_result.changed_paths:
            parts.append("Previous changed paths:")
            parts.extend(f"- {path}" for path in last_result.changed_paths)
        if failed_checks:
            parts.append("Raw validator failures:")
            for check in failed_checks:
                parts.append(f"[{check.id}]")
                parts.append(check.detail.strip())
        if error_text:
            parts.append("Driver error:")
            parts.append(error_text)
        return "\n".join(parts)

    @staticmethod
    def _retry_skip_reason(result: DriverResult) -> str | None:
        if result.status == "stalled_no_progress":
            return "stalled_no_progress"
        error_text = str(result.error or result.summary or "").strip()
        if result.status == "contract_error" and error_text.startswith("EnvironmentCheckFailed:"):
            return "environment_preflight_failed"
        return None

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
        recommended_action: str = "reject",
    ) -> DriverResult:
        return DriverResult(
            run_id=run_id,
            agent_id=agent_id,
            attempt=attempt,
            status="contract_error",
            summary=message,
            recommended_action=recommended_action,
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
    def _glob_prefix(value: str) -> str:
        prefix: list[str] = []
        for char in value:
            if char in "*?[":
                break
            prefix.append(char)
        return "".join(prefix).rstrip("/")

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

    @staticmethod
    def _terminate_process(
        process: subprocess.Popen[str],
        *,
        process_group_id: int | None = None,
    ) -> None:
        if process.poll() is not None:
            return

        def _send(sig: signal.Signals) -> None:
            delivered = False
            if process_group_id is not None and hasattr(os, "killpg"):
                try:
                    os.killpg(process_group_id, sig)
                    delivered = True
                except (OSError, ProcessLookupError):
                    delivered = False

            if delivered:
                return

            if sig == signal.SIGTERM:
                process.terminate()
            else:
                process.kill()

        try:
            _send(signal.SIGTERM)
        except (OSError, ProcessLookupError):
            return

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                _send(signal.SIGKILL)
            except (OSError, ProcessLookupError):
                return
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    return
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    return

    @staticmethod
    def _rmtree_force(path: Path) -> None:
        if not path.exists():
            return

        def onexc(func, failed_path, excinfo) -> None:
            _ = excinfo
            try:
                os.chmod(failed_path, 0o777)
            except OSError:
                pass
            try:
                func(failed_path)
            except OSError:
                pass

        shutil.rmtree(path, onexc=onexc)

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
            AgentExecutionRunner._rmtree_force(workspace_dir)
            return
        if not success and not policy.merged.retain_workspace_on_failure:
            AgentExecutionRunner._rmtree_force(workspace_dir)
