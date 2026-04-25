from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


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
    .subcard {
      background: #fbfdff;
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 10px;
      margin-bottom: 10px;
    }
    h3 {
      margin: 0 0 8px;
      font-size: 15px;
    }
    .inline-check {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      padding: 4px 0;
    }
    .inline-check input {
      width: 14px;
      height: 14px;
      margin: 0;
    }
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
        <button onclick="createAgent()">新建 Agent（表单）</button>
        <button onclick="createAgentAdvancedJson()">高级 JSON</button>
      </div>
      <div class="subcard" id="agent-form-card">
        <h3 id="agent-form-title">Agent 表单（新建）</h3>
        <p class="muted">默认走表单，复杂参数再点"高级 JSON"。</p>
        <div class="row">
          <input id="agent-form-name" placeholder="name" value="assistant-main" />
          <input id="agent-form-task" placeholder="task_name" value="general-task" />
          <input id="agent-form-timeout" type="number" min="1" max="7200" value="900" />
          <input id="agent-form-depth" type="number" min="1" max="10" value="1" />
        </div>
        <textarea id="agent-form-description" placeholder="description">default admin agent</textarea>
        <textarea id="agent-form-prompt" placeholder="prompt_template">You are my primary autonomous agent.</textarea>
        <div class="row">
          <input id="agent-form-channels" placeholder="channel_bindings, comma separated" value="telegram-main" />
          <input id="agent-form-actor" placeholder="actor" value="admin-ui" />
          <label class="inline-check"><input id="agent-form-append" type="checkbox" checked />append_prompt</label>
          <label class="inline-check"><input id="agent-form-enabled" type="checkbox" checked />enabled</label>
        </div>
        <div class="row">
          <button class="btn-primary" onclick="submitAgentForm()">保存 Agent</button>
          <button onclick="resetAgentForm()">清空</button>
        </div>
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
        <button onclick="createChannel()">新建 Channel（表单）</button>
        <button onclick="createChannelAdvancedJson()">高级 JSON</button>
      </div>
      <div class="subcard">
        <h3>Telegram 快速配置（ClawX 风格）</h3>
        <p class="muted">只填 key、bot token、allowed ids，一键保存。</p>
        <div class="row">
          <input id="tg-quick-key" placeholder="key" value="telegram-main" />
          <input id="tg-quick-token" type="password" placeholder="bot token (@BotFather)" value="" />
          <input id="tg-quick-ids" placeholder="allowed ids, comma separated" value="" />
          <input id="tg-quick-actor" placeholder="actor" value="admin-ui" />
        </div>
        <div class="row">
          <button class="btn-primary" onclick="quickCreateTelegramChannel()">一键保存 Telegram Channel</button>
        </div>
      </div>
      <div class="subcard" id="channel-form-card">
        <h3 id="channel-form-title">Channel 表单（新建）</h3>
        <p class="muted">默认走表单，secret 可选。编辑时可覆盖字段并自动保存版本。</p>
        <div class="row">
          <input id="channel-form-key" placeholder="key" value="telegram-main" />
          <input id="channel-form-display" placeholder="display_name" value="Telegram Main" />
          <select id="channel-form-provider">
            <option value="telegram">telegram</option>
            <option value="webhook">webhook</option>
            <option value="http">http</option>
            <option value="custom">custom</option>
          </select>
          <input id="channel-form-endpoint" placeholder="endpoint_url (optional)" value="" />
        </div>
        <div class="row">
          <input id="channel-form-secret-ref" placeholder="secret_ref (optional)" value="" />
          <input id="channel-form-secret-value" type="password" placeholder="secret_value (optional)" value="" />
        </div>
        <div class="row">
          <input id="channel-form-allowed-chat-ids" placeholder="allowed_chat_ids, comma separated" value="" />
          <input id="channel-form-allowed-user-ids" placeholder="allowed_user_ids, comma separated" value="" />
          <input id="channel-form-actor" placeholder="actor" value="admin-ui" />
          <label class="inline-check"><input id="channel-form-enabled" type="checkbox" checked />enabled</label>
        </div>
        <div class="row">
          <button class="btn-primary" onclick="submitChannelForm()">保存 Channel</button>
          <button onclick="resetChannelForm()">清空</button>
        </div>
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

    <section class="card">
      <h2>Capability Inventory</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Domain</th>
              <th>Status</th>
              <th>Capabilities</th>
              <th>Skills</th>
              <th>Tools</th>
              <th>Read Ops</th>
            </tr>
          </thead>
          <tbody id="capabilities-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Approval Queue</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Title</th>
              <th>UID</th>
              <th>Source</th>
              <th>Expires</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="approvals-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Managed Skill Queue</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Install</th>
              <th>Status</th>
              <th>Skill</th>
              <th>Version</th>
              <th>Requested By</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="skills-body"></tbody>
        </table>
      </div>
      <div class="subcard">
        <h3>Skill Detail</h3>
        <pre id="skill-detail-pre">{}</pre>
      </div>
    </section>
  </section>

  <section class="card">
    <h2>Agent Audit Trail</h2>
    <div class="row">
      <button class="btn-primary" onclick="loadAuditTrail()">刷新</button>
      <select id="audit-status-filter" onchange="loadAuditTrail()">
        <option value="all">全部状态</option>
        <option value="success">Success</option>
        <option value="failed">Failed</option>
        <option value="pending">Pending</option>
        <option value="running">Running</option>
        <option value="review">Review</option>
      </select>
      <select id="audit-role-filter" onchange="loadAuditTrail()">
        <option value="all">全部角色</option>
        <option value="manager">Manager</option>
        <option value="planner">Planner</option>
        <option value="worker">Worker</option>
      </select>
      <span id="audit-trail-summary">最近 20 条执行足迹</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Role</th>
            <th>Run</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Files</th>
            <th>Scope</th>
            <th>Changed</th>
            <th>Inspect</th>
          </tr>
        </thead>
        <tbody id="audit-trail-body"></tbody>
      </table>
    </div>
    <div class="subcard">
      <h3>Audit Detail</h3>
      <p id="audit-detail-meta" class="muted">点击单条记录查看输入、patch diff 和失败原因。</p>
      <div class="row">
        <button onclick="clearAuditDetail()">清空详情</button>
      </div>
      <div class="subcard">
        <h3>Input Context</h3>
        <pre id="audit-input-pre">暂无</pre>
      </div>
      <div class="subcard">
        <h3>Patch Diff</h3>
        <pre id="audit-patch-pre">暂无</pre>
      </div>
      <div class="subcard">
        <h3>Failure / Traceback</h3>
        <pre id="audit-error-pre">暂无</pre>
      </div>
    </div>
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
const capabilitiesBody = document.getElementById("capabilities-body");
const approvalsBody = document.getElementById("approvals-body");
const skillsBody = document.getElementById("skills-body");
const skillDetailPre = document.getElementById("skill-detail-pre");
const auditTrailSummary = document.getElementById("audit-trail-summary");
const auditTrailBody = document.getElementById("audit-trail-body");
const auditStatusFilter = document.getElementById("audit-status-filter");
const auditRoleFilter = document.getElementById("audit-role-filter");
const auditDetailMeta = document.getElementById("audit-detail-meta");
const auditInputPre = document.getElementById("audit-input-pre");
const auditPatchPre = document.getElementById("audit-patch-pre");
const auditErrorPre = document.getElementById("audit-error-pre");
const revisionsPre = document.getElementById("revisions-pre");
const tokenFromQuery = new URLSearchParams(window.location.search).get("token") || "";
let adminToken = localStorage.getItem("autoresearch_admin_token") || tokenFromQuery;
let agentFormMode = "create";
let editingAgentId = null;
let editingAgentStatus = "active";
let channelFormMode = "create";
let editingChannelId = null;
let editingChannelStatus = "active";
let selectedAuditEntryId = "";

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

