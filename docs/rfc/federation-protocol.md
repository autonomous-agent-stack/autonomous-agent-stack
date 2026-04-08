# RFC: Federation Protocol - 分层联邦与能力共享

**Status**: Draft | **Author**: AAS Core Team | **Created**: 2026-04-09
**Depends on**: [distributed-execution.md](./distributed-execution.md), [three-machine-architecture.md](./three-machine-architecture.md)

## 摘要

本文档定义 AAS 的联邦协议：如何让多个独立的 AAS 实例建立分层信任关系，实现算力、worker、agent 的分级共享。核心原则是"分层互信、有限共享、主权独立、可撤销建交"。

## 背景与动机

### 为什么需要联邦

单个 AAS 实例有天然的物理限制：
- 算力瓶颈：单机 GPU/CPU 有限
- 认证边界：某些 GitHub/SaaS 账号只登录在特定机器
- 地理分布：跨国团队需要就近执行
- 专业能力：某些机器有特殊硬件/环境

### 联邦的价值

```
┌─────────────────────────────────────────────────────────────────┐
│                        Federation Layer                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              共享能力目录与路由协商                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │                           │                          │
         ▼                           ▼                          ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  AAS Instance │         │  AAS Instance │         │  AAS Instance │
│    (Your)     │         │  (Partner Org)│         │   (Public)    │
│               │         │               │         │               │
│ Pool: mac     │◄────────┤ Pool: gpu     │◄────────┤ Pool: generic │
│ OpenHands     │ 共享    │ A100/H100     │  共享   │ Low-trust     │
│ GitHub:Private│         │ GitHub:Public │         │ Read-only     │
└───────────────┘         └───────────────┘         └───────────────┘
```

## 核心原则

### 1. 分层互信

不要把联邦做成平面网络，要分层次：

```
L0: 本地自治
    └─ AAS 自己玩，只从 store 下载 agent

L1: 开放协作层
    └─ 任何符合最低规则的 AAS 都可申请加入
    └─ 只共享：公共 agent、低风险 worker、配额算力、只读能力

L2: 互信联邦层
    └─ 需要更强认证、审核和协议承诺
    └─ 可共享：部分 worker、任务委托、更高配额、私有 agent

L3: 战略联盟层
    └─ 高信任、长期合作
    └─ 可共享：专项 worker pool、联合调度、治理标准
```

### 2. 有限共享

**共享顺序**（从低风险到高风险）：

```
1. 公共 agent 元数据
2. 低风险算力（CPU、通用容器）
3. 沙箱 worker（无敏感凭据）
4. 只读 worker（有访问权限但无修改）
5. 特定能力 worker（如 GitHub 公开 API）
6. 身份绑定 worker（如私有仓库访问）⚠️
```

**永远不共享**：
- ❌ 主机 root 权限
- ❌ 敏感凭据（token、私钥）
- ❌ 控制面写权限
- ❌ 跨联邦的 promotion 权限

### 3. 主权独立

```
联邦 ≠ 统一主权

每个 AAS 实例：
✅ 保留自己的控制面
✅ 保留自己的 promotion 权限
✅ 可以随时退出联邦
✅ 可以拒绝任何任务委托

联邦只协调，不接管
```

### 4. 可撤销建交

```python
# 建交
federation.establish_peer(
    peer_id="partner-org",
    trust_level="L2",  # 互信联邦层
    shared_resources=["pool.gpu", "agent.readme_writer"],
    revoke_token="random_secret"
)

# 随时撤销
federation.revoke_peer(
    peer_id="partner-org",
    reason="security_incident",
    revoke_token="random_secret"  # 必须匹配
)
```

## 联邦成员类型

### 观察员（Observer）

```yaml
member:
  id: "observer-001"
  level: L0
  capabilities:
    - read_public_agent_catalog
    - download_public_agents

  restrictions:
    - cannot_submit_tasks
    - cannot_access_workers
    - cannot_view_internal_state
```

**适合场景**：
- 新成员观察期
- 只想使用公共 agent 的个人

### 普通成员（Member）

