# 🎯 集成指南

> **快速集成 Autonomous Agent Stack 到你的项目**

---

## 📋 前置要求

### 必需
- Python 3.10+
- FastAPI 0.115+
- SQLite 3.0+

### 可选（按需安装）
- Docker（L2 沙盒隔离）
- Kubernetes（L3 企业级部署）
- Anthropic API Key（Claude Code 集成）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 安装依赖
pip install fastapi uvicorn pydantic sqlalchemy

# 或使用 requirements.txt
pip install -r requirements.txt
```

### 2. 启动 API 服务

```bash
# 启动 FastAPI 服务
uvicorn src.autoresearch.api.main:app --reload --port 8000

# 访问 API 文档
open http://localhost:8000/docs
```

### 3. 创建评估任务

```python
import requests

# 创建评估任务
response = requests.post(
    "http://localhost:8000/api/v1/evaluations",
    json={
        "task_name": "my_first_task",
        "config_path": "task.json",
        "description": "首次集成测试",
        "evaluator_command": {
            "command": ["python", "evaluate.py"],
            "timeout_seconds": 60,
            "work_dir": ".",
            "env": {"DEBUG": "true"}
        }
    }
)

task_id = response.json()["task_id"]
print(f"任务 ID: {task_id}")
```

### 4. 查询评估结果

```python
# 查询评估结果
result = requests.get(f"http://localhost:8000/api/v1/evaluations/{task_id}")

print(f"状态: {result.json()['status']}")
print(f"结果: {result.json()['result']}")
```

---

## 🔧 核心组件集成

### 1. SQLite 持久化

**自动配置**：
```python
# 默认路径: artifacts/api/evaluations.sqlite3
# 或通过环境变量覆盖
import os
os.environ["AUTORESEARCH_API_DB_PATH"] = "/path/to/your/db.sqlite3"
```

**手动初始化**：
```python
from src.autoresearch.core.repositories.evaluations import Database

# 初始化数据库
db = Database("path/to/evaluations.sqlite3")

# 创建表
# 自动创建（首次运行时）
```

### 2. evaluator_command override

**基础用法**：
```python
{
    "evaluator_command": {
        "command": ["python", "evaluate.py"],
        "timeout_seconds": 60,
        "work_dir": ".",
        "env": {"FOO": "bar"}
    }
}
```

**高级用法**：
```python
{
    "evaluator_command": {
        "command": ["python", "-m", "pytest", "tests/"],
        "timeout_seconds": 300,
        "work_dir": "/workspace/project",
        "env": {
            "PYTHONPATH": "/workspace/lib",
            "TEST_ENV": "integration"
        }
    }
}
```

### 3. AppleDouble 污染防治

**自动清理**：
```bash
# 启动前自动清理
python scripts/pre-start-check.py

# 手动清理
bash scripts/cleanup-appledouble.sh
```

**集成到 CI/CD**：
```yaml
# .github/workflows/ci.yml
- name: Clean AppleDouble
  run: python scripts/pre-start-check.py
```

---

## 📚 架构组件集成

### Part 1: MetaClaw 自演化

**快循环集成**：
```python
from src.metaclaw import SkillEvolver

# 初始化技能进化器
evolver = SkillEvolver()

# 从失败中生成新技能
new_skill = evolver.generate_skill(
    failure_trajectory=failed_task_log,
    context=current_context
)

# 即时注入
evolver.inject_skill(new_skill)
```

**慢循环集成**：
```python
from src.metaclaw import OMLS

# 初始化机会主义调度器
scheduler = OMLS()

# 检测空闲窗口
if scheduler.is_idle_window():
    # 触发 RL 训练
    scheduler.trigger_training(batch_data)
```

---

### Part 2: Autoresearch API-first

**5 大 API 集成**：

```python
# 1. Evaluator API（已实现）
POST /api/v1/evaluations

# 2. Generator API（待实现）
POST /api/v1/generators

# 3. Executor API（待实现）
POST /api/v1/executors

# 4. Synthesis API（待实现）
POST /api/v1/synthesis

# 5. Loop Control API（待实现）
POST /api/v1/loops
```

---

### Part 3: Deer-flow 并发隔离

**L2 Docker 沙盒**：
```python
from src.deer_flow import AioSandboxProvider

# 初始化 Docker 沙盒
sandbox = AioSandboxProvider()

# 执行任务
result = await sandbox.execute(
    command=["python", "task.py"],
    timeout=900,  # 15 分钟
    work_dir="/workspace"
)
```

**并发编排**：
```python
from src.deer_flow import LeadAgent

