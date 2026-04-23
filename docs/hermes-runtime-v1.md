# Hermes Runtime v1 契约
# Hermes Runtime v1 Contract

这份文档定义 AAS 内部 `hermes` runtime lane 在 PR 1 + PR 2 后的稳定 v1 契约。
This document defines the stable v1 contract for the internal `hermes` runtime lane in AAS after PR 1 + PR 2.

## 文档角色 / Document Role

- 这是 Hermes runtime v1 的唯一 canonical contract 文档。
  This is the single canonical contract document for Hermes runtime v1.
- 平台差异和启动细节放在 runbook：
  Platform-specific setup details live in the runbooks:
  - [docs/macos-hermes-control-plane.md](./macos-hermes-control-plane.md)
  - [docs/windows-wsl2-hermes-control-plane.md](./windows-wsl2-hermes-control-plane.md)
- 当前文档描述仓库里已经落地的 v1 行为，包括 command builder、error taxonomy、cancel hardening 与 summary 语义。
  This document describes the v1 behavior that is now implemented in the repository, including the command builder, error taxonomy, cancel hardening, and summary semantics.

## Runtime Surface / Runtime Surface

- 统一 API 仍然是 `create_session / run / stream / cancel / status`。
  The unified API remains `create_session / run / stream / cancel / status`.
- `session_id` 只表示 AAS runtime session 绑定，不表示 Hermes CLI 的 resume 或 continue 能力。
  `session_id` represents only AAS runtime session binding and does not imply Hermes CLI resume or continue behavior.
- 当前执行底座继续复用 `ClaudeAgentService`，Hermes 作为 runtime adapter lane 接入。
  The execution substrate still reuses `ClaudeAgentService`, with Hermes integrated as a runtime adapter lane.

## 支持面 / Supported Inputs

- Hermes runtime v1 支持：
  Hermes runtime v1 supports:
  - `prompt`
  - `work_dir`
  - `timeout_seconds`
  - `env`
  - `cli_args`
  - `metadata.hermes`
- `metadata.hermes` 会参与结构化命令映射，固定投影到 Hermes one-shot CLI。
  `metadata.hermes` now participates in structured command mapping and projects into the Hermes one-shot CLI.
- `cli_args` 仍然保留为 escape hatch，但会追加在结构化映射之后，并先经过 denylist 检查。
  `cli_args` remain as an escape hatch, but they are appended after structured mapping and are checked against a denylist first.

## 不支持面 / Explicit Non-Goals

- Hermes runtime v1 不支持：
  Hermes runtime v1 does not support:
  - `images`
  - `skill_names`
  - `command_override`
  - 长会话恢复
    Long-lived session restore
  - 交互式审批回流
    Interactive approval callbacks
  - gateway 反向事件
    Gateway reverse events
- 对 API caller 的表现是稳定拒绝，而不是静默忽略。
  Unsupported request shapes are rejected consistently instead of being silently ignored.

## `metadata.hermes` Schema / `metadata.hermes` Schema

PR 1 固定以下结构化字段：
PR 1 fixes the following structured fields:

- `provider`
- `model`
- `profile`
- `toolsets`
- `approval_mode`
- `session_mode`

校验规则：
Validation rules:

- `provider` / `model` / `profile`：非空字符串或空值。
  `provider` / `model` / `profile`: non-empty strings or empty values.
- `toolsets`：字符串列表，去重并清理空项。
  `toolsets`: string list, deduplicated with empty entries removed.
- `approval_mode`：只允许 `manual`、`smart`、`off`。
  `approval_mode`: only `manual`, `smart`, and `off` are allowed.
- `session_mode`：PR 1 只允许 `oneshot`。
  `session_mode`: PR 1 allows only `oneshot`.
- 额外字段会被拒绝。
  Extra fields are rejected.
- `approval_mode=off` 在 PR 2 会被直接拒绝，作为 `invalid_request`。
  In PR 2, `approval_mode=off` is rejected directly as `invalid_request`.
- `approval_mode=manual` 与 `approval_mode=smart` 在 PR 2 阶段对 Hermes CLI 没有行为差异，只体现在 AAS 审计 metadata。
  In PR 2, `approval_mode=manual` and `approval_mode=smart` do not change Hermes CLI behavior and are reflected only in AAS audit metadata.

run metadata 中会写回：
Run metadata writes back:

```json
{
  "error_kind": "nonzero_exit",
  "failed_stage": "execute",
  "hermes": {
    "contract_version": "1.0",
    "requested": {
      "profile": "local",
      "toolsets": ["shell", "git"]
    },
    "effective": {
      "provider": null,
      "model": null,
      "profile": "local",
      "toolsets": ["shell", "git"],
      "approval_mode": null,
      "session_mode": "oneshot"
    },
    "command_projection": {
      "argv": ["hermes", "--profile", "local", "chat", "-Q", "-q", "task", "--toolsets", "shell,git"],
      "cwd": "/workspace",
      "timeout_seconds": 900,
      "mapped_fields": ["profile", "toolsets"],
      "unmapped_fields": ["session_mode"],
      "blocked_cli_args": []
    },
    "safety_flags": {
      "approval_mode": null,
      "oneshot_only": true,
      "cli_args_escape_hatch_used": false,
      "blocked_cli_args": []
    }
  }
}
```

## 命令投影 / Command Projection

- 基础调用路径固定为 `hermes chat -Q -q <prompt>`。
  The base invocation path is fixed as `hermes chat -Q -q <prompt>`.
- `--profile` 作为全局参数放在 `chat` 之前。
  `--profile` is treated as a global argument and appears before `chat`.
- `--provider`、`--model`、`--toolsets` 作为 `hermes chat` 参数放在 prompt 之后。
  `--provider`, `--model`, and `--toolsets` are treated as `hermes chat` arguments and appear after the prompt.