```yaml
member:
  id: "member-001"
  level: L1
  capabilities:
    - submit_limited_tasks
    - access_sandbox_workers
    - use_public_agents

  quotas:
    - max_concurrent_tasks: 5
    - max_cpu_hours: 100
    - max_execution_time: 3600

  restrictions:
    - cannot_access_sensitive_workers
    - cannot_delegate_privileged_tasks
```

**适合场景**：
- 开源社区贡献者
- 合作伙伴的初步对接

### 互信成员（Trusted Member）

```yaml
member:
  id: "trusted-001"
  level: L2
  capabilities:
    - submit_unlimited_tasks
    - access_dedicated_workers
    - use_private_agents
    - delegate_tasks_to_my_pool

  quotas:
    - max_concurrent_tasks: 50
    - priority: high

  audit_required: true
  approval_required_for:
    - production_promotion
    - sensitive_data_access
```

**适合场景**：
- 长期合作伙伴
- 内部不同团队/部门

### 战略成员（Strategic Partner）

```yaml
member:
  id: "strategic-001"
  level: L3
  capabilities:
    - full_capability_sharing
    - joint_governance
    - cross_promotion
    - shared_agent_templates

  governance:
    - voting_rights: true
    - policy_proposal: true

  sla:
    - availability: 99.9%
    - response_time: <100ms
```

**适合场景**：
- 战略联盟
- 联合项目
- 深度技术整合

## 资源共享模型

### 算力共享（最简单）

```python
# AAS A 共享 GPU 给联邦
federation.share_compute(
    resource_type="gpu",
    pool_name="a100-pool",
    quotas={
        "member-001": {"gpu_hours": 50, "max_jobs": 5},
        "trusted-001": {"gpu_hours": 200, "max_jobs": 20}
    },
    restrictions={
        "no_interactive_access": True,
        "max_job_duration": 7200,
        "allowed_images": ["pytorch/*", "tensorflow/*"]
    }
)

# AAS B 提交任务到 AAS A 的 GPU
job = federation.submit_remote_job(
    target_federation="aas-a",
    resource_type="gpu",
    job_spec={
        "image": "pytorch:latest",
        "command": "python train.py",
        "data_url": "s3://my-bucket/data"
    }
)
```

### Worker 共享（需要更多信任）

```python
# 共享只读 worker
federation.share_worker(
    worker_id="github-api-read-only",
    capabilities=["github.api.read"],
    access_level="read_only",
    allowed_members=["trusted-001", "strategic-001"],
    rate_limit={"requests_per_minute": 1000}
)

# 共享有权限的 worker（高风险）
federation.share_worker(
    worker_id="github-api-private",
    capabilities=["github.api.private"],
    access_level="privileged",
    allowed_members=["strategic-001"],  # 只有战略成员
    audit_every_request=True,
    require_explicit_approval=True
)
```

### Agent 共享

```python
# 发布公共 agent
federation.publish_agent(
    agent_id="readme-writer",
    version="1.0.0",
    visibility="public",  # 任何人可用
    manifest={
        "description": "自动生成 README",
        "required_caps": ["shell.write"]
    }
)

# 发布私有 agent（只给互信成员）
federation.publish_agent(
    agent_id="internal-security-auditor",
    version="2.0.0",
    visibility="federation_private",
    allowed_members=["trusted-001", "strategic-001"],
    manifest={
        "description": "内部安全审计工具",
        "required_caps": ["security.scan", "code.read"]
    }
)
```

## 发现与建交协议

### 公开可发现的联邦

```python
# 联邦 A 宣告自己的存在
federation.announce(
    name="AAS-Public-Grid",
    endpoint="https://grid.example.com",
    capabilities={
        "workers": ["gpu.a100", "cpu.x86"],
        "agents": ["public:*"],
        "max_concurrent_jobs": 100
    },
    join_policy="open",  # 任何人可申请
    contact_email="admin@example.com"
)

# 联邦 B 发现并申请加入
peer = federation.discover("AAS-Public-Grid")
peer.apply_for_membership(
    applicant_id="aas-b-001",
    capabilities={
        "workers": ["cpu.arm"],
        "agents": ["public:*"]
    },
    intended_use="research"
)
```

### 受邀可发现的联邦

