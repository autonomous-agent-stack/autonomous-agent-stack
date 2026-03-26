# Autonomous Agent Stack

一个面向多智能体编排、工作流触发、自集成验证和零信任加固的工程化仓库。

## 为什么现在更容易上手

参考 ClawX 的使用体验，这个仓库把新手最常见的三个问题做了统一入口。

| 常见痛点 | 现在的做法 |
| --- | --- |
| 启动命令太多，不知道先跑哪个 | `make setup -> make doctor -> make start` |
| 报错信息分散，定位慢 | `scripts/doctor.py` 统一体检并给出下一步建议 |
| 文档和实际入口不一致 | README、Makefile、启动脚本使用同一套命令 |

## 3 分钟上手

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
make setup
make doctor
make start
```

启动后可访问：

- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/panel`

## 常用命令

```bash
make help
make setup
make doctor
make start
make test-quick
make ai-lab
make ai-lab-check
make ai-lab-setup
make masfactory-flight
```

如果端口冲突：

```bash
PORT=8010 make start
```

## 你可以拿它做什么

- 从 Telegram 触发仓库审查任务
- 生成带语言分布的审查报告
- 为外部仓库生成 prototype，并在 secure-fetch 后推进 promotion
- 扫描并执行本地技能
- 运行零信任加固脚本和相关验证脚本

## 关键入口

- [API 主入口](./src/autoresearch/api/main.py)
- [工作流引擎](./src/workflow/workflow_engine.py)
- [Telegram Webhook](./src/gateway/telegram_webhook.py)
- [自集成服务](./src/autoresearch/core/services/self_integration.py)
- [自集成路由](./src/autoresearch/api/routers/integrations.py)
- [技能注册表](./src/opensage/skill_registry.py)
- [MASFactory 骨架](./src/masfactory/graph.py)
- [MASFactory 首航示例](./examples/masfactory_first_flight.py)

## 快速排错

1. 先跑 `make doctor`，看是否有 `FAIL`
2. 如果是依赖问题，执行 `make setup`
3. 如果是端口问题，执行 `PORT=8010 make start`
4. 如果是导入问题，确认通过 `make start` 启动（脚本会自动设置 `PYTHONPATH=src`）

## 深入文档

- [快速启动文档](./docs/QUICK_START.md)
- [Admin View 字段填写教程](./docs/admin-view-field-guide.md)
- [状态与发布说明](./STATUS_AND_RELEASE_NOTES.md)
- [工作流引擎验证报告](./docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md)
- [自集成协议](./docs/p4-self-integration-protocol.md)
- [零信任实施方案](./docs/zero-trust-implementation-plan-v2.md)
