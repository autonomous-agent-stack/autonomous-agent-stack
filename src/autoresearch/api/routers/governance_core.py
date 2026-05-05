from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from autoresearch.core.services.governance_core import GovernanceCoreService
from autoresearch.shared.governance_core import (
    GovernanceAdapterRead,
    GovernanceApprovalDecisionRequest,
    GovernanceAuditEventRead,
    GovernanceRunRead,
    GovernanceTaskCreateRequest,
    GovernanceTaskRead,
)


def get_governance_core_service_dependency() -> GovernanceCoreService:
    from autoresearch.api.dependencies import get_governance_core_service

    return get_governance_core_service()


def build_router(prefix: str = "") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["governance core"])

    @router.get("/governance", response_class=HTMLResponse, include_in_schema=False)
    def governance_panel() -> HTMLResponse:
        return HTMLResponse(_GOVERNANCE_PANEL_HTML)

    @router.post(
        "/tasks",
        response_model=GovernanceTaskRead,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_task(
        payload: GovernanceTaskCreateRequest,
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> GovernanceTaskRead:
        return service.create_task(payload)

    @router.get("/tasks", response_model=list[GovernanceTaskRead])
    def list_tasks(
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> list[GovernanceTaskRead]:
        return service.list_tasks()

    @router.get("/tasks/{task_id}", response_model=GovernanceTaskRead)
    def get_task(
        task_id: str,
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> GovernanceTaskRead:
        task = service.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    @router.post("/tasks/{task_id}/approve", response_model=GovernanceTaskRead)
    def approve_task(
        task_id: str,
        payload: GovernanceApprovalDecisionRequest,
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> GovernanceTaskRead:
        try:
            task = service.decide_task(task_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    @router.get("/runs/{run_id}", response_model=GovernanceRunRead)
    def get_run(
        run_id: str,
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> GovernanceRunRead:
        run = service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return run

    @router.get("/runs/{run_id}/events", response_model=list[GovernanceAuditEventRead])
    def get_run_events(
        run_id: str,
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> list[GovernanceAuditEventRead]:
        if service.get_run(run_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        return service.list_run_events(run_id)

    @router.get("/adapters", response_model=list[GovernanceAdapterRead])
    def list_adapters(
        service: GovernanceCoreService = Depends(get_governance_core_service_dependency),
    ) -> list[GovernanceAdapterRead]:
        return service.list_adapters()

    return router


router = build_router()
api_router = build_router(prefix="/api/v1/governance")


_GOVERNANCE_PANEL_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AAS Governance</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f7f8fb;
        --panel: #ffffff;
        --ink: #18202f;
        --muted: #647084;
        --line: #d8dee8;
        --accent: #176b87;
        --danger: #b42318;
        --ok: #087443;
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
        padding: 18px 24px;
        border-bottom: 1px solid var(--line);
        background: #fff;
      }
      h1 { margin: 0; font-size: 20px; font-weight: 700; }
      main {
        display: grid;
        grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
        gap: 16px;
        padding: 16px;
      }
      section {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
      }
      h2 { margin: 0 0 12px; font-size: 15px; }
      label { display: block; margin: 10px 0 6px; font-size: 13px; color: var(--muted); }
      input, textarea, select {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 9px 10px;
        font: inherit;
        background: #fff;
        color: var(--ink);
      }
      textarea { min-height: 104px; resize: vertical; }
      button {
        border: 0;
        border-radius: 6px;
        padding: 9px 12px;
        font: inherit;
        font-weight: 650;
        background: var(--accent);
        color: #fff;
        cursor: pointer;
      }
      button.secondary { background: #42526b; }
      button.reject { background: var(--danger); }
      button:disabled { cursor: not-allowed; opacity: .5; }
      .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .task {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
        padding: 12px 0;
        border-top: 1px solid var(--line);
      }
      .task:first-child { border-top: 0; }
      .title { font-weight: 700; overflow-wrap: anywhere; }
      .meta { margin-top: 4px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
      .pill {
        align-self: start;
        min-width: 88px;
        text-align: center;
        border-radius: 999px;
        padding: 4px 8px;
        background: #e9eef5;
        color: #2d3b4f;
        font-size: 12px;
        font-weight: 700;
      }
      .pill.succeeded { background: #def7ec; color: var(--ok); }
      .pill.failed, .pill.rejected { background: #fee4e2; color: var(--danger); }
      .pill.awaiting_approval { background: #fff3c4; color: #7a4d00; }
      pre {
        max-height: 260px;
        overflow: auto;
        margin: 12px 0 0;
        padding: 12px;
        border-radius: 6px;
        background: #111827;
        color: #f8fafc;
        font-size: 12px;
      }
      @media (max-width: 860px) {
        main { grid-template-columns: 1fr; padding: 12px; }
        header { align-items: flex-start; flex-direction: column; }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>AAS Governance Core</h1>
      <button class="secondary" id="refresh">Refresh</button>
    </header>
    <main>
      <section>
        <h2>Create Task</h2>
        <form id="taskForm">
          <label for="name">Name</label>
          <input id="name" name="name" value="Echo smoke task" required />
          <div class="grid">
            <div>
              <label for="adapter">Adapter</label>
              <select id="adapter" name="adapter_id"></select>
            </div>
            <div>
              <label for="risk">Risk Tags</label>
              <input id="risk" name="risk_tags" placeholder="shell, external_api" />
            </div>
          </div>
          <label for="params">Parameters</label>
          <textarea id="params" name="parameters">{ "message": "hello governance" }</textarea>
          <div class="actions">
            <button type="submit">Submit</button>
          </div>
        </form>
      </section>
      <section>
        <h2>Tasks</h2>
        <div id="tasks"></div>
        <pre id="events" hidden></pre>
      </section>
    </main>
    <script>
      const tasksEl = document.querySelector("#tasks");
      const eventsEl = document.querySelector("#events");
      const adapterEl = document.querySelector("#adapter");

      async function api(path, options = {}) {
        const response = await fetch(path, {
          headers: { "content-type": "application/json" },
          ...options
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
      }

      function tags(value) {
        return value.split(",").map((item) => item.trim()).filter(Boolean);
      }

      function parseParams() {
        const raw = document.querySelector("#params").value.trim();
        if (!raw) return {};
        return JSON.parse(raw);
      }

      async function loadAdapters() {
        const adapters = await api("/adapters");
        adapterEl.innerHTML = adapters.map((adapter) =>
          `<option value="${adapter.adapter_id}" ${adapter.enabled ? "" : "disabled"}>${adapter.name}</option>`
        ).join("");
      }

      async function loadTasks() {
        const tasks = await api("/tasks");
        tasksEl.innerHTML = tasks.map((task) => `
          <div class="task">
            <div>
              <div class="title">${task.name}</div>
              <div class="meta">${task.task_id}</div>
              <div class="meta">adapter=${task.adapter_id} tags=${task.risk_tags.join(",") || "none"}</div>
              <div class="actions">
                ${task.status === "awaiting_approval" ? `<button data-approve="${task.task_id}">Approve</button><button class="reject" data-reject="${task.task_id}">Reject</button>` : ""}
                ${task.run_id ? `<button class="secondary" data-events="${task.run_id}">Events</button>` : ""}
              </div>
            </div>
            <span class="pill ${task.status}">${task.status}</span>
          </div>
        `).join("") || `<div class="meta">No tasks yet.</div>`;
      }

      document.querySelector("#taskForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = new FormData(event.target);
        await api("/tasks", {
          method: "POST",
          body: JSON.stringify({
            name: form.get("name"),
            adapter_id: form.get("adapter_id"),
            risk_tags: tags(form.get("risk_tags") || ""),
            parameters: parseParams()
          })
        });
        await loadTasks();
      });

      tasksEl.addEventListener("click", async (event) => {
        const approveId = event.target.dataset.approve;
        const rejectId = event.target.dataset.reject;
        const runId = event.target.dataset.events;
        if (approveId) {
          await api(`/tasks/${approveId}/approve`, {
            method: "POST",
            body: JSON.stringify({ decision: "approved", approver: "panel" })
          });
          await loadTasks();
        }
        if (rejectId) {
          await api(`/tasks/${rejectId}/approve`, {
            method: "POST",
            body: JSON.stringify({ decision: "rejected", approver: "panel", note: "Rejected in panel" })
          });
          await loadTasks();
        }
        if (runId) {
          eventsEl.hidden = false;
          eventsEl.textContent = JSON.stringify(await api(`/runs/${runId}/events`), null, 2);
        }
      });

      document.querySelector("#refresh").addEventListener("click", loadTasks);
      loadAdapters().then(loadTasks).catch((error) => {
        tasksEl.innerHTML = `<div class="meta">${error.message}</div>`;
      });
    </script>
  </body>
</html>
"""
