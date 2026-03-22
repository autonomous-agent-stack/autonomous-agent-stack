# Agent Evaluation & Observability 研究

**日期**: 2026-03-23
**来源**: GitHub Search

## 🔥 Agent Evaluation

### 热门项目

| Stars | 名称 | 说明 |
|-------|------|------|
| 352 | [agent-evaluation (AWS)](https://github.com/awslabs/agent-evaluation) | AWS 生成式 AI 测试框架 |
| 148 | [Agent-Eval-Refine](https://github.com/Berkeley-NLP/Agent-Eval-Refine) | 自动评估与优化 (COLM 2024) |
| 127 | [agent-eval (Vercel)](https://github.com/vercel-labs/agent-eval) | Vercel 官方评估工具 |
| 89 | [LLM-Agent-Evaluation-Survey](https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey) | 论文调研 |
| 70 | [ai-agent-evals (Microsoft)](https://github.com/microsoft/ai-agent-evals) | GitHub Action 评估 |
| 67 | [AgentEval (.NET)](https://github.com/AgentEvalHQ/AgentEval) | .NET 工具包 |
| 37 | [ai-agents-eval-techniques](https://github.com/FareedKhan-dev/ai-agents-eval-techniques) | 12 种评估技术 |

### 评估维度

```
┌─────────────────────────────────────────┐
│           Agent Evaluation              │
├─────────────────────────────────────────┤
│  ✅ 工具使用正确性                       │
│  ✅ RAG 检索质量                         │
│  ✅ 任务完成率                           │
│  ✅ 响应时间                             │
│  ✅ Token 消耗                          │
│  ✅ 安全性                               │
│  ✅ 随机性评估                           │
└─────────────────────────────────────────┘
```

### 评估方法

1. **Model-as-Judge** — 用 LLM 评估 LLM
2. **Ground Truth** — 对比标准答案
3. **Human Evaluation** — 人工评审
4. **Automated Metrics** — 自动化指标

## 📡 Agent Observability

### 热门项目

| Stars | 名称 | 说明 |
|-------|------|------|
| 1.3k | [claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) | Claude Code 实时监控 |
| 352 | [agent-evaluation (AWS)](https://github.com/awslabs/agent-evaluation) | AWS 评估 + 可观测 |
| 83 | [agent-lens](https://github.com/dreadnode/agent-lens) | 回放工具，安全研究 |
| 46 | [www-project-agent-observability-standard](https://github.com/OWASP/www-project-agent-observability-standard) | OWASP 标准 |
| 40 | [FlowMetr](https://github.com/FlowMetr/FlowMetr) | 工作流 + Agent 可观测平台 |

### 可观测三支柱

```
Metrics  ────→  性能指标 (延迟、吞吐、错误率)
Logs    ────→  执行日志 (决策、工具调用)
Traces  ────→  调用链 (端到端追踪)
```

### 关键指标

| 类别 | 指标 |
|------|------|
| 性能 | 响应时间、首字延迟 |
| 成本 | Token 消耗、API 调用 |
| 质量 | 准确率、完成率 |
| 安全 | 注入检测、权限越界 |

## 🏗️ 架构

### 典型 Observability 架构

```
Agent 执行
    ↓
Hook 拦截
    ↓
事件收集 (OTel)
    ↓
存储 (时序数据库)
    ↓
可视化 (Grafana/自定义)
```

### OpenTelemetry 集成

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("agent.task") as span:
    span.set_attribute("agent.name", "claude")
    span.set_attribute("task.type", "code_generation")
    # ... agent 执行
```

## 💡 洞察

1. **OWASP 入场** — Agent Observability 标准化
2. **Hook 是关键** — Claude Code hooks 监控方案
3. **OTel 成标配** — OpenTelemetry 原生支持
4. **评估驱动开发** — AgentEval 等工具链
5. **安全可观测** — agent-lens 专注安全研究

## 🔧 工具对比

| 工具 | 类型 | 特点 |
|------|------|------|
| AgentEval | 评估 | .NET 生态 |
| agent-eval (Vercel) | 评估 | 轻量级 |
| Agent-Eval-Refine | 评估 | 自动优化 |
| agent-lens | 可观测 | 安全导向 |
| FlowMetr | 可观测 | 全栈平台 |

## 🔗 待研究

- [ ] OWASP Agent Observability 标准
- [ ] Claude Code hooks 实现细节
- [ ] agent-lens 的回放机制
- [ ] OpenTelemetry Agent 集成
