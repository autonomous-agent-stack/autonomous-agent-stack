---
name: Three-Machine Architecture
description: Linux + Mac mini + MacBook 异构执行池设计
type: project
---

# Three-Machine Architecture

## 角色划分

### Linux: 控制面 + OpenHands

```yaml
worker_id: linux-oh-01
site: linux
pool: linux
capabilities:
  - openhands.host
  - analysis.cpu
  - controlplane.local
priority_weight: 10
connectivity: always_online
```

**职责**：
- 权威调度器
- OpenHands 容器执行
- 最终 promotion / merge / 发布
- 全局审计与状态归档

### Mac mini: 主力 Mac 执行池

```yaml
worker_id: macmini-gh-01
site: macmini
pool: mac
capabilities:
  - github.content_kb
  - gh_agent
  - analysis.high_throughput
priority_weight: 7
connectivity: stable
```

**职责**：
- 承担大部分 Mac 系任务
- GitHub API / content-kb 查询
- gh agent 调用
- 长期开机、稳定在线

### MacBook: 身份绑定 + 桌面上下文

```yaml
worker_id: macbook-gh-01
site: macbook
pool: mac
capabilities:
  - github.content_kb.private_account
  - desktop.session.bound
  - keychain.access
priority_weight: 5
connectivity: intermittent
```

**职责**：
- 只在 MacBook 登录的 GitHub 账号任务
- 需要钥匙串/桌面会话的任务
- 可能休眠/离线

## 任务分类

### 第 1 类：Linux-Only

OpenHands、最终 promotion、全局编排。

### 第 2 类：Mac-Pool

普通 GitHub/API 任务，优先 Mac mini，fallback 到 MacBook。

### 第 3 类：MacBook-Bound

必须用特定登录态的任务，只能排队等 MacBook 上线。

## 路由引擎

```python
def route_task(task):
    # 1. 硬约束：must_run_on
    if task.must_run_on:
        return assign_to_worker(task.must_run_on)

    # 2. 能力匹配
    capable = get_workers_by_capabilities(task.required_caps)

    # 3. 池偏好
    if task.preferred_pool:
        capable = [w for w in capable if w.pool == task.preferred_pool]

    # 4. 负载均衡
    return min(capable, key=lambda w: w.current_load)
```

## 迁移路径

**阶段 1**：双机验证
- Linux + Mac mini

**阶段 2**：三机运行
- Mac mini 提升为默认 Mac 池
- MacBook 降级为"仅绑定任务"

**阶段 3**：池化扩展
- 引入更多 worker
- GPU 池
- 动态池管理

## 文档

详见：`docs/rfc/three-machine-architecture.md`
