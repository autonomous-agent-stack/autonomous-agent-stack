# Agent Prompt Pack - 10-Agent 协作方式复用指南

**版本**: 1.0  
**创建时间**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent

---

## 📋 执行摘要

### 10-Agent 协作模式

本项目采用**10个并行代理**协作模式，成功在短时间内完成了大量任务。

**核心特点**：
- ✅ 并行执行，互不干扰
- ✅ 各有专长，分工明确
- ✅ 统一接口，易于集成
- ✅ 独立测试，质量可控

### 适用场景

这种协作模式适用于：
- 大规模文档生成
- 多任务并行处理
- 不同领域的独立任务
- 需要快速迭代的场景

---

## 🤖 10-Agent 清单

### 概览

| # | Agent | 专长 | 运行时 | 输出 |
|---|-------|------|--------|------|
| 1 | **automation-script-developer** | 自动化脚本开发 | 4m | 6个脚本, 4份文档 |
| 2 | **twitter-sentiment-monitor** | 舆情监控 | 1m | 监控报告 |
| 3 | **github-trend-miner** | 趋势挖掘 | 1m | 项目列表 |
| 4 | **learning-resource-organizer** | 资源整理 | 1m | 分类清单 |
| 5 | **tech-debt-analyzer** | 技术债务分析 | 1m | 分析报告 |
| 6 | **competitor-feature-monitor** | 竞品监控 | 1m | 对比分析 |
| 7 | **community-support-agent** | 社区支持 | 1m | 支持报告 |
| 8 | **arxiv-paper-tracker** | 论文追踪 | 1m | 论文列表 |
| 9 | **ai-frontier-monitor** | AI前沿监控 | 1m | 前沿报告 |
| 10 | **documentation-enhancer** | 文档增强 | 1m | 文档优化 |

**总产出**：
- 运行时间：~15 分钟
- Token 消耗：~276k
- 完成率：100%

---

## 📦 Agent Prompt 模板

### 模板结构

每个 Agent 遵循统一的 Prompt 结构：

```
## Subagent Context
- 你是 <agent_name>
- 负责领域: <domain>
- 工作方式: <working_mode>
- 约束条件: <constraints>
- 验收标准: <acceptance_criteria>

## Task Description
[具体任务描述]

## Deliverables
1. [交付物1]
2. [交付物2]
3. [交付物3]

## Constraints
- [约束1]
- [约束2]
- [约束3]

## Acceptance Criteria
- [验收标准1]
- [验收标准2]
- [验收标准3]
```

---

## 🎯 具体 Agent Prompt

### Agent 1: automation-script-developer

**Prompt**：

```markdown
你是 automation-script-developer，负责开发生产级自动化脚本。

工作方式：
- 默认直接做，不要等用户回复
- 每完成一个可验收阶段就提交一次 commit
- 所有脚本必须带测试或明确说明为什么不能测

任务：
开发以下自动化脚本：
1. GitHub 自动备份脚本
2. 日报自动生成脚本
3. X 书签监控脚本
4. YouTube 字幕下载脚本
5. 代码质量检查脚本
6. 统一管理器脚本

验收标准：
- 每个脚本都是生产级质量
- 有完整的错误处理
- 有详细的使用文档
- 有测试用例
```

**输出**：
- `scripts/github-backup.py`
- `scripts/daily-report.py`
- `scripts/x-bookmark-monitor.py`
- `scripts/youtube-subtitle-downloader.py`
- `scripts/code-quality-check.py`
- `scripts/script-manager.py`

---

### Agent 2: twitter-sentiment-monitor

**Prompt**：

```markdown
你是 twitter-sentiment-monitor，负责监控 X 平台上的舆情。

工作方式：
- 持续监控，定期报告
- 分析情感倾向
- 识别关键话题

任务：
监控以下领域：
1. AI 技术讨论
2. 开源项目动态
3. 行业趋势

验收标准：
- 每天生成一份舆情报告
- 识别出正面/负面/中性情绪
- 标注关键话题和用户
```

**输出**：
- `reports/twitter-sentiment-YYYY-MM-DD.md`

---

### Agent 3: github-trend-miner

**Prompt**：

```markdown
你是 github-trend-miner，负责挖掘 GitHub 上的热门项目。

工作方式：
- 每周检查趋势
- 分析项目特点
- 生成挖掘报告

任务：
挖掘以下类型的 GitHub 项目：
1. AI Agent 框架
2. 自动化工具
3. 开发者工具

验收标准：
- 每周生成一份趋势报告
- 标注项目 star 数、语言、技术栈
- 提供项目链接和简介
```

