from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalDecisionRequest,
    ControlPlaneApprovalRead,
    ControlPlaneAuditEventRead,
    ControlPlaneCapabilityRead,
    ControlPlaneRunRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
)
from autoresearch.control_plane.butler_bridge import (
    ButlerControlPlaneRouteRead,
    ButlerControlPlaneRouteRequest,
    route_butler_message,
)
from autoresearch.control_plane.service import ControlPlaneService
from autoresearch.core.services.butler_dispatch import ButlerDispatchCenter
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionTimelineRead


def get_control_plane_service_dependency() -> ControlPlaneService:
    from autoresearch.api.dependencies import get_control_plane_service

    return get_control_plane_service()


def get_butler_dispatch_center_dependency() -> ButlerDispatchCenter:
    from autoresearch.api.dependencies import get_butler_dispatch_center

    return get_butler_dispatch_center()


def get_session_event_service_dependency() -> SessionEventService:
    from autoresearch.api.dependencies import get_session_event_service

    return get_session_event_service()


router = APIRouter(prefix="/api/v2", tags=["control-plane-v2"])
console_router = APIRouter(tags=["control-plane-v2"])


@console_router.get("/control-plane", response_class=HTMLResponse, include_in_schema=False)
def control_plane_console() -> HTMLResponse:
    return HTMLResponse(_CONTROL_PLANE_HTML)


@router.post("/tasks", response_model=ControlPlaneTaskRead, status_code=status.HTTP_202_ACCEPTED)
def create_task(
    payload: ControlPlaneTaskCreateRequest,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> ControlPlaneTaskRead:
    try:
        return service.create_task(payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability not found: {exc.args[0]}",
        ) from exc


@router.post("/butler/route", response_model=ButlerControlPlaneRouteRead)
def route_butler_task(
    payload: ButlerControlPlaneRouteRequest,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center_dependency),
    session_events: SessionEventService = Depends(get_session_event_service_dependency),
) -> ButlerControlPlaneRouteRead:
    return route_butler_message(
        payload,
        dispatch_center=dispatch_center,
        session_events=session_events,
        capabilities=service.list_capabilities(),
    )


@router.post(
    "/butler/tasks",
    response_model=ButlerControlPlaneRouteRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_butler_task(
    payload: ButlerControlPlaneRouteRequest,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center_dependency),
    session_events: SessionEventService = Depends(get_session_event_service_dependency),
) -> ButlerControlPlaneRouteRead:
    routed = route_butler_message(
        payload,
        dispatch_center=dispatch_center,
        session_events=session_events,
        capabilities=service.list_capabilities(),
    )
    try:
        task = service.create_task(routed.task_request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability not found: {exc.args[0]}",
        ) from exc
    return routed.model_copy(update={"task": task})


