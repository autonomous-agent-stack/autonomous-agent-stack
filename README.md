# Autonomous Agent Stack

**A governed infrastructure stack for autonomous agents.**

Run AI coding agents under zero-trust safety, patch-only execution, auditable control flow, and explicit promotion gates instead of handing them repository ownership.

[![CI](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20Draft-orange)](docs/rfc/)

**English** | [简体中文](README.zh-CN.md)

---

## What AAS Is

Autonomous Agent Stack (AAS) is a control plane for autonomous agent execution. It separates planning, isolated work, validation, and promotion so that no single agent runtime gets to discover work, edit code, approve its own output, and publish it.

This repository is not a generic "AI agent demo." It is built for teams that want to integrate tools such as OpenHands, Codex, or custom agents without collapsing trust boundaries. In AAS, those tools are execution surfaces, not the system of record.

Current focus: a stable single-repo control plane with isolated execution and promotion checks, with distributed execution and federation evolving through RFCs.

## Why It Is Different

| Traditional agent project | AAS |
|---|---|
| Agent gets repository write authority | Worker produces a bounded patch candidate |
| Planning, execution, and merge authority live in one runtime | Planner, worker, and promotion gate are separate |
| Validation is optional or ad hoc | Policy checks, tests, and promotion rules are part of the main path |
| External tools become the de facto control plane | OpenHands, Codex, and custom agents plug into a governed control plane |
| Runtime state can leak into source changes | Runtime artifacts and source promotion are isolated |
| Trust is implicit | Zero-trust invariants are explicit and auditable |

## Core Model

```text
Planner -> isolated worker -> validation gate -> promotion gate -> patch artifact or draft PR
```

Core invariants:

- Patch-only by default
- Deny-wins policy merging
- Single-writer promotion for mutable state
- Runtime artifacts never promote into source
- Clean-base checks before draft PR promotion

Deep implementation details live in [ARCHITECTURE.md](ARCHITECTURE.md) and the RFC index in [docs/rfc/README.en.md](docs/rfc/README.en.md).

## Quick Start

Requirements:

- Python 3.11+
- `make`
- Docker or Colima for `ai-lab` and sandbox-backed flows (optional for basic local startup)

```bash
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

Open after startup:

- API docs: `http://127.0.0.1:8001/docs`
- Admin panel: `http://127.0.0.1:8001/panel`
- Health check: `http://127.0.0.1:8001/health`

Validate the local setup:

```bash
make test-quick
make hygiene-check
```

For detailed setup and troubleshooting, read [docs/QUICK_START.md](docs/QUICK_START.md). For remote or multi-machine execution, start with [docs/linux-remote-worker.md](docs/linux-remote-worker.md).

## Controlled Integrations

AAS is designed to integrate agent runtimes without turning them into the trusted core:

- OpenHands as a constrained worker behind patch-only contracts and promotion gates
- Codex and custom adapters through controlled execution and AEP-style job specs
- Remote workers for machine-specific capabilities, credentials, or isolated execution surfaces
- GitHub and chat-triggered workflows routed back into the same control plane

See [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md), [docs/agent-execution-protocol.md](docs/agent-execution-protocol.md), and [docs/linux-remote-worker.md](docs/linux-remote-worker.md).

## Documentation

Start here:

- [WHY_AAS.md](WHY_AAS.md): project motivation and design direction
- [docs/QUICK_START.md](docs/QUICK_START.md): detailed setup and troubleshooting
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution workflow and expectations

Go deeper:

- [ARCHITECTURE.md](ARCHITECTURE.md): canonical current architecture
- [docs/agent-execution-protocol.md](docs/agent-execution-protocol.md): execution contract and policy model
- [docs/api-reference.md](docs/api-reference.md): API surface

Explore integrations and evolution:

- [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md): OpenHands as a controlled worker
- [docs/github-assistant-quickstart.md](docs/github-assistant-quickstart.md): GitHub assistant flows
- [docs/rfc/README.en.md](docs/rfc/README.en.md): RFC index and design process

## Roadmap

- Now: harden the single-repo control plane, isolated execution flow, and promotion checks.
- Next: distributed execution with durable queues, leases, heartbeats, and credential-bound workers. See [docs/rfc/distributed-execution.md](docs/rfc/distributed-execution.md).
- Later: heterogeneous worker pools across Linux and Mac surfaces. See [docs/rfc/three-machine-architecture.md](docs/rfc/three-machine-architecture.md).
- Long term: federation between governed AAS instances with layered trust. See [docs/rfc/federation-protocol.md](docs/rfc/federation-protocol.md).

## Contributing

If you want to contribute, start with [CONTRIBUTING.md](CONTRIBUTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Small documentation fixes and focused bug fixes are good first contributions. Architectural changes should start as an RFC in [docs/rfc/](docs/rfc/).

A typical local loop is:

```bash
make test-quick
make hygiene-check
make review-gates-local
```

Open an issue or discussion if you want to validate a design direction before implementation.

## License

[MIT](LICENSE)