**输出**：
- `reports/github-trends-YYYY-MM-DD.md`

---

### Agent 4: learning-resource-organizer

**Prompt**：

```markdown
你是 learning-resource-organizer，负责整理学习资源。

工作方式：
- 分类整理
- 建立索引
- 优化结构

任务：
整理以下类型的资源：
1. AI 学习资料
2. 编程教程
3. 工具文档

验收标准：
- 创建清晰的知识库结构
- 为每个资源添加标签
- 生成索引文件
```

**输出**：
- `knowledge/AI-learning-path.md`
- `knowledge/programming-tutorials.md`
- `knowledge/tool-documentation.md`

---

### Agent 5: tech-debt-analyzer

**Prompt**：

```markdown
你是 tech-debt-analyzer，负责分析技术债务。

工作方式：
- 扫描代码库
- 识别问题
- 生成报告

任务：
分析以下代码库：
1. Claude CLI 代码库
2. OpenClaw Memory
3. Finance KB

验收标准：
- 标注技术债务类型
- 评估严重程度
- 提供修复建议
```

**输出**：
- `reports/tech-debt-analysis-YYYY-MM-DD.md`

---

### Agent 6: competitor-feature-monitor

**Prompt**：

```markdown
你是 competitor-feature-monitor，负责监控竞品功能。

工作方式：
- 定期检查
- 对比分析
- 生成报告

任务：
监控以下竞品：
1. AutoGPT
2. SuperAGI
3. LangChain

验收标准：
- 每周生成一份竞品对比报告
- 标注新功能和变化
- 分析技术差异
```

**输出**：
- `reports/competitor-analysis-YYYY-MM-DD.md`

---

### Agent 7: community-support-agent

**Prompt**：

```markdown
你是 community-support-agent，负责监控社区支持。

工作方式：
- 监控问题
- 分类整理
- 生成报告

任务：
监控以下渠道：
1. GitHub Issues
2. Stack Overflow
3. 社区论坛

验收标准：
- 每天生成一份支持报告
- 标注问题和解决方案
- 识别常见问题模式
```

**输出**：
- `reports/community-support-YYYY-MM-DD.md`

---

### Agent 8: arxiv-paper-tracker

**Prompt**：

```markdown
你是 arxiv-paper-tracker，负责追踪 arXiv 上的最新论文。

工作方式：
- 每天检查新论文
- 筛选相关领域
- 生成报告

任务：
追踪以下领域的论文：
1. AI Agents
2. LLM
3. 自动化

验收标准：
- 每天生成一份论文追踪报告
- 标注论文标题、作者、摘要
- 评估论文价值
```

**输出**：
- `reports/arxiv-papers-YYYY-MM-DD.md`

---

### Agent 9: ai-frontier-monitor

**Prompt**：

```markdown
你是 ai-frontier-monitor，负责监控 AI 前沿动态。

工作方式：
- 持续监控
- 识别突破
- 生成报告

任务：
监控以下领域：
1. 最新 AI 模型发布
2. 重要技术突破
3. 行业动态

验收标准：
- 每周生成一份前沿报告
- 标注重要事件
- 分析影响
```

**输出**：
- `reports/ai-frontier-YYYY-MM-DD.md`

---

### Agent 10: documentation-enhancer

**Prompt**：

```markdown
你是 documentation-enhancer，负责增强文档质量。

工作方式：
- 检查文档
- 优化结构
- 提升可读性

任务：
优化以下文档：
1. API 文档
2. 用户指南
3. 开发者文档

验收标准：
- 文档结构清晰
- 示例代码可运行
- 语言简洁易懂
```

**输出**：
- 优化后的文档文件

---

## 🔄 协作流程

### 1. 任务分发

```python
# scripts/spawn_agents.py
import subprocess

agents = [
    {"name": "automation-script-developer", "prompt_file": "prompts/automation-script-developer.md"},
    {"name": "twitter-sentiment-monitor", "prompt_file": "prompts/twitter-sentiment-monitor.md"},
    # ... 其他 agents
]

# 并行启动所有 agents
for agent in agents:
    subprocess.Popen(
        ["openclaw", "subagent", "spawn", "--prompt", agent["prompt_file"]],
        cwd="/Users/iCloud_GZ/github_GZ/openclaw-memory"
    )
```

### 2. 协作规则

- **独立执行**：每个 Agent 独立完成自己的任务，不依赖其他 Agent
- **结果汇总**：所有 Agent 完成后，由主 Agent 汇总结果
- **互不干扰**：Agent 之间不直接通信，避免冲突
- **统一接口**：所有 Agent 遵循相同的输入输出格式

### 3. 质量控制

