# AAS 管家治理运行手册 / AAS Butler Governance Runbook

## 目标 / Goal

中文：本手册说明 Butler 如何集中登记共用 MCP/工具能力，再按用户角色、agent 能力、任务风险和数据敏感度派发 scoped tool grant。Hermes 保留兜底与复杂拆解角色，稳定任务逐步沉淀为 Butler 规则并交给专业 agent。

English: This runbook explains how Butler centrally registers shared MCP/tool capabilities, then issues scoped tool grants according to user role, agent capability, task risk, and data sensitivity. Hermes remains the fallback and complex decomposition runtime, while stable workflows are promoted into Butler rules and delegated to specialized agents.

## 工具登记 / Tool Registry

中文：共用工具登记在 `configs/butler/tools.yaml`。agent 不直接持有共用工具密钥或全量工具清单，只在任务 payload/metadata 中接收本次任务允许使用的 grant。

English: Shared tools are registered in `configs/butler/tools.yaml`. Agents do not directly hold shared tool secrets or the full tool catalog; they receive only the grants allowed for the current task in payload/metadata.

中文：`/api/v2/butler/registry` 同时汇总现有 MCP provider registry、agent manifest、runtime agent、tool profile 与 GitHub account profile 的安全摘要。

English: `/api/v2/butler/registry` also summarizes the existing MCP provider registry, agent manifests, runtime agents, tool profiles, and GitHub account profiles.

中文：工具分层如下：

English: Tool tiers are:

- `common_read`：天气、地址粗查、POI、时间与公开地理查询，默认可按需派发。
- `common_read`: Weather, coarse address lookup, POI, time, and public geo queries; granted on demand by default.
- `sensitive_read`：个人账号、精确私人地址、文件正文等，需要更严格审计与脱敏。
- `sensitive_read`: Personal account data, precise private addresses, file contents, and similar data requiring stricter audit and redaction.
- `external_write`：push、PR、评论、上传等外部写入，默认触发审批。
- `external_write`: Pushes, PRs, comments, uploads, and other external writes; approval is required by default.
- `destructive`：删除、强推、关闭、merge 等破坏性动作，默认阻断或 owner 审批。
- `destructive`: Delete, force-push, close, merge, and other destructive actions; blocked by default or owner-approved.

## Amap 默认策略 / Amap Default Policy

中文：`amap.weather`、`amap.geocode`、`amap.poi_lookup` 属于 `common_read`。所有 agent 可声明对应 capability，由 ButlerToolBroker 按任务需要派发。

English: `amap.weather`, `amap.geocode`, and `amap.poi_lookup` belong to `common_read`. Any agent may declare the matching capability, and ButlerToolBroker grants it when the task needs it.

中文：当输入像私人住址时，Butler 自动追加 `pii_location` risk tag，审计摘要只保存脱敏文本。只有查询结果将写入仓库、日报或外部平台时，才升级到更高审批路径。

English: When input resembles a private address, Butler automatically adds the `pii_location` risk tag and stores only a redacted audit summary. Higher approval is needed only when the result will be written into a repository, report, or external platform.

## 安全审计 / Security Audit

中文：`security_audit` 是专业审计 agent，对接现有静态分析、AST 审计、prompt hygiene、audit trail 和审批策略。

English: `security_audit` is the specialized audit agent wired to existing static analysis, AST auditing, prompt hygiene, audit trail, and approval policy surfaces.

中文：默认节奏是关键动作前轻扫、2-4 小时漂移轻扫、每日简报、规则/配置变化后深扫。严重发现即时通知；普通 warning 汇总进日报。

English: The default cadence is quick scan before critical actions, drift checks every 2-4 hours, daily digest, and deep scan after rule or configuration changes. Severe findings notify immediately; ordinary warnings are folded into the daily digest.

## 规则成熟闭环 / Rule Promotion Loop

中文：Hermes 处理未知任务后记录 route evidence。同类任务多次成功后生成 `rule_candidate`，由 `security_audit` 扫描影响面。owner/supervisor 批准后，候选规则才可写入 `configs/butler/rules.yaml`。

English: After Hermes handles an unknown task, it records route evidence. Repeated successful tasks may generate a `rule_candidate`, which `security_audit` scans for impact. Only after owner/supervisor approval may the candidate be written into `configs/butler/rules.yaml`.

## API / API

中文：当前治理 API：

English: Current governance APIs:

- `GET /api/v2/butler/registry`：查看工具、agent manifest、规则与候选规则摘要。
- `GET /api/v2/butler/registry`: Inspect tools, agent manifests, stable rules, and rule candidate summaries.
- `POST /api/v2/butler/tools/resolve`：按任务解析 scoped tool grant。
- `POST /api/v2/butler/tools/resolve`: Resolve scoped tool grants for a task.
- `POST /api/v2/security-audit/quick-scan`：执行 diff/files/rule candidate 轻扫。
- `POST /api/v2/security-audit/quick-scan`: Run a quick scan over diff, files, or rule candidates.
- `GET /api/v2/security-audit/daily`：生成本地日报 artifact。
- `GET /api/v2/security-audit/daily`: Generate a local daily report artifact.

## 验证 / Validation

中文：推荐在修改 Butler 工具、规则、审计服务或 worker dispatch 后运行：

English: After changing Butler tools, rules, audit services, or worker dispatch, run:

```bash
uv run --no-project --with-requirements requirements.txt pytest tests/test_butler_governance.py
```

中文：若同时修改 Control Plane v2 主路径，再追加相关 v2/worker 测试和 `git diff --check`。

English: If the Control Plane v2 main path changed as well, add the relevant v2/worker tests and `git diff --check`.
