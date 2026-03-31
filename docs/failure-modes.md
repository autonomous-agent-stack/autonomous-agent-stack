# Failure Modes

这份文档定义控制面统一使用的 failure taxonomy。无论以后任务跑在 Mac 还是 Linux，都先按这套分类落账。

## Canonical Failure Classes

### `planner_stalled`

- Meaning: 控制面调度本身卡住，轮询没有拿到终态。
- Default action: `require_human_review`
- Typical signal: dispatch polling exhausted before terminal status.

### `executor_stalled`

- Meaning: 执行面启动了，但没有持续进展。
- Default action: `retry`
- Typical signal: AEP `stalled_no_progress` or fake remote `stalled`.

### `tool_timeout`

- Meaning: 执行超时。
- Default action: `retry`
- Typical signal: AEP `timed_out` or fake remote `timed_out`.

### `model_fallback`

- Meaning: 主要执行链退化到了 mock / fallback model，但结果仍可用。
- Default action: `downgrade_to_draft`
- Typical signal: fallback agent succeeded and produced a valid patch.

### `assertion_failed_after_fallback`

- Meaning: fallback model 产出了结果，但验证仍然失败。
- Default action: `require_human_review`
- Typical signal: fallback agent is `mock` and validator stays red.

### `env_missing`

- Meaning: 运行环境缺依赖、命令、路径或运行时前置条件。
- Default action: `abort`
- Typical signal: `EnvironmentCheckFailed: ...`

### `workspace_dirty`

- Meaning: 基线工作区不干净，不允许继续 promotion 或受控执行。
- Default action: `abort`
- Typical signal: `repository worktree is not clean` or `clean git checkout`.

### `transient_network`

- Meaning: 远端连接瞬断或暂时性网络故障。
- Default action: `retry`
- Typical signal: `ssh: connection reset by peer`, `connection refused`, `network is unreachable`.

### `unknown`

- Meaning: 当前证据不足以更精确分类。
- Default action: `quarantine`
- Typical signal: terminal failure without a stronger classifier hit.

## Action Semantics

- `retry`: 控制面可安全重试，不自动放大权限。
- `abort`: 当前环境不满足前置条件，先停。
- `require_human_review`: 需要人判断要不要继续。
- `downgrade_to_draft`: 允许保留结果，但不要当成高置信执行面成功。
- `quarantine`: 先隔离结果和状态，再人工看。

## Current Implementation Sources

- AEP / OpenHands runner outcomes
- Fake remote adapter terminal states
- Validation report failures
- Clean-worktree / environment preflight errors

这套 taxonomy 是控制面协议的一部分，不是某个 adapter 私有约定。
