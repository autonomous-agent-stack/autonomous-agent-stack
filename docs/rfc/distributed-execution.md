# RFC: Distributed Execution Model

**Status**: Draft | **Author**: AAS Core Team | **Created**: 2026-04-09

## 摘要

本文档定义 AAS 的分布式执行架构：Linux 作为权威控制面（Control Plane），Mac 作为能力绑定的执行节点（Worker），通过持久化任务队列 + 心跳/租约 + 结果回传实现"无感调用"。

## 背景与动机

### 当前问题

1. **认证边界约束**：某些 GitHub 账号只登录在 Mac 端，相关能力（如 `content-kb`）必须在本地执行
2. **调度统一性需求**：希望 Linux 仍是全局调度中心，但双端都可能离线
3. **能力隔离要求**：不希望把 Mac 的认证凭据同步给 Linux

### 设计目标

- ✅ 认证能力驻留在 Mac（不出岛）
- ✅ 调度权默认驻留在 Linux
- ✅ 执行过程允许双端断线
- ✅ 任务和结果都必须 durable
- ✅ 恢复上线后能继续、不重做、不冲突

## 架构设计

### 角色划分

```
┌─────────────────────────────────────────────────────────────────┐
│                        Linux Control Plane                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Task      │  │    Worker   │  │   Lease     │             │
│  │   Queue     │  │  Registry   │  │  Manager    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Event    │  │  Result     │  │ Promotion   │             │
│  │    Log      │  │  Artifacts  │  │   Gate      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                               │
                    ╱─────────────────────╲
                   │   Heartbeat / Lease  │
                    ╲─────────────────────╱
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   Mac Worker      │ │   Mac mini        │ │  Linux OpenHands  │
│                   │ │  (High Throughput)│ │    (Primary)      │
│ ┌───────────────┐ │ │ ┌───────────────┐ │ │ ┌───────────────┐ │
│ │ mac-agent-    │ │ │ │ mac-agent-    │ │ │ │ oh-worker     │ │
│ │ bridge        │ │ │ │bridge         │ │ │ │               │ │
│ └───────────────┘ │ │ └───────────────┘ │ │ └───────────────┘ │
│ ┌───────────────┐ │ │ ┌───────────────┐ │ │ ┌───────────────┐ │
│ │ local outbox  │ │ │ │ local outbox  │ │ │ │ (none)        │ │
│ └───────────────┘ │ │ └───────────────┘ │ │ └───────────────┘ │
│                   │ │                   │ │                   │
│ Capabilities:     │ │ Capabilities:     │ │ Capabilities:     │
│ • github.         │ │ • github.         │ │ • openhands.host  │
│   content_kb.     │ │   content_kb.     │ │ • analysis.cpu    │
│   private_account │ │   public_api      │ │                   │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

### 核心原则

#### 1. 认证不出岛

**反模式**：
- ❌ 把 Mac 上的 `~/.config/gh` 同步到 Linux
- ❌ 把 token/私钥复制给 Linux
- ❌ Linux SSH 到 Mac 强行执行交互命令

**正确模式**：
- ✅ Linux 只知道 `worker=mac-gh-01` 有能力 `github.content_kb.private_account`
- ✅ Linux 发的是 JobSpec
- ✅ Mac 用自己的本地登录态执行
- ✅ Linux 永远拿不到账号原始凭据

#### 2. 拉模型（Pull Model）

**为什么不用推模型**：
- Mac 可能休眠、断网、换 IP、NAT 后面
- Linux 很难稳定打进去

**推荐的拉模型**：
```python
# Mac 端：mac-agent-bridge
class MacAgentBridge:
    def run(self):
        while True:
            # 1. 主动拉取可执行任务
            jobs = self.claim_jobs(worker_id, capabilities, limit=5)

            # 2. 抢租约
            for job in jobs:
                lease = self.acquire_lease(job.id, ttl=300)

            # 3. 本地执行
            result = self.execute_locally(job)

            # 4. 周期性心跳
            self.heartbeat(worker_id, running_tasks)

            # 5. 回传结果
            self.report_result(job.id, result)

            time.sleep(3)  # 3~10 秒轮询
```

#### 3. ACK 机制

**不要"发了就算"**：

```python
# Mac 端
def report_result(task_id, result):
    # 发送完成信号
    response = linux_api.complete_task(task_id, result)

    # 等待 ACK
    if response.status == "ack":
        # 只有收到 ACK 才删本地 outbox
        self.local_outbox.delete(task_id)
    else:
        # 否则保留，后续重试
        self.local_outbox.retries += 1
