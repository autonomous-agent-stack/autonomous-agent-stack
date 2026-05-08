# Autonomous Agent Stack

[Simplified Chinese](README.zh-CN.md)

Autonomous Agent Stack (AAS) is an evergreen control plane for governed agent execution. It keeps durable sessions, policy, approvals, audit, runtime routing, artifacts, and promotion above replaceable agent frameworks such as OpenHands, Hermes, OpenClaw, CrewAI, LangGraph, Haystack, MCP, and A2A.

[![CI](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-Drafts-orange)](docs/rfc/)

## Current Status

AAS has passed the Evergreen OS GA v1.0 blocking evidence gates in this checkout. `/api/v2/*` is the active development surface; `/api/v1/*` remains for compatibility while integrations move forward.

The current stable model is:

```text
Session -> Task -> Policy/Approval -> Capability Routing -> Worker/Adapter Execution -> Audit/Event Log -> Artifact/Promotion
```

Adapters must still honestly report runtime capability, streaming, cancellation, artifacts, approval behavior, storage contracts, and isolation. Mock-only or fake-stable integrations must stay `beta` or `experimental`.

## GA Evidence

The Evergreen OS GA v1.0 result is evidence-first, not a demo claim. The committed evidence package includes:

- [GA release tag v1.0.0-evergreen-ga](https://github.com/autonomous-agent-stack/autonomous-agent-stack/releases/tag/v1.0.0-evergreen-ga): release marker for the GA evidence baseline.
- [ga_gap_report.json](ga_gap_report.json) and [ga_gap_report.md](ga_gap_report.md): GA gap report with `status: passed` and `missing_total: 0`.
- [adapter_certification_report.json](adapter_certification_report.json): adapter certification report with `status: passed` and no blocked adapters.
- [stable_adapters.lock](stable_adapters.lock): generated lock file covering all configured scoped adapters.
- [docs/certification/adapter-certification-matrix.md](docs/certification/adapter-certification-matrix.md): derived adapter certification matrix.
- [bypass_ga_report.json](bypass_ga_report.json): bypass validation report with all security checks passing.
- [furniture_e2e_report.json](furniture_e2e_report.json): furniture workflow evidence report with governed dry-run external writes.
- [ga_release_gate_report.json](ga_release_gate_report.json): blocking release gate report with GA pytest return code `0`.

External writes remain dry-run by default. Live external writes require explicit live credentials, policy decision metadata, approval, recipient allowlist, audit timeline, and session facts.

```bash
make ga-gap-report
make furniture-e2e
make bypass-ga
make ga-release-gate
```

## What AAS Is

AAS is a governed control plane for long-running agents. It answers enterprise questions that should not depend on a single model runtime:

- who can use a capability,
- what data and tools a run touched,
- which policy and approval gates applied,
- what artifact was produced,
- whether the result can be promoted,
- how the system can audit, replay, or recover the work later.

AAS does not treat any agent framework as the trusted core. Frameworks and tools are execution surfaces; the control plane owns the system record.

## Core Principles

- **Session-first state:** durable facts live outside the prompt window.
- **Patch-only default:** autonomous coding workers produce bounded patches rather than owning repository writes.
- **Deny-wins policy:** stricter constraints override permissive requests.
- **Single-writer promotion:** dangerous mutable transitions require a writer lease.
- **Runtime artifact isolation:** logs, memory, runtime state, and control debris do not enter source promotion by accident.
- **Language-separated docs:** English canonical docs use `.md`; Simplified Chinese mirrors use `.zh-CN.md`.

## Quick Start

Requirements:

- Python `3.11+`
- `make`
- SQLite for default local state
- Docker or Colima only for sandbox-backed flows

```bash
git clone https://github.com/autonomous-agent-stack/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

Common local entry points after startup:

- API docs: `http://127.0.0.1:8001/docs`
- Control Plane v2: `http://127.0.0.1:8001/control-plane`
- Admin panel: `http://127.0.0.1:8001/panel`
- Health check: `http://127.0.0.1:8001/health`
- Study Workbench Sync: `http://127.0.0.1:8001/api/v1/study-workbench/health`

## Common Validation

```bash
make test-quick
make smoke-local
make hygiene-check
make runtime-doctor
make capability-doctor
make mcp-doctor
make evergreen-demo
```

`make hygiene-check` writes prompt hygiene reports under `logs/audit/prompt_hygiene/`.

GA evidence validation:

```bash
make furniture-e2e
make bypass-ga
make ga-gap-report
make ga-release-gate
```

## Documentation

Start here:

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Study Dashboard](docs/runbooks/study-dashboard.md)
- [Study Workbench Sync MVP](docs/runbooks/study-workbench-sync.md)
- [Life Companion Personal Package](docs/runbooks/life-companion.md)
- [Why AAS](WHY_AAS.md)
- [Contributing](CONTRIBUTING.md)
- [Runtime Adapter v1](docs/runtime-adapter-v1.md)
- [Capability Manifest v1](docs/capability-manifest-v1.md)
- [Tool Proxy + MCP Host](docs/tool-proxy-mcp-host.md)
- [Federation-ready v1](docs/federation-ready-v1.md)
- [RFC index](docs/rfc/README.md)

Chinese mirrors are linked from the matching English documents when they are maintained as active docs.

## Configuration Notes

Public docs should not hard-code developer-machine paths. Use environment variables or paths relative to the checkout:

```bash
export AAS_REPO_ROOT="$PWD"
export AAS_WORKSPACE_ROOT="$AAS_REPO_ROOT/.aas/workspace"
export AAS_LOG_ROOT="$AAS_REPO_ROOT/logs"
export AAS_CACHE_ROOT="$AAS_REPO_ROOT/.cache"
```

Secrets belong in gitignored local environment files. Never commit real tokens, local credentials, or personal machine paths.

## Scope

The GA v1.0 line does not claim to provide:

- an open marketplace,
- real-money settlement,
- dynamic bidding,
- full dispute arbitration,
- unrestricted autonomous repository mutation.

The implemented boundary is governed local and bilateral execution: static peers, leases, quota, approvals, audit, artifacts, and promotion.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Architecture or governance changes should usually start with an RFC under `docs/rfc/`.
