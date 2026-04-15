# open-multi-agent reference assessment

## Date

- 2026-04-07

## Repository

- upstream: `https://github.com/JackChen-me/open-multi-agent`

## Goal

Capture whether `open-multi-agent` is worth borrowing from for this repository, without widening current implementation scope.

## Conclusion

`open-multi-agent` has clear reference value for runtime ergonomics and public API shape, but it should not become the control-plane blueprint for this repository.

Current recommendation:

- keep the existing Python/FastAPI + SQLite-first control plane
- keep current worker runtime work focused on durable queue + lease + report flows
- revisit selective adoption later for agent-runtime ergonomics only

## Why It Is Interesting

- clean top-level runtime API shape around team/task/agent execution
- lightweight orchestration concepts, easier to understand than heavier agent frameworks
- useful attention to execution traces, approval hooks, structured outputs, and loop protection
- small enough to study quickly and borrow ideas from without taking on a large platform migration

## Why It Is Not The Right Base Architecture

- the upstream project is optimized for lightweight orchestration, not for a durable local control plane
- its design center is closer to short-lived in-process task execution than to persisted worker scheduling
- it explicitly avoids several surfaces that this repository already needs or is likely to need later, including durable persistence and richer system integration
- adopting it as the base would pull this repository toward a TypeScript-first orchestration path, while the current execution path is intentionally centered on Python/FastAPI

## Fit Against Current Repo Direction

This repository has already chosen a narrower execution path for the current worker line:

- `docs/decisions/mac-standby-worker-claim-slice.md`
  - smallest possible queue + lease scheduler
  - one queue only: `housekeeping`
  - no TypeScript control plane changes
- `docs/decisions/mac-standby-worker-runtime-v1.md`
  - enqueue -> claim -> execute -> report end-to-end
  - no multi-agent orchestration
  - no worker pool or concurrent execution

That means the immediate bottleneck is not "more orchestration features." It is durable execution, observability, and recovery discipline on the existing Python control plane.

## What To Borrow Later

If this repository revisits multi-agent runtime improvements, the most promising pieces to borrow conceptually are:

- public API layering for single agent vs task graph vs team execution
- structured trace and progress event model
- loop detection and runtime guardrails
- approval hook patterns
- example-first documentation style

These should be re-expressed inside the existing Python control plane, not imported by switching architectural center of gravity to the upstream project.

## What Not To Borrow

- in-process queue assumptions
- non-durable task lifecycle assumptions
- TypeScript-first control-plane direction
- architecture decisions that bypass the existing shared models and SQLite-backed persistence

## Deferred Decision

No implementation work is approved from this assessment alone.

Revisit only if one of these becomes true:

- the current Python runtime needs a cleaner agent/team/task API surface
- the current subagent execution path needs stronger runtime guardrails or traces
- there is an explicit decision to expand beyond the current single-worker durable execution focus

Until then, treat `open-multi-agent` as a reference repository, not as a migration target.
