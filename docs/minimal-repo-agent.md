# Minimal Repo Agent

## Scope

`minimal_repo` is a docs-only demo agent that proves an agent-specific adapter
can run on top of the shared routing foundation without changing platform
contracts.

## What It Uses

- agent manifest loading from `configs/agents/`
- declarative route selection through the existing control-plane builder
- standard `JobSpec` materialization
- existing AEP runner execution
- standard `driver_result.json` output

## First-Cut Behavior

- default mode is `apply_in_workspace`
- policy defaults are limited to `docs/**`
- the adapter only appends a single-line marker to `docs/demo.md`
- no-op runs return a partial driver result instead of inventing a patch

## Non-Goals

- no scheduler or routing rule changes
- no fallback planning
- no host failover
- no commit, push, or archive behavior
- no platform contract expansion
