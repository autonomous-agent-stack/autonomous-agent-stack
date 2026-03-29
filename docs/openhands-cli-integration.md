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

For a real non-interactive CLI path, the launcher now defaults to OpenHands headless mode and sources `ai_lab.env` before dispatch:

```bash
OPENHANDS_SANDBOX_PROVIDER=process \
make openhands OH_TASK="Scan /opt/workspace/src and add the smallest passing regression."
```

Equivalent command template:

```bash
RUNTIME=process \
SANDBOX_VOLUMES=/actual/workspace:/workspace:rw \
openhands --exp --headless -t "your task"
```

Notes:

- `scripts/openhands_start.sh` prefers a dedicated host-side CLI at `./.masfactory_runtime/tools/openhands-cli-py312/bin/openhands` when present, and bootstraps `agent_settings.json` from `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL`.
- `sandbox/ai-lab/Dockerfile` now pins the container-side CLI to the same validated `OpenHands CLI 1.5.0`, so the host and `ai-lab` runtime do not silently diverge.
- The launcher now `cd`s into the target worktree before invoking the CLI, so OpenHands sees the real isolated workspace as its current working directory.
- The local `OpenHands CLI 1.5.0` smoke checks confirmed that `--exp --headless` auto-exits cleanly for pipeline use, while plain `--headless` completes the task but can remain attached to the prompt.
- The same local smoke checks confirmed `--headless` and `-t`, but not `--json`, so JSON mode is opt-in only for CLI builds that actually expose that flag.
- `ai-lab` runtime intentionally defaults to `openhands` inside the container, instead of reusing a host-only binary path.
- If your session cannot access the configured Docker/Colima socket, the launcher first tries a safe Colima fallback: repo-managed external store when configured, otherwise the current user's own `~/.colima/<profile>` socket. The current-user fallback also adds `/Volumes/AI_LAB` as a Colima mount when that external workspace root exists; on shared machines, using a dedicated profile such as `COLIMA_PROFILE=ai-lab` is the lowest-risk path.
- The process provider is operationally useful but weaker than the full container sandbox, so it should be treated as an explicit fallback rather than the end-state isolation model.

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
