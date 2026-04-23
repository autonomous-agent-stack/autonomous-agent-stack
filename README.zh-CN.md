# Autonomous Agent Stack

**面向长时运行 Agent 的、受治理且以 session 为中心的控制面。**

在不把仓库控制权交给单一运行时的前提下，让各类 coding agent 运行在零信任执行、可恢复会话历史、隔离能力面和显式晋升门之下。

[![CI](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20篇-orange)](docs/rfc/)

[English](README.md) | **简体中文**

---

## 它是什么

Autonomous Agent Stack（AAS）是一套面向长时运行 Agent 的受治理控制面。

它把 durable session history、execution capabilities、orchestration policies 和 promotion authority 拆开，避免任何单一模型运行时同时拥有“发现任务、修改代码、自我审批、直接发布”的完整权力链。

AAS 不是常见的“AI agent 直接改仓库”的演示项目，而是给想接入 OpenHands、Codex 或自定义 Agent、同时又不愿放弃治理边界的团队准备的基础设施。在 AAS 里，这些工具是 execution surfaces，不是 system of record。

今天，AAS 先聚焦在一个高价值垂直场景上：**受治理的仓库改动**。更长期看，同一套 control-plane 抽象会继续扩展到跨异构 runtime、工具和环境的更广义 agent work。

AAS 正在向一种更像 Agent OS 的控制层演进，但当前首先是一个受治理的 long-running agent control plane。

随着生态发展，agent 的分发形态确实可能越来越像 app，可以被安装、卸载、启用和禁用。但那更接近分发层；AAS 更关心的是它下面的系统层：session、capability、policy 和 promotion。

到了联邦场景里，agent 又不只是 app-like package。它们也更像可被外派的工人：有边界、有租约、可审计、可召回，并且要跨信任边界执行。capability 更像应用，agent 更像执行者，而 AAS 是同时治理这两者的 control plane。

## 为什么这很重要

当 Agent 开始承担跨多个 context windows 的工作时，难题已经不只是“模型会不会写代码”。

真正的难题是：

- 系统能不能在多个 session 之间保持进展？
- 失败或交接之后，能不能恢复状态？
- 能不能隔离能力边界，而不是让某个 runtime 变成 trusted core？
- 能不能把高权限变更做成显式晋升，而不是隐式发生？

很多 agent stack 会把模型今天的短板写成永久架构。AAS 反过来做：尽量把系统抽象做稳，把 harness 保持为可替换层。

## 核心模型

```text
Session -> policy -> isolated capability -> validation -> promotion
```

当前落地重点仍然是：

```text
规划器 -> 隔离执行器 -> 验证门 -> 晋升门 -> 补丁产物 / 草稿合并请求
```

核心约束：

- 默认补丁式执行
- 更严格规则优先
- 可变状态采用单写者晋升
- 运行时产物不进入源码晋升
- 升级为草稿合并请求之前必须满足干净基线

更深入的实现细节放在 [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)，架构演进与边界讨论放在 [docs/rfc/README.zh-CN.md](docs/rfc/README.zh-CN.md)。

## 稳定抽象

### Session

可恢复的执行历史，而不是上下文窗口的镜像。

### Capability

把 sandbox、remote worker、MCP server、browser、git proxy 都视为隔离的 hands。

### Policy

可替换的编排规则，用于上下文组装、重试、评估、升级和路由。

### Promotion

任何高权限变更都必须经过显式且可审计的状态晋升。

## AAS 有什么不同

| 常见 Agent Stack | AAS |
|---|---|
| Agent 直接持有仓库写权限 | 执行器只生成有边界的补丁候选 |
| 规划、执行、合并权集中在一个运行时 | policy、执行和晋升彼此分离 |
| 验证流程可选，或者靠人工兜底 | 验证和晋升规则属于主路径 |
| 外部工具天然变成控制面 | 工具接在受治理的控制面之下 |
| 运行时产物容易混进源码变更 | 运行时产物与源码晋升严格隔离 |
| 信任边界靠约定 | 零信任约束明确且可审计 |

## 设计原则

- 不把模型暂时性的短板固化成永久系统架构。
- 不让任何单一 runtime 成为 trusted core。
- 不把安全建立在“模型应该没那么聪明”上。
- 保持 orchestration 可替换。
- 保持高权限变更显式可见。
- 把可恢复历史放在 context window 之外。

## 快速开始

环境要求：

- Python 3.11+
- `make`
- Docker 或 Colima，用于 `ai-lab` 和依赖沙箱的流程；仅本地启动基础服务时不是必需项

