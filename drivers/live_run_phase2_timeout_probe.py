#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def main() -> int:
    job_spec = json.loads(Path(os.environ["AEP_JOB_SPEC"]).read_text(encoding="utf-8"))
    run_dir = Path(os.environ["AEP_RUN_DIR"])
    attempt = int(os.environ.get("AEP_ATTEMPT", "1"))

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "status.json").write_text(
        json.dumps(
            {
                "probe": "phase2-timeout",
                "status": "running",
                "attempt": attempt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "heartbeat.json").write_text(
        json.dumps(
            {
                "probe": "phase2-timeout",
                "heartbeat": "initial",
                "attempt": attempt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"phase-2 timeout probe attempt {attempt}: seeded progress", flush=True)
    time.sleep(0.5)

    payload = {
        "protocol_version": "aep/v0",
        "run_id": job_spec["run_id"],
        "agent_id": job_spec["agent_id"],
        "attempt": attempt,
        "status": "timed_out",
        "summary": "phase-2 timeout probe intentionally reports a timeout failure",
        "changed_paths": [],
        "output_artifacts": [],
        "metrics": {
            "duration_ms": 0,
            "steps": 1,
            "commands": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": "fallback",
        "error": "timeout probe reached its hard timeout boundary",
    }
    Path(os.environ["AEP_RESULT_PATH"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
