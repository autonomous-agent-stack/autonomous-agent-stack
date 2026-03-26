# Autonomous Agent Stack

一个面向多智能体编排、工作流触发、零信任审计和自集成验证的工程化仓库。

## 已实现功能

### 多智能体编排
- 图式编排引擎
- Planner / Generator / Executor / Evaluator 链路
- prompt 驱动的图编排
- 回环重试与流程回退

### 工作流引擎
- `src/workflow/workflow_engine.py` 工作流引擎 v2.0
- GitHub 深度审查流水线
- 语言分布分析与报告组装
- 与 Telegram Webhook 结合的指令触发

### Telegram 网关
- `/telegram/webhook` 指令拦截
- `执行审查` / `#1` 快捷触发
- 异步执行工作流并投递结果

### 自集成协议
- `/api/v1/integrations/discover`
- `/api/v1/integrations/prototype`
- `/api/v1/integrations/prototype/{prototype_id}/secure-fetch`
- `/api/v1/integrations/promote`
- 依赖请求、审计产物、SBOM、hash manifest、评估门禁

### OpenSage / Skill Registry
- 本地技能扫描与挂载
- 远端技能下载与验证
- AST 安全审计
- 技能执行与集市验证

### 安全与零信任
- 依赖哈希锁定
- Docker / Colima 沙盒执行
- AppleDouble / `.DS_Store` 清理
- 访问控制与面板审计
- 零信任加固脚本与方案文档

## 关键入口

- API 服务：`src/autoresearch/api/main.py`
- 自集成服务：`src/autoresearch/core/services/self_integration.py`
- 自集成路由：`src/autoresearch/api/routers/integrations.py`
- Telegram Webhook：`src/gateway/telegram_webhook.py`
- 工作流引擎：`src/workflow/workflow_engine.py`
- 技能注册表：`src/opensage/skill_registry.py`
- 零信任脚本：`scripts/zero-trust-dependencies.sh`

## 快速开始

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
.venv/bin/python -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
open http://127.0.0.1:8000/health
```

工作流点火测试：

```bash
.venv/bin/python tests/test_workflow_quick.py
```

技能注册表简化验证：

```bash
.venv/bin/python scripts/test_registry_simple.py
```

## 专业小 Agent 最佳实践（可打包、可编排）

### 你现在该做什么（推荐顺序）

1. 先做一个单点高价值 Agent，不做“大而全”。
2. 固化输入输出契约，再接 Skill 与 MCP。
3. 用 MAS Factory 先跑通最小闭环，再扩展并发与重试策略。
4. 通过最小测试集后再打包发布。

### 1) 如何设计一个小而专业的 Agent

原则：`1 Agent = 1 职责域 = 1 KPI`。

- 职责域示例：`repo-health-agent`（仅做仓库健康度审查）。
- 统一输入：`repo`、`branch`、`depth`。
- 统一输出：`status`、`score`、`findings`、`next_actions`。
- 统一失败：`error_code`、`error_message`、`retryable`。

建议目录（兼容插件式和 OpenClaw 技能目录）：

```text
skills/repo-health-agent/
├── skill.json
├── SKILL.md
├── main.py
├── README.md
└── tests/test_repo_health_agent.py
```

`main.py` 最小入口（兼容 `SkillLoader`）：

```python
class Skill:
    def execute(self, payload, credentials=None):
        repo = payload.get("repo", "")
        if not repo:
            return {
                "status": "error",
                "error_code": "MISSING_REPO",
                "retryable": False,
            }
        return {
            "status": "success",
            "score": 0.92,
            "findings": [],
            "next_actions": ["run_full_scan"],
        }
```

### 2) 如何加载通用 Skill

方式 A：本地动态加载（`src/bridge/skill_loader.py`）

```python
from pathlib import Path
from src.bridge.skill_loader import SkillLoader

loader = SkillLoader(
    base_path=Path("skills"),
    enable_security_scan=True,
    strict_mode=True,  # 生产建议开启
)

skill = await loader.load_skill("repo-health-agent/main.py")
result = skill.execute({"repo": "srxly888-creator/autonomous-agent-stack"})
```

方式 B：会话级注入（`/api/v1/openclaw/sessions/{session_id}/skills`）

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/openclaw/sessions/<session_id>/skills" \
  -H "Content-Type: application/json" \
  -d '{
    "skill_names": ["repo-health-agent"],
    "merge": true
  }'
```

可通过环境变量扩展技能目录：

```bash
export AUTORESEARCH_OPENCLAW_SKILLS_DIRS="/absolute/path/to/skills"
```

### 3) 如何加载通用 MCP

运行时调用层：`MCPContextBlock`（`src/orchestrator/mcp_context.py`）

```python
from src.orchestrator import MCPContextBlock

async def web_search(params: dict):
    return {"result": f"mock search: {params['query']}"}

mcp = MCPContextBlock()
mcp.register_tool("web_search", web_search)
tool_result = await mcp.call_tool("web_search", {"query": "agent orchestration"})
```

契约治理层：`MCPRegistry`（`src/orchestrator/mcp_registry.py`）

```python
from src.orchestrator.mcp_registry import MCPRegistry

registry = MCPRegistry()
registry.load_manifest("mcp.manifest.json")
assert registry.validate_input("web_search", {"query": "hello"})
```

建议：`MCPRegistry` 管 Schema，`MCPContextBlock` 管调用与缓存。

### 4) 如何用 MAS Factory 灵活编排

模式 A：Prompt DSL 图编排（`create_graph_from_prompt`）

```python
from src.orchestrator import create_graph_from_prompt

prompt = """
goal: 生成仓库健康度审查报告
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 12
max_concurrency: 3
"""

graph = create_graph_from_prompt(prompt, graph_id="repo_health_v1")
results = await graph.execute()
```

模式 B：能力匹配编排（`src/bridge/mas_factory_bridge.py`）

```python
from src.bridge.mas_factory_bridge import MASFactoryBridge, AgentSpec, TaskSpec

bridge = MASFactoryBridge()

async def repo_health_executor(desc: str, meta: dict):
    return {"status": "success", "summary": desc, "meta": meta}

await bridge.register_agent(
    AgentSpec(
        agent_id="repo_health_001",
        name="RepoHealthAgent",
        capabilities=["repo_audit", "risk_scoring"],
        priority=10,
    ),
    executor=repo_health_executor,
)

await bridge.submit_task(
    TaskSpec(
        task_id="task_repo_health_001",
        description="审查主分支稳定性与风险",
        required_capabilities=["repo_audit"],
        timeout=120,
    )
)

result = await bridge.orchestrate("task_repo_health_001", strategy="capability_match")
```

### 5) 发布前最小验收

```bash
pytest tests/test_prompt_orchestration.py -v
pytest tests/test_dynamic_tool_synthesis.py -v
pytest tests/test_mcp_registry.py -v
pytest tests/test_bridge_api.py -v
```

```bash
python3 quickstart.py
```

## 说明

- 这份 README 只记录已经落到代码里的功能
- 某些工具脚本依赖额外运行环境，例如 `aiohttp`、`pip-compile` 或外部服务
- 如果你要判断当前能力是否能直接生产使用，建议同时查看 `STATUS_AND_RELEASE_NOTES.md` 和 `docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md`

### 配套文档
- `docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md`
- `docs/masfactory-integration.md`（含 Prompt 编排最佳实践）
- `docs/vscode-direct-orchestration.md`（VS Code 直连运行手册）
- `docs/48-hour-action-plan.md`
- `docs/auto-cruise-config.md`
- `docs/zero-trust-implementation-plan-v2.md`
