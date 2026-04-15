# RFC: Three-Machine Heterogeneous Architecture

**Status**: Draft | **Author**: AAS Core Team | **Created**: 2026-04-09
**Depends on**: [distributed-execution.md](./distributed-execution.md)

## 摘要

本文档定义 AAS 的三机异构执行架构：Linux（控制面 + OpenHands）、Mac mini（主力 Mac 执行池）、MacBook（身份绑定能力）。重点阐述如何从"单 Mac 例外处理"升级为"多节点异构执行池"。

## 背景与动机

### 现状

当前 AAS 主要运行在 MacBook 上，但面临以下约束：

1. **OpenHands 资源需求**：需要更稳定的 CPU/内存环境
2. **MacBook 便携性冲突**：日常携带导致服务中断
3. **能力分散**：部分 GitHub 账号只登录在特定机器

### 目标状态

```
┌───────────────────────────────────────────────────────────────┐
│                     Linux Control Plane                       │
│                   (Authoritative Scheduler)                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐ │
│  │ Global    │ │ Worker    │ │ Lease     │ │ Routing       │ │
│  │ Task      │ │ Registry  │ │ Manager   │ │ Engine        │ │
│  │ Queue     │ │           │ │           │ │               │ │
│  └───────────┘ └───────────┘ └───────────┘ └───────────────┘ │
└───────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Linux       │   │ Mac mini    │   │ MacBook     │
    │ OpenHands   │   │ (主力)      │   │ (身份绑定)   │
    │ Worker      │   │             │   │             │
    │             │   │ Capabilities│   │ Capabilities│
    │ • openhands │   │ • github.   │   │ • github.   │
    │ • analysis  │   │   content_kb│   │   content_kb│
    │ • control   │   │ • gh_agent  │   │   private_* │
    │             │   │ • analysis  │   │ • desktop.* │
    │ Always      │   │             │   │             │
    │ Online      │   │ Long Uptime │   │ Portable    │
    └─────────────┘   └─────────────┘   └─────────────┘
```

## 角色定义

### Linux: 控制面 + OpenHands 专用节点

**职责**：
- 权威调度器（所有任务入队）
- OpenHands 容器执行
- 最终 promotion / merge / 发布
- 全局审计与状态归档

**特点**：
- 长期稳定在线
- CPU/内存资源充足
- 不持有 GitHub 个人账号

**配置示例**：
```yaml
worker_id: linux-oh-01
site: linux
pool: linux
capabilities:
  - openhands.host
  - analysis.cpu
  - controlplane.local
  - validation
priority_weight: 10  # 最高优先级
connectivity: always_online
```

### Mac mini: 主力 Mac 执行池

**职责**：
- 承担大部分 Mac 系任务
- GitHub API / content-kb 查询
- gh agent 调用
- 仓库分析、总结类任务

**特点**：
- 长期开机、稳定在线
- 无需个人登录态
- 高吞吐能力

**配置示例**：
```yaml
worker_id: macmini-gh-01
site: macmini
pool: mac
capabilities:
  - github.content_kb
  - gh_agent
  - analysis.high_throughput
  - shell.mac
priority_weight: 7
connectivity: stable
```

### MacBook: 身份绑定 + 桌面上下文

**职责**：
- 只在 MacBook 登录的 GitHub 账号任务
- 需要钥匙串/桌面会话的任务
- 本地专有配置相关任务

**特点**：
- 可能休眠/离线
- 持有敏感凭据
- 低到中等吞吐

**配置示例**：
```yaml
worker_id: macbook-gh-01
site: macbook
pool: mac
capabilities:
  - github.content_kb.private_account
  - gh_agent
  - desktop.session.bound
  - keychain.access
priority_weight: 5
connectivity: intermittent  # 可能离线
```

## 任务分类与路由

### 第 1 类：Linux-Only 任务

```python
linux_task = Task(
    required_caps=["openhands"],
    must_run_on="linux-oh-01",
    fallback_policy="queue_until_linux_online"
)
```

**适用场景**：
- OpenHands 执行
- 最终 promotion / 发布 / merge
- 全局编排与审计
- 控制面状态变更

