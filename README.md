# Autonomous Agent Stack

一个**受控的 agent execution control plane**，统一调度代码 agent、Linux worker、Mac worker、Windows RPA worker。

**核心理念**: 安全地让 agent 干活，而不是让 agent 自己变聪明并长期自治。

---

## 🚀 18 天冲刺计划

**目标**: 做出"能跑的控制平面 + 2 到 3 个 worker + 1 条闭环业务流"

**不是**: 18 天做出"无需人类干预、还能自我进化的超级智能体"
**而是**: 18 天造出一个能调度 Mac/Linux/Win+影刀的受控自治底座 v0

**口号**: **"18 天做出一个可治理的 AI 调度中枢"**

### 📅 18 天排期概览

| 阶段 | 时间 | 任务 |
|------|------|------|
| Day 1-2 | 收缩范围 | 定义统一任务 schema、worker 注册、run 状态机 |
| Day 3-4 | 跨机器协议 | 新增 linux_worker、mac_worker、win_yingdao_worker |
| Day 5-6 | 最小控制台 | 任务列表、worker 列表、run 详情、人工审批页 |
| Day 7-8 | Linux worker | shell command、python script、file upload |
| Day 9-10 | Windows + 影刀 | 调用已有影刀流程 |
| Day 11-12 | task gate | 泛化 patch gate 为通用 task gate |
| Day 13-14 | 真实闭环 | 抓数据 → 清洗 → 录入 → 生成回执 |
| Day 15-16 | 最小自优化 | 优化路由/重试/参数（不碰权限） |
| Day 17-18 | 压测演示 | 连跑 20-50 次任务，制造 5 类失败 |

### 🎯 18 天目标（4 个）

1. **一个统一任务面板**
2. **两类 worker 跑通**（linux_worker + win_yingdao_worker）
3. **一条真实闭环流程**
4. **一套最小自优化**

### 💡 核心理念

```
一句任务 → 控制平面分发 → worker 执行 →
回传日志/截图/结果 → gate 判定 → 必要时人工接管
```

**完整计划**: [18-DAY-SPRINT.md](./18-DAY-SPRINT.md)

---

## 🎯 新愿景（2026-03-31 调整）

### 定位

**一个受控的 agent execution control plane**

统一调度：
- 代码 agent（OpenHands/Codex）
- Linux worker
- Mac worker
- Windows RPA worker（影刀）

### 为什么不是"超级智能体"？


- ❌ **当前不现实**: "无需人类干预 + 自我进化"
- ✅ **现实可行**: "受控自动化平台"

**现有能力**（非常有价值）:
- JobSpec
- driver adapter
- isolated workspace
- validation gate
- promotion gate
- Draft PR / patch artifact 输出

**结论**: 这些解决的是"怎么安全地让 agent 干活"，不是"怎么让 agent 自己变聪明"。

---

## 📖 为什么现在更容易上手

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

## OpenHands 接入边界（重要）

- "更容易上手"指 AAS 的统一启动和排错流程：`make setup -> make doctor -> make start`。
- OpenHands 文档里的"切换简单"指其内部 SDK/workspace 抽象下的切换，不等同于跨平台融合。
- 本仓库采用分层接法：AAS 负责任务路由、状态、校验与 promotion；OpenHands 只负责隔离 workspace 内的代码执行。

最窄链路：

1. AAS 下发 task（受控输入契约）
2. OpenHands 在隔离 workspace 执行
3. 输出 promotion patch 与审计摘要（不直接污染主仓库）

---

## 🔗 相关文档

**愿景调整**: [VISION-ADJUSTMENT.md](./VISION-ADJUSTMENT.md)
**18 天计划**: [18-DAY-SPRINT.md](./18-DAY-SPRINT.md)

---

**最后更新**: 2026-03-31 13:41
**愿景**: ✅ 已调整
**18 天计划**: ✅ 已制定
**标签**: #控制平面 #AI调度中枢 #18天冲刺
