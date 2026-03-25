from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_panel_audit_service,
    get_telegram_notifier_service,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    ClaudeAgentCancelRequest,
    ClaudeAgentRetryRequest,
    ClaudeAgentRunRead,
    OpenClawSessionRead,
    PanelAuditLogRead,
    PanelStateRead,
    utc_now,
)


router = APIRouter(prefix="/api/v1/panel", tags=["panel"])


@dataclass(frozen=True)
class PanelAccessContext:
    telegram_uid: str
    auth_method: str = "jwt_magic_link"
    token_id: str | None = None


def _extract_panel_token(request: Request) -> str:
    bearer = request.headers.get("authorization", "").strip()
    if bearer.lower().startswith("bearer "):
        return bearer.split(" ", 1)[1].strip()
    return request.headers.get("x-autoresearch-panel-token", "").strip()


def _extract_telegram_init_data(request: Request) -> str:
    header_value = request.headers.get("x-telegram-init-data", "").strip()
    if header_value:
        return header_value
    query_value = request.query_params.get("initData")
    if query_value:
        return query_value.strip()
    telegram_query_value = request.query_params.get("tgWebAppData")
    if telegram_query_value:
        return telegram_query_value.strip()
    return ""


def _require_panel_access(
    request: Request,
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
) -> PanelAccessContext:
    token = _extract_panel_token(request)
    if token:
        try:
            claims = panel_access_service.verify_token(token)
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
        return PanelAccessContext(
            telegram_uid=claims.telegram_uid,
            auth_method="jwt_magic_link",
            token_id=claims.token_id,
        )

    init_data = _extract_telegram_init_data(request)
    if init_data:
        try:
            claims = panel_access_service.verify_telegram_init_data(init_data)
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
        return PanelAccessContext(
            telegram_uid=claims.telegram_uid,
            auth_method="telegram_init_data",
            token_id=claims.query_id,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing panel credential",
    )


@router.get("/view", response_class=HTMLResponse, include_in_schema=False)
def panel_view() -> HTMLResponse:
    return HTMLResponse(_PANEL_HTML)


@router.get("/health")
def panel_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/state", response_model=PanelStateRead)
def get_panel_state(
    limit_runs: int = Query(default=50, ge=1, le=200),
    limit_audit: int = Query(default=50, ge=1, le=200),
    access: PanelAccessContext = Depends(_require_panel_access),
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    audit_service: PanelAuditService = Depends(get_panel_audit_service),
) -> PanelStateRead:
    sessions = _sessions_for_uid(openclaw_service=openclaw_service, telegram_uid=access.telegram_uid)
    session_ids = {session.session_id for session in sessions}
    runs = [run for run in agent_service.list() if run.session_id in session_ids]
    runs.sort(key=lambda item: item.updated_at, reverse=True)
    audit_logs = audit_service.list_by_uid(access.telegram_uid, limit=limit_audit)
    return PanelStateRead(
        telegram_uid=access.telegram_uid,
        sessions=sessions,
        agent_runs=runs[:limit_runs],
        audit_logs=audit_logs,
        issued_at=utc_now(),
    )


@router.get("/audit/logs", response_model=list[PanelAuditLogRead])
def list_panel_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    access: PanelAccessContext = Depends(_require_panel_access),
    audit_service: PanelAuditService = Depends(get_panel_audit_service),
) -> list[PanelAuditLogRead]:
    return audit_service.list_by_uid(access.telegram_uid, limit=limit)


