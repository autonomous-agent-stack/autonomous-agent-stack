# OpenHands 驱动集成 (AEP v0)

## 定位

OpenHands 作为 **AEP driver adapter** 集成，而不是独立的 control plane。

- AAS 拥有路由/状态/验证/晋升
- OpenHands 只在隔离工作区中执行有界任务

## 入口命令

```bash
make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
```

验证本地连接时的 dry-run 行为：

```bash
OPENHANDS_DRY_RUN=1 make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
```

对于真正的非交互式 CLI 路径，launcher 现在默认为 OpenHands headless 模式，并在分发前 source `ai_lab.env`：

```bash
OPENHANDS_SANDBOX_PROVIDER=process \
make openhands OH_TASK="Scan /opt/workspace/src and add the smallest passing regression."
```

等效命令模板：

```bash
RUNTIME=process \
SANDBOX_VOLUMES=/actual/workspace:/workspace:rw \
openhands --exp --headless -t "your task"
```

注意事项：

- `scripts/openhands_start.sh` 优先使用位于 `./.masfactory_runtime/tools/openhands-cli-py312/bin/openhands` 的专用 host-side CLI，并从 `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` 引导 `agent_settings.json`
- `sandbox/ai-lab/Dockerfile` 现在将容器侧 CLI 固定到同一验证的 `OpenHands CLI 1.5.0`，因此 host 和 `ai-lab` 运行时不会静默 diverge
- launcher 现在在调用 CLI 之前 `cd` 到目标 worktree，因此 OpenHands 将真实的隔离工作区视为其当前工作目录
- 本地 `OpenHands CLI 1.5.0` smoke checks 确认 `--exp --headless` 对于管道使用会自动干净退出，而 plain `--headless` 完成任务但可能保持附加到提示符
- 相同的本地 smoke checks 确认 `--headless` 和 `-t`，但不是 `--json`，因此 JSON 模式仅对于实际暴露该标志的 CLI 构建是可选的
- `ai-lab` 运行时有意识地在容器内默认为 `openhands`，而不是重用仅主机的二进制路径
- 如果你的会话无法访问配置的 Docker/Colima socket，launcher 首先尝试安全的 Colima fallback：配置时的 repo 管理的外部存储，否则当前用户自己的 `~/.colima/<profile>` socket。当前用户 fallback 还会在该外部工作区根目录存在时添加 `/Volumes/AI_LAB` 作为 Colima 挂载；在共享机器上，使用专用配置文件（如 `COLIMA_PROFILE=ai-lab`）是最低风险的路径
- process 提供程序在操作上有用，但比完整的容器沙箱弱，因此应将其视为显式 fallback，而不是最终状态的隔离模型

## 运行时布局

每次运行写入：

```text
.masfactory_runtime/runs/<run_id>/
  job.json
  effective_policy.json
  workspace/
  artifacts/
    stdout.log
    stderr.log
    compliance.json
    promotion.patch
  driver_result.json
  summary.json
  events.ndjson
```

## 代码契约

- 协议模型：`src/autoresearch/agent_protocol/models.py`
- 策略合并（deny-wins）：`src/autoresearch/agent_protocol/policy.py`
- 运行器核心：`src/autoresearch/executions/runner.py`
- OpenHands 适配器：`drivers/openhands_adapter.sh`
- 驱动清单：`configs/agents/openhands.yaml`

## 补丁门

Runner 在晋升之前应用内置检查：

- `builtin.allowed_paths`
- `builtin.forbidden_paths`
- `builtin.no_runtime_artifacts`
- `builtin.no_binary_changes`
- `builtin.max_changed_files`
- `builtin.max_patch_lines`

运行时产物（`logs/`、`.masfactory_runtime/`、`memory/`、`.git/`）从晋升补丁中排除。

## 失败策略

AEP 支持在 `JobSpec` 中显式 fallback 步骤：

- `retry` - 重试
- `fallback_agent` - 切换到 fallback agent
- `human_review` - 人工审查
- `reject` - 拒绝

查看完整协议文档：`docs/agent-execution-protocol.zh-CN.md`。
