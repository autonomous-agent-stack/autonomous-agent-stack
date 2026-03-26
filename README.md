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
make hygiene-check
```

`make hygiene-check` 会把结果写到 `logs/audit/prompt_hygiene/report.txt` 和 `logs/audit/prompt_hygiene/report.json`。

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
