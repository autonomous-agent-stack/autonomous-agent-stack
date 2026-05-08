# Documentation

[Simplified Chinese](README.zh-CN.md)

This is the maintained documentation index for Autonomous Agent Stack. English docs are canonical by default; Simplified Chinese mirrors use `.zh-CN.md`.

Historical reports and old checklists are preserved under `docs/archive/**` and are not active architecture sources.

## Start Here

- [Project README](../README.md)
- [Architecture](architecture.md)
- [Project health](project-health.md)
- [Why AAS](../WHY_AAS.md)
- [Contributing](../CONTRIBUTING.md)
- [Task brief guide](task-brief-guide.md)

## Current Control Plane

- [Evergreen Agent Control Plane](evergreen-agent-control-plane.md)
- [Runtime Adapter v1](runtime-adapter-v1.md)
- [Capability Manifest v1](capability-manifest-v1.md)
- [Tool Proxy + MCP Host](tool-proxy-mcp-host.md)
- [Federation-ready v1](federation-ready-v1.md)
- [Runtime Isolation](runtime-isolation.md)
- [GA Definition](ga-definition.md)
- [GA Prohibitions](ga-prohibitions.md)
- [Adapter Certification Matrix](certification/adapter-certification-matrix.md)

## Operations

- [Control Plane v2 smoke runbook](runbooks/control-plane-v2-smoke.md)
- [Butler governance runbook](runbooks/butler-governance.md)
- [Session Spine v1 runbook](runbooks/session-spine-v1.md)
- [Worker schedules](runbooks/worker-schedules.md)
- [Study Dashboard](runbooks/study-dashboard.md)
- [Mac standby worker smoke](runbooks/mac-standby-worker-smoke.md)
- [Linux remote worker](linux-remote-worker.md)
- [Windows + WSL2 Hermes control plane](windows-wsl2-hermes-control-plane.md)

## Integrations

- [OpenHands CLI integration](openhands-cli-integration.md)
- [OpenClaw runtime adapter](openclaw-runtime-adapter.md)
- [Hermes runtime v1](hermes-runtime-v1.md)
- [GitHub assistant quickstart](github-assistant-quickstart.md)
- [GitHub assistant safety](github-assistant-safety.md)
- [cc-switch usage](cc-switch-usage.md)

## Design Records

- [RFC index](rfc/README.md)
- [Enterprise runtime governance blueprint](rfc/enterprise-runtime-governance-blueprint.md)
- [Distributed control plane architecture](decisions/distributed-control-plane-architecture-v1.md)
- [Fast policy router and slow orchestration](decisions/fast-policy-router-and-slow-orchestration-v1.md)
- [Deterministic job best practice](decisions/deterministic-job-best-practice-v1.md)

## Archives

- [Legacy root documents](archive/legacy-root/README.md)
- [Legacy root specs](specs/legacy-root/README.md)
- [Audit reports](archive/audit_reports/)

## Maintenance Rules

- Active docs should avoid developer-machine absolute paths.
- Active docs should not use inline bilingual blocks.
- When an active doc has a maintained Chinese mirror, update both files together.
- Archive old reports instead of keeping them in the repository root.
