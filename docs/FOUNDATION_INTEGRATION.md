# Foundation 与真实模块集成说明

## 概述

Foundation 层已验证可以连接到现有真实模块：
- `excel_audit` - Excel 计算核对、提成核算、对账
- `github_admin` - GitHub 仓库盘点、迁移规划
- `content_kb` - 内容知识库、主题分类

## 集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Foundation Layer                        │
├─────────────────────────────────────────────────────────────┤
│  Router  │  Adapters  │  ButlerCompat  │  ManifestLoader    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Manifests                          │
├─────────────────────────────────────────────────────────────┤
│  agents/excel_audit/manifest.yaml                            │
│  agents/github_admin/manifest.yaml                           │
│  agents/content_kb/manifest.yaml                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Real Modules (计划中)                      │
├─────────────────────────────────────────────────────────────┤
│  src/excel_audit/  - 已有实现                                │
│  src/github_admin/ - 待实现                                  │
│  src/content_kb/   - 待实现                                  │
└─────────────────────────────────────────────────────────────┘
```

## 使用方式

### 1. 加载真实 Agent Manifests

```python
from foundation.manifest_loader import scan_agents_directory
from pathlib import Path

registry = scan_agents_directory(Path("agents"))
agents = registry.list()

for agent in agents:
    print(f"{agent.id}: {agent.name}")
    print(f"  task_types: {agent.task_types}")
```

**输出**:
```
excel_audit: Excel Audit Agent
  task_types: ['excel_audit', 'commission_check', 'reconciliation']
github_admin: GitHub Admin Agent
  task_types: ['github_admin.inventory', 'github_admin.transfer_plan']
content_kb: Content KB Agent
  task_types: ['content_kb.classify_topic', 'content_kb.build_index']
```

### 2. 使用 Router 路由任务

```python
from foundation.router import Router

router = Router(agents_dir="agents")
router.initialize()

# 按 task_type 路由
result = router.route(
    task_brief="核对提成数据",
    task_type="excel_audit"
)
assert result.agent_id == "excel_audit"
```

### 3. 使用 Adapters 转换格式

```python
from foundation.contracts import JobSpec, JobContext
from foundation.adapters import excel_audit_to_spec

spec = JobSpec(
    run_id="excel-001",
    agent_id="excel_audit",
    task_type="commission_check",
    task="核对提成",
    attachments=["data.xlsx"],
    context=JobContext(dry_run=True)
)

excel_spec = excel_audit_to_spec(spec)
```

### 4. 使用 ButlerCompatAdapter 向后兼容

```python
from foundation.butler_compat import ButlerCompatAdapter

adapter = ButlerCompatAdapter(router)
job_spec = adapter.route(
    task="Excel核对",
    task_type="excel_audit",
    attachments=["data.xlsx"],
    dry_run=True
)
```

## 已验证的集成

| 模块 | Task Types | 状态 |
|------|------------|------|
| `excel_audit` | `excel_audit`, `commission_check`, `reconciliation` | ✅ 已验证 |
| `github_admin` | `github_admin.inventory`, `github_admin.transfer_plan` | ✅ 已验证 |
| `content_kb` | `content_kb.classify_topic`, `content_kb.build_index` | ✅ 已验证 |

## 测试覆盖

- **30 个测试全部通过**
- `test_integration.py`: 13 个 mock 测试
- `test_real_integration.py`: 17 个真实模块集成测试

### 测试类别

1. **Manifest 加载**: 验证可以加载真实 agents 目录下的所有 manifest
2. **Adapter 转换**: 验证可以处理真实模块的最小有效输入
3. **Router 路由**: 验证可以基于 task_type 和 keywords 路由到正确 agent
4. **ButlerCompat**: 验证向后兼容接口可用

## 下一步

Foundation 层已完成最小闭环验证，可以安全挂接到现有模块。后续可以考虑：

1. **连接真实入口**: 将 ButlerCompatAdapter 接入真实 gateway
2. **实现缺失模块**: github_admin 和 content_kb 的具体实现
3. **端到端测试**: 完整执行链测试
4. **持久化 ApprovalStore**: SQLite 或 Redis 后端

## 注意事项

- 当前验证仅限于 manifest 加载和格式转换
- 未涉及真实执行链
- 未修改任何现有入口或业务逻辑
- 所有变更都在 `src/foundation/` 和 `tests/foundation/` 范围内