### 第 2 类：Mac-Pool 任务

```python
mac_task = Task(
    required_caps=["github.content_kb"],
    preferred_pool="mac",
    fallback_policy="macmini_then_macbook_then_queue"
)
```

**适用场景**：
- GitHub content-kb 查询
- gh agent 调用
- 读仓库、查知识、分析、总结
- 大多数非 OpenHands 的 agent 任务

**路由优先级**：
1. Mac mini（默认首选）
2. MacBook（当 Mac mini 忙/离线）
3. 队列等待（都不可用时）

### 第 3 类：MacBook-Bound 任务

```python
bound_task = Task(
    required_caps=["github.content_kb.private_account"],
    must_run_on="macbook-gh-01",
    fallback_policy="queue_until_macbook_online"
)
```

**适用场景**：
- 只在 MacBook 登录的 GitHub 账号
- 需要桌面会话的任务
- 需要钥匙串访问的任务

## 路由引擎设计

### 核心算法

```python
def route_task(task: Task) -> Optional[Worker]:
    """
    三机路由引擎
    """
    # 1. 硬约束检查
    if task.must_run_on:
        worker = get_worker(task.must_run_on)
        if worker and worker.is_schedulable():
            return worker
        return None  # 等待指定 worker

    # 2. 能力匹配
    capable = get_workers_by_capabilities(task.required_caps)
    capable = [w for w in capable if w.is_schedulable()]

    if not capable:
        return None

    # 3. 池偏好
    if task.preferred_pool:
        pool_workers = [w for w in capable if w.pool == task.preferred_pool]
        if pool_workers:
            capable = pool_workers

    # 4. 负载均衡
    # 优先选择负载低的 worker
    return min(capable, key=lambda w: w.current_load())

    # 5. fallback 策略在调度层处理
```

### 池化路由示例

```python
# 自动路由到任意 Mac
task = Task(
    required_caps=["github.content_kb"],
    preferred_pool="mac"  # 自动在 macmini/macbook 间选择
)

# 路由到 Mac mini（如果可用）
# 否则 fallback 到 MacBook
# 否则进入队列等待
```

## 离线场景矩阵

### 场景 1：MacBook 离线，Mac mini 在线

| 任务类型 | 处理方式 |
|---------|---------|
| 普通 Mac 任务 | 路由到 Mac mini |
| MacBook 绑定任务 | 进入队列等待 |
| OpenHands 任务 | 正常执行（Linux） |

### 场景 2：Mac mini 离线，MacBook 在线

| 任务类型 | 处理方式 |
|---------|---------|
| 普通 Mac 任务 | 降级到 MacBook（吞吐下降） |
| MacBook 绑定任务 | 正常执行 |
| OpenHands 任务 | 正常执行（Linux） |

### 场景 3：Linux 在线，两个 Mac 都离线

| 任务类型 | 处理方式 |
|---------|---------|
| 普通 Mac 任务 | 进入 `pool=mac` 队列等待 |
| MacBook 绑定任务 | 进入 `worker=macbook` 队列等待 |
| OpenHands 任务 | 正常执行 |

### 场景 4：Linux 离线，Mac mini 在线

**边缘自治模式**：

```python
# Mac mini 进入有限自治
def enter_limited_autonomy():
    # 只执行已授权的任务
    local_jobs = get_authorized_jobs()

    # 不做全局决策
    for job in local_jobs:
        result = execute(job)
        save_to_local_outbox(result)

    # Linux 恢复后对账
    # 不做 promotion，不修改全局状态
```

**允许的操作**：
- ✅ 执行已领取的 content-kb 任务
- ✅ 执行分析类任务
- ✅ 产出中间结果

**禁止的操作**：
- ❌ 全局优先级重排
- ❌ 跨 worker 资源争抢
- ❌ 最终 promotion / merge
- ❌ 修改 Linux 权威状态

### 场景 5：Linux 离线，MacBook + Mac mini 都在线

**不要选主，各自自治**：

- 两台 Mac 各自只执行本地/已授权任务
- 各自维护本地 spool
- 不尝试选举"临时主控"
- Linux 恢复后统一回收

## Worker Registry 扩展

