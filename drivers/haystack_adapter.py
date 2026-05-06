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


def _write_result(
    *,
    run_id: str,
    agent_id: str,
    summary: str,
    changed_paths: list[str],
    output_artifacts: list[dict[str, Any]],
    started: float,
) -> None:
    result_path = Path(os.environ["AEP_RESULT_PATH"])
    duration_ms = int((time.perf_counter() - started) * 1000)
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": "aep/v0",
                "run_id": run_id,
                "agent_id": agent_id,
                "attempt": int(os.environ.get("AEP_ATTEMPT", "1")),
                "status": "succeeded",
                "summary": summary,
                "changed_paths": changed_paths,
                "output_artifacts": output_artifacts,
                "metrics": {
                    "duration_ms": duration_ms,
                    "steps": 3,
                    "commands": 1,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                },
                "recommended_action": "promote",
                "error": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    started = time.perf_counter()
    workspace = Path(os.environ["AEP_WORKSPACE"])
    job = _read_job()
    run_id = str(job.get("run_id") or "haystack-demo")
    agent_id = str(job.get("agent_id") or "haystack_demo")
    task = str(job.get("task") or "Summarize AAS evergreen knowledge runtime.").strip()
    haystack_available = find_spec("haystack") is not None

    docs = [
        {
            "id": "runtime-contract",
            "title": "RuntimeAdapter v1",
            "text": "AAS keeps create_session, run, stream, cancel, status, and doctor stable while external frameworks change.",
        },
        {
            "id": "knowledge-boundary",
            "title": "Knowledge boundary",
            "text": "Haystack owns local retrieval pipelines; AAS owns actor permissions, provenance, citations, and artifacts.",
        },
        {
            "id": "evergreen-core",
            "title": "Evergreen core",
            "text": "Session, Policy, Approval, Audit, Artifact, Runtime, Capability, and Lease are long-lived AAS abstractions.",
        },
    ]
    query_terms = {item.lower() for item in task.replace("/", " ").replace(",", " ").split() if len(item) > 3}
    scored = []
    for doc in docs:
        text = f"{doc['title']} {doc['text']}".lower()
        score = sum(1 for term in query_terms if term in text)
        scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    citations = [item[1] for item in scored[:2]]

    out_dir = workspace / "docs" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "haystack_demo_report.md"
    out_path.write_text(
        "# Haystack Knowledge Runtime Demo\n\n"
        "中文：这个产物演示 Haystack 作为 AAS 知识/RAG runtime 的边界。AAS 管权限、引用审计和产物，Haystack 管检索流水线。\n\n"
        "English: This artifact demonstrates Haystack as an AAS knowledge/RAG runtime. AAS owns permissions, citation audit, and artifacts; Haystack owns retrieval pipelines.\n\n"
        f"- task: {task}\n"
        f"- haystack_available: {haystack_available}\n\n"
        "## Citations\n\n"
        + "\n".join(f"- `{doc['id']}`: {doc['text']}" for doc in citations)
        + "\n",
        encoding="utf-8",
    )
    rel = out_path.relative_to(workspace).as_posix()
    _write_result(
        run_id=run_id,
        agent_id=agent_id,
        summary=f"Haystack knowledge demo completed with {len(citations)} citations.",
        changed_paths=[rel],
        output_artifacts=[
            {
                "name": "haystack_demo_report",
                "kind": "report",
                "uri": f"workspace://{rel}",
            }
        ],
        started=started,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
