#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from autoresearch.core.services.host_standby import (
    HostStandbyJobInbox,
    HostStandbyLeaseStore,
    HostStandbyWorker,
    default_host_id,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the manual lease-gated standby worker for host takeover."
    )
    parser.add_argument("--repo-root", default=None, help="optional repository root")
    parser.add_argument("--standby-root", default=None, help="optional standby runtime root")
    parser.add_argument("--lease-path", default=None, help="optional explicit lease.json path")
    parser.add_argument(
        "--host-id",
        default=os.environ.get("AUTORESEARCH_HOST_ID") or default_host_id(),
        help="host identifier that must match lease.owner",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="idle poll interval")
    parser.add_argument("--once", action="store_true", help="process at most one loop iteration")
    return parser.parse_args()


def _default_standby_root(repo_root: Path) -> Path:
    return (repo_root / "artifacts" / "runtime" / "standby").resolve()


def _print_result(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    standby_root = Path(args.standby_root).resolve() if args.standby_root else _default_standby_root(repo_root)
    lease_path = Path(args.lease_path).resolve() if args.lease_path else standby_root / "lease.json"

    worker = HostStandbyWorker(
        host_id=args.host_id,
        repo_root=repo_root,
        lease_store=HostStandbyLeaseStore(lease_path),
        inbox=HostStandbyJobInbox(standby_root / "jobs"),
    )

    while True:
        result = worker.run_once()
        if args.once or result.action not in {"standby", "idle"}:
            _print_result(result.model_dump(mode="json"))
        if args.once:
            return 0 if result.action != "failed" else 1
        time.sleep(max(args.poll_seconds, 0.5))


if __name__ == "__main__":
    raise SystemExit(main())
