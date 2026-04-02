#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def main() -> int:
    run_dir = Path(os.environ["AEP_RUN_DIR"])
    workspace_dir = Path(os.environ["AEP_WORKSPACE"])
    attempt = int(os.environ.get("AEP_ATTEMPT", "1"))

    docs_dir = workspace_dir / "docs" / "phase2"
    docs_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "status.json").write_text(
        json.dumps(
            {
                "probe": "phase2-stall-no-progress",
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
                "probe": "phase2-stall-no-progress",
                "heartbeat": "initial",
                "attempt": attempt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (docs_dir / "stall_probe_marker.txt").write_text(
        f"attempt={attempt}\nstate=initial-progress\n",
        encoding="utf-8",
    )
    print(f"phase-2 stall probe attempt {attempt}: seeded initial progress", flush=True)
    time.sleep(3600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
