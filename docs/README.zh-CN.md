# 文档

[English](README.md)

这是 Autonomous Agent Stack 当前维护的文档索引。英文文档默认是 canonical；简体中文镜像使用 `.zh-CN.md`。

历史报告和旧 checklist 保存在 `docs/archive/**`，不再作为当前架构事实源。

## 从这里开始

- [项目 README](../README.zh-CN.md)
- [架构](architecture.zh-CN.md)
- [项目健康](project-health.zh-CN.md)
- [为什么选择 AAS](../WHY_AAS.zh-CN.md)
- [贡献指南](../CONTRIBUTING.zh-CN.md)
- [任务简报指南](task-brief-guide.md)

## 当前控制面

- [Evergreen Agent Control Plane](evergreen-agent-control-plane.md)
- [Runtime Adapter v1](runtime-adapter-v1.md)
- [Capability Manifest v1](capability-manifest-v1.md)
- [Tool Proxy + MCP Host](tool-proxy-mcp-host.md)
- [Federation-ready v1](federation-ready-v1.md)
- [Runtime Isolation](runtime-isolation.md)
- [GA Definition](ga-definition.md)
- [GA Prohibitions](ga-prohibitions.md)
- [Adapter Certification Matrix](certification/adapter-certification-matrix.md)

## 运维

- [Control Plane v2 smoke runbook](runbooks/control-plane-v2-smoke.md)
- [Butler governance runbook](runbooks/butler-governance.md)
- [Session Spine v1 runbook](runbooks/session-spine-v1.md)
- [Worker schedules](runbooks/worker-schedules.md)
- [Mac standby worker smoke](runbooks/mac-standby-worker-smoke.md)
- [Linux remote worker](linux-remote-worker.zh-CN.md)
- [Windows + WSL2 Hermes control plane](windows-wsl2-hermes-control-plane.md)

## 集成

- [OpenHands CLI integration](openhands-cli-integration.zh-CN.md)
- [OpenClaw runtime adapter](openclaw-runtime-adapter.md)
- [Hermes runtime v1](hermes-runtime-v1.md)
- [GitHub assistant quickstart](github-assistant-quickstart.zh-CN.md)
- [GitHub assistant safety](github-assistant-safety.md)
- [cc-switch usage](cc-switch-usage.md)

## 设计记录

- [RFC 索引](rfc/README.zh-CN.md)
- [Distributed control plane architecture](decisions/distributed-control-plane-architecture-v1.md)
- [Fast policy router and slow orchestration](decisions/fast-policy-router-and-slow-orchestration-v1.md)
- [Deterministic job best practice](decisions/deterministic-job-best-practice-v1.md)

## 归档

- [根目录旧文档](archive/legacy-root/README.md)
- [根目录旧规格](specs/legacy-root/README.md)
- [审计报告](archive/audit_reports/)

## 维护规则

- 活跃文档避免开发机器绝对路径。
- 活跃文档不要使用同页中英混排块。
- 有维护中中文镜像的活跃文档应同步更新双语文件。
- 旧报告应归档，而不是继续堆在仓库根目录。
