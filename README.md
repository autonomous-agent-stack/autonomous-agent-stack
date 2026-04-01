# autonomous-agent-stack: Agent Execution Control Plane

`autonomous-agent-stack` 不是另一个个人 agent runtime，也不是另一个 memory system、training framework 或 channel OS。

它的主定位是一个受控的 agent execution control plane：把 OpenClaw 兼容层、Claude CLI、OpenHands、Linux worker、Windows RPA worker、浏览器自动化和脚本 worker 纳入统一执行面，提供任务路由、隔离执行、审批、审计、回滚和迁移能力。

当前仓库的 4 个关键词：

- **Control Plane**: 统一任务契约、worker registry、状态流转与入口路由
- **Worker Fabric**: 接不同 runtime/worker，而不是绑定单一 agent runtime
- **Governance Layer**: 提供隔离、审批、验证、审计、回滚与幂等重放边界
- **Migration Hub**: 平滑承接 OpenClaw 的 session、skills、Telegram 与 workflow，并支持分阶段迁移和回滚

## 它不是什么

- 不是另一个个人 agent runtime
- 不是另一个长程记忆系统
- 不是另一个训练或自进化框架
- 不是另一个多渠道 channel OS
- 不要求你先推倒现有 OpenClaw 或 CLI 工作流再接入

## 它替代什么

- 替代散落在 shell 脚本、tmux 会话、人工 SSH 和临时 glue code 里的执行编排
- 替代 runtime 各自为政、缺少统一审批、审计与回滚边界的真实执行链
- 替代“要么全量迁移、要么完全不动”的高风险切换方式

## 它依赖什么

- 它依赖现成 runtime/worker 干活：OpenClaw、Claude CLI、OpenHands、本地脚本、浏览器自动化、Linux/Windows worker
- 它依赖执行边界基础设施：Docker 或 host runtime、独立 workspace、validator、patch gate、approval surface
- 它依赖兼容层，而不是自造全套生态：session/skills/Telegram 兼容、上游 workflow 挂载、分阶段迁移

## 它的最小闭环

1. 控制面接收任务并选择合适的 worker 或 adapter
2. 在隔离 workspace 或受控队列中执行任务
3. 产出 patch、artifacts、summary 和 heartbeat
4. 经过 validator、approval 和 audit 后决定 promote、retry、fallback、human_review 或 rollback

## 项目方向

更多长期边界和吸收规则见 [Project Direction](./docs/project-direction.md)。
面向投资人的版本见 [Investor Brief](./docs/investor-brief.md) 与 [投资人一页纸](./docs/investor-one-pager.md)。

当前项目只保留三条硬规则：

- prompt orchestration 只做计划层，不替代 control plane
- self-exploration 只做受控研究执行，不绕过 gate / acceptance
- memory 只分三层：run checkpoint state、replay / audit stream、knowledge memory

## 运行时要求

- Python 基线：`3.11+`
- 本仓库当前在 CI 中验证：`3.11`、`3.12`
- 如果本机默认 `python3` 低于 3.11，请先安装 3.11+ 再执行 `make setup`

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
# 确保这里用的是 Python 3.11+
make setup
make doctor
make doctor-linux
make start
```

启动后可访问：

- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/panel`

如果你要启用 Telegram 提醒和 Mini App 审批，至少补齐这 4 个环境变量：

```bash
AUTORESEARCH_TELEGRAM_BOT_TOKEN=...
AUTORESEARCH_TELEGRAM_ALLOWED_UIDS=你的TelegramUID
AUTORESEARCH_PANEL_JWT_SECRET=随机长串
AUTORESEARCH_PANEL_BASE_URL=https://你的面板域名/api/v1/panel/view
```

如果还希望通知卡片直接带 `Mini App` 按钮，再补：

```bash
AUTORESEARCH_TELEGRAM_MINI_APP_URL=https://你的面板域名/api/v1/panel/view
```

如果你要把上游 OpenClaw 巡检挂成 Planner 的可选低噪音任务，再补这 3 个变量：

```bash
AUTORESEARCH_UPSTREAM_WATCH_URL=https://github.com/openclaw/openclaw.git
AUTORESEARCH_UPSTREAM_WATCH_WORKSPACE_ROOT=/Volumes/AI_LAB/ai_lab/workspace
AUTORESEARCH_UPSTREAM_WATCH_MAX_COMMITS=5
```

当前代码会优先使用 `AUTORESEARCH_TELEGRAM_BOT_TOKEN`；旧变量 `TELEGRAM_BOT_TOKEN` 还能兼容，但已经是 deprecated。

