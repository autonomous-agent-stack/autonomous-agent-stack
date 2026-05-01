# Mac 单机管家闭环 MVP

## 目标

在一台 Mac 上跑通 Telegram / Panel 到 Butler、worker、审批、回写的最小闭环。Butler 对外使用 dotted canonical task type，例如 `youtube.autoflow` 与 `github.pr_ops`；worker 队列继续使用既有枚举，例如 `youtube_autoflow` 与 `github_ops`，避免破坏已落地链路。

## Goal

Run the minimal Telegram / Panel to Butler, worker, approval, and write-back loop on one Mac. Butler exposes dotted canonical task types such as `youtube.autoflow` and `github.pr_ops`; the worker queue keeps existing enum values such as `youtube_autoflow` and `github_ops` to avoid breaking deployed paths.

## 建议目录

```text
~/aas/
├─ autonomous-agent-stack/
├─ data/
│  ├─ aas.sqlite3
│  ├─ artifacts/
│  └─ logs/
├─ workers/
│  ├─ github/
│  ├─ youtube/
│  ├─ excel/
│  └─ hermes/
├─ secrets/
│  ├─ telegram.env
│  ├─ github-accountA.env
│  ├─ github-accountB.env
│  └─ hermes.env
└─ launch/
   ├─ start-aas.sh
   ├─ start-worker.sh
   ├─ start-hermes-gateway.sh
   └─ start-all.sh
```

## Suggested Layout

```text
~/aas/
├─ autonomous-agent-stack/
├─ data/
│  ├─ aas.sqlite3
│  ├─ artifacts/
│  └─ logs/
├─ workers/
│  ├─ github/
│  ├─ youtube/
│  ├─ excel/
│  └─ hermes/
├─ secrets/
│  ├─ telegram.env
│  ├─ github-accountA.env
│  ├─ github-accountB.env
│  └─ hermes.env
└─ launch/
   ├─ start-aas.sh
   ├─ start-worker.sh
   ├─ start-hermes-gateway.sh
   └─ start-all.sh
```

## 启动方式

从仓库根目录启动：

```bash
launch/start-all.sh
```

默认状态：

- `AUTORESEARCH_API_DB_PATH=${HOME}/aas/data/aas.sqlite3`
- API 日志写入 `${HOME}/aas/data/logs/aas-api.log`
- Mac worker 日志写入 `${HOME}/aas/data/logs/mac-worker.log`
- 如需启动 Hermes gateway，先设置 `HERMES_GATEWAY_COMMAND`

## Start Commands

Start from the repository root:

```bash
launch/start-all.sh
```

Default state:

- `AUTORESEARCH_API_DB_PATH=${HOME}/aas/data/aas.sqlite3`
- API logs go to `${HOME}/aas/data/logs/aas-api.log`
- Mac worker logs go to `${HOME}/aas/data/logs/mac-worker.log`
- To start the Hermes gateway, set `HERMES_GATEWAY_COMMAND` first

## Butler 路由

新增 canonical metadata 字段：

- `canonical_task_type`: dotted 业务语义，例如 `github.pr_ops`
- `worker_task_type`: worker 队列枚举，例如 `github_ops`
- `approval_policy`: `auto`、`approval_required` 或 `blocked`

默认短语映射：

- “总结这个 YouTube” → `youtube.autoflow`
- “帮我看这个 PR” → `github.pr_ops`
- “算这个月提成” → `excel.commission`
- “这个任务你判断一下” → `hermes.general`

未知任务先走模型补位，仍无法确认时落到 Hermes interactive。

## Butler Routing

New canonical metadata fields:

- `canonical_task_type`: dotted business meaning, for example `github.pr_ops`
- `worker_task_type`: worker queue enum, for example `github_ops`
- `approval_policy`: `auto`, `approval_required`, or `blocked`

Default phrase mapping:

- “总结这个 YouTube” → `youtube.autoflow`
- “帮我看这个 PR” → `github.pr_ops`
- “算这个月提成” → `excel.commission`
- “这个任务你判断一下” → `hermes.general`

Unknown tasks go through model fill first, then fall back to Hermes interactive when still unresolved.

## GitHub Ops

安全动作：

- `read_issue`
- `read_pr`
- `read_checks`
- `summarize_pr`
- `add_comment`
- `add_label`

禁止动作：

- merge PR
- push commit
- 删除分支
- 修改 repo settings

API：

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/worker-runs/github-ops \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "summarize_pr",
    "repo": "owner/repo",
    "pr_number": 123,
    "requested_by": "manual_smoke"
  }'
```

## GitHub Ops

Safe actions:

- `read_issue`
- `read_pr`
- `read_checks`
- `summarize_pr`
- `add_comment`
- `add_label`

Blocked actions:

- merge PR
- push commit
- delete branch
- change repo settings

API:

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/worker-runs/github-ops \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "summarize_pr",
    "repo": "owner/repo",
    "pr_number": 123,
    "requested_by": "manual_smoke"
  }'
```

## 审批策略

策略文件：

- `configs/approval_policy.yaml`
- `configs/role_permissions.yaml`

默认策略：

- YouTube 摘要：自动执行
- GitHub 读取与摘要：自动执行
- GitHub comment / label：需要审批
- GitHub merge / push / 删除 / settings：阻断

Telegram `/approve <approval_id>`、Telegram `/reject <approval_id>` 与 Panel 审批按钮继续复用同一个审批服务。

## Approval Policy

Policy files:

- `configs/approval_policy.yaml`
- `configs/role_permissions.yaml`

Default policy:

- YouTube summary: auto-run
- GitHub reads and summaries: auto-run
- GitHub comment / label: approval required
- GitHub merge / push / delete / settings: blocked

Telegram `/approve <approval_id>`, Telegram `/reject <approval_id>`, and Panel approval buttons continue to use the shared approval service.

## 验收命令

```bash
pytest --noconftest \
  tests/test_butler_router.py \
  tests/test_standby_youtube_autoflow.py \
  tests/test_approvals_api.py \
  tests/test_hermes_approval_decisions.py \
  tests/test_github_ops.py
```

## Validation Command

```bash
pytest --noconftest \
  tests/test_butler_router.py \
  tests/test_standby_youtube_autoflow.py \
  tests/test_approvals_api.py \
  tests/test_hermes_approval_decisions.py \
  tests/test_github_ops.py
```
