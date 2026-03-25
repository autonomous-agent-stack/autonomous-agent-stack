# OpenClaw 替代迁移最佳实践（Playbook）

> 目标：将现有 OpenClaw 工作流平滑迁移到 `autonomous-agent-stack`，并以最小风险实现“可回滚、可观测、可扩展”的生产运行。

---

## 1. 文档定位

本文件是工程落地手册，不是概念介绍。重点回答三件事：

1. 如何分阶段迁移，避免一次性切换导致业务中断。
2. 如何用新底座承接 OpenClaw 的会话/调度/执行能力。
3. 如何建立安全边界（Docker 隔离）与可回滚机制。

适用对象：
- 当前已经运行 OpenClaw 的团队
- 希望接入 Claude CLI 子 agent 调度
- 需要在 macOS（尤其 M1 + 外置盘）稳定运行的场景

---

## 2. 当前能力边界（截至 2026-03-25）

已具备：
- OpenClaw 兼容会话层：会话创建、事件追加、状态持久化（SQLite）
- Claude 子 agent 调度：排队/执行/状态跟踪（并发与代际限制）
- Dynamic Tool Synthesis 默认 Docker 沙盒执行（local 仅用于调试）
- API-first 5 大接口骨架 + 测试通过

未完全覆盖（迁移时需注意）：
- Telegram/Webhook 全链路接管（需按你的网关生态定制）
- OpenClaw 全通道协议 1:1 兼容（当前是兼容层，不是字节级复刻）

---

## 3. 迁移总原则（Best Practices）

1. **先并行、后切流、再下线**
   - 先让新旧系统并行跑同一任务集。
   - 指标对齐后，灰度切流。
   - 稳定窗口结束再关闭 OpenClaw 主进程。

2. **每一步都可回滚**
   - 每次迁移动作都应有“恢复到上一状态”的明确命令与数据快照。

3. **先安全后智能**
   - 动态代码执行默认进 Docker 隔离。
   - 不要在宿主机直接跑合成工具（除非本地调试且可控）。

4. **指标先行**
   - 没有观测，不做切换。
   - 至少监控：成功率、平均时延、失败类型分布、资源占用峰值。

5. **限制代理繁衍**
   - 强制代际深度与并发上限，防止 runaway spawning。

---

## 4. OpenClaw → 新底座能力映射

| OpenClaw 能力 | 新底座承接模块 | 迁移动作 |
|---|---|---|
| 会话与状态记录 | `OpenClawCompatService` | 将会话入口切至 `/api/v1/openclaw/sessions` |
| 子任务执行 | `ClaudeAgentService` | 将 agent spawn 入口切至 `/api/v1/openclaw/agents` |
| 动态工具执行 | `ToolSynthesizer` (Docker backend) | 默认 `AUTORESEARCH_TOOL_SANDBOX_BACKEND=docker` |
| 结果与运行状态持久化 | SQLite (`AUTORESEARCH_API_DB_PATH`) | 保持单库或分库策略，先单库后拆分 |
| 监控与追踪 | API + SSE + Dashboard | 将历史任务映射到统一看板 |

---

## 5. 分阶段迁移方案（推荐）

### Phase 0：基线冻结（0.5 天）

目标：固定可比基线，防止迁移中指标失真。

- 冻结 OpenClaw 当前配置（agent prompt、工具列表、超时策略）。
- 导出最近 7 天代表任务集（建议 30~100 条）。
- 记录基线指标：
  - P50/P95 任务时延
  - 成功率
  - 失败 Top5 原因
  - 单任务 Token 消耗区间（如可得）

交付物：
- `migration/baseline-metrics.md`
- `migration/golden-taskset.json`

---

### Phase 1：双写会话层（1 天）

目标：先迁“记账系统”，不迁“执行系统”。

- 保留 OpenClaw 主执行链路不变。
- 在入口处增加会话镜像写入到新 API：
  - `POST /api/v1/openclaw/sessions`
  - `POST /api/v1/openclaw/sessions/{session_id}/events`
- 验证会话完整性（事件顺序、状态一致性）。

验收标准：
- 会话镜像成功率 ≥ 99.9%
- 写入延迟可接受（建议 < 100ms/事件）

---

### Phase 2：子 agent 调度灰度（1~2 天）

目标：将“部分子任务”由新调度器执行。

- 将低风险任务（无外部副作用）先切到：
  - `POST /api/v1/openclaw/agents`
- 关键参数：
  - `AUTORESEARCH_AGENT_MAX_CONCURRENCY=20`（可从 5 起步）
  - `AUTORESEARCH_AGENT_MAX_DEPTH=3`
- 灰度比例建议：
  - Day1: 10%
  - Day2: 30%
  - 稳定后 60%+

验收标准：
- 灰度组成功率不低于对照组
- 无明显排队雪崩与资源耗尽

---

### Phase 3：动态工具执行切 Docker（0.5~1 天）

目标：把风险最高环节放进强隔离容器。

- 确认 Docker/Colima 可用（M1 场景建议已完成外置盘配置）。
- 设置：
  - `AUTORESEARCH_TOOL_SANDBOX_BACKEND=docker`
  - `AUTORESEARCH_TOOL_SANDBOX_IMAGE=python:3.12-alpine`
  - `AUTORESEARCH_TOOL_SANDBOX_CPUS=1.0`
  - `AUTORESEARCH_TOOL_SANDBOX_MEMORY=512m`
  - `AUTORESEARCH_TOOL_SANDBOX_PIDS_LIMIT=128`
