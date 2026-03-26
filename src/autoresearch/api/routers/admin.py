from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_admin_config_service,
    get_claude_agent_service,
)
from autoresearch.core.services.admin_auth import AdminAccessClaims, AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.shared.models import (
    AdminAgentConfigCreateRequest,
    AdminAgentConfigRead,
    AdminAgentConfigUpdateRequest,
    AdminAgentLaunchRequest,
    AdminChannelConfigCreateRequest,
    AdminChannelConfigRead,
    AdminChannelConfigUpdateRequest,
    AdminConfigRevisionRead,
    AdminConfigRollbackRequest,
    AdminConfigStatusChangeRequest,
    AdminTokenIssueRequest,
    AdminTokenRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
)


router = APIRouter(prefix="/api/v1/admin", tags=["admin-config"])

_ADMIN_READ_ROLES = {"viewer", "editor", "admin", "owner"}
_ADMIN_WRITE_ROLES = {"editor", "admin", "owner"}
_ADMIN_HIGH_ROLES = {"admin", "owner"}


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "").strip()
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return ""


def _require_admin_roles(
    request: Request,
    *,
    required_roles: set[str],
    auth_service: AdminAuthService,
) -> AdminAccessClaims:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing admin bearer token")
    try:
        return auth_service.verify_token(token, required_roles=required_roles)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _require_admin_read(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_READ_ROLES, auth_service=auth_service)


def _require_admin_write(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_WRITE_ROLES, auth_service=auth_service)


def _require_admin_high_risk(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_HIGH_ROLES, auth_service=auth_service)


@router.get("/health")
def admin_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/view", response_class=HTMLResponse, include_in_schema=False)
def admin_view() -> HTMLResponse:
    return HTMLResponse(_ADMIN_HTML)


