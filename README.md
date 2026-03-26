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

## 说明

- 这份 README 只记录已经落到代码里的功能
- 某些工具脚本依赖额外运行环境，例如 `aiohttp`、`pip-compile` 或外部服务
- 如果你要判断当前能力是否能直接生产使用，建议同时查看 `STATUS_AND_RELEASE_NOTES.md` 和 `docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md`

### 配套文档
- `docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md`
- `docs/48-hour-action-plan.md`
- `docs/auto-cruise-config.md`
- `docs/zero-trust-implementation-plan-v2.md`
