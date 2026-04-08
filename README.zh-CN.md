# Autonomous Agent Stack

**面向自治智能体的受控基础设施栈。**

在不把仓库控制权交给 Agent 的前提下，让 OpenHands、Codex 和自定义执行器运行在零信任安全、补丁式执行、可审计执行流和显式晋升门之下。

[![CI](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/srxly888-creator/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/srxly888-creator/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20篇-orange)](docs/rfc/)

[English](README.md) | **简体中文**

---

## 它是什么

Autonomous Agent Stack（AAS）是一套面向自治执行的控制面。它把规划、隔离执行、验证和晋升拆开，避免任何单一执行器同时拥有“发现任务、修改代码、自我审批、直接发布”的完整权力链。

这个仓库不是常见的“AI agent 能直接改仓库”的演示项目，而是给想要接入 OpenHands、Codex 或自定义 Agent、同时又不愿放弃治理边界的团队准备的基础设施。在 AAS 里，这些工具是受控执行面，不是系统主脑。

当前主线聚焦于单仓库控制面、隔离执行和晋升检查；分布式执行与联邦能力放在 RFC 里持续演进。

## 为什么它不一样

| 常见 Agent 项目 | AAS |
|---|---|
| Agent 直接持有仓库写权限 | 执行器只生成有边界的补丁候选 |
| 规划、执行、合并权集中在一个运行时 | 规划器、执行器、晋升门彼此分离 |
| 验证流程可选，或者靠人工兜底 | 策略检查、测试和晋升规则属于主路径 |
| 外部工具天然变成控制面 | OpenHands、Codex、自定义 Agent 都接在受控控制面之下 |
| 运行时产物容易混进源码变更 | 运行时产物与源码晋升严格隔离 |
| 信任边界靠约定 | 零信任约束明确且可审计 |

## 核心模型

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

启动后可访问：

- API 文档：`http://127.0.0.1:8001/docs`
- 管理面板：`http://127.0.0.1:8001/panel`
- 健康检查：`http://127.0.0.1:8001/health`

本地验证：

```bash
make test-quick
make hygiene-check
```

如果你需要更完整的安装与排障说明，请看 [docs/QUICK_START.md](docs/QUICK_START.md)。如果要继续到远端或多机执行，先读 [docs/linux-remote-worker.md](docs/linux-remote-worker.md)。

## 受控集成方式

AAS 的目标不是替代各种执行运行时，而是在不放弃治理能力的前提下接入它们：

- 把 OpenHands 作为受补丁式合约和晋升门约束的执行器
- 通过 controlled execution 与 AEP 风格任务契约接入 Codex 和自定义适配器
- 用远端执行器承接机器特定能力、身份凭据或隔离执行面
- 把 GitHub 触发、聊天入口等统一收口回同一条控制面主路径

相关文档见 [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md)、[docs/agent-execution-protocol.md](docs/agent-execution-protocol.md) 和 [docs/linux-remote-worker.md](docs/linux-remote-worker.md)。

## 文档导航

先读这些：

- [WHY_AAS.zh-CN.md](WHY_AAS.zh-CN.md)：项目动机与方向
- [docs/QUICK_START.md](docs/QUICK_START.md)：详细启动与排障
- [CONTRIBUTING.md](CONTRIBUTING.md)：贡献流程与协作约定

想深入理解：

- [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)：当前架构中文导读
- [docs/agent-execution-protocol.md](docs/agent-execution-protocol.md)：执行契约与策略模型
- [docs/api-reference.md](docs/api-reference.md)：API 参考

想看集成与演进：

- [docs/openhands-cli-integration.md](docs/openhands-cli-integration.md)：把 OpenHands 接成受控 worker
- [docs/github-assistant-quickstart.md](docs/github-assistant-quickstart.md)：GitHub 助手用法
- [docs/rfc/README.zh-CN.md](docs/rfc/README.zh-CN.md)：RFC 索引与流程

## 路线图

- 当前：继续加固单仓库控制面、隔离执行链路与晋升检查。
- 下一步：引入持久队列、租约、心跳和身份绑定执行器，推进分布式执行。见 [docs/rfc/distributed-execution.md](docs/rfc/distributed-execution.md)。
- 后续：把 Linux 与 Mac 执行面扩展为异构执行池。见 [docs/rfc/three-machine-architecture.md](docs/rfc/three-machine-architecture.md)。
- 长期：在可治理前提下推进 AAS 实例之间的分层互信联邦。见 [docs/rfc/federation-protocol.md](docs/rfc/federation-protocol.md)。

## 贡献入口

如果你准备参与贡献，建议先读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)。文档修正和聚焦的 bug fix 很适合作为第一步；涉及系统边界、执行模型或治理策略的改动，建议先走 [docs/rfc/](docs/rfc/)。

本地常用检查流程：

```bash
make test-quick
make hygiene-check
make review-gates-local
```

如果你还不确定设计方向是否合适，先开 issue 或讨论帖再实现。

## 许可证

[MIT](LICENSE)