# 初始化 Lead Agent
lead = LeadAgent(max_parallel=3)

# 派生子智能体
sub_agents = lead.spawn_subagents([
    {"task": "data_collection", "tools": ["web_search"]},
    {"task": "analysis", "tools": ["python", "pandas"]},
    {"task": "visualization", "tools": ["matplotlib"]}
])

# 并发执行
results = await lead.execute_parallel(sub_agents)
```

---

### Part 4: InfoQuest/MCP 深度耦合

**MCP 配置**：
```python
from src.infoquest import MCPClient

# 初始化 MCP 客户端
mcp = MCPClient(
    endpoint="https://mcp.infoquest.bytepluses.com/mcp",
    auth_token="your_token"
)

# 动态发现工具
tools = mcp.discover_tools()

# 调用工具
result = mcp.call_tool("web_search", {
    "query": "AI agent architecture 2026",
    "domain": "arxiv.org",
    "time_period": "last_30_days"
})
```

---

### Part 5: Claude Code 终端集成

**四维执行模式**：
```python
from src.claude_code import ExecutionMode

# Flash 模式（快速问答）
result = execute("What is Python?", mode=ExecutionMode.FLASH)

# Standard 模式（代码重构）
result = execute("Refactor this code", mode=ExecutionMode.STANDARD)

# Pro 模式（项目搭建）
result = execute("Create REST API", mode=ExecutionMode.PRO)

# Ultra 模式（深度研究）
result = execute("Research AI trends", mode=ExecutionMode.ULTRA)
```

---

### Part 6: OpenClaw 持久化架构

**记忆管理**：
```python
from src.openclaw import MemoryManager

# 初始化记忆管理器
memory = MemoryManager()

# 写入长期记忆
memory.write_to_memory(
    key="user_preference",
    value="prefer concise responses",
    confidence=0.9
)

# 读取记忆
pref = memory.read_from_memory("user_preference")

# 记忆刷新（Token 上限时）
memory.flush_short_term_memory()
```

---

## 🧪 测试集成

### 单元测试

```python
# tests/test_my_integration.py
from fastapi.testclient import TestClient
from src.autoresearch.api.main import app

client = TestClient(app)

def test_create_evaluation():
    response = client.post(
        "/api/v1/evaluations",
        json={
            "task_name": "test_task",
            "config_path": "test.json"
        }
    )
    assert response.status_code == 200
    assert "task_id" in response.json()
```

### 集成测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_evaluation_api.py -v
```

---

## 🚨 故障排查

### 常见问题

#### 1. SQLite 锁定错误
```
sqlite3.OperationalError: database is locked
```

**解决方案**：
```python
# 增加超时时间
db = Database("evaluations.sqlite3", timeout=30)
```

#### 2. AppleDouble 污染
```
SyntaxError: invalid syntax in ._script.py
```

**解决方案**：
```bash
# 运行清理脚本
python scripts/pre-start-check.py
```

#### 3. SSE 流式挂起
```
SSE connection stalled for 138.6s
```

**解决方案**：
```python
# 增加超时时间
client = TestClient(app, timeout=300)
```

---

## 📖 最佳实践

### 1. 错误处理

```python
try:
    result = requests.post("/api/v1/evaluations", json=data)
    result.raise_for_status()
except requests.exceptions.Timeout:
    print("请求超时，请增加 timeout_seconds")
except requests.exceptions.HTTPError as e:
    print(f"HTTP 错误: {e.response.status_code}")
```

### 2. 日志记录

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("评估任务已创建")
```

### 3. 性能优化

```python
# 批量创建任务
tasks = [
    {"task_name": f"task_{i}", "config_path": "task.json"}
    for i in range(10)
]

# 并发执行
import asyncio
results = await asyncio.gather(*[
    create_evaluation(task) for task in tasks
])
```

---

## 🔗 相关资源

- **主文档**: [README.zh-CN.md](../README.zh-CN.md)
- **架构文档**: [ARCHITECTURE.zh-CN.md](../ARCHITECTURE.zh-CN.md)
- **API 参考**: [api-reference.md](api-reference.md)
- **路线图**: [roadmap.md](roadmap.md)

---

## 💬 获取帮助

- **GitHub Issues**: https://github.com/srxly888-creator/autonomous-agent-stack/issues
- **文档**: https://github.com/srxly888-creator/autonomous-agent-stack#readme

---

**集成愉快！** 🚀