## Linux 远端节点

如果你准备把 Linux 当“执行面”来跑真实 OpenHands，最稳的第一步不是照搬 Mac/Colima，而是直接走 `host` runtime。

最小路径：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
make setup
OPENHANDS_RUNTIME=host make doctor-linux
OPENHANDS_RUNTIME=host make start
```

更完整的落地清单、环境变量建议和远端使用姿势见：

- [Linux Remote Worker Guide](./docs/linux-remote-worker.md)
- [cc-switch Usage Guide](./docs/cc-switch-usage.md)
- [OpenHands Controlled Backend Integration](./docs/openhands-cli-integration.md)

## 常用命令

```bash
make help
make setup
make doctor
make doctor-linux
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
make linux-housekeeper-start
make linux-housekeeper-status
make linux-housekeeper-enqueue-test
make linux-housekeeper-run-once
make hygiene-check
make review-gates-local
```

`make hygiene-check` 会把结果写到 `logs/audit/prompt_hygiene/report.txt` 和 `logs/audit/prompt_hygiene/report.json`。

`make openhands` 会调用 `scripts/openhands_start.sh`（CLI 直连模式），默认注入 `DIFF_ONLY=1` 与 `MAX_FILES_PER_STEP=3` 的执行约束；当前真实边界请以 [ARCHITECTURE.md](./ARCHITECTURE.md) 为总图，以 [memory/SOP/MASFactory_Strict_Execution_v1.md](./memory/SOP/MASFactory_Strict_Execution_v1.md) 为执行清单。

当前 launcher 会优先读取根目录 `ai_lab.env`。`host` 模式下会优先寻找 `./.masfactory_runtime/tools/openhands-cli-py312/bin/openhands` 这类独立工具 venv，并自动在本地 OpenHands home 下生成 `agent_settings.json`；`ai-lab` 模式则默认调用容器内的 `openhands`。默认模板会走 `--exp --headless`，因为本地验证的 `OpenHands CLI 1.5.0` 在这条路径上能自动收尾退出，更适合作为 pipeline worker：

```bash
RUNTIME=process \
SANDBOX_VOLUMES=/你的workspace:/workspace:rw \
openhands --exp --headless -t "你的任务"
```

实际执行时 launcher 会先 `cd` 到目标 worktree，再启动 CLI，所以 OpenHands 的 workspace 会对准当前任务目录。如果你要切回旧的“把 prompt 当位置参数”模式，可显式设置 `OPENHANDS_HEADLESS=0`；如果你明确想关闭 `--exp`，可设置 `OPENHANDS_EXPERIMENTAL=0`。`OPENHANDS_JSON=1` 仅适用于明确支持该 flag 的 CLI 版本；当前本地验证的 `OpenHands CLI 1.5.0` 默认不带它。如果要走真实 `ai-lab` 容器链，除了容器内 `openhands` 本身可用，还需要当前 shell 对配置的 Docker/Colima socket 有访问权限。`sandbox/ai-lab/Dockerfile` 也默认锁到同一个 `OpenHands CLI 1.5.0`，避免容器冷启动时漂移到未验证的新版本。

`launch_ai_lab.sh` 也会显式识别 `DOCKER_HOST=unix://...` 这类 Colima socket。如果当前配置指向了一个当前用户不可访问的 Colima socket，它会先尝试安全回退：有外置盘 Colima store 时走 repo 自带的 `scripts/colima-external.sh`，否则直接回退到当前用户自己的 `~/.colima/<profile>/docker.sock`，而不是直接放宽宿主机 socket 权限。当前用户回退分支还会显式把 `/Volumes/AI_LAB` 挂进 Colima；如果你不想碰现有默认 profile，可直接用独立 profile，例如 `COLIMA_PROFILE=ai-lab bash ./scripts/launch_ai_lab.sh status`。

`make openhands-controlled` 会走最窄闭环：创建隔离 workspace、执行 OpenHands 子任务、运行校验、输出 promotion patch 与审计摘要（不直接污染主仓库）。

`make agent-run` 走 AEP v0 统一执行内核：`JobSpec -> driver adapter -> patch gate -> decision`，OpenHands/Codex/本地脚本都可作为 driver 接入。

`make linux-housekeeper-start` / `make linux-housekeeper-status` / `make linux-housekeeper-enqueue-test` 提供 Linux 常驻 supervisor MVP 的最小入口：文件任务协议、heartbeat、timeout/watchdog、run summary。详细见 [Linux Remote Worker Guide](./docs/linux-remote-worker.md)。