```bash
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

环境变量：`make setup` 若发现没有 `.env`，会从 [`.env.example`](.env.example) 复制生成；敏感项请放在 `.env.local`（已 gitignore），勿提交真实 token。  
Environment: if `.env` is missing, `make setup` copies from `.env.example`. Put secrets in gitignored `.env.local`; never commit real tokens.

启动后可访问：

- API 文档：`http://127.0.0.1:8001/docs`
- 管理面板：`http://127.0.0.1:8001/panel`
- 健康检查：`http://127.0.0.1:8001/health`

本地验证：

```bash
make test-quick
make hygiene-check
```

如果你需要更完整的安装与排障说明，请看 [docs/QUICK_START.md](docs/QUICK_START.md)。如果要在单机版 AAS 上开启基于 APScheduler 的 `once` / `interval` 定时任务，请读 [docs/runbooks/worker-schedules.md](docs/runbooks/worker-schedules.md)。如果要继续到远端或多机执行，先读 [docs/linux-remote-worker.zh-CN.md](docs/linux-remote-worker.zh-CN.md)。如果你要在 Windows 上通过 WSL2 跑 Hermes，再由底座接管，先读 [docs/windows-wsl2-hermes-control-plane.md](docs/windows-wsl2-hermes-control-plane.md)。

当前 Windows 原生支持只覆盖最小本地主链：`make setup`、`make doctor`、`make start`。仓库中的其他 target 仍然大量依赖 Bash 和 macOS/Linux 工具，不应默认视为 Windows 已支持。

## 受控集成方式

AAS 的目标不是替代各种执行运行时，而是在不放弃治理能力的前提下接入它们：

- 把 OpenHands 作为受补丁式合约和晋升门约束的执行器
- 通过 controlled execution 与 AEP 风格任务契约接入 Codex 和自定义适配器
- 用远端执行器承接机器特定能力、身份凭据或隔离执行面
- 把 GitHub 触发、聊天入口等统一收口回同一条控制面主路径

相关文档见 [docs/openhands-cli-integration.zh-CN.md](docs/openhands-cli-integration.zh-CN.md)、[docs/agent-execution-protocol.zh-CN.md](docs/agent-execution-protocol.zh-CN.md) 和 [docs/linux-remote-worker.zh-CN.md](docs/linux-remote-worker.zh-CN.md)。

## 文档导航

先读这些：

- [WHY_AAS.zh-CN.md](WHY_AAS.zh-CN.md)：项目动机与方向
- [docs/QUICK_START.md](docs/QUICK_START.md)：详细启动与排障
- [CONTRIBUTING.md](CONTRIBUTING.md)：贡献流程与协作约定

想深入理解：

- [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)：当前架构中文导读
- [docs/agent-execution-protocol.zh-CN.md](docs/agent-execution-protocol.zh-CN.md)：执行契约与策略模型
- [docs/api-reference.md](docs/api-reference.md)：API 参考

想看集成与演进：

- [docs/openhands-cli-integration.zh-CN.md](docs/openhands-cli-integration.zh-CN.md)：把 OpenHands 接成受控 worker
- [docs/github-assistant-quickstart.zh-CN.md](docs/github-assistant-quickstart.zh-CN.md)：GitHub 助手用法
- [docs/rfc/README.zh-CN.md](docs/rfc/README.zh-CN.md)：RFC 索引与流程

## 路线图

### 当前

继续加固单仓库控制面、隔离执行链路与晋升检查。

### 下一步

- session-first 的恢复与 replay
- 面向异构 worker 与工具的 capability registry
- 面向 orchestration 的 policy seams
- 基于 durable queue、lease、heartbeat 的 distributed execution

### 长期

把 AAS 演进成一个面向多模型、多 hands、多信任边界的 governed runtime substrate。

## 适合谁

AAS 适合这样的团队：

- 想要自治执行，但不想交出仓库控制权
- 想要长任务的可恢复进展
- 想要零信任安全边界
- 想要可审计的晋升工作流
- 想要多 runtime 互操作，但不想失去控制

## 贡献入口

如果你准备参与贡献，建议先读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)。文档修正和聚焦的 bug fix 很适合作为第一步；涉及系统边界、执行模型或治理策略的改动，建议先走 [docs/rfc/](docs/rfc/)。

本地常用检查流程：

```bash
make review-setup
make test-quick
make hygiene-check
make review-gates-local
```

`make review-setup` 会把 mypy、bandit、semgrep 装到独立的 `.venv-review`，避免把
review 工具依赖混进主链路 `.venv`。

如果你还不确定设计方向是否合适，先开 issue 或讨论帖再实现。

## 许可证

[MIT](LICENSE)
