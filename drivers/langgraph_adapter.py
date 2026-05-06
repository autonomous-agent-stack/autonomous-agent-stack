#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from importlib.util import find_spec
from pathlib import Path
from typing import Any


def _read_job() -> dict[str, Any]:
    return json.loads(Path(os.environ["AEP_JOB_SPEC"]).read_text(encoding="utf-8"))


def _write_result(payload: dict[str, Any]) -> None:
    Path(os.environ["AEP_RESULT_PATH"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    started = time.perf_counter()
    workspace = Path(os.environ["AEP_WORKSPACE"])
    job = _read_job()
    run_id = str(job.get("run_id") or "langgraph-demo")
    agent_id = str(job.get("agent_id") or "langgraph_order_flow")
    task = str(job.get("task") or "Run an order workflow demo.").strip()
    langgraph_available = find_spec("langgraph") is not None

    checkpoint_dir = workspace / "apps" / "langgraph_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"{run_id}.json"
    checkpoint = {
        "run_id": run_id,
        "state": "awaiting_or_completed_approval",
        "steps": ["intake", "risk_check", "approval_interrupt", "draft_result"],
        "approval_event_type": "approval.required",
        "resume_policy": "AAS approval decision resumes the local workflow runtime",
    }
    checkpoint_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")

    out_dir = workspace / "docs" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "langgraph_order_flow.md"
    out_path.write_text(
        "# LangGraph Workflow Runtime Demo\n\n"
        "中文：这个产物演示 LangGraph 作为局部有状态 workflow runtime 的边界。AAS 保存 checkpoint 引用、审批和全局审计，不接管框架内部状态。\n\n"
        "English: This artifact demonstrates LangGraph as a local stateful workflow runtime. AAS stores checkpoint references, approvals, and global audit without owning framework internals.\n\n"
        f"- task: {task}\n"
        f"- langgraph_available: {langgraph_available}\n"
        f"- checkpoint_ref: workspace://{checkpoint_path.relative_to(workspace).as_posix()}\n",
        encoding="utf-8",
    )
    rel_report = out_path.relative_to(workspace).as_posix()
    rel_checkpoint = checkpoint_path.relative_to(workspace).as_posix()
    duration_ms = int((time.perf_counter() - started) * 1000)
    _write_result(
        {
            "protocol_version": "aep/v0",
            "run_id": run_id,
            "agent_id": agent_id,
            "attempt": int(os.environ.get("AEP_ATTEMPT", "1")),
            "status": "succeeded",
            "summary": "LangGraph workflow demo completed with checkpoint reference and approval boundary.",
            "changed_paths": [rel_report, rel_checkpoint],
            "output_artifacts": [
                {"name": "langgraph_order_flow", "kind": "report", "uri": f"workspace://{rel_report}"},
                {"name": "langgraph_checkpoint_ref", "kind": "custom", "uri": f"workspace://{rel_checkpoint}"},
            ],
            "metrics": {"duration_ms": duration_ms, "steps": 4, "commands": 1},
            "recommended_action": "promote",
            "error": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
