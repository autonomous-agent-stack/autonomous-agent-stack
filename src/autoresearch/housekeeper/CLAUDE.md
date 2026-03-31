# CLAUDE.md - Housekeeper subsystem

## Purpose
This subsystem implements the private frontdesk / housekeeper entrypoint.
It is not the final authority for execution dispatch.

## Responsibilities
The housekeeper may:
- read session context
- read allowed personal/shared memory
- translate natural language into a structured draft
- propose agent_package_id and backend_kind
- request approval
- generate user-facing summaries

The housekeeper must NOT:
- directly run backend jobs without control plane registration
- bypass approval
- invent unsupported packages
- read memory outside allowed scope

## Task boundary
Use a two-step model:
- HousekeeperIntent / TaskDraft = frontdesk proposal
- Task = control-plane registered execution object

The housekeeper creates drafts.
The control plane validates, resolves, and dispatches final tasks.

## Routing rules
- manager_agent for software / code change requests
- linux_supervisor for ops / scripts / inspection tasks
- win_yingdao only for structured business packages
- if no clear match exists, return clarification_required

## Testing rules
Changes in this subsystem must keep these green:
- unsupported request is rejected instead of misrouted
- high-risk package cannot run before approval
- memory scoping does not leak
- result summary contains task/package/worker/backend summary