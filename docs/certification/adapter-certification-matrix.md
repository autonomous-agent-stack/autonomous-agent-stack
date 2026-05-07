# Adapter Certification Matrix

Generated from live adapter certification evidence. Adapter config declares intent only; stable status is derived from this runner.

- generated_at: `2026-05-07T00:57:04.120133+00:00`
- status: `passed`
- stable_adapters: `16`
- blocked_adapters: `0`

| Adapter | Intent | Derived | Status | Missing checks | Blocked reason | Evidence |
|---|---:|---:|---:|---|---|---|
| `a2a` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/a2a/live_evidence.json` |
| `autogen_ag2` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/autogen_ag2/live_evidence.json` |
| `crewai` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/crewai/live_evidence.json` |
| `dify` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/dify/live_evidence.json` |
| `flowise` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/flowise/live_evidence.json` |
| `haystack` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/haystack/live_evidence.json` |
| `hermes` | `beta` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/hermes/live_evidence.json` |
| `langchain_agents` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/langchain_agents/live_evidence.json` |
| `langflow` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/langflow/live_evidence.json` |
| `langgraph` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/langgraph/live_evidence.json` |
| `llamaindex` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/llamaindex/live_evidence.json` |
| `mcp_tool_broker` | `beta` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/mcp_tool_broker/live_evidence.json` |
| `microsoft_agent_framework` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/microsoft_agent_framework/live_evidence.json` |
| `openclaw` | `beta` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/openclaw/live_evidence.json` |
| `openhands` | `beta` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/openhands/live_evidence.json` |
| `semantic_kernel` | `experimental` | `stable` | `certified` | - | - | `artifacts/ga/adapter_certification/semantic_kernel/live_evidence.json` |

Required checks:

- `real_doctor`
- `session_binding`
- `real_run`
- `real_stream`
- `real_cancel`
- `real_status`
- `artifact_collection`
- `error_taxonomy`
- `policy_hook`
- `approval_hook`
- `tool_broker_enforcement`
- `model_gateway_enforcement`
- `secret_lease_enforcement`
- `session_event_mapping`
- `live_integration_test`
- `failure_drill`
