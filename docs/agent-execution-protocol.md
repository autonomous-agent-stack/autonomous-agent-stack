# Agent Execution Protocol (AEP v0)

## Goal

AEP v0 makes every agent a **driver adapter** instead of a control plane.

```text
AAS control plane
  -> JobSpec
  -> isolated workspace
  -> driver adapter
  -> DriverResult
  -> validators
  -> promotion.patch
  -> decision (promote / retry / fallback / human_review)
```

## Iron Rules

1. Agent never edits main repo directly.
2. Agents do not share writable workspaces.
3. Policy merge is deny-wins.
4. Protocol is file-contract first, SDK second.

## Core Files

- `src/autoresearch/agent_protocol/models.py`
- `src/autoresearch/agent_protocol/policy.py`
- `src/autoresearch/agent_protocol/registry.py`
- `src/autoresearch/executions/runner.py`
- `drivers/openhands_adapter.sh`
- `configs/agents/openhands.yaml`
- `scripts/agent_run.py`

## Runner Contract

Runner creates a run folder:

```text
.masfactory_runtime/runs/<run_id>/
  job.json
  effective_policy.json
  baseline/
  workspace/
  artifacts/
    stdout.log
    stderr.log
    promotion.patch
  driver_result.json
  summary.json
  events.ndjson
```

Environment variables passed to adapters:

- `AEP_RUN_DIR`
- `AEP_WORKSPACE`
- `AEP_ARTIFACT_DIR`
- `AEP_JOB_SPEC`
- `AEP_RESULT_PATH`
- `AEP_EVENT_LOG`
- `AEP_BASELINE`

Adapter must write `driver_result.json` to `AEP_RESULT_PATH`.

## Policy Merge (Deny Wins)

- `forbidden_paths`: union
- `allowed_paths`: intersection
- `network`: stricter wins (`disabled < allowlist < full`)
- `tool_allowlist`: intersection
- `timeout_sec`, `max_changed_files`, `max_patch_lines`: minimum wins

## Built-in Patch Gates

Runner validates patch via built-in checks:

- `builtin.allowed_paths`
- `builtin.forbidden_paths`
- `builtin.no_runtime_artifacts`
- `builtin.no_binary_changes`
- `builtin.max_changed_files`
- `builtin.max_patch_lines`

Runtime artifacts (`logs/`, `.masfactory_runtime/`, `memory/`, `.git/`) are excluded from promotion patch.

## Run Command

```bash
make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
```
