# OpenClaw Runtime Adapter v1

`OpenClaw` 走独立的 runtime lane，不伪装成 process driver。

## Contract

runtime adapter v1 暴露五个动作：

- `create_session`
- `run`
- `stream`
- `cancel`
- `status`

实现落点：

- contract: `src/autoresearch/agent_protocol/runtime_models.py`
- manifest: `configs/runtime_agents/openclaw.yaml`
- registry: `src/autoresearch/agent_protocol/runtime_registry.py`
- bridge service: `src/autoresearch/core/services/openclaw_runtime_adapter.py`

## AEP Bridge Boundary

从 `JobSpec` 进入 OpenClaw runtime 的最小输入：

- `run_id`
- `agent_id`
- `task`
- `mode`
- `policy.timeout_sec`
- `metadata.openclaw`
- `input_artifacts`

映射回 `aep/v0 DriverResult` 的输出：

- `status`
- `summary`
- `changed_paths`
- `output_artifacts`
- `metrics`
- `recommended_action`
- `error`

workspace / artifacts / logs 的最小接法：

- `JobSpec.metadata.openclaw.work_dir -> ClaudeAgentCreateRequest.work_dir -> RuntimeRunRead.work_dir`
- `ClaudeAgentRunRead.stdout_preview -> log artifact`
- `ClaudeAgentRunRead.stderr_preview -> log artifact`
- `OpenClawSessionRead.events -> session event log artifact`

## Non-goals

- 不改现有 `agent-run` / process adapter lane
- 不把 OpenClaw 伪装成 process driver
- 不做 runtime factory v2
