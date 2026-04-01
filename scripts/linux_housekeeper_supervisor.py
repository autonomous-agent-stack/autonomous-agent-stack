#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from autoresearch.core.services.linux_supervisor import LinuxSupervisorService
from autoresearch.shared.linux_supervisor_contract import LinuxSupervisorTaskCreateRequest


def _service(args: argparse.Namespace) -> LinuxSupervisorService:
    return LinuxSupervisorService(
        repo_root=Path(args.repo_root).resolve(),
        runtime_root=Path(args.runtime_root).resolve() if args.runtime_root else None,
        python_bin=args.python_bin,
        poll_interval_sec=args.poll_interval_sec,
        heartbeat_interval_sec=args.heartbeat_interval_sec,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Linux housekeeper supervisor MVP")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--poll-interval-sec", type=float, default=1.0)
    parser.add_argument("--heartbeat-interval-sec", type=float, default=5.0)

    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue = subparsers.add_parser("enqueue", help="enqueue a task.json entry for the resident supervisor")
    enqueue.add_argument("--prompt", required=True)
    enqueue.add_argument("--agent", default="openhands")
    enqueue.add_argument("--retry", type=int, default=1)
    enqueue.add_argument("--fallback-agent", default="mock")
    enqueue.add_argument("--validator-cmd", action="append", default=[])
    enqueue.add_argument("--total-timeout-sec", type=int, default=1800)
    enqueue.add_argument("--stall-timeout-sec", type=int, default=600)

    subparsers.add_parser("run-once", help="process one queued task if present")
    subparsers.add_parser("run-forever", help="run the resident supervisor loop")
    subparsers.add_parser("status", help="print queue and supervisor status")
    subparsers.add_parser("repair", help="mark orphaned running tasks as infra_error")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = _service(args)

    if args.command == "enqueue":
        task = service.enqueue_task(
            LinuxSupervisorTaskCreateRequest(
                prompt=args.prompt,
                agent_id=args.agent,
                retry=args.retry,
                fallback_agent=args.fallback_agent or None,
                validator_commands=list(args.validator_cmd),
                total_timeout_sec=args.total_timeout_sec,
                stall_timeout_sec=args.stall_timeout_sec,
            )
        )
        print(json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "run-once":
        summary = service.run_once()
        payload = None if summary is None else summary.model_dump(mode="json")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "run-forever":
        service.run_forever()
        return 0

    if args.command == "repair":
        repaired = service.repair_orphaned_tasks()
        print(json.dumps({"repaired": repaired}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "status":
        print(json.dumps(service.status_snapshot(), ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
