# Foundation Integration Layer

## 概述

`src/foundation/` 提供统一的任务编排基础层，用于集成现有模块（ excel_audit, github_admin, content_kb）。

## 核心组件

### 1. 统一契约 (`contracts.py`)

- `JobSpec` - 统一任务规格
- `DriverResult` - 驱动执行结果
- `RunState` - 任务状态枚举 (queued, running, succeeded, failed, needs_review, timed_out, cancelled)
- `RunDecision` - 门禁决策 (accept, retry, fallback, needs_review)
- `JobContext` - 执行上下文 (dry_run, requires_approval, timeout)
- `ApprovalRequirement` - 审批要求

### 2. Manifest Loader (`manifest_loader.py`)

- `AgentManifest` - Agent 配置清单
- `AgentRegistry` - Agent 注册表
- `load_manifest()` - 加载单个 manifest
- `scan_agents_directory()` - 扫描 agents/ 目录

### 3. Router (`router.py`)

- `Router` - 任务路由器
- `ButlerCompatAdapter` - 兼容现有 butler 的适配器

### 4. State Machine (`state_machine.py`)

- `RunStateMachine` - 状态机实现
- `InvalidStateTransition` - 非法状态转换异常

### 5. Task Gate (`gate.py`)

- `TaskGate` - 统一任务门禁
- 5 个检查维度：success, policy/permission, timeout, critical artifact, human approval

### 6. Approvals (`approvals.py`)

- `ApprovalManager` - 审批管理器
- `ApprovalStore` - 审批存储（内存实现）
- `ApprovalDecision` - 审批决策

### 7. Adapters (`adapters.py`)

- `excel_audit_to_spec()` / `excel_audit_from_spec()` - Excel 审计适配器
- `github_admin_to_spec()` / `github_admin_from_spec()` - GitHub 管理适配器
- `content_kb_to_spec()` / `content_kb_from_spec()` - 内容知识库适配器

## Agent Manifests

现有 agent manifests 位于 `agents/` 目录：

- `agents/excel_audit/manifest.yaml` - Excel 审计 agent
- `agents/github_admin/manifest.yaml` - GitHub 管理 agent
- `agents/content_kb/manifest.yaml` - 内容知识库 agent
- `agents/butler_orchestrator/manifest.yaml` - Butler 编排器

## 使用示例

```python
from foundation import Router, JobSpec, JobContext

# 初始化路由器
router = Router(agents_dir="agents")
router.initialize()

# 路由任务
result = router.route("Excel核对任务", task_type="excel_audit")
if result:
    print(f"Agent: {result.agent_id}")
    print(f"Task Type: {result.task_type}")
    print(f"Confidence: {result.confidence}")

# 创建 JobSpec
job_spec = router.route_to_job_spec(
    task="核对提成计算",
    task_type="excel_audit",
    dry_run=True
)
```

## 与现有系统集成

### Butler 兼容适配器

```python
from foundation import Router, ButlerCompatAdapter

router = Router(agents_dir="agents")
adapter = ButlerCompatAdapter(router)

# 使用适配器路由
result = adapter.route(
    task="Excel核对任务",
    task_type="excel_audit",
    attachments=["file.xlsx"],
    dry_run=True
)
```

### Excel Audit 适配器

```python
from foundation.adapters import excel_audit_to_spec, excel_audit_from_spec

# 转换现有 excel_audit spec 为 JobSpec
spec = excel_audit_to_spec(existing_spec)

# 反向转换
result = excel_audit_from_spec(spec)
```

## 测试

运行 foundation 测试：

```bash
pytest tests/foundation/ -v
```

## 文件结构

```
src/foundation/
├── __init__.py
├── contracts.py        # 统一契约
├── manifest_loader.py  # Manifest 加载器
├── router.py          # 路由器
├── state_machine.py   # 状态机
├── gate.py            # 任务门禁
├── approvals.py       # 审批机制
├── adapters.py        # 现有模块适配器
└── butler_compat.py   # Butler 兼容适配器

agents/
├── excel_audit/manifest.yaml
├── github_admin/manifest.yaml
├── content_kb/manifest.yaml
└── butler_orchestrator/manifest.yaml

tests/foundation/
└── test_integration.py  # 集成测试
```
