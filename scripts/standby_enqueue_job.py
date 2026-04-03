#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from autoresearch.agent_protocol.models import FallbackStep, JobSpec, ValidatorSpec
from autoresearch.core.services.host_standby import HostStandbyJobInbox
from autoresearch.routing import ControlPlaneJobBuilder, ControlPlaneJobRequest


def _default_run_id(agent: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"standby-{agent}-{ts}"


def _default_fallback_agent(agent: str, configured: str | None) -> str | None:
    if configured:
        return configured
    if agent == "openhands":
        return "mock"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enqueue a JobSpec into the manual standby worker inbox."
    )
    parser.add_argument("--repo-root", default=None, help="optional repository root")
    parser.add_argument("--standby-root", default=None, help="optional standby runtime root")
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


def _default_standby_root(repo_root: Path) -> Path:
    return (repo_root / "artifacts" / "runtime" / "standby").resolve()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or _default_run_id(args.agent)
    fallback_agent = _default_fallback_agent(args.agent, args.fallback_agent)
    resolved_repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    )
    standby_root = (
        Path(args.standby_root).resolve()
        if args.standby_root
        else _default_standby_root(resolved_repo_root)
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
            metadata={"entrypoint": "scripts/standby_enqueue_job.py"},
        )
    )
    job: JobSpec = build_result.job

    inbox = HostStandbyJobInbox(standby_root / "jobs")
    queued_path = inbox.enqueue(job, metadata={"source": "standby_enqueue_job"})
    print(
        json.dumps(
            {
                "run_id": job.run_id,
                "queued_path": str(queued_path),
                "agent_id": job.agent_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