@router.post("/auth/token", response_model=AdminTokenRead)
def issue_admin_token(
    payload: AdminTokenIssueRequest,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
    bootstrap_key: str | None = Header(default=None, alias="x-admin-bootstrap-key"),
) -> AdminTokenRead:
    try:
        return auth_service.issue_token(
            subject=payload.subject,
            roles=list(payload.roles),
            bootstrap_key=bootstrap_key,
            ttl_seconds=payload.ttl_seconds,
        )
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/agents", response_model=AdminAgentConfigRead, status_code=status.HTTP_201_CREATED)
def create_agent_config(
    payload: AdminAgentConfigCreateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.create_agent(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/agents", response_model=list[AdminAgentConfigRead])
def list_agent_configs(
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminAgentConfigRead]:
    return service.list_agents()


@router.get("/agents/{agent_id}", response_model=AdminAgentConfigRead)
def get_agent_config(
    agent_id: str,
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    item = service.get_agent(agent_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    return item


@router.put("/agents/{agent_id}", response_model=AdminAgentConfigRead)
def update_agent_config(
    agent_id: str,
    payload: AdminAgentConfigUpdateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.update_agent(agent_id=agent_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/agents/{agent_id}/activate", response_model=AdminAgentConfigRead)
def activate_agent_config(
    agent_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.set_agent_enabled(
            agent_id=agent_id,
            enabled=True,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc


@router.post("/agents/{agent_id}/deactivate", response_model=AdminAgentConfigRead)
def deactivate_agent_config(
    agent_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.set_agent_enabled(
            agent_id=agent_id,
            enabled=False,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc


@router.post("/agents/{agent_id}/rollback", response_model=AdminAgentConfigRead)
def rollback_agent_config(
    agent_id: str,
    payload: AdminConfigRollbackRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.rollback_agent(agent_id=agent_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/agents/{agent_id}/history", response_model=list[AdminConfigRevisionRead])
def list_agent_history(
    agent_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    if service.get_agent(agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    return service.list_revisions(target_type="agent", target_id=agent_id, limit=limit)


@router.post(
    "/agents/{agent_id}/launch",
    response_model=ClaudeAgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def launch_agent_from_config(
    agent_id: str,
    payload: AdminAgentLaunchRequest,
    background_tasks: BackgroundTasks,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    config_service: AdminConfigService = Depends(get_admin_config_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    config = config_service.get_agent(agent_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    if config.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent config is inactive")

    prompt = payload.prompt_override if payload.prompt_override is not None else config.prompt_template
    metadata = {
        **config.metadata,
        **payload.metadata_updates,
        "agent_config_id": config.agent_id,
        "agent_config_version": config.version,
        "launch_mode": "admin_config",
    }
    request_payload = ClaudeAgentCreateRequest(
        task_name=config.task_name,
        prompt=prompt,
        session_id=payload.session_id,
        generation_depth=(
            payload.generation_depth_override
            if payload.generation_depth_override is not None
            else config.default_generation_depth
        ),
        timeout_seconds=(
            payload.timeout_seconds_override
            if payload.timeout_seconds_override is not None
            else config.default_timeout_seconds
        ),
        cli_args=list(config.cli_args),
        command_override=list(config.command_override) if config.command_override else None,
        append_prompt=config.append_prompt,
        env={**config.default_env, **payload.env_overrides},
        metadata=metadata,
    )
    try:
        run = agent_service.create(request_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    background_tasks.add_task(agent_service.execute, run.agent_run_id, request_payload)
    return run


@router.post("/channels", response_model=AdminChannelConfigRead, status_code=status.HTTP_201_CREATED)
def create_channel_config(
    payload: AdminChannelConfigCreateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.create_channel(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/channels", response_model=list[AdminChannelConfigRead])
def list_channel_configs(
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminChannelConfigRead]:
    return service.list_channels()


@router.get("/channels/{channel_id}", response_model=AdminChannelConfigRead)
def get_channel_config(
    channel_id: str,
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    item = service.get_channel(channel_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")
    return item


@router.put("/channels/{channel_id}", response_model=AdminChannelConfigRead)
def update_channel_config(
    channel_id: str,
    payload: AdminChannelConfigUpdateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.update_channel(channel_id=channel_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/channels/{channel_id}/activate", response_model=AdminChannelConfigRead)
def activate_channel_config(
    channel_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.set_channel_enabled(
            channel_id=channel_id,
            enabled=True,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc


@router.post("/channels/{channel_id}/deactivate", response_model=AdminChannelConfigRead)
def deactivate_channel_config(
    channel_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.set_channel_enabled(
            channel_id=channel_id,
            enabled=False,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc


@router.post("/channels/{channel_id}/rollback", response_model=AdminChannelConfigRead)
def rollback_channel_config(
    channel_id: str,
    payload: AdminConfigRollbackRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.rollback_channel(channel_id=channel_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/history", response_model=list[AdminConfigRevisionRead])
def list_channel_history(
    channel_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    if service.get_channel(channel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")
    return service.list_revisions(target_type="channel", target_id=channel_id, limit=limit)


@router.get("/revisions", response_model=list[AdminConfigRevisionRead])
def list_revisions(
    target_type: Literal["agent", "channel"] | None = None,
    target_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    return service.list_revisions(target_type=target_type, target_id=target_id, limit=limit)


_ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Autoresearch Admin</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #0f1f3d;
      --muted: #5f6b81;
      --line: #d9e1ee;
      --ok: #0d7f4f;
      --warn: #92400e;
      --danger: #b42318;
      --accent: #0b6cff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans SC", sans-serif;
    }
    main {
      max-width: 1260px;
      margin: 0 auto;
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }
    @media (min-width: 1100px) {
      .grid { grid-template-columns: 1fr 1fr; }
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }
    h1, h2 { margin: 0 0 10px; }
    h1 { font-size: 24px; }
    h2 { font-size: 18px; }
    .muted { color: var(--muted); font-size: 13px; margin: 0; }
    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    input, textarea, select, button {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 13px;
      background: #fff;
      color: var(--text);
    }
    textarea {
      width: 100%;
      min-height: 94px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    button {
      cursor: pointer;
      font-weight: 600;
    }
    .btn-primary {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .btn-danger {
      color: #fff;
      border-color: var(--danger);
      background: var(--danger);
    }
    .table-wrap {
      overflow: auto;
      max-height: 420px;
      border: 1px solid var(--line);
      border-radius: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 700px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 8px;
      font-size: 12px;
      vertical-align: top;
    }
    th {
      background: #f8faff;
      position: sticky;
      top: 0;
      z-index: 1;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .active { color: var(--ok); border-color: #a7f3d0; background: #ecfdf3; }
    .inactive { color: var(--warn); border-color: #fcd9bd; background: #fff7ed; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 6px; }
    pre {
      margin: 0;
      padding: 10px;
      background: #0e1a33;
      color: #dbe8ff;
      border-radius: 8px;
      max-height: 200px;
      overflow: auto;
      font-size: 12px;
    }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>Autoresearch 可编辑后台</h1>
    <div class="row">
      <button onclick="setAdminToken()">设置 Admin Token</button>
      <button class="btn-danger" onclick="clearAdminToken()">清除 Token</button>
    </div>
    <p id="summary" class="muted">加载中...</p>
  </section>

  <section class="grid">
    <section class="card">
      <h2>Agent 配置</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
        <button onclick="createAgent()">新建 Agent</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Task</th>
              <th>Version</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="agents-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Channel 配置</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
        <button onclick="createChannel()">新建 Channel</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Key</th>
              <th>Provider</th>
              <th>Secret</th>
              <th>Version</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="channels-body"></tbody>
        </table>
      </div>
    </section>
  </section>

  <section class="card">
    <h2>Revision Timeline</h2>
    <div class="row">
      <select id="rev-type">
        <option value="">全部</option>
        <option value="agent">agent</option>
        <option value="channel">channel</option>
      </select>
      <input id="rev-target" placeholder="target_id (可选)" />
      <button onclick="loadRevisions()">过滤</button>
    </div>
    <pre id="revisions-pre">[]</pre>
  </section>
</main>

<script>
const summary = document.getElementById("summary");
const agentsBody = document.getElementById("agents-body");
const channelsBody = document.getElementById("channels-body");
const revisionsPre = document.getElementById("revisions-pre");
const tokenFromQuery = new URLSearchParams(window.location.search).get("token") || "";
let adminToken = localStorage.getItem("autoresearch_admin_token") || tokenFromQuery;

function setAdminToken() {
  const input = prompt("请输入 Bearer Token（不含 Bearer 前缀）", adminToken || "");
  if (!input) return;
  adminToken = input.trim();
  localStorage.setItem("autoresearch_admin_token", adminToken);
  refreshAll();
}

function clearAdminToken() {
  adminToken = "";
  localStorage.removeItem("autoresearch_admin_token");
  summary.textContent = "已清除 token";
}

async function callApi(path, method = "GET", body = null) {
  if (!adminToken) {
    throw new Error("missing admin token; click 设置 Admin Token");
  }
  const headers = {"content-type": "application/json", "authorization": `Bearer ${adminToken}`};
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

function asJSON(value) {
  return JSON.stringify(value, null, 2);
}

function fmtDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN");
}

function agentRow(item) {
  const toggleOp = item.status === "active" ? "deactivate" : "activate";
  const toggleLabel = item.status === "active" ? "停用" : "启用";
  const encoded = encodeURIComponent(JSON.stringify(item));
  return `
    <tr>
      <td>${item.agent_id}</td>
      <td>${item.name}</td>
      <td>${item.task_name}</td>
      <td>${item.version}</td>
      <td><span class="pill ${item.status}">${item.status}</span></td>
      <td>${fmtDate(item.updated_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='editAgent("${encoded}")'>编辑</button>
          <button onclick='launchAgent("${item.agent_id}")'>启动</button>
          <button onclick='toggleAgent("${item.agent_id}", "${toggleOp}")'>${toggleLabel}</button>
          <button onclick='rollbackAgent("${item.agent_id}")'>回滚</button>
        </div>
      </td>
    </tr>`;
}

function channelRow(item) {
  const toggleOp = item.status === "active" ? "deactivate" : "activate";
  const toggleLabel = item.status === "active" ? "停用" : "启用";
  const encoded = encodeURIComponent(JSON.stringify(item));
  return `
    <tr>
      <td>${item.channel_id}</td>
      <td>${item.key}</td>
      <td>${item.provider}</td>
      <td>${item.has_secret ? "yes" : "no"}</td>
      <td>${item.version}</td>
      <td><span class="pill ${item.status}">${item.status}</span></td>
      <td>${fmtDate(item.updated_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='editChannel("${encoded}")'>编辑</button>
          <button onclick='toggleChannel("${item.channel_id}", "${toggleOp}")'>${toggleLabel}</button>
          <button onclick='rollbackChannel("${item.channel_id}")'>回滚</button>
        </div>
      </td>
    </tr>`;
}

async function refreshAll() {
  try {
    const [agents, channels] = await Promise.all([
      callApi("/api/v1/admin/agents"),
      callApi("/api/v1/admin/channels"),
    ]);
    agentsBody.innerHTML = agents.map(agentRow).join("") || "<tr><td colspan='7'>暂无</td></tr>";
    channelsBody.innerHTML = channels.map(channelRow).join("") || "<tr><td colspan='8'>暂无</td></tr>";
    summary.textContent = `Agents: ${agents.length} | Channels: ${channels.length} | API: /api/v1/admin`;
    await loadRevisions();
  } catch (err) {
    summary.textContent = `加载失败: ${err.message}`;
  }
}

async function loadRevisions() {
  const targetType = document.getElementById("rev-type").value;
  const targetId = document.getElementById("rev-target").value.trim();
  const params = new URLSearchParams();
  params.set("limit", "80");
  if (targetType) params.set("target_type", targetType);
  if (targetId) params.set("target_id", targetId);
  try {
    const list = await callApi(`/api/v1/admin/revisions?${params.toString()}`);
    revisionsPre.textContent = asJSON(list);
  } catch (err) {
    revisionsPre.textContent = String(err);
  }
}

async function createAgent() {
  const raw = prompt("输入 Agent JSON（create payload）", asJSON({
    name: "assistant-main",
    description: "default admin agent",
    task_name: "general-task",
    prompt_template: "You are my primary autonomous agent.",
    default_timeout_seconds: 900,
    default_generation_depth: 1,
    default_env: {},
    cli_args: [],
    command_override: null,
    append_prompt: true,
    channel_bindings: ["telegram-main"],
    metadata: {},
    enabled: true,
    actor: "admin-ui"
  }));
  if (!raw) return;
  await callApi("/api/v1/admin/agents", "POST", JSON.parse(raw));
  await refreshAll();
}

async function editAgent(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  const raw = prompt("输入 Agent 更新 JSON（update payload）", asJSON({
    name: item.name,
    description: item.description,
    task_name: item.task_name,
    prompt_template: item.prompt_template,
    default_timeout_seconds: item.default_timeout_seconds,
    default_generation_depth: item.default_generation_depth,
    default_env: item.default_env,
    cli_args: item.cli_args,
    command_override: item.command_override,
    append_prompt: item.append_prompt,
    channel_bindings: item.channel_bindings,
    metadata_updates: {},
    actor: "admin-ui",
    reason: "manual edit"
  }));
  if (!raw) return;
  await callApi(`/api/v1/admin/agents/${item.agent_id}`, "PUT", JSON.parse(raw));
  await refreshAll();
}

async function toggleAgent(agentId, op) {
  await callApi(`/api/v1/admin/agents/${agentId}/${op}`, "POST", {actor: "admin-ui", reason: "toggle from ui"});
  await refreshAll();
}

async function rollbackAgent(agentId) {
  const version = prompt("回滚到哪个 version？", "1");
  if (!version) return;
  await callApi(`/api/v1/admin/agents/${agentId}/rollback`, "POST", {
    version: Number(version),
    actor: "admin-ui",
    reason: "manual rollback"
  });
  await refreshAll();
}

async function launchAgent(agentId) {
  const raw = prompt("输入 Launch JSON", asJSON({
    session_id: null,
    prompt_override: null,
    timeout_seconds_override: null,
    generation_depth_override: null,
    env_overrides: {},
    metadata_updates: {trigger: "admin-ui"}
  }));
  if (!raw) return;
  const run = await callApi(`/api/v1/admin/agents/${agentId}/launch`, "POST", JSON.parse(raw));
  alert(`已启动 agent_run_id: ${run.agent_run_id}`);
}

async function createChannel() {
  const raw = prompt("输入 Channel JSON（create payload）", asJSON({
    key: "telegram-main",
    display_name: "Telegram Main",
    provider: "telegram",
    endpoint_url: null,
    secret_ref: null,
    secret_value: null,
    allowed_chat_ids: [],
    allowed_user_ids: [],
    routing_policy: {},
    metadata: {},
    enabled: true,
    actor: "admin-ui"
  }));
  if (!raw) return;
  await callApi("/api/v1/admin/channels", "POST", JSON.parse(raw));
  await refreshAll();
}

async function editChannel(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  const raw = prompt("输入 Channel 更新 JSON（update payload）", asJSON({
    display_name: item.display_name,
    provider: item.provider,
    endpoint_url: item.endpoint_url,
    secret_ref: item.secret_ref,
    secret_value: null,
    clear_secret: false,
    allowed_chat_ids: item.allowed_chat_ids,
    allowed_user_ids: item.allowed_user_ids,
    routing_policy: item.routing_policy,
    metadata_updates: {},
    actor: "admin-ui",
    reason: "manual edit"
  }));
  if (!raw) return;
  await callApi(`/api/v1/admin/channels/${item.channel_id}`, "PUT", JSON.parse(raw));
  await refreshAll();
}

async function toggleChannel(channelId, op) {
  await callApi(`/api/v1/admin/channels/${channelId}/${op}`, "POST", {actor: "admin-ui", reason: "toggle from ui"});
  await refreshAll();
}

async function rollbackChannel(channelId) {
  const version = prompt("回滚到哪个 version？", "1");
  if (!version) return;
  await callApi(`/api/v1/admin/channels/${channelId}/rollback`, "POST", {
    version: Number(version),
    actor: "admin-ui",
    reason: "manual rollback"
  });
  await refreshAll();
}

refreshAll();
</script>
</body>
</html>
"""
