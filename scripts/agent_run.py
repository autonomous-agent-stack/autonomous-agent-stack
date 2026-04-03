#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from autoresearch.agent_protocol.models import FallbackStep, JobSpec, ValidatorSpec
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.routing import ControlPlaneJobBuilder, ControlPlaneJobRequest


def _default_run_id(agent: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"aep-{agent}-{ts}"


def _default_fallback_agent(agent: str, configured: str | None) -> str | None:
    if configured:
        return configured
    if agent == "openhands":
        return "mock"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AEP v0 job with a registered agent adapter")
    parser.add_argument("--repo-root", default=None, help="optional repository root for manifests/runtime")
    parser.add_argument("--agent", required=True, help="agent id from configs/agents/<id>.yaml")
    parser.add_argument("--task", required=True, help="execution task")
    parser.add_argument("--run-id", default=None, help="optional run id")
    parser.add_argument(
        "--validator-cmd", action="append", default=[], help="command validator to run in workspace"
    )
    parser.add_argument(
        "--retry", type=int, default=0, help="additional retry attempts after primary attempt"
    )
    parser.add_argument("--fallback-agent", default=None, help="fallback agent id")
    parser.add_argument(
        "--no-human-review", action="store_true", help="do not append human_review fallback step"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or _default_run_id(args.agent)
    fallback_agent = _default_fallback_agent(args.agent, args.fallback_agent)
    resolved_repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    )

    validators = [
        ValidatorSpec(id=f"cmd_{idx+1}", kind="command", command=command)
        for idx, command in enumerate(args.validator_cmd)
    ]

    fallback: list[FallbackStep] = []
    if args.retry > 0:
        fallback.append(FallbackStep(action="retry", max_attempts=args.retry))
    if fallback_agent:
        fallback.append(
            FallbackStep(action="fallback_agent", agent_id=fallback_agent, max_attempts=1)
        )
    if not args.no_human_review:
        fallback.append(FallbackStep(action="human_review", max_attempts=1))

    # Compatibility shell only: keep the CLI semantics explicit and avoid
    # introducing automatic routing or workflow logic through this entrypoint.
    builder = ControlPlaneJobBuilder(resolved_repo_root / "configs" / "agents")
    build_result = builder.build(
        ControlPlaneJobRequest(
            run_id=run_id,
            requested_agent_id=args.agent,
            role="executor",
            mode_hint="apply_in_workspace",
            task=args.task,
            validators=validators,
            fallback=fallback,
            metadata={"entrypoint": "scripts/agent_run.py"},
        )
    )
    job: JobSpec = build_result.job

    runner = AgentExecutionRunner(repo_root=resolved_repo_root)
    summary = runner.run_job(job)
    print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if summary.final_status in {"ready_for_promotion", "promoted"}:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