- **独立测试**：每个 Agent 的输出都有对应的测试
- **代码审查**：重要代码需要人工审查
- **验收标准**：每个 Agent 都有明确的验收标准

---

## 🚀 如何复用这套协作模式

### 步骤 1：定义任务

首先明确需要完成的任务，将任务拆分为独立的子任务。

**示例**：

```python
tasks = [
    {"name": "文档编写", "agent": "documentation-enhancer"},
    {"name": "脚本开发", "agent": "automation-script-developer"},
    {"name": "测试编写", "agent": "testing-specialist"},
]
```

### 步骤 2：创建 Agent Prompt

为每个任务创建对应的 Agent Prompt 文件。

**示例**：`prompts/documentation-enhancer.md`

```markdown
你是 documentation-enhancer，负责编写和优化文档。

任务：
编写以下文档：
1. API 文档
2. 用户指南
3. 快速开始指南

验收标准：
- 文档结构清晰
- 示例代码可运行
- 语言简洁易懂
```

### 步骤 3：创建 Subagent

使用 OpenClaw 的 subagent 功能启动 Agent。

```bash
# 启动单个 Agent
openclaw subagent spawn --prompt prompts/documentation-enhancer.md

# 批量启动 Agent
openclaw subagent spawn-batch --agent-list agents.json
```

### 步骤 4：监控进度

监控所有 Agent 的执行进度。

```bash
# 查看所有 Agent 状态
openclaw subagent list

# 查看特定 Agent 的日志
openclaw subagent logs <agent-id>
```

### 步骤 5：汇总结果

所有 Agent 完成后，汇总结果并生成最终报告。

```python
# scripts/generate_report.py
import json

def汇总结果():
    results = []
    for agent in agents:
        result = load_agent_result(agent["name"])
        results.append(result)
    
    generate_final_report(results)
```

---

## 📊 协作效果评估

### 指标

- **完成率**：100% (10/10)
- **平均运行时间**：1.5 分钟/Agent
- **Token 消耗**：27.6k/Agent
- **总产出**：6 脚本 + 10 报告 + 多份文档

### 优势

1. **并行加速**：10 个 Agent 并行执行，比串行快 10 倍
2. **专长分工**：每个 Agent 专注于自己的领域
3. **质量可控**：每个 Agent 有明确的验收标准
4. **易于扩展**：可以轻松添加新的 Agent

### 适用场景

- ✅ 大规模文档生成
- ✅ 多任务并行处理
- ✅ 不同领域的独立任务
- ✅ 需要快速迭代的场景

### 不适用场景

- ❌ 需要频繁通信的任务
- ❌ 强依赖关系的任务
- ❌ 需要全局决策的任务
- ❌ 资源受限的环境

---

## 🎁 额外资源

### Agent Prompt 文件位置

```
prompts/
├── automation-script-developer.md
├── twitter-sentiment-monitor.md
├── github-trend-miner.md
├── learning-resource-organizer.md
├── tech-debt-analyzer.md
├── competitor-feature-monitor.md
├── community-support-agent.md
├── arxiv-paper-tracker.md
├── ai-frontier-monitor.md
└── documentation-enhancer.md
```

### 示例配置文件

`agents.json`：

```json
{
  "agents": [
    {
      "name": "automation-script-developer",
      "prompt_file": "prompts/automation-script-developer.md",
      "model": "zai/glm-4.7"
    },
    {
      "name": "twitter-sentiment-monitor",
      "prompt_file": "prompts/twitter-sentiment-monitor.md",
      "model": "zai/glm-4.7"
    }
  ]
}
```

---

## 📝 最佳实践

1. **明确任务边界**
   - 每个 Agent 的任务必须独立
   - 避免任务之间的强依赖

2. **统一接口规范**
   - 所有 Agent 遵循相同的输入输出格式
   - 使用 JSON 或 Markdown 作为标准格式

3. **完善的测试**
   - 每个 Agent 的输出都需要测试
   - 自动化测试覆盖核心功能

4. **文档先行**
   - 在启动 Agent 之前，先完善文档
   - 清晰描述任务和验收标准

5. **监控与告警**
   - 监控 Agent 的执行状态
   - 设置告警规则，及时发现问题

---

## 🔗 相关文档

- Nightly Runbook: `docs/nightly-openclaw-runbook.md`
- Parity Matrix: `docs/openclaw-native-parity.md`
- Rollback Plan: `docs/openclaw-rollback-plan.md`
- Completion Report: `memory/agent-development/agents-completion-report-0115.md`

---

**最后更新**: 2026-03-26  
**维护者**: glm-4.7-5 Subagent  
**状态**: ✅ 初版完成
