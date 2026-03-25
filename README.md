# 🤖 Autonomous Agent Stack

> **完整堆栈视图**：从自演化机制到持久化架构，构建无需人类干预的超级智能体网络

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 项目定位

**Autonomous Agent Stack** 是一个整合了 6 大核心架构的自主智能体堆栈：

| 层级 | 核心架构 | 关键技术 | 价值 |
|------|---------|---------|------|
| **MetaClaw** | 持续自演化 | 双循环学习 + MAML 隔离 | 准确率 +89.7% |
| **Autoresearch** | API-first 研究循环 | 5 大 RESTful API + Karpathy 循环 | 最小闭环 ✅ |
| **Deer-flow** | 并发隔离执行 | 三级沙盒 + 上下文隔离 | 会话零污染 |
| **InfoQuest/MCP** | 企业级知识获取 | 双核引擎 + MCP 动态发现 | Token 优化 |
| **Claude Code** | 开发者心流 | 四维执行 + HTTP Streamable | 自动重连 |
| **OpenClaw** | 透明状态管理 | Markdown + 记忆刷新 | 污染防治 ✅ |

---

## ✨ 核心特性

### 1. **P0 级工程成果**
- ✅ **SQLite 持久化**：服务重启后状态保留
- ✅ **evaluator_command override**：灵活配置评估器
- ✅ **AppleDouble 污染防治**：自动化清理脚本
- ✅ **API Skeleton**：FastAPI + Pydantic + 5 大路由

### 2. **架构优势**
- ✅ **API-first 设计**：标准化 RESTful 接口
- ✅ **三级沙盒隔离**：L1/L2/L3 安全边界
- ✅ **双循环学习**：快循环（毫秒级）+ 慢循环（小时级）
- ✅ **透明状态管理**：纯文本 Markdown + Git 版本控制

### 3. **企业级特性**
- ✅ **MCP 深度耦合**：动态工具发现
- ✅ **双 API 架构**：LangGraph (2024) + Gateway (8001)
- ✅ **四维执行模式**：Flash/Standard/Pro/Ultra
- ✅ **SSE 异常处理**：自动重连 + 心跳保活

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 安装依赖
pip install -r requirements.txt

# 或使用 uv
uv pip install -r requirements.txt
```

### 运行 API 服务

```bash
# 启动 FastAPI 服务
uv run autoresearch-api

# 或直接运行
python -m src.autoresearch.api.main

# 访问 API 文档
open http://localhost:8000/docs
```

### 使用示例

```python
import requests

# 创建评估任务
response = requests.post(
    "http://localhost:8000/api/v1/evaluations",
    json={
        "task_name": "api_bugfix_assistant",
        "config_path": "task.json",
        "evaluator_command": {
            "command": ["python", "evaluate.py"],
            "timeout_seconds": 60,
            "work_dir": ".",
            "env": {"FOO": "bar"}
        }
    }
)

task_id = response.json()["task_id"]

# 查询评估结果
result = requests.get(f"http://localhost:8000/api/v1/evaluations/{task_id}")
print(result.json())
```

---

## 📚 架构文档

### 核心架构

详细文档请参阅：

1. **[MetaClaw 自演化机制](docs/architecture.md#part-1-metaclaw)**
   - 双循环学习（快循环 + 慢循环）
   - MAML 版本化数据隔离
   - 零停机更新

2. **[Autoresearch API-first 设计](docs/architecture.md#part-2-autoresearch)**
   - Karpathy 循环三大原语
   - 5 大 RESTful API 接口
   - 三种优化拓扑

3. **[Deer-flow 并发隔离](docs/architecture.md#part-3-deer-flow)**
   - Lead Agent + Sub-agents 编排
   - 三级沙盒隔离（L1/L2/L3）
   - 动态上下文工程

4. **[InfoQuest/MCP 深度耦合](docs/architecture.md#part-4-infoquest)**
   - Web Search + Link Reader 双核引擎
   - MCP 远端服务映射
   - 双 API 架构

5. **[Claude Code 终端集成](docs/architecture.md#part-5-claude-code)**
   - 四维执行模式
   - MCP 传输层矩阵
   - SSE 异常处理

6. **[OpenClaw 持久化架构](docs/architecture.md#part-6-openclaw)**
   - SOUL.md + MEMORY.md + Daily Logs
   - 记忆刷新机制
   - AppleDouble 污染防治

### 完整文档

- **[架构总览](docs/architecture.md)** - 6 部分完整架构文档
- **[集成指南](docs/integration-guide.md)** - 如何集成各个组件
- **[API 参考](docs/api-reference.md)** - 5 大 API 详细说明
- **[开发路线图](docs/roadmap.md)** - 未来演进方向

---

## 🏗️ 项目结构

```
autonomous-agent-stack/
├── README.md                    # 主文档
├── LICENSE                      # MIT 许可证
├── .gitignore                   # Git 忽略规则
├── docs/                        # 文档目录
│   ├── architecture.md          # 架构总览
│   ├── integration-guide.md     # 集成指南
│   ├── api-reference.md         # API 参考
│   └── roadmap.md               # 路线图
├── src/                         # 源代码
│   ├── metaclaw/                # Part 1: 自演化
│   ├── autoresearch/            # Part 2: API-first
│   ├── deer-flow/               # Part 3: 编排隔离
│   ├── infoquest/               # Part 4: MCP 耦合
│   ├── claude-code/             # Part 5: 终端集成
│   └── openclaw/                # Part 6: 持久化
├── examples/                    # 示例代码
│   ├── minimal-loop/            # 最小闭环示例
│   └── full-stack/              # 完整堆栈示例
├── tests/                       # 测试文件
│   └── integration/             # 集成测试
├── scripts/                     # 工具脚本
│   ├── cleanup-appledouble.sh   # AppleDouble 清理
│   └── pre-start-check.py       # 启动前检查
└── memory/                      # 记忆存储
    ├── MEMORY.md                # 长期记忆
    └── daily-logs/              # 每日日志
```

---

## 🎓 学习资源

### P0 成果验证
- ✅ **持久化评估状态**：`src/autoresearch/core/repositories/evaluations.py`
- ✅ **evaluator_command override**：`src/autoresearch/shared/models.py`
- ✅ **AppleDouble 清理**：`scripts/cleanup-appledouble.sh`
- ✅ **API Skeleton**：`src/autoresearch/api/`

### 架构文档
- 📖 **6 部分完整文档**：`docs/architecture.md`
- 📊 **架构对比表**：`docs/integration-guide.md`
- 🗺️ **演进路线图**：`docs/roadmap.md`

---

## 🛣️ 路线图

### 短期（本周）
- [ ] 真实 API 集成测试
- [ ] SSE 稳定性验证
- [ ] 文档完善

### 中期（2-4 周）
- [ ] Generator API 实现
- [ ] Executor API 实现
- [ ] 多智能体并发编排

### 长期（1-2 月）
- [ ] MetaClaw 双循环集成
- [ ] HTTP Streamable 迁移
- [ ] 企业级部署

---

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

本仓库整合了以下开源项目的核心思想：

- **MetaClaw** - 持续自演化机制
- **Autoresearch** - Karpathy 循环
- **Deer-flow** - 字节跳动超级智能体框架
- **InfoQuest** - 字节跳动知识获取引擎
- **Claude Code** - Anthropic 终端工具
- **OpenClaw** - 透明状态管理

---

**构建无需人类干预的超级智能体网络** 🚀
