# Autonomous Agent Stack

**A governed, session-centered control plane for long-running agents.**

Run coding agents under zero-trust execution, durable session history, isolated capabilities, and explicit promotion gates instead of handing repository ownership to a single runtime.

[![CI](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20Draft-orange)](docs/rfc/)

**English** | [简体中文](README.zh-CN.md)

---

## What AAS Is

Autonomous Agent Stack (AAS) is a governed control plane for long-running agent execution.

It separates durable session history, execution capabilities, orchestration policies, and promotion authority so that no single model runtime gets to discover work, edit code, approve its own output, and publish it.

AAS is not a generic AI agent demo. It is built for teams that want to integrate tools such as OpenHands, Codex, or custom agents without collapsing trust boundaries. In AAS, those tools are execution surfaces, not the system of record.

Today, AAS is focused on a high-value vertical: governed repository changes. Long term, the same control-plane model is intended to support broader agent work across heterogeneous runtimes, tools, and environments.

## Why This Matters

As agents take on work that spans many context windows, the hard problem is no longer just "can the model code?"

The hard problem is:

- Can the system preserve progress across sessions?
- Can it recover state after failure or handoff?
- Can it isolate capabilities without making one runtime the trusted core?
- Can it promote privileged changes explicitly instead of implicitly?

Most agent stacks hard-code temporary model limitations into permanent architecture. AAS takes the opposite approach: keep the system abstractions stable, and keep the harness replaceable.

## Core Model

```text
Session -> policy -> isolated capability -> validation -> promotion
```

Current implementation focus:

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

## Stable Abstractions

### Session

A durable execution history, not a mirror of the context window.

### Capability

Sandboxes, remote workers, MCP servers, browsers, and git proxies treated as isolated hands.

### Policy

Replaceable orchestration rules for context assembly, retries, evaluation, escalation, and routing.

### Promotion

Explicit, auditable state transitions for any privileged change.

## What Makes AAS Different

| Traditional agent stack | AAS |
|---|---|
| Agent gets repository write authority | Worker produces a bounded patch candidate |
| Planning, execution, and merge authority live in one runtime | Policy, execution, and promotion are separated |
| Validation is optional or ad hoc | Validation and promotion rules are on the main path |
| External tools become the de facto control plane | Tools plug into a governed control plane |
| Runtime state leaks into source changes | Runtime artifacts and source promotion are isolated |
| Trust is implicit | Zero-trust invariants are explicit and auditable |

## Design Principles

- Do not turn temporary model weaknesses into permanent system architecture.
- Do not let a single runtime become the trusted core.
- Do not rely on the model being "not clever enough" for security.
- Keep orchestration replaceable.
- Keep privileged changes explicit.
- Preserve recoverable history outside the context window.

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

### Now

A stable single-repo control plane with isolated execution and promotion checks.

### Next

- Session-first recovery and replay
- Capability registry for heterogeneous workers and tools
- Policy seams for orchestration strategies
- Distributed execution with durable queues, leases, and heartbeats

### Long Term

A governed runtime substrate for long-running agent work across multiple models, multiple hands, and multiple trust boundaries.

## Who This Is For

AAS is for teams that want:

- autonomous execution without repository ownership
- durable progress across long-running tasks
- zero-trust safety boundaries
- auditable promotion workflows
- multi-runtime interoperability without surrendering control

## Contributing

If you want to contribute, start with [CONTRIBUTING.md](CONTRIBUTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Small documentation fixes and focused bug fixes are good first contributions. Architectural changes should start as an RFC in [docs/rfc/](docs/rfc/).

A typical local loop is:

```bash
make review-setup
make test-quick
make hygiene-check
make review-gates-local
```

`make review-setup` installs mypy, bandit, and semgrep into `.venv-review` so the
main `.venv` can stay aligned with `make setup`.

Open an issue or discussion if you want to validate a design direction before implementation.

## License

[MIT](LICENSE)
