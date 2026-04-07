# MASFactory Strict Execution v1

This SOP is the short operational checklist for bounded autonomous work in this repository.

The canonical system picture lives in `/Volumes/AI_LAB/Github/autonomous-agent-stack/ARCHITECTURE.md`. If this SOP and the architecture doc ever disagree, follow `ARCHITECTURE.md` and update this file.

## Purpose

Keep autonomous execution useful without letting workers bypass the control plane.

## Mandatory Defaults

- Default output mode is patch-only.
- Workers may edit only explicitly allowed repo-relative paths.
- Forbidden paths always include `.git/`, `logs/`, `.masfactory_runtime/`, `memory/`, and secret material such as `*.key` or `*.pem`.
- Git branch creation, commit, push, merge, rebase, reset, and checkout are not worker actions.
- Promotion is owned by the promotion gate, never by the worker.

## Preflight

Before running OpenHands or any AEP worker:

1. Confirm the task is bounded and can be expressed as a small patch.
2. Provide `allowed_paths`, `forbidden_paths`, and at least one validation command.
3. Prefer adding or updating a direct regression test alongside the source edit.
4. If the execution path is `OpenHandsControlledBackendService`, require a clean repo root first.

## Execution Rules

- Work inside isolated workspaces only.
- Treat the main repo checkout as the baseline, not the mutable execution target.
- Never widen scope from inside the worker prompt.
- If a required file is outside scope, fail and request a new contract instead of reaching around the boundary.

## Promotion Rules

- The worker emits a patch candidate.
- Validation runs before promotion.
- `GitPromotionGateService` re-checks scope, runtime artifacts, binary changes, changed file count, patch size, writer lease, and Draft PR prerequisites.
- Draft PR mode requires explicit approval plus remote and credential checks.
- If Draft PR preconditions fail but patch checks pass, degrade to patch mode instead of escalating.

## Single Writer Rule

Mutable control-plane actions must hold a `WriterLease`.

This applies to:

- git promotion finalization,
- skill promotion from `cold_validated` to `promoted`,
- and any future path that upgrades shared mutable state.

If the lease is unavailable, block the action. Do not race another writer.

## Managed Skill Trust Ladder

Managed skills follow:

`pending -> quarantined -> cold_validated -> promoted`

Meaning:

- `quarantined`: copied out of the untrusted source into holding
- `cold_validated`: static and contract checks passed
- `promoted`: copied into the active runtime root

Do not skip `quarantined` or `cold_validated`.

## Physical Runtime Reminder

Current stable environment:

- repo checkout on `/Volumes/AI_LAB/Github/autonomous-agent-stack`
- ai-lab writable roots on `/Volumes/AI_LAB/ai_lab`
- Docker runtime through Colima
- isolated execution and promotion worktrees rooted outside the main checkout

The architecture depends on that separation. Do not silently collapse everything back into one writable repo.
