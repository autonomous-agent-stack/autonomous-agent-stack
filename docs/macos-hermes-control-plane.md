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