```

## 数据模型

### 扩展 Worker 表

```sql
CREATE TABLE workers (
    worker_id TEXT PRIMARY KEY,
    site TEXT NOT NULL,              -- 'linux', 'macbook', 'macmini'
    pool TEXT NOT NULL,               -- 'linux', 'mac'
    capabilities JSON,                -- ["github.content_kb", "openhands"]
    priority_weight INTEGER DEFAULT 1,
    heartbeat_at TIMESTAMP,
    lease_expires_at TIMESTAMP,
    schedulable BOOLEAN DEFAULT 1,
    supports_edge_autonomy BOOLEAN DEFAULT 0,
    connectivity TEXT DEFAULT 'unknown'  -- 'online', 'offline', 'degraded'
);
```

### 扩展 Task 表

```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    required_caps JSON,               -- ["github.content_kb"]
    preferred_pool TEXT,              -- 'mac'
    must_run_on TEXT,                 -- 'macbook-gh-01' (可选)
    fallback_policy TEXT,             -- 'queue_until_worker_online'
    durability_class TEXT,            -- 'durable', 'ephemeral'
    idempotency_key TEXT UNIQUE,      -- 防重复执行
    status TEXT,                      -- 'pending', 'leased', 'running', ...
    worker_id TEXT,                   -- 当前分配的 worker
    attempt_no INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    leased_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

### 新增租约表

```sql
CREATE TABLE leases (
    task_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    leased_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    heartbeat_count INTEGER DEFAULT 0,
    last_heartbeat_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (worker_id) REFERENCES workers(worker_id)
);
```

### Worker Outbox 表

```sql
CREATE TABLE worker_outbox (
    event_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,         -- 'started', 'progress', 'completed', 'failed'
    payload JSON,
    acked BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (worker_id) REFERENCES workers(worker_id)
);
```

## 任务状态机

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │ eligible worker available
                           ▼
                    ┌─────────────┐
                    │  dispatched │
                    └──────┬──────┘
                           │ worker claims
                           ▼
                    ┌─────────────┐
                    │   leased    │◄────────┐
                    └──────┬──────┘         │
                           │ heartbeat      │ lease timeout
                           ▼               │
                    ┌─────────────┐         │
                    │   running   │─────────┘
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        ┌───────────┐             ┌───────────┐
        │ completed │             │   failed  │
        └─────┬─────┘             └─────┬─────┘
              │                         │
              │                         │
              ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │ result buffered │       │ retryable /     │
    │ (wait for ACK)  │       │ terminal        │
    └─────────────────┘       └─────────────────┘
```

## 离线场景处理

### 场景 A：Mac 离线，Linux 在线

**处理方式**：
```python
# 任务进入等待状态
task.status = "waiting_worker_online"
task.worker_id = "mac-gh-01"  # 预分配

# Mac 恢复后
def on_worker_reconnect(worker_id):
    # 1. 重新分配等待中的任务
    waiting_tasks = get_tasks(status="waiting_worker_online",
                             worker_id=worker_id)
    for task in waiting_tasks:
        task.status = "leased"
        task.leased_at = now()
        task.expires_at = now() + timedelta(seconds=300)

    # 2. 通知 worker 拉取
    notify_worker(worker_id, "new_tasks_available")
```

### 场景 B：Linux 离线，Mac 在线

**边缘自治模式**：

```python
# Mac 进入自治模式
def enter_edge_autonomy():
    # 只执行已授权的任务
    local_jobs = get_local_claimed_jobs()

    # 维护本地 outbox
    for job in local_jobs:
        result = execute_locally(job)
        local_outbox.append({
            "task_id": job.id,
            "result": result,
            "status": "completed_locally"
        })

# Linux 恢复后的对账
def reconcile_on_linux_recovery():
    # 1. 拉取 worker 未确认事件
    unacked = worker_outbox.select().where(worker_outbox.acked == 0)

    # 2. 去重处理
    for event in unacked:
        existing = tasks.select().where(
            tasks.task_id == event.task_id,
            tasks.attempt_no >= event.attempt_no
        )
        if not existing:
            # 补登记结果
            apply_result(event)

    # 3. 发送 ACK，清理 worker outbox
    for event in unacked:
        event.acked = True
        notify_worker_acked(event.event_id)
```

## 路由策略

### 按能力路由

```python
def route_task(task):
    # 1. 硬约束：必须运行在特定 worker
    if task.must_run_on:
        return assign_to_worker(task.must_run_on)

    # 2. 能力匹配
    capable_workers = workers.select().where(
        workers.capabilities.contains(task.required_caps),
        workers.schedulable == True,
        workers.connectivity == 'online'
    )

    # 3. 池偏好
    if task.preferred_pool:
        pool_workers = [w for w in capable_workers if w.pool == task.preferred_pool]
        if pool_workers:
            capable_workers = pool_workers

    # 4. 负载均衡
    return min(capable_workers, key=lambda w: w.current_load)
```

### 路由示例

```python
# OpenHands 任务
openhands_task = Task(
    required_caps=["openhands"],
    must_run_on="linux-oh-01",
    fallback_policy="queue_until_linux_online"
)

# 普通 GitHub 任务
github_task = Task(
    required_caps=["github.content_kb"],
    preferred_pool="mac",
    fallback_policy="macbook_then_macmini_then_queue"
)

