# Why AAS?

## The Problem

As AI agents become more capable, a fundamental tension emerges:

**How do we harness agent productivity while maintaining control over codebases?**

### Current Approaches Are Broken

1. **Direct Access Models**
   - Agents get full git push access
   - No validation between agent output and main branch
   - Security vulnerabilities slip through

2. **Manual Review Bottlenecks**
   - Every agent change requires human review
   - Scalability issues as agent usage grows
   - Inconsistent review standards

3. **Fragile Sandboxing**
   - Containers are escaped or misconfigured
   - Runtime artifacts leak into source code
   - No clear boundary between agent and system

## Our Solution

AAS introduces a **governed execution model** with three key properties:

### 1. Separation of Concerns

```
Planner (what to do) → Worker (do it in isolation) → Validator (check it) → Promoter (decide)
```

No single component has both the ability to execute code and approve its integration.

### 2. Zero-Trust Invariants

- **Patch-Only**: Agents can only propose changes, never commit directly
- **Deny-Wins**: If any policy says "no", the answer is "no"
- **Single-Writer**: Only one promotion operation can happen at a time
- **Artifact Isolation**: Runtime state never becomes source code

### 3. Durable Control Plane

- SQLite as authoritative state store
- All operations auditable and replayable
- Clear separation of control plane and execution artifacts

## Why Now?

The timing is right for three reasons:

1. **Agent Capabilities Are Maturing**
   - LLMs can now do meaningful code modification
   - But they still make mistakes and need guardrails

2. **Distributed Systems Patterns Are Well Understood**
   - We can borrow from CI/CD, distributed transactions, and durable execution
   - Patterns like lease, heartbeat, and outbox are proven

3. **The Community Is Ready**
   - Security-conscious developers are wary of unconstrained agents
   - Teams need agent productivity but won't compromise on safety

## What AAS Enables Today

### For Individuals

- **Personal GitHub Assistant**: Triage your repos, analyze issues, draft PRs
- **Safe Experimentation**: Try agent ideas in isolated workspaces
- **Local Control**: Keep authentication on your machines, execution elsewhere

### For Teams

- **Controlled Agent Workflows**: Agents propose, humans approve
- **Audit Trail**: Every agent action is logged and attributable
- **Gradual Autonomy**: Start with patch-only, loosen constraints as trust builds

### For Organizations

- **Federated Execution**: Share compute and capabilities across teams/orgs
- **Policy Enforcement**: Organizational standards apply to all agent work
- **Compliance Ready**: Audit logs and approval gates satisfy security reviews

## Where We're Going

### Phase 2: Distributed Execution (In Progress)

Linux control plane coordinates workers across machines:
- Mac workers handle GitHub-authenticated tasks
- GPU workers run heavy inference
- Edge workers operate with local capabilities during outages

### Phase 3: Multi-Machine Pools

- Capability-based routing instead of machine-hardcoded logic
- Automatic failover and load balancing
- Support for heterogeneous execution environments

### Phase 4: Federation Network

- Layered trust model (L0-L3)
- Graduated resource sharing
- Market mechanisms for resource exchange
- Sovereign nodes with revocable federation

## The Bigger Vision

We believe agent infrastructure should be:

- **Safe by default**: Zero-trust, not trusted-by-default
- **Composable**: Mix and match workers, capabilities, and policies
- **Auditable**: Every decision traceable to its source
- **Federated**: Work across organizational boundaries
- **Economically Sustainable**: Resource exchange with clear terms

## Join Us

If you believe AI agents should be powerful **and** governable, AAS is your community.

- **Contributors**: We need help with distributed execution, federation protocols, and market mechanisms
- **Users**: Try it out and tell us what works and what doesn't
- **Architects**: Join our RFC discussions and shape the future

Let's build the infrastructure for trustworthy autonomous agents.

---

*[Read the full documentation](README.md) | [Join the discussion](https://github.com/srxly888-creator/autonomous-agent-stack/discussions)*
