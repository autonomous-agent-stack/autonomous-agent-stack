# OpenHands Driver Integration (AEP v0)

## Positioning

OpenHands is integrated as an **AEP driver adapter**, not as a separate control plane.

- AAS owns routing/state/validation/promotion.
- OpenHands only executes bounded tasks in isolated workspace.

## Entry Command

```bash
make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
```

For dry-run behavior while validating local wiring:

```bash
OPENHANDS_DRY_RUN=1 make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
```

## Runtime Layout

Each run writes to:

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

## Code Contracts

- Protocol models: `src/autoresearch/agent_protocol/models.py`
- Policy merge (deny-wins): `src/autoresearch/agent_protocol/policy.py`
- Runner core: `src/autoresearch/executions/runner.py`
- OpenHands adapter: `drivers/openhands_adapter.sh`
- Driver manifest: `configs/agents/openhands.yaml`

## Patch Gate

Runner applies built-in checks before promotion:

- `builtin.allowed_paths`
- `builtin.forbidden_paths`
- `builtin.no_runtime_artifacts`
- `builtin.no_binary_changes`
- `builtin.max_changed_files`
- `builtin.max_patch_lines`

Runtime artifacts (`logs/`, `.masfactory_runtime/`, `memory/`, `.git/`) are excluded from promotion patch.

## Failure Strategy

AEP supports explicit fallback steps in `JobSpec`:

- `retry`
- `fallback_agent`
- `human_review`
- `reject`

See full protocol doc: `docs/agent-execution-protocol.md`.
