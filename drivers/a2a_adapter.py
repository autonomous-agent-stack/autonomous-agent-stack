#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from importlib.util import find_spec
from pathlib import Path
from typing import Any


def main() -> int:
    started = time.perf_counter()
    workspace = Path(os.environ["AEP_WORKSPACE"])
    job_path = Path(os.environ["AEP_JOB_SPEC"])
    result_path = Path(os.environ["AEP_RESULT_PATH"])
    job: dict[str, Any] = json.loads(job_path.read_text(encoding="utf-8"))
    run_id = str(job.get("run_id") or "a2a-demo")
    agent_id = str(job.get("agent_id") or "a2a_bridge")
    task = str(job.get("task") or "Run an A2A bridge demo.").strip()
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    a2a_available = find_spec("a2a") is not None

    card = {
        "name": "AAS A2A Bridge",
        "description": "AAS publishes governed capability cards and receives remote agent tasks through federation-aware quota and audit.",
        "capabilities": ["federation.a2a_bridge"],
        "ledger": "federation",
        "lease_required": True,
    }
    out_dir = workspace / "docs" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "a2a_bridge_demo.md"
    out_path.write_text(
        "# A2A Bridge Runtime Demo\n\n"
        "中文：这个产物演示 AAS 作为 A2A server/client 的边界。A2A 负责 agent 间互操作，AAS 复用 federation lease、quota 和 audit。\n\n"
        "English: This artifact demonstrates the AAS boundary as an A2A server/client. A2A provides agent interoperability while AAS reuses federation leases, quota, and audit.\n\n"
        f"- task: {task}\n"
        f"- a2a_available: {a2a_available}\n"
        f"- remote_endpoint: {metadata.get('endpoint') or 'local-demo'}\n\n"
        "```json\n"
        + json.dumps(card, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    rel = out_path.relative_to(workspace).as_posix()
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": "aep/v0",
                "run_id": run_id,
                "agent_id": agent_id,
                "attempt": int(os.environ.get("AEP_ATTEMPT", "1")),
                "status": "succeeded",
                "summary": "A2A bridge demo completed with governed capability card.",
                "changed_paths": [rel],
                "output_artifacts": [{"name": "a2a_bridge_demo", "kind": "report", "uri": f"workspace://{rel}"}],
                "metrics": {"duration_ms": int((time.perf_counter() - started) * 1000), "steps": 2, "commands": 1},
                "recommended_action": "promote",
                "error": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
