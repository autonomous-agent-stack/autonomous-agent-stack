# Autonomous Agent Stack

一个面向多智能体编排、工作流触发、自集成验证和零信任加固的工程化仓库。

## 为什么现在更容易上手

参考 ClawX 的使用体验，这个仓库把新手最常见的三个问题做了统一入口。

| 常见痛点 | 现在的做法 |
| --- | --- |
| 启动命令太多，不知道先跑哪个 | `make setup -> make doctor -> make start` |
| 报错信息分散，定位慢 | `scripts/doctor.py` 统一体检并给出下一步建议 |
| 文档和实际入口不一致 | README、Makefile、启动脚本使用同一套命令 |

## 3 分钟上手

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
make setup
make doctor
make start
```

启动后可访问：

- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/panel`

## 常用命令

```bash
make help
make setup
make doctor
make start
make test-quick
make ai-lab
make ai-lab-check
make ai-lab-setup
make masfactory-flight
make masfactory-flight GOAL="探测当前 M1 的 CPU 核心数"
make masfactory-flight GOAL="探测当前 M1 的 CPU 核心数" WATCH=1
make openhands-dry-run
make openhands OH_TASK="Please scan /opt/workspace/src/autoresearch/core and fix TODOs with tests."
make openhands-controlled-dry-run
make openhands-controlled OH_TASK="Create src/demo_math.py with add(a,b), then run validation."
make openhands-demo OH_BACKEND=mock OH_TASK="Create src/demo_math.py with add(a,b)."
make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
make hygiene-check
make review-gates-local
```

`make hygiene-check` 会把结果写到 `logs/audit/prompt_hygiene/report.txt` 和 `logs/audit/prompt_hygiene/report.json`。

`make openhands` 会调用 `scripts/openhands_start.sh`（CLI 直连模式），默认注入 `DIFF_ONLY=1` 与 `MAX_FILES_PER_STEP=3` 的执行约束，并优先读取 `memory/SOP/MASFactory_Strict_Execution_v1.md`。

`make openhands-controlled` 会走最窄闭环：创建隔离 workspace、执行 OpenHands 子任务、运行校验、输出 promotion patch 与审计摘要（不直接污染主仓库）。

`make agent-run` 走 AEP v0 统一执行内核：`JobSpec -> driver adapter -> patch gate -> decision`，OpenHands/Codex/本地脚本都可作为 driver 接入。

`make review-gates-local` 会在本地运行 reviewer 核心模块的 `mypy + bandit + semgrep`，与 CI 的 `Quality Gates` 流程保持一致。

## PR 审查与门禁

- OpenHands 首轮审查（comment-only）：`.github/workflows/pr-review-by-openhands.yml`
  - 触发方式：默认 `review-this` label；可选通过 `OPENHANDS_REVIEWER_HANDLE` 启用 reviewer 触发
  - 安全策略：`pull_request` 事件、仅内部分支 PR（跳过 forks）、最小权限、action/extension 固定 SHA
  - 合并策略：按需触发模式下不设为 required status check（仅作为 advisory reviewer）
- 质量门禁：`.github/workflows/quality-gates.yml`
  - 检查项：`mypy + bandit + semgrep`（工具版本固定在 `requirements-review.lock`）
  - 包含 `merge_group` 触发，兼容 merge queue
- 仓库 required checks 建议：`CI / lint-test-audit` + `Quality Gates / reviewer-gates`

完整落地说明见：[PR Review Hardening](./docs/pr-review-hardening.md)

如果端口冲突：

```bash
PORT=8010 make start
```

## 你可以拿它做什么

- 从 Telegram 触发仓库审查任务
- 生成带语言分布的审查报告
- 为外部仓库生成 prototype，并在 secure-fetch 后推进 promotion
- 扫描并执行本地技能
- 运行零信任加固脚本和相关验证脚本

## Telegram Worker Orchestration：怎么用

现在 Telegram 入口已经接上 deterministic worker routing，可以直接把自然语言任务交给系统，由它决定走哪条最窄执行链路。

### 任务会怎么路由

