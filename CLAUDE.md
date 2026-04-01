# CLAUDE.md

## Project goal
This repository is building a private frontdesk + controlled execution system.
The goal is NOT to build a general super-agent platform.
The goal is to ship a usable private housekeeper entrypoint with a minimal control plane.

## Architecture
There are 3 layers:

1. Personal Housekeeper (frontdesk)
   - Understand user requests
   - Read allowed memory
   - Draft structured tasks
   - Ask for approval on high-risk actions
   - Summarize results for the user

2. Control Plane
   - Owns Task / AgentPackage / Worker lifecycle
   - Owns routing, approval, logs, replay, and status aggregation
   - Makes final dispatch decisions

3. Workers / Backends
   - Execute only
   - Do not interpret user intent
   - Do not bypass approval rules

## Source of truth
- `agent-control-plane/` is the spec source of truth for Task / AgentPackage / Worker shapes.
- Python runtime under `src/autoresearch/` is the shipping runtime for v0.
- If runtime and spec diverge, update the spec first, then sync runtime.

## Current v0 scope
Allowed:
- housekeeper dispatch flow
- package registry loading from manifest.json
- worker registry and heartbeat
- approval flow
- result summaries
- software_change_agent
- linux_housekeeping_agent

Deferred:
- second runtime stack
- Node/Prisma/React control plane runtime
- long-term autonomous loops
- multi-agent debate
- rich personality systems
- production-grade win_yingdao execution

## Hard rules
- Do not create a second orchestration system beside the control plane.
- Do not let the housekeeper directly execute business logic.
- Do not bypass approval for high-risk or write operations.
- Do not add vague routing. If no package matches, return clarification_required.
- Do not expand memory access beyond explicitly allowed scope.
- Do not modify unrelated directories.

## Required checks before finishing
- Run package validator / smoke tests
- Run relevant Python tests
- Update docs when APIs or schemas change
- Add a short change summary

## gstack

Use gstack's `/browse` skill for **all** web browsing tasks. Never use `mcp__claude-in-chrome__*` tools.

If gstack skills don't work, run `cd .claude/skills/gstack && ./setup` to build binaries and register skills.

Available skills:
`/office-hours` `/plan-ceo-review` `/plan-eng-review` `/plan-design-review` `/design-consultation` `/design-shotgun` `/design-html` `/review` `/ship` `/land-and-deploy` `/canary` `/benchmark` `/browse` `/connect-chrome` `/qa` `/qa-only` `/design-review` `/setup-browser-cookies` `/setup-deploy` `/retro` `/investigate` `/document-release` `/codex` `/cso` `/autoplan` `/careful` `/freeze` `/guard` `/unfreeze` `/gstack-upgrade` `/learn`