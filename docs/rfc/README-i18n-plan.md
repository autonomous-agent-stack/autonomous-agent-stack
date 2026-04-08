# README 中英双语重构方案

## 设计原则

1. **英文主入口**：README.md 面向全球开源社区
2. **中文独立版**：README.zh-CN.md 面向中文社区
3. **分离不混排**：避免文档臃肿，阅读体验更好
4. **专业技术表达**：减少口号感，增强可信度
5. **情绪入口**：除了架构正确，还要回答"为什么要加入"

---

## 首页标题与副标题

### 英文版

```markdown
# Autonomous Agent Stack

**Build trustworthy agent infrastructure across machines, identities, and organizations.**
```

### 中文版

```markdown
# Autonomous Agent Stack

**跨机器、跨身份、跨组织，构建可信的自治智能体协作底座。**
```

---

## 一句话价值主张

### 英文版

> A governed infrastructure stack for autonomous agents, focused on zero-trust safety, controlled execution, and auditable collaboration.

### 中文版

> 面向自治智能体的受控基础设施栈，强调零信任、受控执行与可治理协作。

---

## 目录结构

```
autonomous-agent-stack/
├── README.md                    # 英文主入口
├── README.zh-CN.md              # 中文完整版
├── CONTRIBUTING.md              # 英文贡献指南
├── CONTRIBUTING.zh-CN.md        # 中文贡献指南
├── WHY_AAS.md                   # 为什么要做 AAS（英文）
├── WHY_AAS.zh-CN.md             # 为什么要做 AAS（中文）
├── docs/
│   ├── rfc/
│   │   ├── README.md            # RFC 索引（英文）
│   │   ├── README.zh-CN.md      # RFC 索引（中文）
│   │   ├── distributed-execution.md
│   │   ├── three-machine-architecture.md
│   │   ├── federation-protocol.md
│   │   └── federation-market-model.md
│   │   # RFC 正文暂时保持英文，顶部加 English Summary
│   └── ...
└── ...
```

---

## README.md 开头样稿（英文）

```markdown
# Autonomous Agent Stack

**Build trustworthy agent infrastructure across machines, identities, and organizations.**

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/srxly888-creator/autonomous-agent-stack/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![RFC](https://img.shields.io/badge/RFC-4%20Draft-orange)](docs/rfc/)

---

## Why AAS?

Most AI agent projects give agents direct access to codebases. **This is dangerous.**

AAS takes a different approach:

| Traditional Agents | AAS |
|-------------------|-----|
| Agent can `git push` directly | Agent only produces patches |
| Agent owns repository write access | Controlled execution + validation + approval |
| Single-point execution, hard to scale | Control plane / worker separation |
| State scattered everywhere | SQLite authoritative control plane |
| Security boundaries fuzzy | Zero-trust invariants: patch-only, deny-wins, single-writer |

## What Makes AAS Different

### Zero-Trust Architecture

- **Brain and Hand Separation**: Planning and execution are independent from promotion
- **Patch-Only Default**: Workers can only edit files, never `git commit`/`push`
- **Deny-Wins Policy**: Stricter constraints always win
- **Single Writer Lease**: Mutable operations require global lock
- **Runtime Artifact Isolation**: `logs/` and runtime folders never enter source patches

### Real-World Usage

AAS is currently used for:

- **GitHub Repository Automation**: Triage, analyze, and manage issues and PRs
- **Remote Worker Orchestration**: Linux control plane + Mac execution nodes
- **Multi-Agent Coordination**: Planner → Worker → Validator → Promoter pipeline
- **Telegram Integration**: Trigger and monitor tasks via chat

## Quick Start

```bash
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack
make setup
make doctor
make start
```

Visit http://127.0.0.1:8001/docs for API documentation.

## Roadmap

- **Phase 1 ✅**: Single-machine control plane + isolated execution
- **Phase 2 🚧**: Distributed execution (Linux + Mac workers)
- **Phase 3 📋**: Multi-machine heterogeneous pools
- **Phase 4 📋**: Federation network with layered trust

## Get Involved

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Good first issues**: [Filter by label](https://github.com/srxly888-creator/autonomous-agent-stack/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

**Architecture discussions**: [Check RFCs](docs/rfc/)

---

*README.md continues with standard sections: Features, Installation, Documentation, License, etc.*
```