```python
# 联邦 A 不公开目录
federation.configure(
    discovery_mode="invite_only",
    invitation_token="secret_token_123"
)

# 联邦 B 通过邀请加入
peer = federation.connect_with_invitation(
    endpoint="https://private.example.com",
    invitation_token="secret_token_123",
    my_credentials={
        "id": "aas-b-001",
        "public_key": "..."
    }
)
```

### 不可发现/隐式联邦

```python
# 没有公开发现面
# 只能通过直接配置连接

federation.add_static_peer(
    peer_id="internal-team-2",
    endpoint="https://internal-2.company.local",
    pre_shared_key="...",
    trust_level="L3"  # 最高信任
)
```

## 安全机制

### 1. 身份验证

```python
# 联邦成员身份
class FederationIdentity:
    member_id: str
    public_key: str  # 用于签名验证
    certificates: List[str]  # 可选，用于 mTLS
    level: TrustLevel  # L0-L3

    def sign_request(self, request):
        # 所有跨联邦请求必须签名
        request.signature = sign(request.data, self.private_key)
        request.timestamp = now()
        request.nonce = random_nonce()
        return request
```

### 2. 任务验证

```python
# 接收方验证任务
def validate_incoming_task(task, peer_identity):
    # 1. 签名验证
    if not verify_signature(task, peer_identity.public_key):
        raise SecurityError("Invalid signature")

    # 2. 时间戳检查（防重放）
    if now() - task.timestamp > 300:  # 5分钟
        raise SecurityError("Task too old")

    # 3. Nonce 检查（防重放）
    if nonce_seen(task.nonce):
        raise SecurityError("Replay attack detected")

    # 4. 权限检查
    if not peer_identity.can_perform(task):
        raise SecurityError("Unauthorized task")

    # 5. 配额检查
    if not peer_identity.has_quota_for(task):
        raise SecurityError("Quota exceeded")

    return True
```

### 3. 审计

```python
# 所有跨联邦操作必须审计
audit_log = {
    "timestamp": now(),
    "from_peer": "aas-b-001",
    "to_peer": "aas-a-001",
    "action": "submit_task",
    "task_id": "task-123",
    "resources_requested": {"gpu": 1, "memory": "16GB"},
    "duration": 3600,
    "result": "success",
    "artifacts": ["output.tar.gz"]
}
```

## 联邦宪章

每个联邦层都应有明确的规则：

```yaml
# federation-charter.yaml
federation:
  name: "AAS Open Grid"
  version: "1.0"

L1_rules:  # 开放协作层
  membership:
    - "任何人可申请"
    - "需通过基础安全检查"
    - "观察期 7 天"

  shared_resources:
    - "公共 agent 元数据"
    - "沙箱 worker（无敏感凭据）"
    - "配额算力（CPU/通用容器）"

  restrictions:
    - "禁止访问私有数据"
    - "禁止修改控制面状态"
    - "任务优先级：最低"

  violations:
    - "滥用资源：暂停 30 天"
    - "安全事件：立即撤销"
    - "恶意行为：永久封禁"

L2_rules:  # 互信联邦层
  membership:
    - "需现有成员推荐"
    - "需通过技术审核"
    - "需签署合作协议"

  shared_resources:
    - "私有 agent（经审核）"
    - "专用 worker"
    - "更高配额"
    - "任务委托"

  restrictions:
    - "所有操作可审计"
    - "敏感操作需审批"
    - "需遵守 SLA"

  governance:
    - "成员会议：月度"
    - "政策变更：需投票"
    - "争议解决：仲裁委员会"

L3_rules:  # 战略联盟层
  membership:
    - "需全票通过"
    - "需签署战略协议"
    - "需联合治理"

  shared_resources:
    - "专项 worker pool"
    - "联合调度"
    - "共享 agent 模板"
    - "部分治理权限"

  governance:
    - "联合技术委员会"
    - "共享知识产权协议"
    - "联合安全响应"
```

## 离线与故障处理

### 联邦成员离线

```python
def handle_peer_offline(peer_id: str):
    peer = get_peer(peer_id)

    # 1. 标记离线
    peer.status = "offline"

    # 2. 停止向其发送新任务
    cancel_pending_dispatches(peer_id)

    # 3. 已派发任务的处理
    dispatched_tasks = get_tasks dispatched_to=peer_id
    for task in dispatched_tasks:
        if task.attempt_no < MAX_RETRY:
            # 尝试路由到其他成员
            reroute_to_alternative_peer(task)
        else:
            task.status = "failed_peer_unavailable"

    # 4. 通知依赖方
    notify_dependents(f"{peer_id} is offline")
```

