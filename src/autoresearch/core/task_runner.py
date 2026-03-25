from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import uuid

from autoresearch.shared.models import EvaluatorCommand


RESULTS_HEADER = [
    "run_id",
    "branch",
    "commit",
    "score",
    "status",
    "duration_seconds",
    "description",
    "summary",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sanitize_field(value: object) -> str:
    return str(value).replace("\t", " ").replace("\n", " ").strip()


def git_value(repo_root: Path, args: list[str], default: str) -> str:
    try:
        output = subprocess.check_output(
            ["git", *args],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return default
    return output or default


def resolve_command(command: list[str]) -> list[str]:
    resolved = []
    for token in command:
        if token == "__PYTHON__":
            resolved.append(sys.executable)
        else:
            resolved.append(token)
    return resolved


def resolve_work_dir(repo_root: Path, work_dir: str | None) -> Path:
    if work_dir is None:
        return repo_root

    resolved = Path(work_dir)
    if resolved.is_absolute():
        return resolved
    return (repo_root / resolved).resolve()


def preview_output(text: str, limit: int = 1000) -> str | None:
    normalized = text.strip()
    if not normalized:
        return None
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 16] + "\n...[truncated]"


def build_evaluator_config(
    repo_root: Path,
    config: dict[str, Any],
    evaluator_command: EvaluatorCommand | None,
) -> tuple[list[str], int, Path, dict[str, str], str]:
    if evaluator_command is None:
        return (
            resolve_command(list(config["evaluate"]["command"])),
            int(config["evaluate"].get("timeout_seconds", 30)),
            repo_root,
            {},
            "task_config",
        )

    return (
        resolve_command(list(evaluator_command.command)),
        int(evaluator_command.timeout_seconds),
        resolve_work_dir(repo_root, evaluator_command.work_dir),
        dict(evaluator_command.env),
        "request_override",
    )


def execute_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "raw_result": None,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nTimed out after {timeout_seconds}s.",
            "raw_result": {
                "score": 0.0,
                "status": "crash",
                "summary": f"evaluation timed out after {timeout_seconds}s",
            },
        }
    except FileNotFoundError as exc:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "raw_result": {
                "score": 0.0,
                "status": "crash",
                "summary": f"failed to launch evaluator: {exc}",
            },
        }


def append_results(results_path: Path, row: dict[str, object]) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not results_path.exists()
    with results_path.open("a", encoding="utf-8") as handle:
        if write_header:
            handle.write("\t".join(RESULTS_HEADER) + "\n")
        handle.write(
            "\t".join(sanitize_field(row.get(column, "")) for column in RESULTS_HEADER) + "\n"
        )


