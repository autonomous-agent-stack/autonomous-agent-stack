# Why AAS?

## The Problem

As AI agents become more capable, the core question is no longer just "how do we sandbox them?"

It is:

**When model capabilities keep changing, what should stay stable in the system, and what should remain replaceable?**

### What Breaks in Most Agent Stacks

1. **Model limitations become permanent architecture**
   - A temporary planning weakness turns into a fixed DAG
   - A prompt workaround becomes a framework primitive
   - The stack fossilizes around today's harness tricks

2. **History is confused with context**
   - The session is treated as a chat transcript
   - Summaries become the only memory
   - Recovery depends on rebuilding prompts instead of querying facts

3. **Execution surfaces quietly become the trusted core**
   - A worker runtime accumulates planning, execution, approval, and publish authority
   - Tools and sandboxes leak into the system boundary
   - Security depends on assuming the model "probably won't think of that"

## Our Answer

AAS is built around three abstractions that should outlive any specific harness version:

### 1. Session as Durable Fact History

- Session is not a mirror of the context window
- Session should be append-only execution history
- Summaries, prompt bundles, patches, and PRs are derived views, not the source of truth
- Recovery and handoff should start from facts, not from brittle prompt reconstruction

### 2. Policy as Replaceable Orchestration

- Planning, context assembly, retries, checkpoints, evaluation, and promotion should be policy seams
- The system should not hard-code today's best harness forever
- As models improve, AAS should swap policies more often than it rewrites the whole platform

### 3. Capabilities as Isolated Hands

- Sandboxes, remote workers, MCP servers, browsers, and git proxies are execution hands
- The control plane stays above them
- The brain should route over typed capabilities, not over one privileged runtime

## Zero-Trust Still Matters

Session-first does not mean soft boundaries.

The existing safety invariants remain core:

- **Patch-Only**: agents propose bounded changes instead of owning the repo
- **Deny-Wins**: tighter policy always wins
- **Single-Writer**: promotion of mutable state never races
- **Artifact Isolation**: runtime state does not silently become source code
- **Promotion Gate**: execution and approval stay separated

The point is not to trust the model more.
The point is to trust stable interfaces more than model-specific tricks.

## Why This Matters Now

Three things are changing at once:

1. **Models are getting better**
   - More work can be delegated to the model
   - More old harness assumptions will go stale

2. **Durable execution patterns are proven**
   - Leases, heartbeats, append-only logs, replay, and promotion gates are well-understood systems ideas
   - Agent infrastructure can borrow from distributed systems instead of inventing everything from scratch

3. **Teams want governance, not just demos**
   - They want agent productivity without giving away repository authority
   - They want local credentials, audit trails, approvals, and recovery
   - They want control planes that are vendor-neutral

## What AAS Is Building

### Today

AAS is a bounded control plane for autonomous repository changes:

- planner selects a bounded task
- worker edits in isolation
- validators check policy and execution output
- promotion gate decides whether the result may become a patch artifact or Draft PR

### Next

AAS is moving toward a governed runtime substrate for long-running agents:

- session-first state instead of prompt-first memory
- policy-first orchestration instead of fixed harness doctrine
- capability-first routing instead of adapter sprawl

### Later

That opens the door to:

- distributed execution across heterogeneous workers
- many brains / many hands coordination
- federation between governed AAS instances
- durable agent operations beyond repo patching

## What AAS Is Not Trying To Be

- not an unconstrained self-editing super-agent
- not a clone of any single model vendor runtime
- not a framework that hard-codes today's prompt hacks as tomorrow's architecture

## The Bet

We believe the most durable layer in agent infrastructure is not "the smartest harness."

It is:

- durable session state
- replaceable orchestration policy
- isolated capabilities
- governed promotion

That is the layer AAS wants to own.

---

*[Read the full documentation](README.md) | [Read the current roadmap](docs/roadmap.md) | [Join the discussion](https://github.com/srxly888-creator/autonomous-agent-stack/discussions)*