### 网络分区

```python
def handle_network_partition():
    # 检测到分区
    local_peers = discover_reachable_peers()

    # 进入有限模式
    enter_degraded_mode({
        "only_local_tasks": True,
        "no_cross_federation_promotion": True,
        "queue_cross_federation_tasks": True
    })

    # 恢复后的重连
    when_network_restored():
        replay_queued_tasks()
        reconcile_state_with_peers()
```

## 争议与撤销

### 违约处理

```python
# 违规类型
violation_types = {
    "resource_abuse": "warning",
    "security_breach": "immediate_revoke",
    "policy_violation": "suspend_30_days",
    "malicious_activity": "permanent_ban"
}

# 处理流程
def handle_violation(peer_id: str, violation: str):
    severity = violation_types[violation]

    if severity == "immediate_revoke":
        federation.revoke_peer(peer_id, reason=violation)
        notify_all_members(f"{peer_id} revoked for {violation}")

    elif severity == "suspend_30_days":
        federation.suspend_peer(peer_id, duration=30)
        notify_peer(peer_id, f"Suspended for 30 days for {violation}")

    elif severity == "warning":
        federation.warn_peer(peer_id, reason=violation)
        # 3次警告后暂停
        if peer.warning_count >= 3:
            federation.suspend_peer(peer_id, duration=7)
```

### 退出联邦

```python
# 主动退出
def leave_federation():
    # 1. 通知所有成员
    notify_all_members("leaving_federation", grace_period=30)

    # 2. 完成进行中的任务
    wait_for_active_tasks(timeout=3600)

    # 3. 归还共享资源
    release_shared_resources()

    # 4. 撤销跨联邦授权
    revoke_cross_federation_tokens()

    # 5. 更新联邦目录
    federation.unregister(my_id)

    return "clean_exit"
```

## 实现阶段

### Phase 1: 单向发现（本期）

- [ ] 公开能力目录 API
- [ ] 简单的申请/批准流程
- [ ] L1 基础规则

### Phase 2: 双向委托

- [ ] 跨联邦任务提交
- [ ] 算力共享
- [ ] 基础审计

### Phase 3: 成熟治理

- [ ] L2/L3 信任层
- [ ] 联合治理机制
- [ ] 争议解决流程

## 与 Agent Store 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Store                              │
│  - 发布、版本、下载                                          │
│  - 签名、审核、分发                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 独立但配合
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Federation                               │
│  - 身份、建交、委托                                          │
│  - 共享、配额、审计                                          │
└─────────────────────────────────────────────────────────────┘

没有外交关系，也能逛货架
有外交关系，才能互借资源、互托任务
```

## 参考资料

- [W3C Web of Trust](https://www.w3.org/wiki/WebOfTrust)
- [Matrix Federation](https://matrix.org/docs/spec/server_server)
- [ActivityPub Protocol](https://www.w3.org/TR/activitypub/)
- [OAuth 2.0](https://oauth.net/2/)
- [X.509 Public Key Infrastructure](https://www.itu.int/rec/T-REC-X.509/)

## 附录：术语对照

| 中文 | 英文 | 定义 |
|------|------|------|
| 联邦 | Federation | 多个 AAS 实例组成的协作网络 |
| 观察员 | Observer | 只读访问，无执行权限 |
| 普通成员 | Member | 基础执行权限，有限资源 |
| 互信成员 | Trusted Member | 高级权限，可共享私有资源 |
| 战略成员 | Strategic Partner | 最高信任，联合治理 |
| 能力 | Capability | Worker 可提供的服务 |
| 池 | Pool | 同类 Worker 的集合 |
| 租约 | Lease | 任务独占执行的时间窗口 |
| 建交 | Establish Peer | 建立联邦成员关系 |
| 撤销 | Revoke | 终止联邦成员关系 |
| 宪章 | Charter | 联邦运行规则 |
| 边缘自治 | Edge Autonomy | 控制面离线时的有限自主模式 |
