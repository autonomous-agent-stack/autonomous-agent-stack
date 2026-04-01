# Project Direction

This document records the current direction of `autonomous-agent-stack` so future work stays aligned.

## Core Positioning

`autonomous-agent-stack` is a controlled agent execution control plane, not another autonomous agent runtime.

The project exists to unify:

- task routing
- worker registry
- execution isolation
- approval and audit
- rollback and replay
- migration for OpenClaw-compatible workflows

## What to Keep from Other Projects

- OpenHands: controlled execution, isolated workspace, patch/artifact output
- OpenClaw: OS-like runtime boundaries, session/skills compatibility, migration thinking
- MAS Factory: prompt-based task decomposition and role assignment
- DeerFlow: checkpoint, replay, and knowledge layering
- ClawX-style workflows: unified setup/doctor/start entry points

## What Not to Reintroduce

- uncontrolled multi-agent self-governance
- a second control plane
- a single all-purpose memory system
- prompt orchestration that bypasses contracts and gates
- direct production mutation by exploratory agents

## Prompt Orchestration Rule

Prompt orchestration is allowed only as a planning layer.

It may:

- decompose goals
- assign roles
- generate candidate plans
- attach validation requirements

It may not:

- replace the control plane
- bypass gate or acceptance
- write directly to production state
- mutate system policy or permissions

## Self-Exploration Rule

`autoresearch` may explore, but only as a controlled research/execution loop.

Allowed:

- discover gaps
- propose candidate fixes
- write failing tests
- produce draft patches in isolation
- summarize findings into replayable artifacts

Disallowed:

- self-modifying the control plane
- silently expanding scope
- introducing new execution primitives without review
- merging exploratory results without gate/acceptance

## Memory Model

Memory should stay split into:

- run checkpoint state
- replay / audit stream
- knowledge memory

This keeps execution, observability, and documentation separate.

