# AAS RFC (Request for Comments)

[**English**](README.en.md) | [简体中文](README.zh-CN.md)

This directory contains architecture design documents and RFCs for the AAS project.

## RFC Index

### Core Architecture

| RFC | Status | Description |
|-----|------|------|
| [distributed-execution.md](./distributed-execution.md) | 📝 Draft | Distributed execution: Linux control plane + Mac credential-bound worker |
| [three-machine-architecture.md](./three-machine-architecture.md) | 📝 Draft | Three-machine heterogeneous pools: Linux + Mac mini + MacBook |
| [federation-protocol.md](./federation-protocol.md) | 📝 Draft | Federation protocol with layered trust (L0-L3) and graduated sharing |
| [federation-market-model.md](./federation-market-model.md) | 📝 Draft | Dual-layer model: Federation (diplomacy) + Market (trade) with resource pricing and settlement |

## RFC Process

### 1. Proposal Phase

```bash
# Create RFC draft
docs/rfc/
├── rfc-001-feature-name.md
└── templates/
    └── rfc-template.md
```

### 2. Discussion Phase

- Create discussion thread in GitHub Discussions
- Invite relevant reviewers
- Collect feedback and iterate

### 3. Approval Phase

- Core RFCs require maintainer approval
- Technical decisions require consensus
- Record objections and resolutions

### 4. Implementation Phase

- Create implementation issue
- Link related PRs
- Update RFC status

### 5. Completion Phase

- Change RFC status to Accepted/Implemented
- Update ARCHITECTURE.md
- Archive to memory/

## RFC Status

- **📝 Draft**: Under discussion
- **👀 Under Review**: Being reviewed
- **✅ Accepted**: Approved, awaiting implementation
- **🚧 In Progress**: Being implemented
- **✅ Implemented**: Delivered
- **❌ Rejected**: Declined
- **📦 Superseded**: Replaced by newer RFC

## RFC Template

```markdown
# RFC: [Title]

**Status**: Draft | **Author**: ... | **Created**: YYYY-MM-DD
**Depends on**: [Related RFC]

## Summary

One-sentence summary of the core content.

## Background & Motivation

Why do this? What problem does it solve?

## Design

### Core Solution

Detailed design description.

### Data Model

```sql
-- Data model changes, if any
```

### API Changes

```python
# API changes, if any
```

## Implementation Phases

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3

## Relationship to Existing Architecture

How does it integrate with existing code?

## Alternative Approaches

What alternatives were considered? Why not chosen?

## Risks & Mitigations

Potential risks and mitigation strategies.

## References

Related links.
```

## Contributing

We welcome new RFC submissions!

1. Fork repository
2. Create `docs/rfc/rfc-XXX-title.md`
3. Fill in RFC template
4. Submit PR and initiate discussion in Discussions

## Recommended Reading Order

**For new contributors**:

1. Read [ARCHITECTURE.md](../../ARCHITECTURE.md) for current architecture
2. Read [distributed-execution.md](./distributed-execution.md) for distributed foundations
3. Read [three-machine-architecture.md](./three-machine-architecture.md) for multi-machine expansion
4. Read [federation-protocol.md](./federation-protocol.md) for federation vision

**For implementers**:

Read RFCs based on current implementation phase.
