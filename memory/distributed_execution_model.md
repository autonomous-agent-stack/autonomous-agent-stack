---
name: Distributed Execution Model
description: Linux 控制面 + Mac 认证绑定节点的分布式执行架构
type: project
---

# Distributed Execution Model

## 核心架构

Linux 作为权威控制面（Control Plane），Mac 作为能力绑定的执行节点（Worker），通过：
- 持久化任务队列
- 心跳/租约机制
- 本地 outbox + ACK 结果回传

实现"无感调用"，支持双端断线恢复。

## 关键设计原则

### 1. 认证不出岛

**反模式**：
- ❌ 把 Mac 上的 `~/.config/gh` 同步到 Linux
- ❌ 把 token/私钥复制给 Linux

**正确模式**：
- ✅ Linux 只知道 worker 的能力声明
- ✅ Mac 用自己的本地登录态执行
- ✅ Linux 永远拿不到账号原始凭据

### 2. 拉模型（Pull Model）

Mac 主动向 Linux 拉取任务（3-10秒轮询），而不是 Linux 推送。原因：
- Mac 可能休眠、断网、NAT 后面
- 拉模型更稳定，类似 GitHub self-hosted runner

### 3. ACK 机制

Mac 发送结果后，必须等待 Linux 确认（ACK）才能删除本地 outbox。防止断线时重复执行或丢结果。

## 数据模型

### Worker 扩展

```sql
- site: 'linux' | 'macbook' | 'macmini'
- pool: 'linux' | 'mac'
- capabilities: ["github.content_kb", "openhands"]
- connectivity: 'online' | 'offline' | 'degraded'
- lease_expires_at: 租约过期时间
- supports_edge_autonomy: 是否支持边缘自治
```

### Task 扩展

```sql
- required_caps: 所需能力列表
- preferred_pool: 优选池
- must_run_on: 硬性指定 worker
- fallback_policy: 失败回退策略
- idempotency_key: 幂等键，防重复执行
```

### 新增表

- `leases`: 租约管理
- `worker_outbox`: Worker 本地待发送事件队列

## 离线处理

### Mac 离线，Linux 在线

任务进入 `waiting_worker_online` 状态，Mac 恢复后自动接续。

### Linux 离线，Mac 在线

Mac 进入边缘自治模式（edge-autonomy）：
- 只执行已授权的任务
- 维护本地 outbox
- 不做全局决策
- Linux 恢复后对账回收

## 与现有架构映射

| 现有抽象 | 新扩展 |
|---------|--------|
| Worker.type | Worker.site + Worker.pool |
| Task.status | 扩展状态机（leased, waiting_worker_online） |
| AutoResearchPlannerService | 增加 routing_policy 生成逻辑 |

## 实现阶段

**Phase 1**（本期）：
- Worker registry 扩展
- Task routing policy
- Linux 端 durable task queue
- Mac 端 mac-agent-bridge
- 心跳 + 租约 + 本地 outbox

**Phase 2**：
- edge-autonomy mode
- reconciliation service

**Phase 3**：
- 升级到 Postgres + Redis/NATS
- 或引入 Temporal

## 文档

详见：`docs/rfc/distributed-execution.md`
