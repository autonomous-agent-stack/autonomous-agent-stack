from __future__ import annotations

import json
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoresearch.agent_protocol.models import FallbackStep, JobSpec, ValidatorSpec
from autoresearch.benchmarks.live_run_stability_runner import (
    LiveRunBenchmarkResult,
    normalize_run_dir_artifact_inventory,
    run_live_run_stability_benchmark,
)
from autoresearch.executions.runner import AgentExecutionRunner

_PHASE2_STALL_AGENT_ID = "phase2-stall-probe"
_PHASE2_BUSINESS_AGENT_ID = "phase2-business-assertion-probe"
_PHASE2_REQUIRED_MARKER = "PHASE2_REQUIRED_MARKER"


@dataclass(frozen=True)
class LiveRunPhase2Paths:
    tasks_path: Path
    benchmark_root: Path
    run_root: Path
    runtime_root: Path
    matrix_json_path: Path
    matrix_markdown_path: Path
    retry_overview_json_path: Path


def build_live_run_stability_phase2_paths(
    *,
    repo_root: Path,
    tasks_path: Path | None = None,
    benchmark_root: Path | None = None,
) -> LiveRunPhase2Paths:
    resolved_tasks_path = (
        tasks_path
        if tasks_path is not None
        else repo_root / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    )
    resolved_benchmark_root = (
        benchmark_root
        if benchmark_root is not None
        else repo_root / "artifacts" / "live-run-stability" / "phase-2"
    )
    return LiveRunPhase2Paths(
        tasks_path=resolved_tasks_path,
        benchmark_root=resolved_benchmark_root,
        run_root=resolved_benchmark_root / "runs",
        runtime_root=resolved_benchmark_root / "runner-runtime",
        matrix_json_path=resolved_benchmark_root / "regression-matrix.json",
        matrix_markdown_path=resolved_benchmark_root / "regression-matrix.md",
        retry_overview_json_path=resolved_benchmark_root / "retry-overview.json",
    )


def run_live_run_stability_phase2_benchmark(
    *,
    repo_root: Path,
    tasks_path: Path | None = None,
    benchmark_root: Path | None = None,
) -> LiveRunBenchmarkResult:
    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )
    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=paths.runtime_root,
        manifests_dir=repo_root / "configs" / "agents",
    )

    def executor(task: dict[str, Any], run_dir: Path) -> dict[str, Any]:
        task_id = str(task.get("task_id") or "").strip()
        if task_id == "fail-stall-no-progress":
            return _run_stall_no_progress_probe(
                runner=runner,
                runtime_root=paths.runtime_root,
                task=task,
                run_dir=run_dir,
            )
        if task_id == "fail-business-assertion-mismatch":
            return _run_business_assertion_mismatch_probe(
                runner=runner,
                runtime_root=paths.runtime_root,
                task=task,
                run_dir=run_dir,
            )
        raise ValueError(f"unsupported phase-2 task_id: {task_id}")

    return run_live_run_stability_benchmark(
        tasks_path=paths.tasks_path,
        run_root=paths.run_root,
        matrix_json_path=paths.matrix_json_path,
        matrix_markdown_path=paths.matrix_markdown_path,
        retry_overview_json_path=paths.retry_overview_json_path,
        executor=executor,
    )