def load_previous_scores(results_path: Path) -> list[float]:
    if not results_path.exists():
        return []
    scores: list[float] = []
    with results_path.open("r", encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            status = parts[4]
            if status != "pass":
                continue
            try:
                scores.append(float(parts[3]))
            except ValueError:
                continue
    return scores


def compare_score(
    previous_scores: list[float],
    score: float,
    direction: str,
    status: str,
) -> tuple[str, str]:
    if status != "pass":
        return "n/a", "not comparable"
    if not previous_scores:
        return "n/a", "first run"

    best_before = max(previous_scores) if direction == "maximize" else min(previous_scores)
    if direction == "maximize":
        if score > best_before:
            return f"{best_before:.6f}", "improved"
        if score == best_before:
            return f"{best_before:.6f}", "tied best"
        return f"{best_before:.6f}", "regressed"

    if score < best_before:
        return f"{best_before:.6f}", "improved"
    if score == best_before:
        return f"{best_before:.6f}", "tied best"
    return f"{best_before:.6f}", "regressed"


def normalize_result(raw: dict[str, object], returncode: int) -> dict[str, object]:
    status = str(raw.get("status", "pass" if returncode == 0 else "crash"))
    summary = str(raw.get("summary", ""))

    try:
        score = float(raw.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0

    metrics = raw.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    return {
        "score": score,
        "status": status,
        "summary": summary,
        "metrics": metrics,
    }


def print_summary(
    task_name: str,
    run_id: str,
    score: float,
    direction: str,
    status: str,
    duration: float,
    best_before: str,
    comparison: str,
    summary: str,
    artifact_dir: Path,
) -> None:
    print("---")
    print(f"task:             {task_name}")
    print(f"run_id:           {run_id}")
    print(f"score:            {score:.6f}")
    print(f"score_direction:  {direction}")
    print(f"status:           {status}")
    print(f"duration_seconds: {duration:.3f}")
    print(f"best_score_before:{best_before}")
    print(f"comparison:       {comparison}")
    print(f"summary:          {summary}")
    print(f"artifact_dir:     {artifact_dir}")


def run_task(
    config_path: str | Path = "task.json",
    description: str = "manual run",
    evaluator_command: EvaluatorCommand | None = None,
) -> dict[str, Any]:
    resolved_config_path = Path(config_path).resolve()
    repo_root = resolved_config_path.parent
    config = load_json(resolved_config_path)

    task_name = str(config["name"])
    direction = str(config["evaluate"].get("score_direction", "maximize"))
    command, timeout_seconds, execution_cwd, env_overrides, command_source = build_evaluator_config(
        repo_root=repo_root,
        config=config,
        evaluator_command=evaluator_command,
    )
    artifacts_dir = (repo_root / config["artifacts_dir"]).resolve()
    results_path = artifacts_dir / "results.tsv"
    previous_scores = load_previous_scores(results_path)

    run_stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{run_stamp}-{uuid.uuid4().hex[:6]}"
    run_dir = artifacts_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    output_json = run_dir / "result.json"
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    metadata_json = run_dir / "metadata.json"

    env = os.environ.copy()
    env.update(env_overrides)
    env["AUTORESEARCH_OUTPUT_JSON"] = str(output_json)
    env["AUTORESEARCH_ARTIFACT_DIR"] = str(run_dir)
    env["AUTORESEARCH_TASK_NAME"] = task_name

    started = time.perf_counter()
    execution = execute_command(
        command=command,
        cwd=execution_cwd,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    returncode = int(execution["returncode"])
    stdout_text = str(execution["stdout"])
    stderr_text = str(execution["stderr"])
    raw_result: dict[str, object] | None = execution["raw_result"]

    duration_seconds = time.perf_counter() - started
    stdout_log.write_text(stdout_text, encoding="utf-8")
    stderr_log.write_text(stderr_text, encoding="utf-8")

    if raw_result is None:
        if output_json.exists():
            try:
                raw_result = load_json(output_json)
            except json.JSONDecodeError as exc:
                raw_result = {
                    "score": 0.0,
                    "status": "crash",
                    "summary": f"invalid result JSON: {exc}",
                }
        else:
            raw_result = {
                "score": 0.0,
                "status": "crash",
                "summary": "evaluator did not write AUTORESEARCH_OUTPUT_JSON",
            }

    result = normalize_result(raw_result, returncode)
    best_before, comparison = compare_score(
        previous_scores,
        float(result["score"]),
        direction,
        str(result["status"]),
    )

    branch = git_value(repo_root, ["branch", "--show-current"], "detached")
    commit = git_value(repo_root, ["rev-parse", "--short", "HEAD"], "nogit")

    run_metadata = {
        "task_name": task_name,
        "config_path": str(resolved_config_path),
        "command": command,
        "command_source": command_source,
        "timeout_seconds": timeout_seconds,
        "work_dir": str(execution_cwd),
        "env_overrides": env_overrides,
        "run_id": run_id,
        "branch": branch,
        "commit": commit,
        "returncode": returncode,
        "duration_seconds": duration_seconds,
        "description": description,
        "direction": direction,
        "artifact_dir": str(run_dir),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "stdout_preview": preview_output(stdout_text),
        "stderr_preview": preview_output(stderr_text),
        "best_before": best_before,
        "comparison": comparison,
        "result": result,
    }
    metadata_json.write_text(json.dumps(run_metadata, indent=2, sort_keys=True), encoding="utf-8")
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    append_results(
        results_path,
        {
            "run_id": run_id,
            "branch": branch,
            "commit": commit,
            "score": f"{float(result['score']):.6f}",
            "status": result["status"],
            "duration_seconds": f"{duration_seconds:.3f}",
            "description": description,
            "summary": result["summary"],
        },
    )

    return run_metadata
