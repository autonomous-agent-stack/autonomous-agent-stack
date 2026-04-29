# macOS M1 本机 Hermes 接管 Runbook
# macOS M1 Local Hermes Takeover Runbook

这份 runbook 只解决一件事：在 macOS M1 本机上，让 AAS 通过 runtime adapter 调起本机 Hermes CLI。
This runbook solves one thing only: using AAS to invoke the local Hermes CLI through the runtime adapter on macOS M1.

规范性契约请先看 [docs/hermes-runtime-v1.md](./hermes-runtime-v1.md)。
Read [docs/hermes-runtime-v1.md](./hermes-runtime-v1.md) first for the canonical contract.

## 当前范围 / Current Scope

- 目标是最小运行闭环：`create_session -> run -> status -> stream -> cancel`
  The target is the minimum runtime loop: `create_session -> run -> status -> stream -> cancel`
- 继续复用 AAS 现有 `/api/v1/runtime/{runtime_id}` 公共 API
  The existing AAS `/api/v1/runtime/{runtime_id}` public API remains unchanged
- 当前 Hermes v1 只保证文本 prompt 闭环
  Hermes v1 currently guarantees only the text-prompt runtime path
- `metadata.hermes` 在当前阶段只做结构化校验与回写，不直接驱动 CLI flag 映射
  At this stage, `metadata.hermes` is validated and echoed back but does not directly drive CLI flag mapping
- 当前不包含 schedule、worker queue、draft PR、promotion
  This does not currently include schedule, worker queue, draft PR, or promotion

## 1. 先安装 Hermes / Install Hermes First

先在本机确认 Hermes CLI 可以直接运行，再接 AAS。
First make sure the Hermes CLI runs directly on the machine, then wire in AAS.

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes model
hermes tools
hermes doctor
```

如果你已经把 Hermes 放进自定义路径，也可以保留包装器脚本，只要最终能在 shell 里成功启动。
If Hermes lives behind a custom path or wrapper script, that is also fine as long as it starts cleanly from the shell.

## 2. 配置 AAS / Configure AAS

默认情况下，AAS 会读取 `AUTORESEARCH_HERMES_COMMAND`，未设置时使用 `hermes`。
By default, AAS reads `AUTORESEARCH_HERMES_COMMAND` and falls back to `hermes` when unset.

```bash
cp .env.example .env
```

最小配置：
Minimum configuration:

```bash
AUTORESEARCH_HERMES_COMMAND=hermes
```

如果你需要固定包装器或 profile，可以写成完整命令：
If you need to pin a wrapper or profile, provide the full command:

```bash
AUTORESEARCH_HERMES_COMMAND="/opt/hermes/bin/hermes --profile local"
```

## 3. 启动控制面 / Start the Control Plane

```bash
make setup
make doctor
make start
```

启动后检查：
After startup, check:

- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`

## 4. 手动触发一个 Hermes Run / Trigger a Hermes Run Manually

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/runtime/hermes/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "task_name": "hermes-local-smoke",
    "prompt": "Say hello from Hermes.",
    "work_dir": "/absolute/path/to/workspace",
    "cli_args": ["--model", "local-small"],
    "metadata": {
      "hermes": {
        "profile": "local",
        "toolsets": ["shell"]
      }
    }
  }'
```

轮询状态：
Poll status:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/runtime/hermes/status?run_id=<run_id>"
```

