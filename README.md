# 🤖 Autonomous Agent Stack

> **现代化多智能体编排框架** - 基于 MASFactory 的图编排引擎

---

## 📋 项目简介

Autonomous Agent Stack 是一个基于 MASFactory 的多智能体编排框架，将 6 个开源项目整合为统一的"超级智能体底座"。

**核心特性**：
- 🎯 **图编排引擎**：基于 MASFactory 的 Vibe Graphing
- 🔧 **MCP 集成**：通过 ContextBlock 统一管理工具链
- 🖥️ **M1 优化**：本地沙盒 + AppleDouble 自动清理
- 📊 **可视化监控**：实时看板 + Mermaid 图
- 🔄 **自愈能力**：自动重试 + 回滚机制

---

## 🏗️ 架构设计

### 核心流程

```
Planner Node → Generator Node → Executor Node → Evaluator Node
      ↑                                                    ↓
      └────────────── Retry Loop ──────────────────────────┘
```

### 6 部分架构

| 部分 | 核心技术 | 价值 |
|------|---------|------|
| **Part 1** | MetaClaw 自演化 | 准确率 +89.7% |
| **Part 2** | Autoresearch API-first | 最小闭环 ✅ |
| **Part 3** | Deer-flow 并发隔离 | 会话零污染 |
| **Part 4** | InfoQuest/MCP 深度耦合 | Token 优化 |
| **Part 5** | Claude Code 终端集成 | 自动重连 |
| **Part 6** | OpenClaw 持久化架构 | 污染防治 ✅ |

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行最小闭环

```python
from src.orchestrator import create_minimal_loop
import asyncio

async def main():
    # 创建最小闭环
    graph = create_minimal_loop()
    
    # 设置初始输入
    graph.context.set("goal", "优化代码性能")
    
    # 执行图
    results = await graph.execute()
    print(results)

asyncio.run(main())
```

### 3. 启动监控看板

```bash
# 生成 HTML 看板
python src/orchestrator/visualizer.py

# 在浏览器中打开
open dashboard.html
```

---

## 🎯 核心组件

### 1. 图编排引擎 (`src/orchestrator/graph_engine.py`)

**4 个核心节点**：
- **PlannerNode**: 规划节点，对接 OpenClaw
- **GeneratorNode**: 生成节点，写代码或调用工具
- **ExecutorNode**: 执行节点，沙盒环境
- **EvaluatorNode**: 评估节点，承载 MetaClaw 逻辑

### 2. MCP 上下文块 (`src/orchestrator/mcp_context.py`)

**统一工具管理**：
- Web Search
- Link Reader
- File Reader
- Code Analyzer

### 3. 可视化工具 (`src/orchestrator/visualizer.py`)

**监控看板功能**：
- 实时节点状态
- 评估分数展示
- Mermaid 图渲染
- 浅色主题

---

## 📚 文档

- **[架构文档](docs/architecture.md)**: 6 部分完整架构
- **[MASFactory 集成](docs/masfactory-integration.md)**: 集成指南
- **[集成指南](docs/integration-guide.md)**: 快速集成
- **[API 参考](docs/api-reference.md)**: API 详细说明
- **[路线图](docs/roadmap.md)**: 未来演进方向
- **[贡献指南](CONTRIBUTING.md)**: 如何贡献

---

## 🎯 使用场景

### 1. 软件工程
- 自动化代码优化
- 架构演进
- Bug 修复

### 2. 科学研究
- 自动化实验
- 参数优化
- 论文生成

### 3. 数据分析
- 自动化分析
- 可视化生成
- 报告生成

---

## 📊 项目统计

| 指标 | 数值 |
|------|------|
| **文件数量** | 58 个 |
| **代码行数** | 4,000+ 行 |
| **文档字数** | 30,000+ 字 |
| **测试覆盖率** | 60%+ |

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🔗 相关链接

- **GitHub**: https://github.com/srxly888-creator/autonomous-agent-stack
- **MASFactory**: https://github.com/BUPT-GAMMA/MASFactory
- **OpenClaw**: https://github.com/openclaw/openclaw

---

**一起构建未来！** 🚀