```sql
CREATE TABLE workers (
    worker_id TEXT PRIMARY KEY,
    site TEXT NOT NULL,              -- 'linux', 'macbook', 'macmini'
    pool TEXT NOT NULL,              -- 'linux', 'mac'
    capabilities JSON,                -- 能力列表
    priority_weight INTEGER DEFAULT 1, -- 同池内优先级

    -- 连接状态
    connectivity TEXT DEFAULT 'unknown', -- 'online', 'offline', 'degraded'
    heartbeat_at TIMESTAMP,
    lease_expires_at TIMESTAMP,

    -- 调度状态
    schedulable BOOLEAN DEFAULT 1,
    current_load INTEGER DEFAULT 0,
    max_concurrent INTEGER DEFAULT 3,

    -- 边缘自治
    supports_edge_autonomy BOOLEAN DEFAULT 0,
    autonomy_level TEXT DEFAULT 'none', -- 'none', 'limited', 'full'

    -- 元数据
    worker_version TEXT,
    os_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 任务优先级矩阵

```python
# 高优先级：控制面关键操作
PRIORITY_CRITICAL = 100  # promotion, merge, release

# 中高优先级：安全相关
PRIORITY_HIGH = 80       # security scan, vulnerability fix

# 中优先级：常规开发任务
PRIORITY_NORMAL = 50     # bug fix, feature

# 低优先级：分析类任务
PRIORITY_LOW = 30        # repo analysis, summary

# 最低优先级：清理类任务
PRIORITY_BACKGROUND = 10 # cache warmup, log cleanup
```

### 池内优先级

```python
# Mac 池内优先级
MAC_POOL_PRIORITY = {
    "macmini-gh-01": 7,   # 稳定在线，优先使用
    "macbook-gh-01": 5    # 便携机器，次选
}
```

## 部署配置

### Linux 节点

```yaml
# config/linux-control-plane.yaml
control_plane:
  enabled: true
  database: sqlite:///data/control_plane.db

workers:
  - id: linux-oh-01
    type: openhands
    runtime: host
    max_concurrent: 2

  - id: macmini-gh-01
    type: remote_bridge
    endpoint: http://macmini.local:8002
    heartbeat_interval: 10

  - id: macbook-gh-01
    type: remote_bridge
    endpoint: http://macbook.local:8003
    heartbeat_interval: 30  # 更长，因为可能离线
```

### Mac mini 节点

```yaml
# config/macmini-worker.yaml
worker:
  id: macmini-gh-01
  site: macmini
  pool: mac
  capabilities:
    - github.content_kb
    - gh_agent
    - analysis.high_throughput

bridge:
  control_plane_url: http://linux-control:8001
  heartbeat_interval: 10
  claim_batch_size: 5

autonomy:
  enabled: true
  level: limited
  local_outbox: /var/lib/aas/outbox
```

### MacBook 节点

```yaml
# config/macbook-worker.yaml
worker:
  id: macbook-gh-01
  site: macbook
  pool: mac
  capabilities:
    - github.content_kb.private_account
    - desktop.session.bound
    - keychain.access

bridge:
  control_plane_url: http://linux-control:8001
  heartbeat_interval: 30  # 更宽容
  claim_batch_size: 2     # 更保守

autonomy:
  enabled: true
  level: limited
  local_outbox: ~/Library/Application Support/aas/outbox
```

## 监控与可观测性

### 关键指标

```python
# Worker 健康度
def worker_health_score(worker: Worker) -> float:
    factors = {
        "connectivity": worker.connectivity == 'online',  # 0 or 1
        "heartbeat_age": max(0, 1 - worker.heartbeat_age / 60),  # 衰减
        "load": 1 - worker.current_load / worker.max_concurrent,  # 反向
        "success_rate": worker.recent_success_rate  # 滚动成功率
    }
    return weighted_average(factors)

# 任务路由决策
def should_route_to(worker: Worker, task: Task) -> bool:
    # 1. 基本健康度
    if worker_health_score(worker) < 0.5:
        return False

    # 2. 能力匹配
    if not worker.has_capabilities(task.required_caps):
        return False

    # 3. 负载检查
    if worker.current_load >= worker.max_concurrent:
        return False

    # 4. 连接状态
    if worker.connectivity == 'offline':
        return task.must_run_on == worker.id  # 只分配绑定任务

    return True