`make review-gates-local` 会在本地运行 reviewer 核心模块的 `mypy + bandit + semgrep`，与 CI 的 `Quality Gates` 流程保持一致。

## 本地 CLI 切换工具的边界

像 `cc-switch` 这类工具，适合放在本地开发工作台，用来切换 `Codex`、`OpenClaw`、`Claude Code` 等 CLI 进行人工调试和 prompt 试验。

但它不应该替代本仓库的执行主链。这里真正负责受控执行的是 `make agent-run`、`make openhands-controlled`、AEP runner、validator 和 promotion gate。

如果你想把 `cc-switch` 接进日常工作流，推荐只做旁路工作台，不要改写 `drivers/openhands_adapter.sh` 或 `scripts/openhands_start.sh` 的主逻辑。详细边界见 [cc-switch Usage Guide](./docs/cc-switch-usage.md)。

## PR 审查与门禁

- OpenHands 首轮审查（comment-only）：`.github/workflows/pr-review-by-openhands.yml`
  - 触发方式：默认 `review-this` label；可选通过 `OPENHANDS_REVIEWER_HANDLE` 启用 reviewer 触发
  - 安全策略：`pull_request` 事件、仅内部分支 PR（跳过 forks）、最小权限、action/extension 固定 SHA
  - 合并策略：按需触发模式下不设为 required status check（仅作为 advisory reviewer）
- 质量门禁：`.github/workflows/quality-gates.yml`
  - 检查项：`mypy + bandit + semgrep`（工具版本固定在 `requirements-review.lock`）
  - 包含 `merge_group` 触发，兼容 merge queue
- 仓库 required checks 建议：`CI / lint-test-audit` + `Quality Gates / reviewer-gates`
- 试运行与反馈闭环：见 [PR Review Hardening](./docs/pr-review-hardening.md) 里的 `Trial Rubric` 与 `Feedback Loop`

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
- [Telegram Gateway（主线）](./src/autoresearch/api/routers/gateway_telegram.py)
- [Telegram Webhook（legacy compatibility only）](./src/gateway/telegram_webhook.py)
- [自集成服务](./src/autoresearch/core/services/self_integration.py)
- [自集成路由](./src/autoresearch/api/routers/integrations.py)
- [技能注册表](./src/opensage/skill_registry.py)
- [MASFactory 骨架](./src/masfactory/graph.py)
- [MASFactory 首航示例](./examples/masfactory_first_flight.py)

## 快速排错

1. 先跑 `make doctor`，看是否有 `FAIL`
2. Linux 远端执行节点先跑 `OPENHANDS_RUNTIME=host make doctor-linux`
3. 如果提示 Python 版本过低，先切到 Python 3.11+，再执行 `make setup`
4. 如果是端口问题，执行 `PORT=8010 make start`
5. 如果是导入问题，确认通过 `make start` 启动（脚本会自动设置 `PYTHONPATH=src`）

## 🎯 生态来源与设计边界

这些项目提供了局部灵感，但本仓库当前不试图复刻它们完整的 runtime、memory、channel 或 self-evolution 叙事。最终收敛的是一个受控执行控制面。

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

### 这些灵感如何收敛到当前定位

| 开源库 | 核心价值 | 应用到本项目 |
|--------|---------|-------------|
| **MASFactory** | 任务图与编排思路 | 图式拆解与执行链路设计 |
| **deer-flow** | 并发编排 + 沙盒 | 隔离执行与 worker 编排边界 |
| **OpenSage** | 动态工具与自适应思路 | 受控 adapter / patch 工作流 |
| **OpenClaw** | 渠道、session、skills | 兼容层与迁移入口 |
| **OpenSpace** | SOP 积累方式 | 可审计的文档化治理与操作清单 |
| **AutoResearch** | promote / reject 循环 | validator、promotion、rollback 决策链 |

---

**当前价值主张**: "让不同 agent/runtime/worker 在真实环境里可控、可回滚、可审计地干活"

---

## 深入文档

- [快速启动文档](./docs/QUICK_START.md)
- [架构总图](./ARCHITECTURE.md)
- [Admin View 字段填写教程](./docs/admin-view-field-guide.md)
- [状态与发布说明](./STATUS_AND_RELEASE_NOTES.md)
- [项目方向](./docs/project-direction.md)
- [投资人简报](./docs/investor-brief.md)
- [投资人一页纸](./docs/investor-one-pager.md)
- [工作流引擎验证报告](./docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md)
- [自集成协议](./docs/p4-self-integration-protocol.md)
- [零信任实施方案](./docs/zero-trust-implementation-plan-v2.md)
