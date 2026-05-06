# Evergreen OS GA v1.0 Gap Report

- status: `failed`
- generated_at: `2026-05-06T23:47:41.724129+00:00`
- missing_total: `86`

## Release Gate

- status: `passed`
- missing_checks: `0`

## Bypass GA

- status: `passed`
- missing_checks: `0`

## Adapter Certification

- status: `failed`
- missing_checks: `32`

- a2a: missing checks approval_hook, artifact_collection, failure_drill, live_integration_test, model_gateway_enforcement, policy_hook, real_cancel, real_run, real_status, real_stream, secret_lease_enforcement, session_binding, session_event_mapping, tool_broker_enforcement
- a2a: missing artifacts/ga/adapter_certification/a2a/live_evidence.json
- autogen_ag2: missing all certification checks
- autogen_ag2: missing artifacts/ga/adapter_certification/autogen_ag2/live_evidence.json
- crewai: missing checks approval_hook, failure_drill, live_integration_test, model_gateway_enforcement, policy_hook, real_cancel, real_status, real_stream, secret_lease_enforcement, session_binding, session_event_mapping, tool_broker_enforcement
- crewai: missing artifacts/ga/adapter_certification/crewai/live_evidence.json
- dify: missing all certification checks
- dify: missing artifacts/ga/adapter_certification/dify/live_evidence.json
- flowise: missing all certification checks
- flowise: missing artifacts/ga/adapter_certification/flowise/live_evidence.json
- haystack: missing all certification checks
- haystack: missing artifacts/ga/adapter_certification/haystack/live_evidence.json
- hermes: missing checks failure_drill, live_integration_test, model_gateway_enforcement, secret_lease_enforcement, tool_broker_enforcement
- hermes: missing artifacts/ga/adapter_certification/hermes/live_evidence.json
- langchain_agents: missing all certification checks
- langchain_agents: missing artifacts/ga/adapter_certification/langchain_agents/live_evidence.json
- langflow: missing all certification checks
- langflow: missing artifacts/ga/adapter_certification/langflow/live_evidence.json
- langgraph: missing all certification checks
- langgraph: missing artifacts/ga/adapter_certification/langgraph/live_evidence.json
- llamaindex: missing all certification checks
- llamaindex: missing artifacts/ga/adapter_certification/llamaindex/live_evidence.json
- mcp_tool_broker: missing checks failure_drill, live_integration_test, model_gateway_enforcement, real_cancel, real_stream, secret_lease_enforcement, session_binding
- mcp_tool_broker: missing artifacts/ga/adapter_certification/mcp_tool_broker/live_evidence.json
- microsoft_agent_framework: missing all certification checks
- microsoft_agent_framework: missing artifacts/ga/adapter_certification/microsoft_agent_framework/live_evidence.json
- openclaw: missing checks failure_drill, live_integration_test, model_gateway_enforcement, secret_lease_enforcement, tool_broker_enforcement
- openclaw: missing artifacts/ga/adapter_certification/openclaw/live_evidence.json
- openhands: missing checks failure_drill, live_integration_test, model_gateway_enforcement, real_cancel, real_status, secret_lease_enforcement, session_binding, session_event_mapping, tool_broker_enforcement
- openhands: missing artifacts/ga/adapter_certification/openhands/live_evidence.json
- semantic_kernel: missing all certification checks
- semantic_kernel: missing artifacts/ga/adapter_certification/semantic_kernel/live_evidence.json

## PostgreSQL Event Store

- status: `passed`
- missing_checks: `0`

## Direct Secret/Model/Tool Paths

- status: `failed`
- missing_checks: `15`