- 保留 `local` 仅用于调试环境，不用于生产。

验收标准：
- 动态工具执行成功率达标
- 容器异常不会污染宿主机

---

### Phase 4：主流程切换与 OpenClaw 退役（1 天）

目标：新底座成为唯一主流程。

- 切换流量入口到新 API。
- 保留 OpenClaw 只读观察 3~7 天。
- 稳定后下线 OpenClaw 主进程，保留数据归档。

验收标准：
- 连续稳定窗口内核心指标无回退
- 回滚演练通过

---

## 6. 环境与配置模板

### 6.1 最小环境变量（建议）

```bash
export AUTORESEARCH_API_DB_PATH=/absolute/path/to/evaluations.sqlite3
export AUTORESEARCH_AGENT_MAX_CONCURRENCY=20
export AUTORESEARCH_AGENT_MAX_DEPTH=3

export AUTORESEARCH_TOOL_SANDBOX_BACKEND=docker
export AUTORESEARCH_TOOL_SANDBOX_IMAGE=python:3.12-alpine
export AUTORESEARCH_TOOL_SANDBOX_CPUS=1.0
export AUTORESEARCH_TOOL_SANDBOX_MEMORY=512m
export AUTORESEARCH_TOOL_SANDBOX_PIDS_LIMIT=128

# Claude CLI 命令前缀（按你的环境）
export AUTORESEARCH_CLAUDE_COMMAND="claude"
```

### 6.2 启动 API

```bash
uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8000
```

---

## 7. API 迁移调用示例

### 7.1 创建兼容会话

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "channel":"telegram",
    "title":"campaign-ops",
    "metadata":{"source":"gateway"}
  }'
```

### 7.2 触发 Claude 子 agent

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/agents \
  -H "Content-Type: application/json" \
  -d '{
    "task_name":"landing-page-refactor",
    "prompt":"Refactor hero section with responsive layout",
    "session_id":"oc_xxx",
    "generation_depth":1,
    "timeout_seconds":900
  }'
```

### 7.3 查询执行状态

```bash
curl http://127.0.0.1:8000/api/v1/openclaw/agents/agent_xxx
curl http://127.0.0.1:8000/api/v1/openclaw/sessions/oc_xxx
```

---

## 8. M1 + 外置盘 + Colima 注意事项

1. 外置盘建议 APFS（或通过 sparsebundle 提供 APFS 层）。
2. Docker 资源建议从小配开始（2 CPU / 4GB / 20GB），稳定后再拉高。
3. 本项目动态工具 Docker 执行已采用“源码注入容器”，避免依赖 bind mount 路径可见性。
4. 若容器冷启动慢，优先预拉取镜像（`python:3.12-alpine`）。

---

## 9. 安全基线（必须执行）

1. 动态工具默认 Docker backend，不允许生产用 local。
2. 容器网络默认 `none`，除非明确需要外网访问。
3. 设置超时与资源限额，避免死循环和资源打满。
4. 保留工具源码审计记录（当前会落盘到 `.generated_tools/.../tools`）。
5. 对关键任务启用人工批准闸门（高风险命令/写操作）。

---

## 10. 验收清单（Go-Live Checklist）

- [ ] 双写会话至少稳定 24 小时
- [ ] 子 agent 灰度至少完成 10% → 30% → 60%
- [ ] Docker 沙盒执行成功率达到阈值
- [ ] 失败案例都有可解释日志
- [ ] 回滚脚本已演练并成功
- [ ] 监控看板可见关键指标
- [ ] 关键业务任务端到端通过

---

## 11. 回滚策略（必须预演）

触发条件（任一满足）：
- 连续 15 分钟成功率低于阈值
- P95 时延超过基线 2 倍以上
- 出现安全异常（沙盒逃逸迹象、异常文件污染）

回滚动作：
1. 停止新流量进入新底座入口。
2. 路由切回 OpenClaw 主流程。
3. 导出故障窗口会话与 agent 日志。
4. 保留数据库快照用于复盘。

---

## 12. 常见问题（FAQ）

### Q1：能否一步替换？
不建议。最佳实践是并行灰度，避免一次性切换引发不可控故障。

### Q2：Claude CLI 参数不一致怎么办？
通过 `AUTORESEARCH_CLAUDE_COMMAND` 统一命令前缀；必要时在请求中传 `cli_args`。

### Q3：动态工具一定要 Docker 吗？
生产环境是必须。`local` 仅用于开发调试。

### Q4：数据库要不要拆分？
初期可以单库；当写入量上来后，建议按域拆分（sessions/agents/evaluations）。

---

## 13. 推荐的下一步增强

1. 接入 Telegram Webhook Gateway（把通道层彻底接管）。
2. 给 Claude 调度增加取消/重试/优先级队列。
3. 增加任务树可视化（parent/child lineage）与代际限流看板。
4. 引入故障注入测试（超时、网络断连、CLI 不可用）。

---

## 14. 变更记录

- 2026-03-25：首版迁移手册，覆盖 OpenClawCompat、Claude 子 agent 调度、Docker 沙盒最佳实践。