- `cli_args` 追加在结构化映射之后，因此只能覆盖非安全敏感项。
  `cli_args` are appended after structured mapping, so they can override only non-safety-sensitive items.
- Hermes runtime v1 的 denylist 会拒绝这些参数：
  Hermes runtime v1 denylist rejects these arguments:
  - `--yolo`
  - `--resume` / `-r`
  - `--continue` / `-c`
  - `--pass-session-id`
  - `--image`
  - `--skills` / `-s`
  - `--worktree` / `-w`

## 输出契约 / Output Contract

- `RuntimeRunRead` 现在公开：
  `RuntimeRunRead` now exposes:
  - `status`
  - `summary`
  - `stdout_preview`
  - `stderr_preview`
  - `returncode`
  - `output_artifacts`
- `returncode` 是 PR 1 唯一的退出码字段名，语义等价于进程 exit code。
  `returncode` is the only exit-code field name in PR 1 and is semantically equivalent to the process exit code.
- session events 继续通过 `RuntimeStatusRead.latest_events` 和 `/sessions/{session_id}/events` 提供，不新增新的顶层响应字段。
  Session events continue to flow through `RuntimeStatusRead.latest_events` and `/sessions/{session_id}/events`; no new top-level response field is introduced.
- `summary` 在 PR 2 收紧为平台摘要；原始输出只放在 `stdout_preview` / `stderr_preview`。
  In PR 2, `summary` is tightened into a platform summary; raw output remains only in `stdout_preview` / `stderr_preview`.

## 错误分类 / Error Taxonomy

- Hermes runtime v1 在 `RuntimeRunRead.metadata` 中写入机器可读错误字段：
  Hermes runtime v1 writes machine-readable error fields into `RuntimeRunRead.metadata`:
  - `error_kind`
  - `failed_stage`
- 当前稳定的 `error_kind` 列表：
  The current stable `error_kind` set is:
  - `invalid_request`
  - `binary_missing`
  - `command_build_failed`
  - `launch_failed`
  - `timeout`
  - `nonzero_exit`
  - `cancelled`
  - `internal_error`

## 取消保证 / Cancel Guarantees

- 用户主动取消现在会把 run 终态写成 `CANCELLED`，不再复用 `INTERRUPTED`。
  User-initiated cancellation now drives the run into the `CANCELLED` terminal state instead of reusing `INTERRUPTED`.
- Hermes cancel 通过共享执行底座做真实进程终止：`terminate()` 后等待固定 grace period，再升级到 `kill()`。
  Hermes cancel uses the shared execution substrate for real process termination: `terminate()` first, then a fixed grace period, then `kill()` if needed.
- 取消前已经产生的 `stdout_preview` / `stderr_preview` 会被保留。
  Any `stdout_preview` / `stderr_preview` produced before cancellation are preserved.
- `session_mode` 仍然固定为 `oneshot`，AAS `session_id` 不映射到 Hermes 原生 resume/session continuation。
  `session_mode` remains fixed at `oneshot`, and AAS `session_id` does not map to Hermes-native resume/session continuation.

## Telegram 管家与 Mac worker / Telegram Butler and Mac Worker

- Telegram webhook 将普通对话排队为 `CLAUDE_RUNTIME` 时，可在环境变量中设置 `AUTORESEARCH_TELEGRAM_RUNTIME_ID=hermes`，使 **Mac worker 通过 `WorkerRuntimeDispatchService` 调用与 HTTP `/api/v1/runtime/hermes/runs` 相同的 `HermesRuntimeAdapterService`**，从而继承 v1 的拒绝面、`error_kind`、summary 与取消语义。
  For Telegram messages enqueued as `CLAUDE_RUNTIME`, set `AUTORESEARCH_TELEGRAM_RUNTIME_ID=hermes` so the **Mac worker routes through `WorkerRuntimeDispatchService` into the same `HermesRuntimeAdapterService` as HTTP `POST /api/v1/runtime/hermes/runs`**, inheriting v1 reject rules, `error_kind`, summary, and cancel semantics.
- 可选 Hermes 默认值：`AUTORESEARCH_TELEGRAM_HERMES_PROFILE`、`AUTORESEARCH_TELEGRAM_HERMES_TOOLSETS`（逗号分隔）、`AUTORESEARCH_TELEGRAM_HERMES_APPROVAL_MODE`（`manual` 或 `smart`；`off` 仍会被 Hermes v1 拒绝）。
  Optional Hermes defaults: `AUTORESEARCH_TELEGRAM_HERMES_PROFILE`, comma-separated `AUTORESEARCH_TELEGRAM_HERMES_TOOLSETS`, and `AUTORESEARCH_TELEGRAM_HERMES_APPROVAL_MODE` (`manual` or `smart`; `off` remains rejected by Hermes v1).
- 当 `runtime_id=hermes` 时，webhook **不会**把 Telegram 图片 URL 放进 worker payload，避免触发 v1 对 `images` 的硬拒绝；需要视觉输入时请走其他 runtime 或单独设计入口。
  When `runtime_id=hermes`, the webhook **omits** Telegram image URLs from the worker payload so v1 does not hard-reject on `images`; use another runtime or a dedicated ingress for vision.

## 当前边界 / Current Boundaries

- Hermes runtime v1 仍然是单机 `oneshot` runtime，不支持 Hermes 原生 session 恢复、多实例路由或 gateway 反向事件。
  Hermes runtime v1 remains a single-machine `oneshot` runtime and does not support Hermes-native session restore, multi-instance routing, or gateway reverse events.
- 后续控制面扩展见 [docs/roadmap.md](./roadmap.md)。
  Follow-up control-plane work is tracked in [docs/roadmap.md](./roadmap.md).
