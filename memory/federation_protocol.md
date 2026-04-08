---
name: Federation Protocol
description: 分层互信联邦：L0-L3 信任层级、能力共享、可撤销建交
type: project
---

# Federation Protocol

## 核心原则

### 分层互信

- **L0 本地自治**：AAS 自己玩
- **L1 开放协作**：任何符合最低规则的可申请，只共享低风险资源
- **L2 互信联邦**：需认证审核，可共享部分私有资源
- **L3 战略联盟**：高信任长期合作，联合治理

### 有限共享

**共享顺序**（从低风险到高风险）：
1. 公共 agent 元数据
2. 低风险算力
3. 沙箱 worker
4. 只读 worker
5. 特定能力 worker
6. 身份绑定 worker ⚠️

**永远不共享**：
- 主机 root 权限
- 敏感凭据
- 控制面写权限

### 主权独立

每个 AAS 实例：
- ✅ 保留自己的控制面
- ✅ 保留自己的 promotion 权限
- ✅ 可以随时退出联邦
- ✅ 可以拒绝任何任务委托

### 可撤销建交

随时可以撤销联邦成员关系：
```python
federation.revoke_peer(
    peer_id="partner-org",
    reason="security_incident"
)
```

## 成员类型

### 观察员（Observer）
- 只读访问公共 agent 目录
- 不能提交任务
- 适合：新成员观察期

### 普通成员（Member）
- 可提交有限任务
- 可访问沙箱 worker
- 有配额限制
- 适合：开源社区贡献者

### 互信成员（Trusted Member）
- 可提交无限任务
- 可访问专用 worker
- 可使用私有 agent
- 可委托任务
- 需要审计
- 适合：长期合作伙伴

### 战略成员（Strategic Partner）
- 全能力共享
- 联合治理
- 跨 promotion
- 有投票权
- 适合：战略联盟

## 资源共享

### 算力共享

最简单，风险最低：
```python
federation.share_compute(
    resource_type="gpu",
    pool_name="a100-pool",
    quotas={"member-001": {"gpu_hours": 50}}
)
```

### Worker 共享

需要更多信任：
```python
# 只读 worker
federation.share_worker(
    worker_id="github-api-read-only",
    access_level="read_only"
)

# 有权限的 worker（高风险）
federation.share_worker(
    worker_id="github-api-private",
    access_level="privileged",
    allowed_members=["strategic-001"],
    audit_every_request=True
)
```

### Agent 共享

```python
# 公共 agent
federation.publish_agent(
    agent_id="readme-writer",
    visibility="public"
)

# 私有 agent
federation.publish_agent(
    agent_id="internal-security-auditor",
    visibility="federation_private",
    allowed_members=["trusted-001"]
)
```

## 发现与建交

### 公开可发现

```python
federation.announce(
    name="AAS-Public-Grid",
    endpoint="https://grid.example.com",
    join_policy="open"
)
```

### 受邀可发现

```python
federation.configure(
    discovery_mode="invite_only",
    invitation_token="secret_token_123"
)
```

### 隐式联邦

没有公开发现面，只能通过直接配置连接：
```python
federation.add_static_peer(
    peer_id="internal-team-2",
    endpoint="https://internal-2.company.local",
    pre_shared_key="..."
)
```

## 联邦宪章

每个联邦层都应有明确的规则：
- 成员加入条件
- 身份验证方式
- 可共享资源类型
- 可共享资源上限
- 安全基线
- 审计要求
- 违约处置
- 吊销与退群机制

## 与 Agent Store 的关系

```
Agent Store：货架（发布、版本、下载、签名、审核）
Federation：外交关系（身份、建交、委托、共享、配额）

没有外交关系，也能逛货架
有外交关系，才能互借资源、互托任务
```

## 实现阶段

**Phase 1**：单向发现
- 公开能力目录 API
- 简单申请/批准流程
- L1 基础规则

**Phase 2**：双向委托
- 跨联邦任务提交
- 算力共享
- 基础审计

**Phase 3**：成熟治理
- L2/L3 信任层
- 联合治理机制
- 争议解决流程

## 文档

详见：`docs/rfc/federation-protocol.md`