- direct tool network call: src/autoresearch/agents/opensource_searcher.py
- direct model client: src/autoresearch/api/dependencies.py
- direct env copy into runtime: src/autoresearch/core/services/claude_agents.py
- direct model key/env access: src/autoresearch/core/services/claude_api_adapter.py
- direct tool network call: src/autoresearch/core/services/cluster_manager.py
- direct env copy into runtime: src/autoresearch/core/services/executions.py
- direct tool network call: src/autoresearch/core/services/hitl_approval.py
- direct tool network call: src/autoresearch/core/services/opensage_sandbox_client.py
- direct tool network call: src/autoresearch/core/services/telegram_image_downloader.py
- direct tool network call: src/autoresearch/core/services/telegram_polling.py
- direct env copy into runtime: src/autoresearch/core/task_runner.py
- direct model client: src/autoresearch/llm/__init__.py
- direct model key/env access: src/autoresearch/llm/claude.py
- direct model client: src/autoresearch/llm/glm.py
- direct model key/env access: src/autoresearch/llm/openai.py

## V1 Primary Surfaces

- status: `failed`
- missing_checks: `39`

- /api/v1/a2a in src/autoresearch/api/routers/a2a.py
- /api/v1/admin in src/autoresearch/api/routers/admin/router.py
- /api/v1/approvals in src/autoresearch/api/routers/approvals.py
- /api/v1/autoresearch/plans in src/autoresearch/api/routers/autoresearch_plans.py
- /api/v1/butler in src/autoresearch/api/routers/butler.py
- /api/v1/capabilities in src/autoresearch/api/routers/capabilities.py
- /api/v1/cluster in src/autoresearch/api/routers/cluster.py
- /api/v1/content-kb in src/autoresearch/api/routers/content_kb.py
- /api/v1/evaluations in src/autoresearch/api/routers/evaluations.py
- /api/v1/excel-audit in src/autoresearch/api/routers/excel_audit.py
- /api/v1/excel-ops in src/autoresearch/api/routers/excel_ops.py
- /api/v1/executors in src/autoresearch/api/routers/executors.py
- /api/v1/experiments in src/autoresearch/api/routers/experiments.py
- /api/v1/federation in src/autoresearch/api/routers/federation.py
- /api/v1/gateway/telegram in src/autoresearch/api/routers/gateway_telegram/router.py
- /api/v1/generators in src/autoresearch/api/routers/generators.py
- /api/v1/github-assistant in src/autoresearch/api/routers/github_assistant.py
- /api/v1/github-ops in src/autoresearch/api/routers/github_ops.py
- /api/v1/integrations in src/autoresearch/api/routers/integrations.py
- /api/v1/knowledge in src/autoresearch/api/routers/knowledge_graph.py
- /api/v1/loops in src/autoresearch/api/routers/loops.py
- /api/v1/agents/manager in src/autoresearch/api/routers/manager_agent.py
- /api/v1/mcp in src/autoresearch/api/routers/mcp.py
- /api/v1/openclaw in src/autoresearch/api/routers/openclaw.py
- /api/v1/optimizations in src/autoresearch/api/routers/optimizations.py
- /api/v1/orchestration in src/autoresearch/api/routers/orchestration.py
- /api/v1/panel in src/autoresearch/api/routers/panel.py
- /api/v1/reports in src/autoresearch/api/routers/reports.py
- /api/v1/runtime in src/autoresearch/api/routers/runtime.py
- /api/v1/sessions in src/autoresearch/api/routers/sessions.py
- /api/v1/stream in src/autoresearch/api/routers/streaming.py
- /api/v1/synthesis in src/autoresearch/api/routers/synthesis.py
- /api/v1/usage in src/autoresearch/api/routers/usage.py
- /api/v1/variants in src/autoresearch/api/routers/variants.py
- /api/v1/auth in src/autoresearch/api/routers/webauthn.py
- /api/v1/worker-runs in src/autoresearch/api/routers/worker_runs.py
- /api/v1/worker-schedules in src/autoresearch/api/routers/worker_schedules.py
- /api/v1/workers in src/autoresearch/api/routers/workers.py
- /api/v1/youtube in src/autoresearch/api/routers/youtube.py

## Furniture E2E

- status: `passed`
- missing_checks: `0`