| 你发的任务类型 | 实际路由 |
| --- | --- |
| 普通聊天、闲聊、非执行问题 | `claude_direct` |
| 分析、调研、方案、风险评估 | `autoresearch` |
| 明确代码修改、补测试、修 bug | `openhands` |
| 先分析再改代码的混合任务 | `autoresearch -> openhands` |
| 带 `main` / `merge` / `delete` / 高风险写意图 | 先挂 approval，再 resume worker |

### 最常见的用法

```text
请分析 src/autoresearch/core/services/worker_orchestrator.py 的风险和边界
```

- 会走 `autoresearch`

```text
请修复 src/autoresearch/api/routers/panel.py 的 bug 并补测试
```

- 会走 `openhands`

```text
先分析 src/autoresearch/api/routers/gateway_telegram.py 的问题，再修复这个 bug 并补测试
```

- 会走 `autoresearch -> openhands`

```text
请修复 src/demo_fix.py 并直接合并到 main
```

- 不会直接进 worker
- 系统会先创建 approval
- approval 通过后，自动恢复同一条 orchestration run

### approval 怎么批

- Telegram：`/approve`、`/approve <approval_id>`、`/approve <approval_id> approve [备注]`
- Panel：待审批列表里直接点 `Approve`
- Admin：Approval Queue 里直接批准
- API：`POST /api/v1/approvals/{approval_id}/decision`

## Worker Orchestration：实现了什么

- deterministic routing：同类任务稳定走同一类 worker，不靠随机 prompt 漂移
- approval replay payload：高风险任务在 approval 里持久化恢复所需上下文
- unified resume path：Telegram / panel / admin / approvals API 批准后统一回到同一条 resume 路径
- async approval UX：Telegram `/approve` 先回执，再异步恢复 worker 执行
- artifact-only analysis stage：`autoresearch -> openhands` 第一段只产出 plan / risk / test artifacts，不额外 finalize promotion
- observability：panel/admin 可以看到 selected worker、route reason、requested/effective promotion mode、approval/resume state、blocker

## Worker Orchestration 最佳实践

1. 分析任务和修改任务分开写，除非你明确想要 `autoresearch -> openhands` 链路。
2. 代码修改类任务尽量带明确文件路径，例如 `src/...py`，这样 allowed paths 会更窄。
3. 在 prompt 里直接写成功条件，例如“补测试”“通过 py_compile”“给出 risk summary”。
4. 不要让 worker 直接承担 merge / main / delete 之类高风险意图；让 approval gate 做唯一出口。
5. 如果你需要“先分析，再执行”，就明确写出“先分析…再修复…”，不要让模型自己猜。
6. 排障先看 panel/admin 的 route reason、promotion requested/effective mode、approval/resume state，再决定是不是 worker 问题。
7. 对链式任务，把第一段当成 artifact producer，不要期待它直接完成 promotion。

## OpenHands 接入边界（重要）

- “更容易上手”指 AAS 的统一启动和排错流程：`make setup -> make doctor -> make start`。
- OpenHands 文档里的“切换简单”指其内部 SDK/workspace 抽象下的切换，不等同于跨平台融合。
- 本仓库采用分层接法：AAS 负责任务路由、状态、校验与 promotion；OpenHands 只负责隔离 workspace 内的代码执行。

最窄链路：

1. AAS 下发 task（受控输入契约）
2. OpenHands 在隔离 workspace 执行
3. AAS 执行 validation gate
4. AAS 产出 promotion patch 并决定 promote/reject

详见：[OpenHands Controlled Backend Integration](./docs/openhands-cli-integration.md)
协议文档：[Agent Execution Protocol (AEP v0)](./docs/agent-execution-protocol.md)

## 关键入口

- [API 主入口](./src/autoresearch/api/main.py)
- [工作流引擎](./src/workflow/workflow_engine.py)
- [Telegram Webhook](./src/gateway/telegram_webhook.py)
- [自集成服务](./src/autoresearch/core/services/self_integration.py)
- [自集成路由](./src/autoresearch/api/routers/integrations.py)
- [技能注册表](./src/opensage/skill_registry.py)
- [MASFactory 骨架](./src/masfactory/graph.py)
- [MASFactory 首航示例](./examples/masfactory_first_flight.py)

## 快速排错