@router.get("/agents/{agent_run_id}", response_model=ClaudeAgentRunRead)
def get_panel_agent(
    agent_run_id: str,
    access: PanelAccessContext = Depends(_require_panel_access),
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    return _authorized_agent_run(
        agent_run_id=agent_run_id,
        telegram_uid=access.telegram_uid,
        openclaw_service=openclaw_service,
        agent_service=agent_service,
    )


@router.post("/agents/{agent_run_id}/cancel", response_model=ClaudeAgentRunRead)
def cancel_panel_agent(
    agent_run_id: str,
    payload: ClaudeAgentCancelRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    access: PanelAccessContext = Depends(_require_panel_access),
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    audit_service: PanelAuditService = Depends(get_panel_audit_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> ClaudeAgentRunRead:
    _authorized_agent_run(
        agent_run_id=agent_run_id,
        telegram_uid=access.telegram_uid,
        openclaw_service=openclaw_service,
        agent_service=agent_service,
    )
    run = agent_service.cancel(agent_run_id=agent_run_id, request=payload)
    entry = audit_service.log_action(
        telegram_uid=access.telegram_uid,
        action="cancel",
        target_id=agent_run_id,
        status="accepted",
        reason=payload.reason,
        request_ip=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "session_id": run.session_id,
            "auth_method": access.auth_method,
            "token_id": access.token_id,
        },
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.notify_manual_action,
            chat_id=access.telegram_uid,
            entry=entry,
            run_status=run.status.value,
        )
    return run


@router.post(
    "/agents/{agent_run_id}/retry",
    response_model=ClaudeAgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_panel_agent(
    agent_run_id: str,
    payload: ClaudeAgentRetryRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    access: PanelAccessContext = Depends(_require_panel_access),
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    audit_service: PanelAuditService = Depends(get_panel_audit_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> ClaudeAgentRunRead:
    _authorized_agent_run(
        agent_run_id=agent_run_id,
        telegram_uid=access.telegram_uid,
        openclaw_service=openclaw_service,
        agent_service=agent_service,
    )
    replay_run, replay_request = agent_service.retry(agent_run_id=agent_run_id, request=payload)
    background_tasks.add_task(agent_service.execute, replay_run.agent_run_id, replay_request)

    entry = audit_service.log_action(
        telegram_uid=access.telegram_uid,
        action="retry",
        target_id=agent_run_id,
        status="accepted",
        reason=payload.reason,
        request_ip=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "session_id": replay_run.session_id,
            "replay_agent_run_id": replay_run.agent_run_id,
            "auth_method": access.auth_method,
            "token_id": access.token_id,
        },
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.notify_manual_action,
            chat_id=access.telegram_uid,
            entry=entry,
            run_status=replay_run.status.value,
        )
    return replay_run


def _sessions_for_uid(
    *,
    openclaw_service: OpenClawCompatService,
    telegram_uid: str,
) -> list[OpenClawSessionRead]:
    sessions = [
        session
        for session in openclaw_service.list_sessions()
        if session.channel == "telegram" and session.external_id == telegram_uid
    ]
    sessions.sort(key=lambda item: item.updated_at, reverse=True)
    return sessions


def _authorized_agent_run(
    *,
    agent_run_id: str,
    telegram_uid: str,
    openclaw_service: OpenClawCompatService,
    agent_service: ClaudeAgentService,
) -> ClaudeAgentRunRead:
    run = agent_service.get(agent_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found")
    if run.session_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    session = openclaw_service.get_session(run.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found")
    if session.channel != "telegram" or session.external_id != telegram_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return run


def _request_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


_PANEL_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Autoresearch Panel</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    :root { --bg:#f6f8fb; --card:#fff; --text:#13213a; --muted:#5e6b84; --accent:#0f766e; --danger:#b42318; --line:#d7deeb; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans SC", sans-serif; background:var(--bg); color:var(--text); }
    main { max-width:1100px; margin:0 auto; padding:24px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:16px; }
    h1 { margin:0 0 12px; font-size:24px; }
    h2 { margin:0 0 8px; font-size:18px; }
    .muted { color:var(--muted); font-size:13px; }
    table { width:100%; border-collapse:collapse; }
    th, td { text-align:left; border-bottom:1px solid var(--line); padding:8px 6px; vertical-align:top; font-size:13px; }
    button { border:0; border-radius:8px; padding:6px 10px; cursor:pointer; margin-right:8px; font-size:12px; }
    .btn-cancel { background:#fee4e2; color:var(--danger); }
    .btn-retry { background:#dff8eb; color:var(--accent); }
    pre { margin:0; max-height:220px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>Autoresearch 控制面板</h1>
    <p class="muted" id="summary">加载中...</p>
  </section>
  <section class="card">
    <h2>任务列表</h2>
    <div id="runs"></div>
  </section>
  <section class="card">
    <h2>审计日志</h2>
    <pre id="audit"></pre>
  </section>
</main>
<script>
const token = new URLSearchParams(window.location.search).get("token") || "";
const tgWebApp = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
const telegramInitData = tgWebApp && tgWebApp.initData ? tgWebApp.initData : "";
const summary = document.getElementById("summary");
const runsEl = document.getElementById("runs");
const auditEl = document.getElementById("audit");

if (tgWebApp) {
  tgWebApp.ready();
  tgWebApp.expand();
}

async function callApi(path, method="GET", body=null) {
  const headers = {"content-type": "application/json"};
  if (token) {
    headers["x-autoresearch-panel-token"] = token;
  } else if (telegramInitData) {
    headers["x-telegram-init-data"] = telegramInitData;
  }
  const res = await fetch(path, {method, headers, body: body ? JSON.stringify(body) : undefined});
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json();
}

function runRow(run) {
  const safeReason = "manual via panel";
  return `
    <tr>
      <td>${run.agent_run_id}</td>
      <td>${run.status}</td>
      <td>${run.task_name}</td>
      <td>${run.updated_at}</td>
      <td>
        <button class="btn-cancel" data-id="${run.agent_run_id}" data-op="cancel">Cancel</button>
        <button class="btn-retry" data-id="${run.agent_run_id}" data-op="retry">Retry</button>
      </td>
      <td class="muted">${safeReason}</td>
    </tr>
  `;
}

async function refresh() {
  if (!token && !telegramInitData) {
    summary.textContent = "缺少访问凭证，请使用 Telegram /status 魔法链接或 Mini App 打开。";
    return;
  }
  try {
    const state = await callApi("/api/v1/panel/state?limit_runs=60&limit_audit=40");
    const mode = token ? "JWT" : "Telegram Mini App";
    summary.textContent = `UID: ${state.telegram_uid} | mode: ${mode} | sessions: ${state.sessions.length} | runs: ${state.agent_runs.length}`;
    const rows = state.agent_runs.map(runRow).join("");
    runsEl.innerHTML = `<table><thead><tr><th>Agent</th><th>Status</th><th>Task</th><th>Updated</th><th>Action</th><th>Hint</th></tr></thead><tbody>${rows}</tbody></table>`;
    auditEl.textContent = JSON.stringify(state.audit_logs, null, 2);
  } catch (err) {
    summary.textContent = `加载失败: ${err.message}`;
  }
}

runsEl.addEventListener("click", async (event) => {
  const target = event.target;
  if (!target || !target.dataset || !target.dataset.id) return;
  const agentId = target.dataset.id;
  const op = target.dataset.op;
  const reason = prompt(`输入 ${op} 原因`, "manual via panel");
  if (!reason) return;
  try {
    if (op === "cancel") {
      await callApi(`/api/v1/panel/agents/${agentId}/cancel`, "POST", {reason});
    } else if (op === "retry") {
      await callApi(`/api/v1/panel/agents/${agentId}/retry`, "POST", {reason, metadata_updates: {}});
    }
    await refresh();
  } catch (err) {
    alert(`操作失败: ${err.message}`);
  }
});

refresh();
setInterval(refresh, 8000);
</script>
</body>
</html>
"""