function fmtDuration(value) {
  if (value === null || value === undefined) return "-";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)} s`;
}

function compactList(values, limit = 2) {
  const items = (values || []).filter(Boolean);
  if (!items.length) return "-";
  const visible = items.slice(0, limit).join(", ");
  const extra = items.length - limit;
  return extra > 0 ? `${visible} +${extra}` : visible;
}

function csvToList(raw) {
  if (!raw) return [];
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toInt(raw, fallback, minValue, maxValue) {
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.min(maxValue, Math.max(minValue, Math.round(value)));
}

function resetAgentForm() {
  agentFormMode = "create";
  editingAgentId = null;
  editingAgentStatus = "active";
  document.getElementById("agent-form-title").textContent = "Agent 表单（新建）";
  document.getElementById("agent-form-name").value = "assistant-main";
  document.getElementById("agent-form-task").value = "general-task";
  document.getElementById("agent-form-timeout").value = "900";
  document.getElementById("agent-form-depth").value = "1";
  document.getElementById("agent-form-description").value = "default admin agent";
  document.getElementById("agent-form-prompt").value = "You are my primary autonomous agent.";
  document.getElementById("agent-form-channels").value = "telegram-main";
  document.getElementById("agent-form-actor").value = "admin-ui";
  document.getElementById("agent-form-append").checked = true;
  document.getElementById("agent-form-enabled").checked = true;
}

async function submitAgentForm() {
  const name = document.getElementById("agent-form-name").value.trim();
  const taskName = document.getElementById("agent-form-task").value.trim();
  const promptTemplate = document.getElementById("agent-form-prompt").value;
  if (!name || !taskName || !promptTemplate.trim()) {
    alert("name / task_name / prompt_template 为必填");
    return;
  }

  const actor = document.getElementById("agent-form-actor").value.trim() || "admin-ui";
  const channels = csvToList(document.getElementById("agent-form-channels").value);
  const timeout = toInt(document.getElementById("agent-form-timeout").value, 900, 1, 7200);
  const depth = toInt(document.getElementById("agent-form-depth").value, 1, 1, 10);
  const appendPrompt = document.getElementById("agent-form-append").checked;
  const enabled = document.getElementById("agent-form-enabled").checked;
  const description = document.getElementById("agent-form-description").value.trim();

  if (agentFormMode === "edit" && editingAgentId) {
    await callApi(`/api/v1/admin/agents/${editingAgentId}`, "PUT", {
      name,
      description,
      task_name: taskName,
      prompt_template: promptTemplate,
      default_timeout_seconds: timeout,
      default_generation_depth: depth,
      append_prompt: appendPrompt,
      channel_bindings: channels,
      metadata_updates: {},
      actor,
      reason: "manual edit from form",
    });
    const currentlyEnabled = editingAgentStatus === "active";
    if (enabled !== currentlyEnabled) {
      const op = enabled ? "activate" : "deactivate";
      await callApi(`/api/v1/admin/agents/${editingAgentId}/${op}`, "POST", {
        actor,
        reason: "toggle from form",
      });
    }
  } else {
    await callApi("/api/v1/admin/agents", "POST", {
      name,
      description,
      task_name: taskName,
      prompt_template: promptTemplate,
      default_timeout_seconds: timeout,
      default_generation_depth: depth,
      default_env: {},
      cli_args: [],
      command_override: null,
      append_prompt: appendPrompt,
      channel_bindings: channels,
      metadata: {},
      enabled,
      actor,
    });
  }

  await refreshAll();
  resetAgentForm();
}

function createAgent() {
  resetAgentForm();
  document.getElementById("agent-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

async function createAgentAdvancedJson() {
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

function capabilityRow(item) {
  const provider = item.provider || {};
  const capabilityList = (provider.capabilities || []).join(", ") || "-";
  const skillList = (item.skills || []).map((skill) => skill.skill_key || skill.name).join(", ") || "-";
  const toolList = (item.tools || []).map((tool) => tool.name).join(", ") || "-";
  const readOps = [
    item.supports_calendar_query ? "calendar" : "",
    item.supports_github_search ? "github" : "",
  ].filter(Boolean).join(", ") || "-";
  return `
    <tr>
      <td>${provider.display_name || provider.provider_id || "-"}</td>
      <td>${provider.domain || "-"}</td>
      <td><span class="pill ${provider.status === "available" ? "active" : "inactive"}">${provider.status || "-"}</span></td>
      <td>${capabilityList}</td>
      <td>${skillList}</td>
      <td>${toolList}</td>
      <td>${readOps}</td>
    </tr>`;
}

function approvalRow(item) {
  return `
    <tr>
      <td>${item.approval_id}</td>
      <td>${item.status}</td>
      <td>${item.risk}</td>
      <td>${item.title}</td>
      <td>${item.telegram_uid || "-"}</td>
      <td>${item.source || "-"}</td>
      <td>${fmtDate(item.expires_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='decideApproval("${item.approval_id}", "approve")'>批准</button>
          <button class="btn-danger" onclick='decideApproval("${item.approval_id}", "reject")'>拒绝</button>
        </div>
      </td>
    </tr>`;
}

function flattenManagedSkillGroups(snapshot) {
  return (snapshot.groups || []).flatMap((group) => (group.installs || []).map((item) => ({
    ...item,
    status: item.status || group.status || "-"
  })));
}

function skillRow(item) {
  const ops = [
    `<button onclick='showSkillDetail("${item.install_id}")'>详情</button>`,
    item.status === "quarantined" ? `<button onclick='validateSkill("${item.install_id}")'>验证</button>` : "",
    item.status === "cold_validated" ? `<button onclick='requestSkillPromotion("${item.install_id}")'>提权</button>` : "",
  ].filter(Boolean).join("");
  return `
    <tr>
      <td>${item.install_id}</td>
      <td><span class="pill ${item.status === "promoted" ? "active" : "inactive"}">${item.status}</span></td>
      <td>${item.skill_id}</td>
      <td>${item.version}</td>
      <td>${item.requested_by || "-"}</td>
      <td>${fmtDate(item.updated_at)}</td>
      <td><div class="toolbar">${ops || "-"}</div></td>
    </tr>`;
}

function clearAuditDetail() {
  selectedAuditEntryId = "";
  auditDetailMeta.textContent = "点击单条记录查看输入、patch diff 和失败原因。";
  auditInputPre.textContent = "暂无";
  auditPatchPre.textContent = "暂无";
  auditErrorPre.textContent = "暂无";
}

function auditTrailRow(item) {
  const finalStatus = item.final_status || item.status || "-";
  const pillClass = ["failed", "blocked", "interrupted", "human_review", "stalled_no_progress"].includes(finalStatus) ? "inactive" : "active";
  return `
    <tr>
      <td>${fmtDate(item.recorded_at)}</td>
      <td>${item.agent_role} / ${item.source}</td>
      <td title="${item.title || item.run_id}">${item.run_id}</td>
      <td><span class="pill ${pillClass}">${finalStatus}</span></td>
      <td>${fmtDuration(item.duration_ms)}</td>
      <td>${item.files_changed || 0}</td>
      <td title="${(item.scope_paths || []).join("\\n")}">${compactList(item.scope_paths, 2)}</td>
      <td title="${(item.changed_paths || []).join("\\n")}">${compactList(item.changed_paths, 2)}</td>
      <td><button onclick='loadAuditDetail("${item.entry_id}")'>查看</button></td>
    </tr>`;
}

async function loadAuditDetail(entryId) {
  selectedAuditEntryId = entryId;
  auditDetailMeta.textContent = "加载详情中...";
  try {
    const detail = await callApi(`/api/v1/admin/audit-trail/${encodeURIComponent(entryId)}`);
    const entry = detail.entry || {};
    const detailLines = [
      `Role: ${entry.agent_role || "-"}`,
      `Source: ${entry.source || "-"}`,
      `Run: ${entry.run_id || "-"}`,
      `Title: ${entry.title || "-"}`,
      `Status: ${entry.final_status || entry.status || "-"}`,
      `Raw: ${entry.status || "-"}`,
      `Recorded: ${fmtDate(entry.recorded_at)}`,
      `First progress: ${fmtDuration(entry.first_progress_ms)}`,
      `First write: ${fmtDuration(entry.first_scoped_write_ms)}`,
      `First state: ${fmtDuration(entry.first_state_heartbeat_ms)}`,
      `Patch: ${entry.patch_uri || "-"}`,
      `Workspace: ${entry.isolated_workspace || "-"}`,
      detail.patch_truncated ? "Patch preview: truncated" : "Patch preview: full",
    ];
    auditDetailMeta.textContent = detailLines.join(" | ");
    auditInputPre.textContent = asJSON({
      prompt: detail.input_prompt || null,
      job_spec: detail.job_spec || {},
      worker_spec: detail.worker_spec || {},
      controlled_request: detail.controlled_request || {},
      raw_record: detail.raw_record || {},
    });
    auditPatchPre.textContent = detail.patch_text || (entry.patch_uri ? `Patch file: ${entry.patch_uri}` : "暂无 patch");
    auditErrorPre.textContent = detail.error_reason || detail.traceback
      ? [detail.error_reason || "no error reason", detail.traceback || ""].filter(Boolean).join("\\n\\n")
      : "无失败细节";
  } catch (err) {
    auditDetailMeta.textContent = `加载详情失败: ${err.message}`;
    auditInputPre.textContent = "加载失败";
    auditPatchPre.textContent = "加载失败";
    auditErrorPre.textContent = String(err);
  }
}

async function loadAuditTrail() {
  try {
    const params = new URLSearchParams();
    params.set("limit", "20");
    params.set("status_filter", auditStatusFilter.value || "all");
    params.set("agent_role", auditRoleFilter.value || "all");
    const snapshot = await callApi(`/api/v1/admin/audit-trail?${params.toString()}`);
    const items = snapshot.items || [];
    const stats = snapshot.stats || {};
    auditTrailBody.innerHTML = items.map(auditTrailRow).join("")
      || "<tr><td colspan='9'>暂无</td></tr>";
    auditTrailSummary.textContent =
      `Recent: ${items.length} | Success: ${stats.succeeded || 0} | Failed: ${stats.failed || 0} | Running: ${stats.running || 0} | Queued: ${stats.queued || 0} | Filter: ${(auditStatusFilter.value || "all")}/${(auditRoleFilter.value || "all")}`;
    if (selectedAuditEntryId && items.some((item) => item.entry_id === selectedAuditEntryId)) {
      await loadAuditDetail(selectedAuditEntryId);
    } else if (!selectedAuditEntryId) {
      clearAuditDetail();
    } else {
      clearAuditDetail();
      auditDetailMeta.textContent = "当前筛选结果不包含已选记录。";
    }
  } catch (err) {
    auditTrailSummary.textContent = `加载失败: ${err.message}`;
    auditTrailBody.innerHTML = "<tr><td colspan='9'>加载失败</td></tr>";
  }
}

async function refreshAll() {
  try {
    const [agents, channels, capabilitySnapshot, approvals, skillSnapshot] = await Promise.all([
      callApi("/api/v1/admin/agents"),
      callApi("/api/v1/admin/channels"),
      callApi("/api/v1/admin/capabilities"),
      callApi("/api/v1/admin/approvals?status=pending&limit=80"),
      callApi("/api/v1/admin/skills/status"),
    ]);
    const skillItems = flattenManagedSkillGroups(skillSnapshot);
    agentsBody.innerHTML = agents.map(agentRow).join("") || "<tr><td colspan='7'>暂无</td></tr>";
    channelsBody.innerHTML = channels.map(channelRow).join("") || "<tr><td colspan='8'>暂无</td></tr>";
    capabilitiesBody.innerHTML = (capabilitySnapshot.providers || []).map(capabilityRow).join("")
      || "<tr><td colspan='7'>暂无</td></tr>";
    approvalsBody.innerHTML = approvals.map(approvalRow).join("") || "<tr><td colspan='8'>暂无</td></tr>";
    skillsBody.innerHTML = skillItems.map(skillRow).join("") || "<tr><td colspan='7'>暂无</td></tr>";
    summary.textContent = `Agents: ${agents.length} | Channels: ${channels.length} | Providers: ${(capabilitySnapshot.providers || []).length} | Approvals: ${approvals.length} | Skills: ${skillItems.length} | API: /api/v1/admin`;
    await loadAuditTrail();
    await loadRevisions();
  } catch (err) {
    summary.textContent = `加载失败: ${err.message}`;
    capabilitiesBody.innerHTML = "<tr><td colspan='7'>加载失败</td></tr>";
    approvalsBody.innerHTML = "<tr><td colspan='8'>加载失败</td></tr>";
    skillsBody.innerHTML = "<tr><td colspan='7'>加载失败</td></tr>";
    auditTrailSummary.textContent = `加载失败: ${err.message}`;
    auditTrailBody.innerHTML = "<tr><td colspan='9'>加载失败</td></tr>";
    clearAuditDetail();
  }
}

async function showSkillDetail(installId) {
  try {
    const detail = await callApi(`/api/v1/admin/skills/${installId}`);
    skillDetailPre.textContent = asJSON(detail);
  } catch (err) {
    skillDetailPre.textContent = String(err);
  }
}

async function validateSkill(installId) {
  try {
    const detail = await callApi(`/api/v1/admin/skills/${installId}/validate`, "POST");
    skillDetailPre.textContent = asJSON(detail);
    await refreshAll();
  } catch (err) {
    alert(`验证失败: ${err.message}`);
  }
}

async function requestSkillPromotion(installId) {
  const telegramUid = prompt("Telegram UID（可空；若只配置了一个 allowed uid，可直接留空）", "");
  if (telegramUid === null) return;
  const note = prompt("审批备注（可空）", "");
  if (note === null) return;
  try {
    const result = await callApi(`/api/v1/admin/skills/${installId}/promote`, "POST", {
      telegram_uid: telegramUid.trim() || null,
      note: note.trim() || null,
      metadata: {source: "admin-ui"},
    });
    skillDetailPre.textContent = asJSON(result.install);
    alert(`已创建审批 ${result.approval.approval_id}${result.mini_app_url ? `\\nMini App: ${result.mini_app_url}` : ""}`);
    await refreshAll();
  } catch (err) {
    alert(`提权申请失败: ${err.message}`);
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

function editAgent(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  agentFormMode = "edit";
  editingAgentId = item.agent_id;
  editingAgentStatus = item.status;
  document.getElementById("agent-form-title").textContent = `Agent 表单（编辑: ${item.agent_id}）`;
  document.getElementById("agent-form-name").value = item.name || "";
  document.getElementById("agent-form-task").value = item.task_name || "";
  document.getElementById("agent-form-timeout").value = String(item.default_timeout_seconds || 900);
  document.getElementById("agent-form-depth").value = String(item.default_generation_depth || 1);
  document.getElementById("agent-form-description").value = item.description || "";
  document.getElementById("agent-form-prompt").value = item.prompt_template || "";
  document.getElementById("agent-form-channels").value = (item.channel_bindings || []).join(", ");
  document.getElementById("agent-form-actor").value = "admin-ui";
  document.getElementById("agent-form-append").checked = Boolean(item.append_prompt);
  document.getElementById("agent-form-enabled").checked = item.status === "active";
  document.getElementById("agent-form-card").scrollIntoView({behavior: "smooth", block: "center"});
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
  const sessionInput = prompt("session_id（可空）", "");
  if (sessionInput === null) return;
  const promptInput = prompt("prompt_override（可空）", "");
  if (promptInput === null) return;
  const timeoutInput = prompt("timeout_seconds_override（可空）", "");
  if (timeoutInput === null) return;
  const depthInput = prompt("generation_depth_override（可空）", "");
  if (depthInput === null) return;

  const timeoutValue = timeoutInput.trim() ? toInt(timeoutInput.trim(), 900, 1, 7200) : null;
  const depthValue = depthInput.trim() ? toInt(depthInput.trim(), 1, 1, 10) : null;
  const run = await callApi(`/api/v1/admin/agents/${agentId}/launch`, "POST", {
    session_id: sessionInput.trim() || null,
    prompt_override: promptInput.trim() || null,
    timeout_seconds_override: timeoutValue,
    generation_depth_override: depthValue,
    env_overrides: {},
    metadata_updates: {trigger: "admin-ui"},
  });
  alert(`已启动 agent_run_id: ${run.agent_run_id}`);
}

async function createChannelAdvancedJson() {
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

async function quickCreateTelegramChannel() {
  const key = document.getElementById("tg-quick-key").value.trim() || "telegram-main";
  const token = document.getElementById("tg-quick-token").value.trim();
  const ids = csvToList(document.getElementById("tg-quick-ids").value);
  const actor = document.getElementById("tg-quick-actor").value.trim() || "admin-ui";

  if (!token) {
    alert("bot token 不能为空");
    return;
  }
  if (ids.length === 0) {
    alert("allowed ids 至少填一个");
    return;
  }

  const channels = await callApi("/api/v1/admin/channels");
  const existing = channels.find((item) => item.key === key);

  if (existing) {
    await callApi(`/api/v1/admin/channels/${existing.channel_id}`, "PUT", {
      display_name: existing.display_name || "Telegram Main",
      provider: "telegram",
      endpoint_url: existing.endpoint_url || null,
      secret_ref: existing.secret_ref || null,
      secret_value: token,
      clear_secret: false,
      allowed_chat_ids: ids,
      allowed_user_ids: ids,
      routing_policy: existing.routing_policy || {},
      metadata_updates: {quick_mode: "telegram"},
      actor,
      reason: "quick telegram update",
    });
    if (existing.status !== "active") {
      await callApi(`/api/v1/admin/channels/${existing.channel_id}/activate`, "POST", {
        actor,
        reason: "activate quick telegram channel",
      });
    }
  } else {
    await callApi("/api/v1/admin/channels", "POST", {
      key,
      display_name: "Telegram Main",
      provider: "telegram",
      endpoint_url: null,
      secret_ref: null,
      secret_value: token,
      allowed_chat_ids: ids,
      allowed_user_ids: ids,
      routing_policy: {quick_mode: "telegram"},
      metadata: {quick_mode: "telegram"},
      enabled: true,
      actor,
    });
  }

  await refreshAll();
  document.getElementById("tg-quick-token").value = "";
}

function resetChannelForm() {
  channelFormMode = "create";
  editingChannelId = null;
  editingChannelStatus = "active";
  document.getElementById("channel-form-title").textContent = "Channel 表单（新建）";
  document.getElementById("channel-form-key").value = "telegram-main";
  document.getElementById("channel-form-display").value = "Telegram Main";
  document.getElementById("channel-form-provider").value = "telegram";
  document.getElementById("channel-form-endpoint").value = "";
  document.getElementById("channel-form-secret-ref").value = "";
  document.getElementById("channel-form-secret-value").value = "";
  document.getElementById("channel-form-allowed-chat-ids").value = "";
  document.getElementById("channel-form-allowed-user-ids").value = "";
  document.getElementById("channel-form-actor").value = "admin-ui";
  document.getElementById("channel-form-enabled").checked = true;
}

async function submitChannelForm() {
  const key = document.getElementById("channel-form-key").value.trim();
  const displayName = document.getElementById("channel-form-display").value.trim();
  if (!key || !displayName) {
    alert("key / display_name 为必填");
    return;
  }

  const actor = document.getElementById("channel-form-actor").value.trim() || "admin-ui";
  const provider = document.getElementById("channel-form-provider").value || "telegram";
  const endpointUrl = document.getElementById("channel-form-endpoint").value.trim() || null;
  const secretRef = document.getElementById("channel-form-secret-ref").value.trim() || null;
  const secretValueRaw = document.getElementById("channel-form-secret-value").value;
  const secretValue = secretValueRaw && secretValueRaw.trim() ? secretValueRaw.trim() : null;
  const allowedChatIds = csvToList(document.getElementById("channel-form-allowed-chat-ids").value);
  const allowedUserIds = csvToList(document.getElementById("channel-form-allowed-user-ids").value);
  const enabled = document.getElementById("channel-form-enabled").checked;

  if (channelFormMode === "edit" && editingChannelId) {
    await callApi(`/api/v1/admin/channels/${editingChannelId}`, "PUT", {
      display_name: displayName,
      provider,
      endpoint_url: endpointUrl,
      secret_ref: secretRef,
      secret_value: secretValue,
      clear_secret: false,
      allowed_chat_ids: allowedChatIds,
      allowed_user_ids: allowedUserIds,
      routing_policy: {},
      metadata_updates: {},
      actor,
      reason: "manual edit from form",
    });
    const currentlyEnabled = editingChannelStatus === "active";
    if (enabled !== currentlyEnabled) {
      const op = enabled ? "activate" : "deactivate";
      await callApi(`/api/v1/admin/channels/${editingChannelId}/${op}`, "POST", {
        actor,
        reason: "toggle from form",
      });
    }
  } else {
    await callApi("/api/v1/admin/channels", "POST", {
      key,
      display_name: displayName,
      provider,
      endpoint_url: endpointUrl,
      secret_ref: secretRef,
      secret_value: secretValue,
      allowed_chat_ids: allowedChatIds,
      allowed_user_ids: allowedUserIds,
      routing_policy: {},
      metadata: {},
      enabled,
      actor,
    });
  }

  await refreshAll();
  resetChannelForm();
}

function createChannel() {
  resetChannelForm();
  document.getElementById("channel-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

function editChannel(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  channelFormMode = "edit";
  editingChannelId = item.channel_id;
  editingChannelStatus = item.status;
  document.getElementById("channel-form-title").textContent = `Channel 表单（编辑: ${item.channel_id}）`;
  document.getElementById("channel-form-key").value = item.key || "";
  document.getElementById("channel-form-display").value = item.display_name || "";
  document.getElementById("channel-form-provider").value = item.provider || "telegram";
  document.getElementById("channel-form-endpoint").value = item.endpoint_url || "";
  document.getElementById("channel-form-secret-ref").value = item.secret_ref || "";
  document.getElementById("channel-form-secret-value").value = "";
  document.getElementById("channel-form-allowed-chat-ids").value = (item.allowed_chat_ids || []).join(", ");
  document.getElementById("channel-form-allowed-user-ids").value = (item.allowed_user_ids || []).join(", ");
  document.getElementById("channel-form-actor").value = "admin-ui";
  document.getElementById("channel-form-enabled").checked = item.status === "active";
  document.getElementById("channel-form-card").scrollIntoView({behavior: "smooth", block: "center"});
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

async function decideApproval(approvalId, op) {
  const note = prompt(`${op === "approve" ? "批准" : "拒绝"}备注（可空）`, "");
  if (note === null) return;
  const path = `/api/v1/admin/approvals/${approvalId}/${op}`;
  await callApi(path, "POST", {
    note: note.trim() || null,
    metadata: {source: "admin-ui"},
  });
  await refreshAll();
}

resetAgentForm();
resetChannelForm();
refreshAll();
</script>
</body>
</html>
"""


def register_ui_routes(router: APIRouter) -> None:
    @router.get("/view", response_class=HTMLResponse, include_in_schema=False)
    def admin_view() -> HTMLResponse:
        return HTMLResponse(_ADMIN_HTML)
