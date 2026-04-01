# Investor Brief

`autonomous-agent-stack` is a controlled agent execution control plane.

It is not trying to become another open-ended autonomous agent runtime. The project is building the layer that lets multiple runtimes and workers run under one governed execution surface: task routing, isolation, approvals, audit, rollback, replay, and migration.

## Current Status

The project is already past the "idea only" stage.

What exists now:

- a unified control-plane direction
- task / run / gate / worker contracts
- a real worker registry
- Linux supervisor production-path wiring
- heartbeat and registration integration
- OpenClaw compatibility and migration scaffolding
- prompt orchestration rules that stay above the control plane, not instead of it
- a three-layer memory model: checkpoint, replay/audit, knowledge

What this means in practice:

- code agents can be run as controlled executors
- Linux workers can be dispatched through a governed execution path
- failures can be audited and replayed
- worker status can be surfaced in a unified registry
- the system already knows how to stay bounded instead of drifting into "free-form autonomy"

## What It Can Realistically Become

The near-term product is not "an agent that replaces humans."

It is:

- a control plane for code agents and operational workers
- a migration hub for OpenClaw-compatible workflows
- a governance layer for review, approval, and rollback
- a worker fabric that can absorb OpenHands, Claude CLI, browser automation, Linux workers, and Windows RPA workers

## Why This Matters

Most agent projects stop at a demo.

This project is trying to solve the missing middle:

- how to run heterogeneous workers under one contract
- how to keep execution isolated
- how to make failures observable and recoverable
- how to keep prompt-based planning from bypassing production controls
- how to absorb existing ecosystems without forcing a full rewrite

That is the part enterprises actually pay for.

## Win + Yingdao Business Scenarios

The Windows + Yingdao worker is the entry point for structured business operations, especially repetitive desktop workflows that are painful to scale manually.

Concrete scenarios:

- ERP / back-office data entry
  - fill structured forms from upstream business data
  - submit records into legacy Windows-only systems
  - capture screenshots or logs as proof of completion

- finance / ops reconciliation
  - move data between spreadsheets, desktop tools, and web portals
  - process recurring checks and updates
  - produce human-reviewable execution artifacts

- customer operations
  - update order status, address, invoice, or ticket records
  - handle repetitive UI workflows that are not worth a full API integration

- compliance-heavy business flows
  - keep step-by-step execution logs
  - attach screenshots and artifacts for audit
  - route exceptions to human review instead of guessing

- cross-system glue work
  - bridge systems that cannot be integrated cleanly by API
  - use RPA as the last-mile execution layer

Why this is valuable:

- the tasks are repetitive and expensive when done manually
- the workflows are common in real businesses
- the ROI is easy to show if time saved and error rate reduction are measured
- the control plane makes the automation governable, not brittle

## What The Project Is Not

- not a generic "another agent OS"
- not a memory-first research toy
- not a self-modifying autonomy framework
- not a prompt swarm that can rewrite production on its own

## Future Milestones Investors Can Understand

1. Expand from Linux-first execution to Windows RPA execution.
2. Turn prompt orchestration into a planning front-end only.
3. Add more worker adapters without changing the control plane contract.
4. Use checkpoint / replay / knowledge separation to make operations auditable.
5. Make Win + Yingdao flows measurable in terms of task success, time saved, and error reduction.

## One-Sentence Pitch

`autonomous-agent-stack` is the governed execution layer that lets heterogeneous agent runtimes and business workers run safely, replayably, and migratably across real operational workflows.