1. 先跑 `make doctor`，看是否有 `FAIL`
2. 如果是依赖问题，执行 `make setup`
3. 如果是端口问题，执行 `PORT=8010 make start`
4. 如果是导入问题，确认通过 `make start` 启动（脚本会自动设置 `PYTHONPATH=src`）

## 🎯 灵感来源（Inspirations）

本项目深受以下 6 个优秀开源库的启发：

### 1. **MASFactory** - 多智能体编排框架
**GitHub**: https://github.com/BUPT-GAMMA/MASFactory  
**Stars**: 125+  
**启发点**:
- ✅ 4 节点图结构（Planner/Generator/Executor/Evaluator）
- ✅ M1 本地执行沙盒
- ✅ MCP 网关集成
- ✅ 可视化监控看板

---

### 2. **deer-flow** - 并发编排与沙盒隔离
**GitHub**: https://github.com/nxs9bg24js-tech/deer-flow  
**Stars**: 45,000+  
**启发点**:
- ✅ 多智能体并发编排（Lead Agent + Sub-agents）
- ✅ 沙盒隔离执行（三级防御：L1/L2/L3）
- ✅ 持久化长程记忆
- ✅ Markdown Skills

---

### 3. **OpenSage** - 自演化智能体
**论文**: arXiv:2602.16891  
**官网**: https://www.opensage-agent.ai/  
**启发点**:
- ✅ 自编程智能体（Level 3 - AI 自动创建）
- ✅ Self-generating Agent Topology（自生成拓扑）
- ✅ Dynamic Tool and Skill Synthesis（动态工具合成）
- ✅ Hierarchical, Graph-based Memory（分层图记忆）

---

### 4. **OpenClaw** - 多渠道接入与技能系统
**GitHub**: https://github.com/openclaw/openclaw  
**Stars**: 1,000+  
**启发点**:
- ✅ 多渠道接入（Telegram、Discord、Signal）
- ✅ 技能系统（SKILL.md）
- ✅ 会话管理
- ✅ 记忆系统（MEMORY.md）

---

### 5. **OpenSpace** - SOP 演化引擎
**GitHub**: https://github.com/HKUDS/OpenSpace  
**版本**: v0.1.0  
**启发点**:
- ✅ 自演化技能引擎（越用越聪明）
- ✅ Markdown SOP 演化（安全、可读、可积累）
- ✅ AUTO-LEARN 机制（自动学习新技能）
- ✅ 网络效应（集体智慧共享）

---

### 6. **AutoResearch** - Karpathy 循环
**GitHub**: https://github.com/karpathy/autoresearch  
**Stars**: 48,800+  
**作者**: Andrej Karpathy（前 Tesla AI 总监）  
**启发点**:
- ✅ **自主实验循环**（Autonomous Experiment Loop）
  ```
  propose → train → evaluate → commit/revert → repeat
  ```
- ✅ 并行探索策略（多分支并行）
- ✅ 结果导向（保留改进，回滚失败）
- ✅ 无限迭代（自主优化）

---

### 整合价值

| 开源库 | 核心价值 | 应用到本项目 |
|--------|---------|-------------|
| **MASFactory** | 多智能体编排 | 4 节点图结构 + MCP 网关 |
| **deer-flow** | 并发编排 + 沙盒 | Lead Agent + Docker 沙盒 |
| **OpenSage** | 自演化机制 | OpenSage 模块 + 动态工具合成 |
| **OpenClaw** | 渠道接入 | Telegram Webhook + 技能系统 |
| **OpenSpace** | SOP 演化引擎 | Markdown 技能库 + AUTO-LEARN |
| **AutoResearch** | Karpathy 循环 | Propose-Train-Evaluate-Repeat |

---

**价值主张**: "构建无需人类干预、通过多渠道自我优化的超级智能体网络"

---

## 深入文档

- [快速启动文档](./docs/QUICK_START.md)
- [Admin View 字段填写教程](./docs/admin-view-field-guide.md)
- [状态与发布说明](./STATUS_AND_RELEASE_NOTES.md)
- [工作流引擎验证报告](./docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md)
- [自集成协议](./docs/p4-self-integration-protocol.md)
- [零信任实施方案](./docs/zero-trust-implementation-plan-v2.md)
