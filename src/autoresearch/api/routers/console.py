"""Enhanced control-plane console router.

JSON API endpoints for the control-plane console.
Mock data only. No real worker connections.

Available endpoints:
- GET /api/v1/console/tasks        - list tasks (with status filter)
- GET /api/v1/console/workers      - list workers (with status filter)
- GET /api/v1/console/runs/{run_id} - run detail
- GET /api/v1/console/approvals    - pending approvals
- POST /api/v1/console/approvals/{task_id}/approve  - approve task
- POST /api/v1/console/approvals/{task_id}/reject   - reject task
- POST /api/v1/console/approvals/{task_id}/retry    - retry task
- POST /api/v1/console/approvals/{task_id}/fallback - fallback task
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
_degraded_time = _now - timedelta(minutes=2)

_MOCK_WORKERS = [
    {
        "worker_id": "linux-housekeeper-01",
        "name": "Linux Housekeeper #1",
        "worker_type": "linux",
        "capabilities": ["shell", "script_runner", "log_collection", "ops_inspection"],
        "status": "online",
        "backend_kind": "linux_supervisor",
        "last_heartbeat": _now.isoformat(),
        "heartbeat_age_seconds": 5,
        "metrics": {
            "cpu_usage_percent": 35.0,
            "memory_usage_mb": 512.0,
            "active_tasks": 1,
            "total_tasks_completed": 42,
        },
    },
    {
        "worker_id": "win-yingdao-01",
        "name": "Windows Yingdao #1",
        "worker_type": "win_yingdao",
        "capabilities": ["yingdao_flow", "form_fill", "structured_data_entry"],
        "status": "offline",
        "backend_kind": "win_yingdao",
        "last_heartbeat": _offline_time.isoformat(),
        "heartbeat_age_seconds": 600,
        "metrics": None,
    },
    {
        "worker_id": "openclaw-runtime-01",
        "name": "OpenClaw Runtime #1",
        "worker_type": "openclaw",
        "capabilities": ["conversation", "skill_execution", "session_runtime"],
        "status": "degraded",
        "backend_kind": "openclaw_runtime",
        "last_heartbeat": _degraded_time.isoformat(),
        "heartbeat_age_seconds": 120,
        "metrics": {
            "cpu_usage_percent": 15.0,
            "memory_usage_mb": 256.0,
            "active_tasks": 0,
            "total_tasks_completed": 12,
        },
    },
]

_MOCK_TASKS = [
    {
        "id": "task-001",
        "type": "software_change",
        "agent_package_id": "software-change",
        "status": "succeeded",
        "priority": "high",
        "worker_id": "linux-housekeeper-01",
        "tags": ["infra"],
        "result": {"success": True, "data": {"files_changed": 3}},
        "created_at": (_now - timedelta(hours=1)).isoformat(),
        "completed_at": (_now - timedelta(minutes=30)).isoformat(),
    },
    {
        "id": "task-002",
        "type": "linux_housekeeping",
        "agent_package_id": "linux-housekeeping",
        "status": "failed",
        "priority": "medium",
        "worker_id": "linux-housekeeper-01",
        "error": {
            "code": "TIMEOUT",
            "message": "Worker timed out after 900s",
            "retryable": True,
            "suggested_action": "retry",
        },
        "tags": ["ops"],
        "created_at": (_now - timedelta(hours=2)).isoformat(),
    },
    {
        "id": "task-003",
        "type": "form_fill",
        "agent_package_id": "form-fill",
        "status": "approval_required",
        "requires_approval": True,
        "priority": "low",
        "tags": ["yingdao"],
        "created_at": (_now - timedelta(minutes=15)).isoformat(),
    },
    {
        "id": "task-004",
        "type": "software_change",
        "agent_package_id": "software-change",
        "status": "running",
        "priority": "high",
        "worker_id": "linux-housekeeper-01",
        "tags": ["infra", "urgent"],
        "created_at": (_now - timedelta(minutes=5)).isoformat(),
    },
    {
        "id": "task-005",
        "type": "linux_housekeeping",
        "agent_package_id": "linux-housekeeping",
        "status": "pending",
        "priority": "medium",
        "tags": ["ops"],
        "created_at": _now.isoformat(),
    },
]

_MOCK_RUNS = [
    {
        "run_id": "run-001",
        "task_id": "task-001",
        "worker_id": "linux-housekeeper-01",
        "status": "succeeded",
        "attempt": 1,
        "queued_at": (_now - timedelta(hours=1)).isoformat(),
        "started_at": (_now - timedelta(minutes=55)).isoformat(),
        "completed_at": (_now - timedelta(minutes=30)).isoformat(),
        "logs": [
            {
                "timestamp": (_now - timedelta(minutes=55)).isoformat(),
                "level": "info",
                "message": "Starting task execution",
            },
            {
                "timestamp": (_now - timedelta(minutes=45)).isoformat(),
                "level": "info",
                "message": "Applied 3 file changes",
            },
            {
                "timestamp": (_now - timedelta(minutes=35)).isoformat(),
                "level": "info",
                "message": "All tests passing",
            },
            {
                "timestamp": (_now - timedelta(minutes=30)).isoformat(),
                "level": "info",
                "message": "Task completed successfully",
            },
        ],
        "artifacts": [
            {"type": "file", "path": "/workspace/diff.patch", "size_bytes": 2048},
            {"type": "log", "path": "/workspace/output.log", "size_bytes": 4096},
        ],
    },
    {
        "run_id": "run-002",
        "task_id": "task-002",
        "worker_id": "linux-housekeeper-01",
        "status": "failed",
        "error_message": "Worker timed out after 900s",
        "attempt": 1,
        "queued_at": (_now - timedelta(hours=2)).isoformat(),
        "started_at": (_now - timedelta(hours=2, minutes=5)).isoformat(),
        "completed_at": (_now - timedelta(hours=1, minutes=40)).isoformat(),
        "logs": [
            {
                "timestamp": (_now - timedelta(hours=2, minutes=5)).isoformat(),
                "level": "info",
                "message": "Starting housekeeping task",
            },
            {
                "timestamp": (_now - timedelta(hours=1, minutes=45)).isoformat(),
                "level": "warning",
                "message": "Task running for 600s, approaching timeout",
            },
            {
                "timestamp": (_now - timedelta(hours=1, minutes=40)).isoformat(),
                "level": "error",
                "message": "TIMEOUT: exceeded 900s limit",
            },
        ],
        "artifacts": [],
    },
    {
        "run_id": "run-003",
        "task_id": "task-002",
        "worker_id": "linux-housekeeper-01",
        "status": "queued",
        "attempt": 2,
        "queued_at": (_now - timedelta(minutes=5)).isoformat(),
        "logs": [],
        "artifacts": [],
    },
]

_MOCK_GATE_VERDICTS = {
    "run-001": {
        "outcome": "success",
        "action": "accept",
        "reason": "All checks passed",
        "checks": [
            {"check_id": "output_exists", "passed": True},
            {"check_id": "tests_pass", "passed": True},
            {"check_id": "scope_check", "passed": True},
        ],
    },
    "run-002": {
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
        "retry_attempt": 0,
        "max_retries": 3,
    },
}

# Approval action log (in-memory, resets on server restart)
_APPROVAL_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks", summary="List tasks")
def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    tasks = _MOCK_TASKS
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
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
    return [t for t in _MOCK_TASKS if t.get("status") == "approval_required"]


@router.post("/approvals/{task_id}/approve", summary="Approve a task")
def approve_task(task_id: str) -> dict:
    for task in _MOCK_TASKS:
        if task["id"] == task_id and task["status"] == "approval_required":
            task["status"] = "queued"
            task["approval_status"] = "approved"
            _APPROVAL_LOG.append({"task_id": task_id, "action": "approve", "at": _now.isoformat()})
            return {"task_id": task_id, "action": "approved", "new_status": "queued"}
    raise HTTPException(
        status_code=404, detail=f"Task {task_id} not found or not awaiting approval"
    )


@router.post("/approvals/{task_id}/reject", summary="Reject a task")
def reject_task(task_id: str) -> dict:
    for task in _MOCK_TASKS:
        if task["id"] == task_id and task["status"] == "approval_required":
            task["status"] = "rejected"
            task["approval_status"] = "rejected"
            _APPROVAL_LOG.append({"task_id": task_id, "action": "reject", "at": _now.isoformat()})
            return {"task_id": task_id, "action": "rejected", "new_status": "rejected"}
    raise HTTPException(
        status_code=404, detail=f"Task {task_id} not found or not awaiting approval"
    )


@router.post("/approvals/{task_id}/retry", summary="Retry a failed task")
def retry_task(task_id: str) -> dict:
    for task in _MOCK_TASKS:
        if task["id"] == task_id and task["status"] == "failed":
            task["status"] = "queued"
            task["retry_count"] = task.get("retry_count", 0) + 1
            _APPROVAL_LOG.append({"task_id": task_id, "action": "retry", "at": _now.isoformat()})
            return {
                "task_id": task_id,
                "action": "retried",
                "new_status": "queued",
                "retry_count": task["retry_count"],
            }
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not failed")


@router.post("/approvals/{task_id}/fallback", summary="Fallback a failed task")
def fallback_task(task_id: str) -> dict:
    for task in _MOCK_TASKS:
        if task["id"] == task_id and task["status"] == "failed":
            task["status"] = "queued"
            task["fallback_agent"] = "fallback-handler"
            _APPROVAL_LOG.append({"task_id": task_id, "action": "fallback", "at": _now.isoformat()})
            return {
                "task_id": task_id,
                "action": "fallback",
                "new_status": "queued",
                "fallback_agent": "fallback-handler",
            }
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not failed")


@router.get("/approval-log", summary="Approval action log")
def get_approval_log() -> list[dict]:
    return _APPROVAL_LOG


@router.get("/", summary="Console landing page")
def console_landing() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Control Plane Console</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; background: #0d1117; color: #c9d1d9; }
  h1 { color: #58a6ff; }
  h2 { color: #8b949e; margin-top: 2rem; }
  nav a { color: #58a6ff; margin-right: 1rem; text-decoration: none; }
  nav a:hover { text-decoration: underline; }
  table { border-collapse: collapse; width: 100%%; margin-top: 1rem; }
  th, td { border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; font-size: 0.9rem; }
  th { background: #161b22; color: #8b949e; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
  .offline { background: #6e7681; color: #fff; }
  .online { background: #238636; color: #fff; }
  .busy { background: #1f6feb; color: #fff; }
  .degraded { background: #d29922; color: #000; }
  .failed { background: #dc3545; color: #fff; }
  .succeeded { background: #238636; color: #fff; }
  .approval_required { background: #f0ad4e; color: #000; }
  .queued { background: #1f6feb; color: #fff; }
  .running { background: #58a6ff; color: #000; }
  .pending { background: #6e7681; color: #fff; }
  .rejected { background: #6e40c9; color: #fff; }
  .needs_review { background: #d29922; color: #000; }
  .cap { background: #161b22; border: 1px solid #30363d; padding: 1px 6px; border-radius: 4px; font-size: 0.7rem; color: #8b949e; }
  .priority-high { color: #f85149; font-weight: 600; }
  .priority-medium { color: #d29922; }
  .priority-low { color: #8b949e; }
  .priority-critical { color: #ff7b72; font-weight: 700; text-transform: uppercase; }
  .mono { font-family: monospace; font-size: 0.85rem; }
  .dim { color: #8b949e; }
  .log-info { color: #58a6ff; }
  .log-warning { color: #d29922; }
  .log-error { color: #f85149; }
  .check-pass { color: #238636; }
  .check-fail { color: #f85149; }
  .artifact { background: #161b22; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; margin: 2px 0; }
  .section { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
  .btn { padding: 4px 12px; border-radius: 6px; border: 1px solid #30363d; cursor: pointer; font-size: 0.8rem; margin: 2px; }
  .btn-approve { background: #238636; color: #fff; }
  .btn-reject { background: #dc3545; color: #fff; }
  .btn-retry { background: #1f6feb; color: #fff; }
  .btn-fallback { background: #d29922; color: #000; }
</style>
</head>
<body>
<h1>Control Plane Console</h1>
<nav>
  <a href="/api/v1/console/">Overview</a>
  <a href="/api/v1/console/tasks">Tasks</a>
  <a href="/api/v1/console/workers">Workers</a>
  <a href="/api/v1/console/approvals">Approvals</a>
</nav>

<h2>Tasks</h2>
<div id="task-filters" style="margin: 0.5rem 0;">
  <button class="btn" onclick="filterTasks()">All</button>
  <button class="btn" onclick="filterTasks('pending')">Pending</button>
  <button class="btn" onclick="filterTasks('queued')">Queued</button>
  <button class="btn" onclick="filterTasks('running')">Running</button>
  <button class="btn" onclick="filterTasks('succeeded')">Succeeded</button>
  <button class="btn" onclick="filterTasks('failed')">Failed</button>
  <button class="btn" onclick="filterTasks('approval_required')">Awaiting Approval</button>
</div>
<table id="task-table">
  <thead>
    <tr><th>ID</th><th>Type</th><th>Status</th><th>Priority</th><th>Worker</th><th>Tags</th><th>Created</th></tr>
  </thead>
  <tbody id="task-body"></tbody>
</table>

<h2>Workers</h2>
<table id="worker-table">
  <thead>
    <tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th><th>Capabilities</th><th>Last Heartbeat</th><th>Age</th></tr>
  </thead>
  <tbody id="worker-body"></tbody>
</table>

<h2>Runs</h2>
<div class="section">
  <input id="run-id-input" class="mono" placeholder="Enter run ID (e.g. run-001)" style="padding:4px 8px; background:#161b22; color:#c9d1d9; border:1px solid #30363d; border-radius:4px;">
  <button class="btn btn-retry" onclick="loadRun()">Load Run</button>
</div>
<div id="run-detail" class="section" style="display:none;">
  <h3 id="run-title"></h3>
  <div id="run-status-bar"></div>
  <div id="run-timeline"></div>
  <h4>Logs</h4>
  <div id="run-logs" class="mono" style="max-height:200px; overflow-y:auto;"></div>
  <h4>Artifacts</h4>
  <div id="run-artifacts"></div>
  <h4>Gate Verdict</h4>
  <div id="run-gate-verdict"></div>
</div>

<h2>Approval Queue</h2>
<div id="approval-section"></div>

<p style="margin-top:2rem;color:#8b949e;">
  Mock data only. No real worker connections.<br>
  API endpoints:
  <code>/api/v1/console/tasks</code> |
  <code>/api/v1/console/workers</code> |
  <code>/api/v1/console/runs/{run_id}</code> |
  <code>/api/v1/console/approvals</code> |
  <code>/api/v1/console/approval-log</code>
</p>

<script>
const _allTasks = %s;
const _allWorkers = %s;

function badge(cls, text) {
  return '<span class="badge ' + cls + '">' + text + '</span>';
}

function priorityBadge(p) {
  return '<span class="priority-' + p + '">' + p.toUpperCase() + '</span>';
}

function capTag(c) {
  return '<span class="cap">' + c + '</span>';
}

function formatAge(seconds) {
  if (seconds < 60) return seconds + 's ago';
  if (seconds < 3600) return Math.floor(seconds/60) + 'm ago';
  return Math.floor(seconds/3600) + 'h ago';
}

// --- Tasks ---
let _currentFilter = null;

function renderTasks(filter) {
  const tbody = document.getElementById('task-body');
  let tasks = _allTasks;
  if (filter) tasks = tasks.filter(t => t.status === filter);
  tbody.innerHTML = tasks.map(t => '<tr>'
    + '<td class="mono">' + t.id + '</td>'
    + '<td>' + t.type + '</td>'
    + '<td>' + badge(t.status, t.status.replace(/_/g, ' ')) + '</td>'
    + '<td>' + priorityBadge(t.priority) + '</td>'
    + '<td class="mono dim">' + (t.worker_id || '—') + '</td>'
    + '<td>' + (t.tags || []).map(capTag).join(' ') + '</td>'
    + '<td class="dim">' + (t.created_at || '—') + '</td>'
    + '</tr>').join('');
}

function filterTasks(status) {
  _currentFilter = status;
  renderTasks(status);
}

// --- Workers ---
function renderWorkers() {
  const tbody = document.getElementById('worker-body');
  tbody.innerHTML = _allWorkers.map(w => '<tr>'
    + '<td class="mono">' + w.worker_id + '</td>'
    + '<td>' + w.name + '</td>'
    + '<td>' + badge(w.worker_type, w.worker_type) + '</td>'
    + '<td>' + badge(w.status, w.status) + '</td>'
    + '<td>' + (w.capabilities || []).map(capTag).join(' ') + '</td>'
    + '<td class="mono dim">' + (w.last_heartbeat || '—') + '</td>'
    + '<td class="dim">' + formatAge(w.heartbeat_age_seconds || 0) + '</td>'
    + '</tr>').join('');
}

// --- Run Detail ---
async function loadRun() {
  const runId = document.getElementById('run-id-input').value.trim();
  if (!runId) return;
  try {
    const resp = await fetch('/api/v1/console/runs/' + runId);
    if (!resp.ok) throw new Error('Run not found');
    const data = await resp.json();
    renderRun(data);
  } catch(e) {
    document.getElementById('run-detail').style.display = 'block';
    document.getElementById('run-title').textContent = 'Error: ' + e.message;
  }
}

function renderRun(data) {
  const run = data.run;
  const verdict = data.gate_verdict;
  const el = document.getElementById('run-detail');
  el.style.display = 'block';
  document.getElementById('run-title').textContent = 'Run: ' + run.run_id + ' (task: ' + run.task_id + ')';
  document.getElementById('run-status-bar').innerHTML = badge(run.status, run.status) + ' attempt #' + (run.attempt || 1);

  // Timeline
  const timeline = ['queued_at', 'started_at', 'completed_at']
    .filter(k => run[k])
    .map(k => '<div class="dim">' + k.replace('_at','') + ': ' + run[k] + '</div>')
    .join('');
  document.getElementById('run-timeline').innerHTML = timeline;

  // Logs
  const logs = (run.logs || []).map(l =>
    '<div class="log-' + l.level + '">' + l.timestamp + ' [' + l.level + '] ' + l.message + '</div>'
  ).join('');
  document.getElementById('run-logs').innerHTML = logs || '<span class="dim">No logs</span>';

  // Artifacts
  const arts = (run.artifacts || []).map(a =>
    '<div class="artifact">' + a.type + ': ' + a.path + ' (' + a.size_bytes + ' bytes)</div>'
  ).join('');
  document.getElementById('run-artifacts').innerHTML = arts || '<span class="dim">No artifacts</span>';

  // Gate verdict
  if (verdict) {
    const checks = (verdict.checks || []).map(c => {
      const icon = c.passed ? '✓' : '✗';
      const cls = c.passed ? 'check-pass' : 'check-fail';
      return '<div class="' + cls + '">' + icon + ' ' + c.check_id + (c.detail ? ': ' + c.detail : '') + '</div>';
    }).join('');
    document.getElementById('run-gate-verdict').innerHTML =
      '<div>' + badge(verdict.outcome, verdict.outcome) + ' → ' + badge(verdict.action, verdict.action) + '</div>'
      + '<div class="dim">' + (verdict.reason || '') + '</div>'
      + checks;
  } else {
    document.getElementById('run-gate-verdict').innerHTML = '<span class="dim">No gate verdict</span>';
  }
}

// --- Approval Queue ---
function loadApprovals() {
  fetch('/api/v1/console/approvals')
    .then(r => r.json())
    .then(tasks => {
      const el = document.getElementById('approval-section');
      if (tasks.length === 0) {
        el.innerHTML = '<p class="dim">No pending approvals</p>';
        return;
      }
      el.innerHTML = tasks.map(t =>
        '<div class="section">'
        + '<div><strong>' + t.id + '</strong> — ' + t.type + ' ' + badge('approval_required', 'AWAITING APPROVAL') + '</div>'
        + '<div class="dim">Priority: ' + priorityBadge(t.priority) + ' | Tags: ' + (t.tags||[]).join(', ') + '</div>'
        + '<div style="margin-top:0.5rem;">'
        + '<button class="btn btn-approve" onclick="doApproval(\\'' + t.id + '\\', \\'approve\\')">Approve</button>'
        + '<button class="btn btn-reject" onclick="doApproval(\\'' + t.id + '\\', \\'reject\\')">Reject</button>'
        + '</div></div>'
      ).join('');
    });
}

function doApproval(taskId, action) {
  fetch('/api/v1/console/approvals/' + taskId + '/' + action, {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      alert('Task ' + taskId + ': ' + data.action + ' → status: ' + data.new_status);
      location.reload();
    })
    .catch(e => alert('Error: ' + e.message));
}

// --- Init ---
renderTasks();
renderWorkers();
loadApprovals();
</script>
</body>
</html>""" % (
        str([_serialize_task(t) for t in _MOCK_TASKS]),
        str([_serialize_worker(w) for w in _MOCK_WORKERS]),
    )
    return HTMLResponse(content=html)


def _serialize_task(t: dict) -> dict:
    """Ensure task is JSON-serializable for embedding in HTML."""
    result = dict(t)
    for k, v in result.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
    return result


def _serialize_worker(w: dict) -> dict:
    """Ensure worker is JSON-serializable for embedding in HTML."""
    result = dict(w)
    for k, v in result.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
    return result
