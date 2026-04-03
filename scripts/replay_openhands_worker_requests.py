#!/usr/bin/env python3
"""Replay recorded OpenHands worker requests through the local contract builders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autoresearch.core.services.openhands_worker import OpenHandsWorkerService
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay recorded OpenHands worker requests without invoking a live backend."
    )
    parser.add_argument("--input", required=True, help="Path to a JSON file of recorded worker requests.")
    parser.add_argument("--output", required=True, help="Path to write the replay report JSON.")
    return parser


def load_requests(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        requests = payload
    elif isinstance(payload, dict) and isinstance(payload.get("requests"), list):
        requests = payload["requests"]
    else:
        raise ValueError("Input JSON must be a list or an object with a requests list")

    normalized: list[dict[str, Any]] = []
    for item in requests:
        if not isinstance(item, dict):
            raise ValueError("Each recorded request must be a JSON object")
        normalized.append(item)
    return normalized


def replay_requests(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    service = OpenHandsWorkerService()
    raw_requests = load_requests(input_path)
    results: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_requests, start=1):
        fallback_job_id = f"request-{index}"
        try:
            spec = OpenHandsWorkerJobSpec.model_validate(raw)
            agent_job = service.build_agent_job_spec(spec)
            controlled_request = service.build_controlled_request(spec)
        except Exception as exc:
            results.append(
                {
                    "job_id": str(raw.get("job_id", fallback_job_id)),
                    "status": "error",
                    "error": str(exc),
                }
            )
            continue

        results.append(
            {
                "job_id": spec.job_id,
                "status": "ok",
                "agent_id": agent_job.agent_id,
                "mode": agent_job.mode,
                "allowed_paths": list(agent_job.policy.allowed_paths),
                "validator_command": agent_job.validators[0].command if agent_job.validators else None,
                "pipeline_target": controlled_request.pipeline_target.value,
                "worker_output_mode": controlled_request.worker_output_mode,
                "artifact_stub": f"{spec.job_id}-{controlled_request.pipeline_target.value}.json",
                "target_base_branch": spec.target_base_branch,
                "language": spec.metadata.get("language"),
            }
        )

    payload = {
        "total_requests": len(results),
        "ok_count": sum(1 for item in results if item["status"] == "ok"),
        "error_count": sum(1 for item in results if item["status"] != "ok"),
        "results": results,
    }

    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = replay_requests(args.input, args.output)
    print(f"Replayed {payload['ok_count']} worker requests with {payload['error_count']} errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
