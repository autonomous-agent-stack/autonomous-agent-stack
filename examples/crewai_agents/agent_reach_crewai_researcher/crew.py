from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from importlib.util import find_spec
from pathlib import Path


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)>\"]+", text)


def _agent_reach_doctor() -> dict[str, object]:
    executable = shutil.which("agent-reach")
    if not executable:
        return {"available": False, "detail": "agent-reach executable not found"}
    try:
        completed = subprocess.run(
            [executable, "doctor"],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return {"available": False, "detail": str(exc)}
    output = (completed.stdout or completed.stderr or "").strip()
    return {
        "available": completed.returncode == 0,
        "returncode": completed.returncode,
        "preview": output[:1200],
    }


def main() -> int:
    started = time.perf_counter()
    task = os.getenv("AAS_TASK", "Summarize https://github.com/Panniantong/Agent-Reach").strip()
    run_id = os.getenv("AAS_RUN_ID", "agent-reach-crewai-demo")
    crewai_available = find_spec("crewai") is not None
    doctor = _agent_reach_doctor()
    urls = _extract_urls(task) or ["https://github.com/Panniantong/Agent-Reach"]

    out_dir = Path("docs") / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "agent_reach_crewai_researcher.md"
    out_path.write_text(
        "# Agent-Reach CrewAI Researcher Demo\n\n"
        "中文：这个产物演示 CrewAI 作为多角色 agent persona / crew 层，Agent-Reach 作为公开资料读取工具层，AAS 作为权限、额度、审批、审计和产物控制面。\n\n"
        "English: This artifact demonstrates CrewAI as the multi-agent persona/crew layer, Agent-Reach as the public-source reading tool layer, and AAS as the control plane for permission, quota, approval, audit, and artifacts.\n\n"
        f"- run_id: {run_id}\n"
        f"- task: {task}\n"
        f"- crewai_available: {crewai_available}\n"
        f"- agent_reach_available: {doctor.get('available')}\n"
        f"- sources: {', '.join(urls)}\n\n"
        "## Crew Roles\n\n"
        "- Researcher: finds readable public sources through Agent-Reach.\n"
        "- Analyst: extracts framework boundaries and integration risks.\n"
        "- Writer: returns an AAS-governed artifact instead of sending anything externally.\n\n"
        "## Agent-Reach Doctor Preview\n\n"
        "```text\n"
        f"{doctor.get('preview') or doctor.get('detail') or 'not available'}\n"
        "```\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "summary": (
                    "Agent-Reach CrewAI researcher demo completed. "
                    f"CrewAI available={crewai_available}, Agent-Reach available={doctor.get('available')}."
                ),
                "changed_paths": [out_path.as_posix()],
                "output_artifacts": [
                    {
                        "name": "agent_reach_crewai_research",
                        "kind": "report",
                        "uri": f"workspace://{out_path.as_posix()}",
                    }
                ],
                "recommended_action": "promote",
                "metrics": {"duration_ms": int((time.perf_counter() - started) * 1000)},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
