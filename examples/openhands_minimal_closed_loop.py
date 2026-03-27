from __future__ import annotations

import argparse
import json
import shlex
import sys

from autoresearch.core.services.openhands_controlled_backend import OpenHandsControlledBackendService
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionRequest,
    FailureStrategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimal AAS->OpenHands->AAS controlled loop demo")
    parser.add_argument("--task-id", default="demo-openhands-minimal", help="Logical task ID for audit")
    parser.add_argument("--prompt", default="Create src/demo_math.py with add(a,b) and a short docstring.")
    parser.add_argument("--backend", choices=[item.value for item in ControlledBackend], default="mock")
    parser.add_argument("--fallback-backend", choices=[item.value for item in ControlledBackend], default=None)
    parser.add_argument(
        "--failure-strategy",
        choices=[item.value for item in FailureStrategy],
        default="human_in_loop",
        help="How to handle failed execution/validation",
    )
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument(
        "--validation-cmd",
        default="python3 -m compileall -q src",
        help="Shell-style command executed inside isolated workspace",
    )
    parser.add_argument("--no-cleanup-on-success", action="store_true")
    parser.add_argument("--drop-workspace-on-fail", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validation_command = shlex.split(args.validation_cmd) if args.validation_cmd.strip() else []

    request = ControlledExecutionRequest(
        task_id=args.task_id,
        prompt=args.prompt,
        backend=ControlledBackend(args.backend),
        fallback_backend=ControlledBackend(args.fallback_backend) if args.fallback_backend else None,
        validation_command=validation_command,
        failure_strategy=FailureStrategy(args.failure_strategy),
        max_retries=args.max_retries,
        cleanup_workspace_on_success=not args.no_cleanup_on_success,
        keep_workspace_on_failure=not args.drop_workspace_on_fail,
        metadata={"entry": "examples/openhands_minimal_closed_loop.py"},
    )

    service = OpenHandsControlledBackendService()
    result = service.run(request)

    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if result.status.value == "ready_for_promotion":
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