---

## README.zh-CN.md 开头样稿（中文）

```markdown
# Autonomous Agent Stack

**跨机器、跨身份、跨组织，构建可信的自治智能体协作底座。**

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/srxly888-creator/autonomous-agent-stack/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![RFC](https://img.shields.io/badge/RFC-4%20篇-orange)](docs/rfc/)

[English](README.md) | 简体中文

---

## 为什么选择 AAS？

大多数 AI Agent 项目让智能体直接操作代码库——**这很危险**。

AAS 采用不同的架构哲学：

| 传统 Agent 项目 | AAS |
|----------------|-----|
| Agent 可直接 `git push` | Agent 只产出 patch |
| Agent 拥有仓库写权限 | 受控执行 + 验证 + 审批 |
| 单点执行，难以扩展 | Control Plane / Worker 分离 |
| 状态散落各处 | SQLite 权威控制面 |
| 安全边界模糊 | 零信任原则：patch-only、deny-wins、单写锁 |

## AAS 的核心差异

### 零信任架构

- **脑手分离**：规划与执行独立，promotion gate 拥有最终决策权
- **Patch-Only 默认**：Worker 只能编辑文件，禁止 `git commit`/`push`
- **Deny-Wins 策略**：限制条件取更严格者
- **Single Writer Lease**：可变状态操作需要全局锁
- **Runtime Artifact 隔离**：运行时产物永不进入源代码

### 实际应用场景

AAS 目前用于：

- **GitHub 仓库自动化**：分类、分析和管理 issues 与 PR
- **远程 Worker 编排**：Linux 控制面 + Mac 执行节点
- **多智能体协作**：Planner → Worker → Validator → Promoter 流水线
- **Telegram 集成**：通过聊天触发和监控任务

## 快速上手

```bash
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack
make setup
make doctor
make start
```

启动后访问 http://127.0.0.1:8001/docs 查看 API 文档。

## 发展路线

- **Phase 1 ✅**：单机 control plane + 隔离执行
- **Phase 2 🚧**：分布式执行（Linux + Mac workers）
- **Phase 3 📋**：多机异构执行池
- **Phase 4 📋**：分层互信联邦网络

## 参与贡献

我们欢迎各种形式的贡献！详见 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

**新手友好任务**：[按标签筛选](https://github.com/srxly888-creator/autonomous-agent-stack/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

**架构讨论**：查看 [RFC 文档](docs/rfc/)

---

*README.zh-CN.md continues with standard sections translated to Chinese*
```

---

## WHY_AAS.md 样稿（英文）

```markdown
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
```

---

## 风格对照表

| 避免 | 推荐 |
|------|------|
| "做大做强" | "Build trustworthy infrastructure" |
| "共同信仰" | "Shared protocols and governance" |
| "让 AI 更安全" | "Zero-trust safety by default" |
| "大家一起共建" | "Join our open development process" |
| "革命性创新" | "Governed execution model" |
| 宣传口号 | 技术定位 + 具体差异点 |

---

## 实施优先级

### P0（立即）

1. 创建 `README.md`（英文主入口）
2. 创建 `README.zh-CN.md`（中文完整版）
3. 更新 `CONTRIBUTING.md` 风格

### P1（本周）

4. 创建 `WHY_AAS.md` / `WHY_AAS.zh-CN.md`
5. 更新 `docs/rfc/README.md` 加中文导航

### P2（下个迭代）

6. 为每篇 RFC 顶部添加 English Summary（200字）
7. 创建 `CONTRIBUTING.zh-CN.md`

---

## 验收标准

- [ ] 英文 README 清晰、专业、有辨识度
- [ ] 中文 README 准确、流畅、不生硬
- [ ] WHY_AAS 回答了"为什么要参与"
- [ ] GitHub 首页吸引人停留 >10 秒
- [ ] 新贡献者能快速找到入口