查看 session events：
Inspect session events:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/runtime/hermes/sessions/<session_id>/events"
```

## 5. 预期结果 / Expected Result

- `runtime_id` 为 `hermes`
  `runtime_id` is `hermes`
- `command` 形如 `hermes chat -Q -q ...`
  `command` looks like `hermes chat -Q -q ...`
- `summary` / `stdout_preview` 可读
  `summary` / `stdout_preview` are readable
- `metadata.hermes` 会返回 `requested / effective / contract_version`
  `metadata.hermes` returns `requested / effective / contract_version`
- `status` 会在 `created/running/completed/failed` 间流转
  `status` moves through `created/running/completed/failed`
- session events 里能看到 queued / running / completed 或 failed
  session events show queued / running / completed or failed

## 6. 当前边界 / Current Boundaries

- `images`、`skill_names`、`command_override` 会被 Hermes runtime v1 直接拒绝
  `images`, `skill_names`, and `command_override` are rejected directly by Hermes runtime v1
- 如果 Hermes 二进制不存在，run 会直接落成 `FAILED`
  If the Hermes executable is missing, the run goes directly to `FAILED`
- 当前失败不会回落到 Claude / OpenClaw 运行面
  Current failures do not fall back to the Claude / OpenClaw execution path
- 如果后续要接 queue、schedule 或 promotion，应继续挂在这条 runtime lane 上，而不是再造一套平行框架
  If queue, schedule, or promotion are added later, they should build on this runtime lane instead of creating a parallel framework

## 7. 让已有 Hermes 被 AAS 发现 / Make an Existing Hermes Discoverable by AAS

- 最佳实践不是让 AAS 直接扫描或托管你手工启动的 `hermes gateway` 进程。
  The best practice is not to have AAS directly scan or manage a manually started `hermes gateway` process.
- 当前 AAS 只会发现主动执行 `register + heartbeat` 的 worker。
  Today AAS only discovers workers that actively perform `register + heartbeat`.
- 因此，**把已有 Hermes 编入 AAS 的推荐方式，是启动 AAS 的 Mac worker，让这个 worker 通过 `WorkerRuntimeDispatchService` 调 Hermes runtime lane**。
  Therefore, the recommended way to bring an existing Hermes into AAS is to start the AAS Mac worker and let that worker call the Hermes runtime lane through `WorkerRuntimeDispatchService`.

推荐启动顺序：
Recommended startup order:

```bash
export AUTORESEARCH_TELEGRAM_INGRESS_MODE=webhook
make start
bash scripts/start-mac-worker.sh
```

说明（双渠道保留，单入口）：
Notes (dual-channel retained, single ingress):

- 默认 `AUTORESEARCH_TELEGRAM_INGRESS_MODE=webhook`，只允许 Webhook 消费 Telegram updates，避免多 poller 抢消息。
  Default `AUTORESEARCH_TELEGRAM_INGRESS_MODE=webhook` allows Webhook-only Telegram update consumption to avoid multi-poller conflicts.
- 如需临时回滚到单 poller，请显式设置 `AUTORESEARCH_TELEGRAM_INGRESS_MODE=polling`，并保证系统里只运行一个 poller。
  To temporarily roll back to single poller mode, explicitly set `AUTORESEARCH_TELEGRAM_INGRESS_MODE=polling` and ensure only one poller process is running.

启动后再查：
Then query:

```bash
curl -sS http://127.0.0.1:8001/api/v1/workers
```

你应该会看到：
You should then see:

- 一个已注册的 `mac-*` worker
  One registered `mac-*` worker
- `capabilities` 包含 `claude_runtime`
  `capabilities` including `claude_runtime`
- `metadata` 里带当前主机与工作目录信息
  `metadata` carrying host and work-dir information

边界要说清楚：
The boundary is important:

- 单独运行 `hermes gateway` 本身不会自动进入 worker 盘点。
  Running `hermes gateway` by itself does not automatically appear in worker inventory.
- 如果以后要把 `hermes gateway` 本体做成一等 worker，需要额外实现一个 Hermes gateway -> AAS worker registry bridge。
  If you later want the `hermes gateway` process itself to become a first-class worker, you need an extra Hermes gateway -> AAS worker registry bridge.

## 8. 管家归因可见性 / Butler Attribution Visibility

- 管家 ack、RUNNING 与终态卡默认会展示：
  Butler ack, RUNNING, and terminal cards now display:
  - `执行面 | Runtime`（`hermes` 或 `claude`）
    `Execution plane | Runtime` (`hermes` or `claude`)
  - `Agent 名称 | Agent name`（未配置时显示 `（未命名）| (unnamed)`）
    `Agent name` (falls back to `（未命名）| (unnamed)` when unset)
- `runtime_id` 来源于 Telegram 入队 payload；
  `runtime_id` comes from Telegram queue payload.
- `agent_name` 来源于 `AUTORESEARCH_TELEGRAM_AGENT_NAME`（若为空则展示占位）。
  `agent_name` comes from `AUTORESEARCH_TELEGRAM_AGENT_NAME` (placeholder is used when empty).

快速检查：
Quick check:

1. 设定 `AUTORESEARCH_TELEGRAM_RUNTIME_ID=hermes`，发一条普通文本任务；
   Set `AUTORESEARCH_TELEGRAM_RUNTIME_ID=hermes` and send a normal text task.
2. 再设定 `AUTORESEARCH_TELEGRAM_RUNTIME_ID=claude`，发另一条任务；
   Then set `AUTORESEARCH_TELEGRAM_RUNTIME_ID=claude` and send another task.
3. 两条卡片都应包含 `执行面 | Runtime` 与 `Agent 名称 | Agent name`。
   Both cards should include `执行面 | Runtime` and `Agent 名称 | Agent name`.

补充：worker 终态回报现在会附带统一诊断字段，`result/metrics` 中可见 `error_kind`、`exit_reason`、`dispatch_runtime` 等键，便于在 `/status` 和 worker 盘点里做快速故障定位。
Additional note: worker terminal reports now include unified diagnostics; `result/metrics` expose keys such as `error_kind`, `exit_reason`, and `dispatch_runtime`, which helps fast triage in `/status` and worker inventory views.

## 9. 十分钟健康检查 / Ten-Minute Health Check

1. 先看控制面与 worker 是否在线：`/health`、`/api/v1/workers`。
   Start with control-plane and worker liveness: `/health`, `/api/v1/workers`.
2. 发一条 Telegram 任务并确认 ack 卡里有 `run_id`。
   Send one Telegram task and confirm the ack card includes `run_id`.
3. 在 `/status` 查看 worker 诊断行：`runtime/phase/exit`。
   Inspect `/status` worker diagnostics: `runtime/phase/exit`.
4. 终态卡里确认 `诊断 | Diagnostics` 是否出现（至少 `runtime` 与 `exit`）。
   In the terminal card, confirm `诊断 | Diagnostics` exists (at least `runtime` and `exit`).
5. 若失败，优先读 `error_kind` 与 `exit_reason` 再决定是重试、切 runtime，还是查 worker 心跳。
   On failure, read `error_kind` and `exit_reason` first, then decide whether to retry, switch runtime, or inspect worker heartbeat.
6. 执行 `python3 scripts/telegram_ingress_health.py --minutes 30 --json`，确认存在稳定字段：`mode`、`active_consumer`、`state`、`healthy`。
   Run `python3 scripts/telegram_ingress_health.py --minutes 30 --json` and confirm stable fields: `mode`, `active_consumer`, `state`, `healthy`.
7. 若 `state=failover`，等待 `AUTORESEARCH_TELEGRAM_POLLING_RECOVER_AFTER_SECONDS` 后再次检查，确认由 `webhook` 回到 `polling`（或按策略保持 webhook）。
   If `state=failover`, wait `AUTORESEARCH_TELEGRAM_POLLING_RECOVER_AFTER_SECONDS` and check again to confirm recovery from `webhook` back to `polling` (or remain webhook per policy).
