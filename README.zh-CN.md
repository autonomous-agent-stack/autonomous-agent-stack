# Autonomous Agent Stack

[English](README.md)

Autonomous Agent Stack（AAS）是一套面向受治理 Agent 执行的 evergreen control plane。它把 durable session、policy、approval、audit、runtime routing、artifact 和 promotion 放在 OpenHands、Hermes、OpenClaw、CrewAI、LangGraph、Haystack、MCP、A2A 等可替换执行框架之上。

[![CI](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-Drafts-orange)](docs/rfc/)

## 当前状态

AAS 已在当前 checkout 通过 Evergreen OS GA v1.0 阻断性证据门禁。`/api/v2/*` 是当前开发面；`/api/v1/*` 只作为兼容面保留，等待集成逐步迁移。

当前稳定模型是：

```text
Session -> Task -> Policy/Approval -> Capability Routing -> Worker/Adapter Execution -> Audit/Event Log -> Artifact/Promotion
```

GA 结果以证据为准，不靠 demo 声称成熟：

- `ga_gap_report.json` 报告 `status: passed` 且 `missing_total: 0`。
- `adapter_certification_report.json` 报告 `status: passed` 且没有 blocked adapters。
- `stable_adapters.lock` 覆盖全部 configured scoped adapters。
- `ga_release_gate_report.json` 报告 `status: passed` 且 GA pytest 返回码为 `0`。

adapter 仍必须真实报告 runtime capability、streaming、cancellation、artifact、approval behavior、storage contract 和 isolation。mock-only 或 fake-stable 集成只能保持 `beta` 或 `experimental`。

```bash
make ga-gap-report
make furniture-e2e
make bypass-ga
make ga-release-gate
```

## AAS 是什么

AAS 是面向长时运行 Agent 的受治理控制面。它回答不应绑定在单一模型 runtime 上的企业问题：

- 谁可以使用某项 capability，
- 一次 run 接触了哪些数据和工具，
- 哪些 policy 与 approval gate 生效，
- 产出了什么 artifact，
- 结果能否被 promotion，
- 系统之后如何 audit、replay 或 recover 这项工作。

AAS 不把任一 Agent 框架当成 trusted core。框架和工具是执行面，控制面才是系统事实源。

## 核心原则

- **Session-first state：** 持久事实存在于 prompt window 之外。
- **Patch-only default：** 自治 coding worker 产出有边界的 patch，而不是拥有仓库写权限。
- **Deny-wins policy：** 更严格约束覆盖宽松请求。
- **Single-writer promotion：** 危险可变状态转换必须取得 writer lease。
- **Runtime artifact isolation：** log、memory、runtime state 和 control debris 不会意外进入源码晋升。
- **语言分文件：** 英文 canonical docs 使用 `.md`；简体中文镜像使用 `.zh-CN.md`。

## 快速开始

环境要求：

- Python `3.11+`
- `make`
- 默认本地状态使用 SQLite
- Docker 或 Colima 只在沙箱相关流程中需要

```bash
git clone https://github.com/autonomous-agent-stack/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

启动后的常用本地入口：

- API docs：`http://127.0.0.1:8001/docs`
- Control Plane v2：`http://127.0.0.1:8001/control-plane`
- Admin panel：`http://127.0.0.1:8001/panel`
- Health check：`http://127.0.0.1:8001/health`

## 常用验证

```bash
make test-quick
make smoke-local
make hygiene-check
make runtime-doctor
make capability-doctor
make mcp-doctor
make evergreen-demo
```

`make hygiene-check` 会把 prompt hygiene 报告写到 `logs/audit/prompt_hygiene/`。

GA 证据验证：

```bash
make furniture-e2e
make bypass-ga
make ga-gap-report
make ga-release-gate
```

## 文档

先读这些：

- [文档索引](docs/README.zh-CN.md)
- [架构](docs/architecture.zh-CN.md)
- [为什么选择 AAS](WHY_AAS.zh-CN.md)
- [贡献指南](CONTRIBUTING.zh-CN.md)
- [Runtime Adapter v1](docs/runtime-adapter-v1.md)
- [Capability Manifest v1](docs/capability-manifest-v1.md)
- [Tool Proxy + MCP Host](docs/tool-proxy-mcp-host.md)
- [Federation-ready v1](docs/federation-ready-v1.md)
- [RFC 索引](docs/rfc/README.zh-CN.md)

当前维护的中文镜像会从对应英文文档顶部链接。

## 配置说明

公开文档不应写死开发机器路径。请使用环境变量或 checkout 相对路径：

```bash
export AAS_REPO_ROOT="$PWD"
export AAS_WORKSPACE_ROOT="$AAS_REPO_ROOT/.aas/workspace"
export AAS_LOG_ROOT="$AAS_REPO_ROOT/logs"
export AAS_CACHE_ROOT="$AAS_REPO_ROOT/.cache"
```

密钥应放在已被 gitignore 的本地环境文件中。不要提交真实 token、本地凭证或个人机器路径。

## 范围边界

GA v1.0 主线不声称提供：

- 开放市场，
- 真实资金结算，
- 动态竞价，
- 完整争议仲裁，
- 无约束自治仓库变更。

当前实现边界是受治理的本地与双边执行：static peers、leases、quota、approvals、audit、artifacts 和 promotion。

## 贡献

提交 pull request 前请先读 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。架构或治理改动通常应先在 `docs/rfc/` 下走 RFC。