def _run_stall_no_progress_probe(
    *,
    runner: AgentExecutionRunner,
    runtime_root: Path,
    task: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    run_id = str(task.get("task_id") or "fail-stall-no-progress")
    summary = runner.run_job(
        JobSpec(
            run_id=run_id,
            agent_id=_PHASE2_STALL_AGENT_ID,
            task=str(task.get("prompt") or task.get("name") or run_id),
            fallback=_build_retry_fallback(task),
            metadata={
                "entrypoint": "phase-2",
                "scenario_type": task.get("scenario_type"),
            },
        )
    )
    summary_payload = summary.model_dump(mode="json")
    runtime_run_dir = runtime_root / run_id
    copied_paths = [
        _copy_if_exists(runtime_run_dir / "events.ndjson", run_dir / "events.ndjson"),
        _ensure_phase2_stall_status_file(
            source=runtime_run_dir / "status.json",
            destination=run_dir / "status.json",
            summary=summary_payload,
        ),
        _ensure_phase2_stall_heartbeat_file(
            source=runtime_run_dir / "heartbeat.json",
            destination=run_dir / "heartbeat.json",
            summary=summary_payload,
        ),
    ]
    return _augment_summary(
        summary=summary_payload,
        run_dir=run_dir,
        extra_paths=[path for path in copied_paths if path is not None],
    )


def _run_business_assertion_mismatch_probe(
    *,
    runner: AgentExecutionRunner,
    runtime_root: Path,
    task: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    run_id = str(task.get("task_id") or "fail-business-assertion-mismatch")
    summary = runner.run_job(
        JobSpec(
            run_id=run_id,
            agent_id=_PHASE2_BUSINESS_AGENT_ID,
            task=str(task.get("prompt") or task.get("name") or run_id),
            validators=[
                ValidatorSpec(
                    id=str(_phase2_business_validator_config(task).get("id") or "phase2.business_assertion.required_marker"),
                    kind=str(_phase2_business_validator_config(task).get("kind") or "command"),
                    command=_phase2_required_marker_validator_command(
                        target_file=str(
                            _phase2_business_validator_config(task).get("target_file")
                            or "src/phase2_business_probe.py"
                        ),
                        required_marker=str(
                            _phase2_business_validator_config(task).get("required_marker")
                            or _PHASE2_REQUIRED_MARKER
                        ),
                    ),
                )
            ],
            metadata={
                "entrypoint": "phase-2",
                "scenario_type": task.get("scenario_type"),
            },
        )
    )
    runtime_run_dir = runtime_root / run_id
    copied_paths = [
        _copy_if_exists(runtime_run_dir / "events.ndjson", run_dir / "events.ndjson"),
        _copy_if_exists(runtime_run_dir / "driver_result.json", run_dir / "driver_result.json"),
        _copy_if_exists(
            runtime_run_dir / "artifacts" / "promotion.patch",
            run_dir / "artifacts" / "promotion.patch",
        ),
    ]
    report_paths = _write_business_assertion_reports(
        run_dir=run_dir,
        summary=summary.model_dump(mode="json"),
        expected_outcome=task.get("expected_outcome"),
    )
    return _augment_summary(
        summary=summary.model_dump(mode="json"),
        run_dir=run_dir,
        extra_paths=[path for path in copied_paths if path is not None] + report_paths,
    )


def _build_retry_fallback(task: dict[str, Any]) -> list[FallbackStep]:
    retry_attempts = task.get("retry_attempts")
    try:
        max_attempts = max(int(retry_attempts), 0)
    except (TypeError, ValueError):
        max_attempts = 0
    if max_attempts <= 0:
        return []
    return [FallbackStep(action="retry", max_attempts=max_attempts)]


def _phase2_business_validator_config(task: dict[str, Any]) -> dict[str, Any]:
    validator = task.get("validator")
    return validator if isinstance(validator, dict) else {}


def _phase2_required_marker_validator_command(*, target_file: str, required_marker: str) -> str:
    script = (
        "from pathlib import Path; import sys; "
        "path = Path(sys.argv[1]); "
        "text = path.read_text(encoding='utf-8') if path.exists() else ''; "
        f"marker = {json.dumps(required_marker)}; "
        "present = marker in text; "
        "message = 'required marker present' if present else f'missing required marker: {marker}'; "
        "sys.stdout.write(message + '\\n'); "
        "raise SystemExit(0 if present else 1)"
    )
    return " ".join(
        [
            shlex.quote(sys.executable),
            "-c",
            shlex.quote(script),
            shlex.quote(target_file),
        ]
    )


def _write_business_assertion_reports(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    expected_outcome: Any,
) -> list[Path]:
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = artifacts_dir / "business_assertion_report.json"
    report_md_path = artifacts_dir / "business_assertion_report.md"
    validation = summary.get("validation") if isinstance(summary.get("validation"), dict) else {}
    checks = validation.get("checks") if isinstance(validation, dict) else []
    failed_checks = [check for check in checks if isinstance(check, dict) and not bool(check.get("passed"))]
    report_payload = {
        "run_id": summary.get("run_id"),
        "final_status": summary.get("final_status"),
        "failure_status": summary.get("failure_status"),
        "failure_stage": summary.get("failure_stage"),
        "business_assertion_status": summary.get("business_assertion_status"),
        "failed_checks": failed_checks,
        "expected_outcome": expected_outcome,
    }
    report_json_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Business Assertion Report",
        "",
        f"- run_id: `{summary.get('run_id')}`",
        f"- final_status: `{summary.get('final_status')}`",
        f"- failure_status: `{summary.get('failure_status')}`",
        f"- failure_stage: `{summary.get('failure_stage')}`",
        f"- business_assertion_status: `{summary.get('business_assertion_status')}`",
        "",
        "## Failed Checks",
    ]
    if failed_checks:
        for check in failed_checks:
            lines.append(
                f"- `{check.get('id')}`: {str(check.get('detail') or 'no detail').strip()}"
            )
    else:
        lines.append("- none")
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [report_json_path, report_md_path]


def _augment_summary(*, summary: dict[str, Any], run_dir: Path, extra_paths: list[Path]) -> dict[str, Any]:
    augmented = dict(summary)
    augmented["artifacts_produced"] = _phase2_artifacts_produced(run_dir=run_dir, extra_paths=extra_paths)
    return augmented


def _phase2_artifacts_produced(*, run_dir: Path, extra_paths: list[Path]) -> list[str]:
    return normalize_run_dir_artifact_inventory(artifacts=extra_paths, run_dir=run_dir)


def _copy_if_exists(source: Path, destination: Path) -> Path | None:
    if not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _ensure_phase2_stall_status_file(
    *,
    source: Path,
    destination: Path,
    summary: dict[str, Any],
) -> Path:
    copied = _copy_if_exists(source, destination)
    if copied is not None:
        return copied
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "probe": "phase2-stall-no-progress",
                "status": summary.get("driver_result", {}).get("status"),
                "final_status": summary.get("final_status"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination


def _ensure_phase2_stall_heartbeat_file(
    *,
    source: Path,
    destination: Path,
    summary: dict[str, Any],
) -> Path:
    copied = _copy_if_exists(source, destination)
    if copied is not None:
        return copied
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "probe": "phase2-stall-no-progress",
                "heartbeat": "synthesized",
                "failure_status": summary.get("failure_status"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination
