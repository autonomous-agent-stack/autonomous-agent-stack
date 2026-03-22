# Agent 调度与自动化研究

**日期**: 2026-03-23
**来源**: GitHub Search

## 🔥 热门项目

### AI Second Brain

| Stars | 名称 | 说明 |
|-------|------|------|
| 33.6k | [khoj](https://github.com/khoj-ai/khoj) | 自托管 AI 第二大脑，调度自动化 |
| 5.1k | [agentic-cronjob](https://github.com/anjumsingla-ai/agentic-cronjob) | Agentic 调度框架 |
| 1.8k | [agent-cron](https://github.com/VincentBai-dotcom/agent-cron) | Agent SDK 定时任务 |

### 调度工具

| Stars | 名称 | 说明 |
|-------|------|------|
| 181 | [agentic-cronjob](https://github.com/anjumsingla-ai/agentic-cronjob) | Cron + Agent |
| 48 | [agentkit-cronjob](https://github.com/Agentic-Ethereum-Hackathon/agentkit-cronjob) | Hackathon 项目 |
| 6 | [agent-cron-scheduler](https://github.com/Jtonna/agent-cron-scheduler) | Cron 调度器 |
| 4 | [hermes-ai-infrastructure-monitoring-toolkit](https://github.com/JackTheGit/hermes-ai-infrastructure-monitoring-toolkit) | Hermes + Cron |
| 1 | [agent-cron](https://github.com/TBOO-AI/agent-cron) | Claude Agent 定时任务 |

## 🏗️ 调度模式

### 1. Cron 调度

```yaml
# agent-cronjob 示例
schedule: "0 */6 * * * *"  # 每 6 小时
agent:
  model: gpt-4o-mini
  task: "检查 PR 状态并通知变化"
```

### 2. Event-Driven

```
事件触发 → Agent 执行 → 结果处理
   ↓
Webhook / Message Queue / Cron
```

### 3. 条件调度

```python
if condition_met():
    agent.run(task)
```

## 📊 OpenClaw Cron 对比

| 特性 | OpenClaw Cron | agent-cronjob |
|------|---------------|---------------|
| 格式 | YAML 配置 | Python 代码 |
| 触发 | 时间/事件 | 时间 |
| 隔离 | Isolated Session | 共享 |
| 模型 | 可配置 | 固定 |

## 💡 洞察

1. **Khoj 33.6k stars** — AI Second Brain 领先
2. **调度是刚需** — 多个项目专注调度
3. **简单有效** — Cron + Agent 最常见
4. **事件驱动** — 比 Cron 更灵活
5. **OpenClaw 内置** — 无需额外工具

## 🔧 OpenClaw Cron 示例

```yaml
# HEARTBEAT.md
- [ ] 检查 PR 状态（每 6 小时）
  - 运行: check-pr-status.sh
  - 变化时通知
```

## 🔗 待研究

- [ ] khoj 的调度实现
- [ ] agentic-cronjob 架构
- [ ] OpenClaw cron 高级用法
- [ ] 事件驱动调度模式
