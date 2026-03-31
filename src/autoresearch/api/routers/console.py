"""Minimal control-plane console router.

JSON API endpoints for the control-plane console.
Mock data only. No real worker connections.

Available endpoints:
- GET /api/v1/console/tasks        - list tasks
- GET /api/v1/console/workers      - list workers
- GET /api/v1/console/runs/{run_id} - run detail
- GET /api/v1/console/approvals    - pending approvals
- GET /api/v1/console/             - landing page
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/v1/console", tags=["console"])

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_now = datetime.now(timezone.utc)
_offline_time = _now - timedelta(minutes=10)

_MOCK_WORKERS = [
    {
        "worker_id": "linux-housekeeper-01",
        "name": "Linux Housekeeper #1",
        "worker_type": "linux",
        "capabilities": ["shell", "script_runner", "log_collection"],
        "status": "offline",
        "backend_kind": "linux_supervisor",
        "last_heartbeat": _offline_time.isoformat(),
    },
    {
        "worker_id": "win-yingdao-01",
        "name": "Windows Yingdao #1",
        "worker_type": "win_yingdao",
        "capabilities": ["yingdao_flow", "form_fill"],
        "status": "offline",
        "backend_kind": "win_yingdao",
    },
    {
        "worker_id": "openclaw-runtime-01",
        "name": "OpenClaw Runtime #1",
        "worker_type": "openclaw",
        "capabilities": ["conversation", "skill_execution"],
        "status": "offline",
        "backend_kind": "openclaw_runtime",
    },
]

_MOCK_TASKS = [
    {
        "id": "task-001",
        "type": "software_change",
        "agent_package_id": "software-change",
        "status": "failed",
        "priority": "high",
        "worker_id": "linux-housekeeper-01",
        "error": {
            "code": "TIMEOUT",
            "message": "Worker timed out",
            "retryable": True,
            "suggested_action": "retry",
        },
        "tags": ["infra"],
    },
    {
        "id": "task-002",
        "type": "linux_housekeeping",
        "agent_package_id": "linux-housekeeping",
        "status": "succeeded",
        "priority": "medium",
        "worker_id": "linux-housekeeper-01",
        "tags": ["ops"],
    },
    {
        "id": "task-003",
        "type": "form_fill",
        "agent_package_id": "form-fill",
        "status": "approval_required",
        "requires_approval": True,
        "priority": "low",
        "tags": ["yingdao"],
    },
]

_MOCK_RUNS = [
    {
        "run_id": "run-001",
        "task_id": "task-001",
        "worker_id": "linux-housekeeper-01",
        "status": "failed",
        "error_message": "Worker timed out after 900s",
        "attempt": 1,
    },
    {
        "run_id": "run-002",
        "task_id": "task-002",
        "worker_id": "linux-housekeeper-01",
        "status": "succeeded",
        "attempt": 1,
    },
    {
        "run_id": "run-003",
        "task_id": "task-001",
        "worker_id": "linux-housekeeper-01",
        "status": "queued",
        "attempt": 2,
    },
]

_MOCK_GATE_VERDICTS = {
    "run-001": {
        "outcome": "timeout",
        "action": "retry",
        "reason": "Worker exceeded 900s timeout",
        "checks": [
            {
                "check_id": "timeout",
                "passed": False,
                "detail": "900s exceeded",
                "severity": "critical",
            },
        ],
    },
    "run-002": {
        "outcome": "success",
        "action": "accept",
        "checks": [
            {"check_id": "output_exists", "passed": True},
            {"check_id": "tests_pass", "passed": True},
        ],
    },
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks", summary="List tasks")
def list_tasks(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    tasks = _MOCK_TASKS
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks[:limit]


@router.get("/workers", summary="List workers")
def list_workers(
    status: str | None = None,
) -> list[dict]:
    workers = _MOCK_WORKERS
    if status:
        workers = [w for w in workers if w["status"] == status]
    return workers


@router.get("/runs/{run_id}", summary="Run detail")
def get_run(run_id: str) -> dict:
    for run in _MOCK_RUNS:
        if run["run_id"] == run_id:
            verdict = _MOCK_GATE_VERDICTS.get(run_id)
            return {"run": run, "gate_verdict": verdict}
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.get("/approvals", summary="Pending approvals")
def list_pending_approvals() -> list[dict]:
    return [t for t in _MOCK_TASKS if t.get("status") == "approval_required"]  # noqa: S709]


@router.get("/", summary="Console landing page")
def console_landing() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Control Plane Console</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; background: #0d1117; color: #c9d1d9; }
  h1 { color: #58a6ff; }
  nav a { color: #58a6ff; margin-right: 1rem; text-decoration: none; }
  nav a:hover { text-decoration: underline; }
  table { border-collapse: collapse; width: 100%%; margin-top: 1rem; }
  th, td { border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; }
  th { background: #161b22; color: #8b949e; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; }
  .offline { background: #6e7681; color: #fff; }
  .online { background: #238636; color: #fff; }
  .failed { background: #dc3545; color: #fff; }
  .succeeded { background: #238636; color: #fff; }
  .approval_required { background: #f0ad4e; color: #000; }
  .queued { background: #1f6feb; color: #000; }
</style>
</head>
<body>
<h1>Control Plane Console</h1>
<nav>
  <a href="/api/v1/console/tasks">Tasks</a>
  <a href="/api/v1/console/workers">Workers</a>
  <a href="/api/v1/console/approvals">Approvals</a>
</nav>
<p style="margin-top:2rem;color:#8b949e;">
  Mock data only. No real worker connections.<br>
  API endpoints:
  <code>/api/v1/console/tasks</code> |
  <code>/api/v1/console/workers</code> |
  <code>/api/v1/console/runs/{run_id}</code> |
  <code>/api/v1/console/approvals</code>
</p>
</body>
</html>"""
    return HTMLResponse(content=html)