```

### Dashboard 展示

```yaml
# 面板展示内容
dashboard:
  workers:
    - id: linux-oh-01
      status: online
      load: 1/2
      queue: 0

    - id: macmini-gh-01
      status: online
      load: 2/3
      queue: 5

    - id: macbook-gh-01
      status: offline
      load: 0/2
      queue: 2  # 等待上线

  tasks:
    by_pool:
      linux: 15 running, 3 queued
      mac: 28 running, 7 queued

    by_type:
      openhands: 8 running
      github_api: 12 running
      analysis: 23 running
```

## 迁移路径

### 阶段 1：双机验证（当前 → Linux + Mac mini）

1. 在 Linux 上部署控制面
2. 在 Mac mini 上部署 worker bridge
3. 验证基础路由和心跳
4. MacBook 继续作为身份绑定节点

### 阶段 2：三机运行

1. Mac mini 稳定后，提升为默认 Mac 池
2. MacBook 降级为"仅绑定任务"
3. 优化路由算法和优先级

### 阶段 3：池化扩展

1. 引入更多 Mac worker（如 iMac）
2. 支持 GPU 池（如果有 GPU 机器）
3. 动态池管理（worker 热插拔）

## 与现有架构的兼容

| 现有组件 | 三机适配 |
|---------|---------|
| `OpenHandsWorkerService` | 绑定 `linux-oh-01` |
| `AgentExecutionRunner` | 根据 `task.preferred_pool` 路由 |
| `GitPromotionGateService` | 只在 Linux 上执行 |
| `AutoResearchPlannerService` | 生成带 `pool` 的 JobSpec |

## 故障恢复

### Worker 完全失联

```python
def handle_worker_permanent_loss(worker_id: str):
    # 1. 标记 worker 为 offline
    worker = get_worker(worker_id)
    worker.connectivity = 'offline'
    worker.schedulable = False

    # 2. 重新排队其任务
    leased_tasks = get_tasks(worker_id=worker_id, status='leased')
    for task in leased_tasks:
        if task.attempt_no < MAX_RETRY:
            task.status = 'pending'
            task.attempt_no += 1
        else:
            task.status = 'failed_terminal'

    # 3. 通知相关方
    if worker_id == "macbook-gh-01":
        notify_admin(f"MacBook 绑定任务将等待恢复")
```

### 任务恢复

```python
def recover_task_on_worker_reconnect(worker_id: str):
    worker = get_worker(worker_id)
    worker.connectivity = 'online'
    worker.schedulable = True

    # 重新分配等待中的任务
    waiting_tasks = get_tasks(
        worker_id=worker_id,
        status='waiting_worker_online'
    )
    for task in waiting_tasks:
        dispatch_task_to_worker(task, worker_id)
```

## 附录：配置示例

### 完整的三机配置

```yaml
# config/aas-cluster.yaml
cluster:
  name: "aas-home-lab"
  control_plane: "linux-oh-01"

pools:
  - name: linux
    workers:
      - id: linux-oh-01
        roles: [control_plane, openhands]
        priority: 10

  - name: mac
    workers:
      - id: macmini-gh-01
        roles: [github, analysis]
        priority: 7
        default_for_pool: true

      - id: macbook-gh-01
        roles: [github_private, desktop]
        priority: 5
        bind_only: true

routing:
  rules:
    - match:
        capabilities: [openhands]
      route_to:
        pool: linux

    - match:
        capabilities: [github.content_kb]
      route_to:
        pool: mac
        preferred_worker: macmini-gh-01

    - match:
        capabilities: [github.content_kb.private_account]
      route_to:
        worker: macbook-gh-01
```

## 参考资料

- [Distributed Execution Model](./distributed-execution.md)
- [Federation Protocol](./federation-protocol.md)
- [GitHub Self-Hosted Runners - Using labels](https://docs.github.com/en/actions/hosting-your-own-runners/using-labels-with-self-hosted-runners)
