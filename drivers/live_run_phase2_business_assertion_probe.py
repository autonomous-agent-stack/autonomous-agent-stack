#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    job_spec = json.loads(Path(os.environ["AEP_JOB_SPEC"]).read_text(encoding="utf-8"))
    run_dir = Path(os.environ["AEP_RUN_DIR"])
    workspace_dir = Path(os.environ["AEP_WORKSPACE"])
    result_path = Path(os.environ["AEP_RESULT_PATH"])
    attempt = int(os.environ.get("AEP_ATTEMPT", "1"))

    run_dir.mkdir(parents=True, exist_ok=True)

    output_path = workspace_dir / "src" / "phase2_business_probe.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\"\"\"Phase 2 business validation probe.\"\"\"\n\n"
        "VALUE = \"phase2-business-probe\"\n",
        encoding="utf-8",
    )
    (run_dir / "status.json").write_text(
        json.dumps(
            {
                "probe": "phase2-business-assertion",
                "status": "completed",
                "attempt": attempt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = {
        "protocol_version": "aep/v0",
        "run_id": job_spec["run_id"],
        "agent_id": job_spec["agent_id"],
        "attempt": attempt,
        "status": "succeeded",
        "summary": "phase-2 business assertion probe completed with the fixed probe file",
        "changed_paths": ["src/phase2_business_probe.py"],
        "output_artifacts": [],
        "metrics": {
            "duration_ms": 0,
            "steps": 1,
            "commands": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": "promote",
        "error": None,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("phase-2 business assertion probe completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