# 身份绑定任务
private_task = Task(
    required_caps=["github.content_kb.private_account"],
    must_run_on="macbook-gh-01",
    fallback_policy="queue_until_macbook_online"
)
```

## 安全考虑

### 1. 凭据隔离

```python
# Linux 端只保存能力声明
worker = Worker(
    worker_id="mac-gh-01",
    capabilities=["github.content_kb.private_account"],
    # ❌ 不保存 token、密钥等
)

# Mac 端自己管理凭据
# ~/.config/gh 或钥匙串
```

### 2. 任务签名

```python
class JobSpec:
    job_id: str
    attempt_no: int
    issued_at: datetime
    expires_at: datetime
    nonce: str  # 防重放
    signature: str  # Linux 签名

    def verify(self, public_key):
        # Mac 验证任务确实来自 Linux
        return verify_signature(self, public_key)
```

### 3. 审计边界

```python
# 所有跨机操作都必须记录
audit_log = {
    "task_id": task.id,
    "worker_id": worker.id,
    "action": "job_dispatched",
    "timestamp": now(),
    "ip_address": client.ip,
    "user": request.user
}
```

## 实现阶段

### Phase 1: 基础设施（本期）

- [ ] Worker registry 扩展（site, pool, capabilities）
- [ ] Task routing policy（preferred_pool, must_run_on）
- [ ] Linux 端 durable task queue
- [ ] Mac 端 mac-agent-bridge
- [ ] 心跳 + 租约 + 重试机制
- [ ] 本地 outbox + ACK 删除

### Phase 2: 离线恢复

- [ ] edge-autonomy mode
- [ ] mac_outbox_replay
- [ ] reconciliation service
- [ ] handoff_openhands_jobs

### Phase 3: 成熟化

- [ ] 升级到 Postgres + Redis Streams / NATS
- [ ] 或引入 Temporal 做 durable workflow

## 与现有架构的映射

| 现有抽象 | 新扩展 |
|---------|--------|
| `Worker.type` | `Worker.site` + `Worker.pool` |
| `Worker.status` | 增加 `connectivity` 字段 |
| `Worker.capabilities` | 细化为能力列表（而非单个 type） |
| `Task.status` | 扩展状态机（leased, waiting_worker_online） |
| `AutoResearchPlannerService` | 增加 `routing_policy` 生成逻辑 |
| `GitPromotionGateService` | 支持 edge自治模式的延迟 promotion |

## 参考实现

### Mac Bridge 示例

```python
# src/masfactory/bridges/mac_agent_bridge.py
class MacAgentBridge:
    def __init__(self, control_plane_url, worker_id):
        self.control_plane = ControlPlaneClient(control_plane_url)
        self.worker_id = worker_id
        self.local_outbox = LocalOutbox(f"/tmp/aas_outbox_{worker_id}")

    def claim_jobs(self, capabilities, limit=5):
        response = self.control_plane.claim_jobs(
            worker_id=self.worker_id,
            capabilities=capabilities,
            limit=limit
        )
        return response.jobs

    def execute_job(self, job):
        # 本地执行（使用本地认证）
        if "github.content_kb" in job.required_caps:
            return self.execute_content_kb(job)
        elif "gh.agent" in job.required_caps:
            return self.execute_gh_agent(job)

    def heartbeat(self, running_tasks):
        self.control_plane.heartbeat(
            worker_id=self.worker_id,
            running_tasks=[t.id for t in running_tasks]
        )

    def report_result(self, task_id, result):
        # 发送并等待 ACK
        response = self.control_plane.complete_task(task_id, result)

        if response.acked:
            self.local_outbox.delete(task_id)
        else:
            self.local_outbox.keep(task_id, result)

    def run(self):
        while True:
            try:
                jobs = self.claim_jobs(self.get_capabilities())

                for job in jobs:
                    result = self.execute_job(job)
                    self.report_result(job.id, result)

                self.heartbeat(jobs)
                time.sleep(3)
            except Exception as e:
                log.error(f"Bridge error: {e}")
                time.sleep(10)
```

## 参考资料

- [GitHub Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)
- [Temporal Durable Execution](https://temporal.io/what-is-durable-execution)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)

## 附录：术语表

| 术语 | 定义 |
|------|------|
| Control Plane | 权威控制面，负责任务调度、状态管理、最终决策 |
| Worker | 执行节点，持有特定能力，实际执行任务 |
| Capability | 工作能力声明（如 `github.content_kb.private_account`） |
| Pool | Worker 池（如 `mac` 池包含 macbook + macmini） |
| Lease | 租约，worker 对任务的时间独占权 |
| Outbox | 本地待发送事件队列 |
| ACK | 确认，控制面已收到并持久化结果 |
| Reconciliation | 对账，控制面恢复后同步 worker 状态 |
| Edge Autonomy | 边缘自治，worker 在控制面离线时的有限自主模式 |