@router.get("/tasks", response_model=list[ControlPlaneTaskRead])
def list_tasks(
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> list[ControlPlaneTaskRead]:
    return service.list_tasks()


@router.get("/tasks/{task_id}", response_model=ControlPlaneTaskRead)
def get_task(
    task_id: str,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> ControlPlaneTaskRead:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/approval", response_model=ControlPlaneTaskRead)
def decide_task_approval(
    task_id: str,
    payload: ControlPlaneApprovalDecisionRequest,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> ControlPlaneTaskRead:
    try:
        task = service.decide_task(task_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/approvals", response_model=list[ControlPlaneApprovalRead])
def list_approvals(
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> list[ControlPlaneApprovalRead]:
    return service.list_approvals()


@router.get("/sessions/{session_id}/timeline", response_model=SessionTimelineRead)
def get_session_timeline(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> SessionTimelineRead:
    return service.session_timeline(session_id=session_id, limit=limit)


@router.get("/capabilities", response_model=list[ControlPlaneCapabilityRead])
def list_capabilities(
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> list[ControlPlaneCapabilityRead]:
    return service.list_capabilities()


@router.get("/runs/{run_id}", response_model=ControlPlaneRunRead)
def get_run(
    run_id: str,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> ControlPlaneRunRead:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/runs/{run_id}/events", response_model=list[ControlPlaneAuditEventRead])
def get_run_events(
    run_id: str,
    service: ControlPlaneService = Depends(get_control_plane_service_dependency),
) -> list[ControlPlaneAuditEventRead]:
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return service.run_events(run_id)


_CONTROL_PLANE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AAS Control Plane</title>
    <style>
      :root {
        --bg: #f6f7f9;
        --panel: #ffffff;
        --ink: #151b26;
        --muted: #667085;
        --line: #d9e0ea;
        --accent: #0f6b64;
        --warn: #8a5600;
        --danger: #b42318;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 16px 22px;
        background: #fff;
        border-bottom: 1px solid var(--line);
      }
      h1 { margin: 0; font-size: 20px; }
      main {
        display: grid;
        grid-template-columns: 370px minmax(0, 1fr);
        gap: 14px;
        padding: 14px;
      }
      section {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
      }
      h2 { margin: 0 0 12px; font-size: 15px; }
      label { display: block; margin: 9px 0 5px; font-size: 12px; color: var(--muted); }
      input, select, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 8px 9px;
        font: inherit;
        color: var(--ink);
        background: #fff;
      }
      textarea { min-height: 98px; resize: vertical; }
      button {
        border: 0;
        border-radius: 6px;
        padding: 8px 11px;
        color: #fff;
        background: var(--accent);
        font: inherit;
        font-weight: 650;
        cursor: pointer;
      }
      button.secondary { background: #475467; }
      button.reject { background: var(--danger); }
      .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
      .bands { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
      .metric { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fbfcfe; }
      .metric span { display: block; color: var(--muted); font-size: 12px; }
      .metric strong { display: block; margin-top: 4px; font-size: 20px; }
      .row { border-top: 1px solid var(--line); padding: 11px 0; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
      .row:first-child { border-top: 0; }
      .title { font-weight: 700; overflow-wrap: anywhere; }
      .meta { margin-top: 4px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
      .pill { border-radius: 999px; padding: 4px 8px; background: #eef2f6; color: #344054; font-size: 12px; font-weight: 700; height: fit-content; }
      .pill.awaiting_approval { background: #fff4d6; color: var(--warn); }
      .pill.succeeded { background: #dcfae6; color: #067647; }
      .pill.failed, .pill.rejected { background: #fee4e2; color: var(--danger); }
      pre { margin: 12px 0 0; max-height: 260px; overflow: auto; padding: 11px; border-radius: 6px; background: #101828; color: #f9fafb; font-size: 12px; }
      @media (max-width: 900px) {
        main { grid-template-columns: 1fr; }
        .bands { grid-template-columns: 1fr; }
      }
      </style>
  </head>
  <body>
    <header>
      <h1>AAS Control Plane v2</h1>
      <button class="secondary" id="refresh">Refresh</button>
    </header>
    <main>
      <section>
        <h2>自然语言任务 | Natural Language Task</h2>
        <form id="butler-form">
          <label>消息 | Message</label>
          <textarea name="message" placeholder="帮我看这个 PR / Review this PR" required></textarea>
          <label>会话 ID | Session ID</label>
          <input name="session_id" placeholder="optional" />
          <label>请求人 | Requested By</label>
          <input name="requested_by" value="control-plane" />
          <div class="actions">
            <button type="submit">创建任务 | Create</button>
            <button class="secondary" type="button" id="preview-route">预览路由 | Preview</button>
          </div>
        </form>
        <h2 style="margin-top:18px;">结构化任务 | Structured Task</h2>
        <form id="task-form">
          <label>名称 | Name</label>
          <input name="name" value="v2 echo smoke" required />
          <label>能力 | Capability</label>
          <select name="capability_id" id="capability"></select>
          <label>风险标签 | Risk Tags</label>
          <input name="risk_tags" placeholder="shell, filesystem_write, external_api" />
          <label>参数 | Parameters</label>
          <textarea name="parameters">{ "message": "hello v2" }</textarea>
          <div class="actions"><button type="submit">提交 | Submit</button></div>
        </form>
      </section>
      <section>
        <div class="bands">
          <div class="metric"><span>Tasks</span><strong id="task-count">0</strong></div>
          <div class="metric"><span>Approvals</span><strong id="approval-count">0</strong></div>
          <div class="metric"><span>Capabilities</span><strong id="capability-count">0</strong></div>
        </div>
        <h2>Task Inbox</h2>
        <div id="tasks"></div>
        <pre id="detail" hidden></pre>
      </section>
    </main>
    <script>
      const tasksEl = document.querySelector("#tasks");
      const detailEl = document.querySelector("#detail");
      const capabilityEl = document.querySelector("#capability");
      const butlerForm = document.querySelector("#butler-form");
      async function api(path, options = {}) {
        const response = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
      }
      function parseTags(value) {
        return value.split(",").map((item) => item.trim()).filter(Boolean);
      }
      function parseJSON(value) {
        const raw = value.trim();
        return raw ? JSON.parse(raw) : {};
      }
      async function loadCapabilities() {
        const caps = await api("/api/v2/capabilities");
        document.querySelector("#capability-count").textContent = caps.length;
        capabilityEl.innerHTML = caps.map((cap) =>
          `<option value="${cap.capability_id}" ${cap.enabled ? "" : "disabled"}>${cap.name}</option>`
        ).join("");
      }
      async function loadTasks() {
        const [tasks, approvals] = await Promise.all([api("/api/v2/tasks"), api("/api/v2/approvals")]);
        document.querySelector("#task-count").textContent = tasks.length;
        document.querySelector("#approval-count").textContent = approvals.filter((item) => item.status === "pending").length;
        tasksEl.innerHTML = tasks.map((task) => `
          <div class="row">
            <div>
              <div class="title">${task.name}</div>
              <div class="meta">${task.task_id} | session=${task.session_id}</div>
              <div class="meta">capability=${task.capability_id} | tags=${task.risk_tags.join(",") || "none"}</div>
              <div class="actions">
                ${task.status === "awaiting_approval" ? `<button data-approve="${task.task_id}">Approve</button><button class="reject" data-reject="${task.task_id}">Reject</button>` : ""}
                ${task.run_id ? `<button class="secondary" data-run="${task.run_id}">Run</button>` : ""}
                <button class="secondary" data-session="${task.session_id}">Timeline</button>
              </div>
            </div>
            <span class="pill ${task.status}">${task.status}</span>
          </div>`).join("") || `<div class="meta">No tasks yet.</div>`;
      }
      function butlerPayload() {
        const form = new FormData(butlerForm);
        const payload = {
          message: form.get("message"),
          requested_by: form.get("requested_by") || "control-plane"
        };
        const sessionId = (form.get("session_id") || "").trim();
        if (sessionId) payload.session_id = sessionId;
        return payload;
      }
      butlerForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const result = await api("/api/v2/butler/tasks", {
          method: "POST",
          body: JSON.stringify(butlerPayload())
        });
        detailEl.hidden = false;
        detailEl.textContent = JSON.stringify(result, null, 2);
        await loadTasks();
      });
      document.querySelector("#preview-route").addEventListener("click", async () => {
        const result = await api("/api/v2/butler/route", {
          method: "POST",
          body: JSON.stringify(butlerPayload())
        });
        detailEl.hidden = false;
        detailEl.textContent = JSON.stringify(result, null, 2);
      });
      document.querySelector("#task-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = new FormData(event.target);
        await api("/api/v2/tasks", {
          method: "POST",
          body: JSON.stringify({
            name: form.get("name"),
            capability_id: form.get("capability_id"),
            risk_tags: parseTags(form.get("risk_tags") || ""),
            parameters: parseJSON(form.get("parameters") || "")
          })
        });
        await loadTasks();
      });
      tasksEl.addEventListener("click", async (event) => {
        const approve = event.target.dataset.approve;
        const reject = event.target.dataset.reject;
        const run = event.target.dataset.run;
        const session = event.target.dataset.session;
        if (approve) {
          await api(`/api/v2/tasks/${approve}/approval`, { method: "POST", body: JSON.stringify({ decision: "approved", decided_by: "control-plane" }) });
          await loadTasks();
        }
        if (reject) {
          await api(`/api/v2/tasks/${reject}/approval`, { method: "POST", body: JSON.stringify({ decision: "rejected", decided_by: "control-plane", note: "Rejected in v2 console" }) });
          await loadTasks();
        }
        if (run) {
          detailEl.hidden = false;
          detailEl.textContent = JSON.stringify(await api(`/api/v2/runs/${run}/events`), null, 2);
        }
        if (session) {
          detailEl.hidden = false;
          detailEl.textContent = JSON.stringify(await api(`/api/v2/sessions/${session}/timeline`), null, 2);
        }
      });
      document.querySelector("#refresh").addEventListener("click", loadTasks);
      loadCapabilities().then(loadTasks).catch((error) => { tasksEl.innerHTML = `<div class="meta">${error.message}</div>`; });
    </script>
  </body>
</html>
"""
