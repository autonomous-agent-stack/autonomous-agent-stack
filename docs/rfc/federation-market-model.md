# RFC: Federation + Market Model v0.1

**Status**: Draft | **Author**: AAS Core Team | **Created**: 2026-04-09
**Depends on**: [federation-protocol.md](./federation-protocol.md), [distributed-execution.md](./distributed-execution.md)

## 摘要

本文档定义 AAS 的双层协作模型：**联邦层**解决"谁跟谁建交、能共享什么、边界在哪"；**交易层**解决"资源怎么定价、怎么买、怎么验收、怎么结算"。两个层正交设计，可以独立演进但协同工作。

> **核心判断**：联邦解决主权与互信，交易解决资源配置与价值交换。

## 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                         Control Plane                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Task      │  │   Worker    │  │    Lease    │             │
│  │   Queue     │  │  Registry   │  │  Manager    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Federation     │  │     Market      │  │   Execution     │
│     Layer       │  │     Layer       │  │     Layer       │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • 成员身份      │  │ • 报价          │  │ • Workers       │
│ • 建交/断交     │  │ • 订单          │  │ • Agents        │
│ • 共享范围      │  │ • 租约          │  │ • Sandboxes     │
│ • 吊销权限      │  │ • 计量          │  └─────────────────┘
│ • 信任层级      │  │ • 结算          │
└─────────────────┘  │ • 争议          │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   Audit Layer   │
                     ├─────────────────┤
                     │ • 日志          │
                     │ • 签名          │
                     │ • 账本          │
                     │ • 可追责        │
                     └─────────────────┘
```

## 联邦 vs 交易边界

### 联邦层（Federation Layer）

**回答的问题**：
- 这个节点可不可以被我调用？
- 我们之间能共享哪些资源？
- 出了问题怎么断交？

**核心机制**：
- 建交与断交
- 身份验证与授权
- 共享范围定义
- 违约处置

**类似**：外交关系

### 交易层（Market Layer）

**回答的问题**：
- 这个调用多少钱？
- 怎么计量和结算？
- 失败了谁承担责任？

**核心机制**：
- 报价与询价
- 订单与撮合
- 计量与审计
- 结算与争议

**类似**：商业贸易

### 关系示例

| 联邦关系 | 交易模式 | 组合效果 |
|---------|---------|---------|
| 观察员 | 无交易 | 只能浏览公开目录 |
| 普通成员 | 市场购买 | 不深度信任，但可买低风险算力 |
| 互信成员 | 配额互助 | 长期合作，资源换资源 |
| 战略成员 | 混合模式 | 部分免费共享 + 部分计费 |

## 可交易资源分类

### 第 1 类：算力商品（Compute Commodities）

最基础，最好起步。

```yaml
compute_products:
  - id: cpu.basic.shared
    name: 共享 CPU 算力
    unit: vcpu-minute
    pricing_model: per_minute

  - id: gpu.inference.a10.hourly
    name: A10 GPU 推理
    unit: gpu-hour
    pricing_model: per_hour

  - id: browser.pool.readonly
    name: 只读浏览器池
    unit: browser-minute
    pricing_model: per_minute

  - id: sandbox.executor.standard
    name: 标准沙箱执行器
    unit: execution-minute
    pricing_model: per_minute
```

**定价方式**：
- 按分钟
- 按任务
- 按 token/step
- 按成功结果
- 包月/包配额

### 第 2 类：能力服务（Capability Services）

比裸算力更高级，卖的是"特殊能力"。

```yaml
capability_services:
  - id: service.github.content_kb.private_account
    name: 私有 GitHub 知识库查询
    provider_requirements:
      - github.private_auth
      - content_kb.indexed
    pricing_model: per_query
    trust_level_required: L2  # 需要互信成员

  - id: service.gh_agent.identity_bound
    name: 身份绑定 gh agent
    provider_requirements:
      - gh.cli_installed
      - github.specific_account
    pricing_model: per_execution
    trust_level_required: L3  # 需要战略成员

  - id: service.browser.automation
    name: 浏览器自动化任务
    provider_requirements:
      - browser.headless
      - puppeteer_driver
    pricing_model: per_task
    trust_level_required: L1
```

### 第 3 类：结果型服务（Outcome Services）

按交付物收费，不是按过程。

```yaml
outcome_services:
  - id: service.repo.analysis.full
    name: 完整仓库分析报告
    deliverable: analysis_report_pdf
    pricing_model: fixed_price
    sla:
      turnaround: 24h
      accuracy_min: 95%

  - id: service.documentation.generate
    name: API 文档生成
    deliverable: markdown_docs
    pricing_model: per_page
    acceptance_required: true
```

## 核心数据模型

### 1. Offer（报价单）

资源提供方挂出来的商品。

```sql
CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY,
    provider_node_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,        -- 'compute', 'capability', 'outcome'
    capability_tags JSON,               -- ["gpu", "inference", "a10"]
    price_model TEXT NOT NULL,          -- 'per_minute', 'fixed_price', 'per_task'
    unit_price DECIMAL,                 -- 单价
    settlement_unit TEXT,               -- 'credits', 'usd', 'cu'
    max_concurrency INTEGER,            -- 最大并发
    region TEXT,                        -- 地理区域
    latency_hint_ms INTEGER,            -- 预估延迟
    visibility TEXT DEFAULT 'federation', -- 'public', 'federation', 'private'
    policy_constraints JSON,            -- 策略限制
    valid_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (provider_node_id) REFERENCES federation_members(node_id)
);
```

### 2. Order（订单）

购买方发起的请求。

```sql
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    buyer_node_id TEXT NOT NULL,
    target_offer_id TEXT NOT NULL,
    requested_units INTEGER NOT NULL,
    budget_limit DECIMAL,
    job_spec_hash TEXT,                 -- 任务规格哈希
    required_sla JSON,                  -- SLA 要求
    expiry TIMESTAMP,
    escrow_amount DECIMAL,              -- 押金/预付
    status TEXT DEFAULT 'pending',      -- 'pending', 'matched', 'active', 'completed', 'cancelled', 'disputed'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (buyer_node_id) REFERENCES federation_members(node_id),
    FOREIGN KEY (target_offer_id) REFERENCES offers(offer_id)
);
```

### 3. Lease（租约）

资源占用权，与分布式执行的 lease 模型一致。

```sql
CREATE TABLE market_leases (
    lease_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,          -- worker_id / capability_id
    leased_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    heartbeat_count INTEGER DEFAULT 0,
    last_heartbeat_at TIMESTAMP,
    status TEXT DEFAULT 'active',       -- 'active', 'expired', 'terminated'

    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
```

### 4. Meter Record（计量记录）

结算依据，需要双边签名验证。

```sql
CREATE TABLE meter_records (
    record_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    lease_id TEXT NOT NULL,

    -- 计量数据
    actual_duration_seconds INTEGER,
    cpu_time_seconds INTEGER,
    gpu_time_seconds INTEGER,
    token_count INTEGER,
    api_call_count INTEGER,

    -- 结果状态
    task_status TEXT,                   -- 'success', 'failure', 'timeout'
    retry_count INTEGER,
    interrupt_reason TEXT,

    -- 签名验证
    provider_signature TEXT,
    buyer_signature TEXT,
    control_plane_signature TEXT,

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (lease_id) REFERENCES market_leases(lease_id)
);
```

### 5. Settlement（结算单）

订单结束后的账单。

```sql
CREATE TABLE settlements (
    settlement_id TEXT PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,

    -- 金额
    base_amount DECIMAL NOT NULL,       -- 基础金额
    refund_amount DECIMAL DEFAULT 0,    -- 退款金额
    penalty_amount DECIMAL DEFAULT 0,   -- 违约扣减
    final_amount DECIMAL NOT NULL,      -- 最终金额

    -- 状态
    status TEXT DEFAULT 'pending',      -- 'pending', 'paid', 'disputed', 'cancelled'
    dispute_status TEXT,                -- 'none', 'opened', 'resolved'

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,

    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
```

### 6. Reputation（信誉）

市场健康度的关键。

```sql
CREATE TABLE reputation_records (
    node_id TEXT NOT NULL,
    as_role TEXT NOT NULL,              -- 'provider', 'buyer'

    -- 统计指标
    total_orders INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    success_rate DECIMAL DEFAULT 1.0,

    timeout_rate DECIMAL DEFAULT 0.0,
    sla_compliance_rate DECIMAL DEFAULT 1.0,

    dispute_count INTEGER DEFAULT 0,
    disputes_lost INTEGER DEFAULT 0,

    -- 恶意行为检测
    malicious_task_rate DECIMAL DEFAULT 0.0,
    fake_result_rate DECIMAL DEFAULT 0.0,
    refusal_to_ack_rate DECIMAL DEFAULT 0.0,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (node_id, as_role),
    FOREIGN KEY (node_id) REFERENCES federation_members(node_id)
);
```

## 交易流程

### 流程 1：标准资源购买

```
┌─────────────┐                              ┌─────────────┐
│   Buyer     │                              │  Provider   │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  1. 浏览 Offer 目录                         │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  2. 选择 Offer，提交 Order                  │
       │ ─────────────────────────────────────────>│
       │                                            │
       │              3. 控制面检查：               │
       │              - 预算充足                    │
       │              - 联邦权限                    │
       │              - 策略合规                    │
       │                                            │
       │  4. 签发 Lease                             │
       │ <─────────────────────────────────────────│
       │                                            │
       │  5. Worker 拉取任务并执行                   │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  6. 周期性 Heartbeat + Meter                │
       │ <─────────────────────────────────────────│
       │                                            │
       │  7. 结果回传 + ACK                          │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  8. 生成 Settlement                         │
       │ <─────────────────────────────────────────│
       │                                            │
       │  9. 结算完成                                │
       │ ─────────────────────────────────────────>│
```

### 流程 2：结果验收型（高价值服务）

```
┌─────────────┐                              ┌─────────────┐
│   Buyer     │                              │  Provider   │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  1. 提交 Order（带验收要求）                │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  2. 冻结资金/积分                           │
       │                                            │
       │  3. Provider 执行                          │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  4. 交付 Artifact + Result Proof            │
       │ <─────────────────────────────────────────│
       │                                            │
       │  5. 验收窗口（如 72 小时）                  │
       │                                            │
       │  6a. ACK（接受）                           │
       │ ─────────────────────────────────────────>│
       │     或                                     │
       │  6b. Reject + 争议原因                     │
       │ ─────────────────────────────────────────>│
       │                                            │
       │  7. 超时自动进入默认规则                    │
       │                                            │
       │  8. 结算/退款                              │
       │ <─────────────────────────────────────────│
```

## 信任等级与市场准入

### 联邦信任层级

```yaml
L0_observer:
  market_access: null  # 无交易权限

L1_member:
  market_access:
    - can_buy: ["compute.basic", "sandbox.standard"]
    - can_sell: ["compute.basic"]
    - settlement_mode: "prepaid"
    - credit_limit: 100

L2_trusted:
  market_access:
    - can_buy: ["compute.*", "capability.readonly"]
    - can_sell: ["compute.*", "capability.*"]
    - settlement_mode: "postpaid"
    - credit_limit: 10000
    - max_single_order: 1000

L3_strategic:
  market_access:
    - can_buy: ["*"]
    - can_sell: ["*"]
    - settlement_mode: "contract"
    - credit_limit: unlimited
    - custom_pricing: true
```

### 市场准入审查

```python
def check_market_access(node_id: str, offer_id: str) -> MarketAccessResult:
    member = get_federation_member(node_id)
    offer = get_offer(offer_id)

    # 1. 信任层级检查
    if member.level < offer.min_trust_level:
        return MarketAccessResult.deny("insufficient_trust_level")

    # 2. 资源类别检查
    if offer.resource_type not in member.market_access.can_buy:
        return MarketAccessResult.deny("resource_type_not_allowed")

    # 3. 信用额度检查
    if member.credit_usage >= member.credit_limit:
        return MarketAccessResult.deny("credit_limit_exceeded")

    # 4. 策略约束检查
    if not offer.policy_constraints.is_satisfied_by(member):
        return MarketAccessResult.deny("policy_constraints_failed")

    return MarketAccessResult.allowed()
```

## 交易模式

### 1. 固定价（Fixed Price）

最适合起步。

```yaml
fixed_price:
 适合:
    - 沙箱 worker
    - GPU 推理
    - 标准能力服务

  特点:
    - 价格透明
    - 计费简单
    - 争议少

  示例:
    - cpu.basic.shared: $0.01/vcpu-minute
    - gpu.inference.a10: $0.50/gpu-hour
```

### 2. 协议价/合同价（Contract Price）

联邦成员之间。

```yaml
contract_price:
  适合:
    - 战略成员之间
    - 长期资源互换

  特点:
    - 月度配额
    - 超额折扣价
    - 关键任务优先

  示例:
    contract:
      parties: [node-a, node-b]
      term: "2026-04-01 to 2026-06-30"
      mutual_quota:
        node-a: { compute_cu: 2000 }
        node-b: { capability_queries: 10000 }
      overage_rate: 0.8  # 超额部分 8 折
```

### 3. 竞价/现货（Spot Market）

后期再做。

```yaml
spot_market:
  适合:
    - 高峰期算力
    - 稀缺资源
    - 可抢占任务

  特点:
    - 动态定价
    - 实时撮合
    - 可被抢占

  风险:
    - 复杂度高
    - 需要做市商
    - 需要价格稳定机制
```

## 计量可信与审计

### 双边签名验证

```python
def create_meter_record(
    lease: Lease,
    provider_data: MeterData,
    buyer_data: MeterData,
    control_plane_data: MeterData
) -> MeterRecord:
    record = MeterRecord(
        lease_id=lease.id,
        provider_data=provider_data,
        buyer_data=buyer_data,
        control_plane_data=control_plane_data
    )

    # 三方签名
    record.provider_signature = provider.sign(record)
    record.buyer_signature = buyer.sign(record)
    record.control_plane_signature = control_plane.sign(record)

    # 验证签名一致性
    if not verify_meter_consistency(record):
        raise MeterInconsistencyError("Signature mismatch")

    return record
```

### 控制面事件验证

```python
def audit_meter_record(record: MeterRecord) -> AuditResult:
    # 1. 检查控制面日志
    control_events = get_control_plane_events(
        lease_id=record.lease_id,
        timestamp_range=(record.start_time, record.end_time)
    )

    # 2. 验证 heartbeat 一致性
    expected_heartbeats = calculate_expected_heartbeats(record.duration)
    actual_heartbeats = len(control_events.heartbeats)
    if abs(expected_heartbeats - actual_heartbeats) > ALLOWED_SKEW:
        return AuditResult.failed("heartbeat_count_mismatch")

    # 3. 验证资源使用
    reported_usage = record.provider_data.usage
    measured_usage = control_events.resource_usage
    if deviation(reported_usage, measured_usage) > ALLOWED_DEVIATION:
        return AuditResult.failed("usage_deviation_too_large")

    return AuditResult.passed()
```

## 争议处理

### 争议类型

```yaml
dispute_types:
  delivery_failed:
    description: "交付失败"
    buyer_claim: true
    evidence_required: ["task_logs", "error_output"]

  quality_disputed:
    description: "质量争议"
    buyer_claim: true
    evidence_required: ["result_artifact", "quality_metrics"]

  non_payment:
    description: "拒付"
    provider_claim: true
    evidence_required: ["meter_record", "delivery_proof"]

  malicious_task:
    description: "恶意任务"
    provider_claim: true
    evidence_required: ["task_spec", "execution_logs"]

  fake_result:
    description: "虚假结果"
    buyer_claim: true
    evidence_required: ["result_analysis", "verification_proof"]
```

### 仲裁流程

```python
def handle_dispute(dispute: Dispute) -> ArbitrationResult:
    # 1. 收集证据
    evidence = collect_evidence(dispute)

    # 2. 查看双方信誉
    buyer_reputation = get_reputation(dispute.buyer_id, as_role='buyer')
    provider_reputation = get_reputation(dispute.provider_id, as_role='provider')

    # 3. 自动判断（简单案例）
    if is_simple_case(dispute):
        result = auto_judge(dispute, evidence, reputation)

    # 4. 人工仲裁（复杂案例）
    else:
        result = manual_arbitration(dispute, evidence, reputation)

    # 5. 执行裁决
    execute_arbitration(result)

    # 6. 更新信誉
    update_reputation_after_dispute(result)

    return result
```

## 安全边界

### 适合进入市场的资源

```yaml
market_safe:
  - 通用 CPU/GPU 算力
  - 沙箱执行器
  - 只读浏览器池
  - 低风险自动化
  - 标准化数据处理流水线
```

### 需要严格限制的资源

```yaml
market_restricted:
  - 身份绑定 worker
  - 持有个人登录态的能力
  - 企业私有系统写权限
  - 本地桌面与文件系统直连能力
  - 能访问敏感知识库的 agent

  access_mode:
    - federation_only  # 只在联邦内共享
    - whitelist        # 白名单制
    - bilateral        # 双边协定
```

### 永远不可交易

```yaml
never_tradable:
  - 控制面写权限
  - promotion gate 权限
  - 其他节点的私钥
  - 审计日志修改权限
  - 联邦成员身份
```

## 实施路线图

### Phase 0: 内部计量（当前）

**目标**：先把"表"做出来。

```yaml
deliverables:
  - 资源计量框架
  - 基础审计日志
  - 使用统计 dashboard

不需要:
  - 结算
  - 定价
  - 支付
```

### Phase 1: 信用点/配额制（v0.1）

**目标**：联邦内结算单位。

```yaml
deliverables:
  - credits/cu 计账系统
  - 配额管理
  - 资源互换记录
  - 基础信誉系统

结算模式:
  - 先记账，后结算
  - 月度对账
  - 资源互换优先
```

### Phase 2: 双边结算（v0.2）

**目标**：明确的报价与扣费。

```yaml
deliverables:
  - Offer/Order 系统
  - 固定价交易
  - 预付/押金机制
  - 结算单生成

新增:
  - 订单匹配
  - 租约管理
  - 计量记录
  - 基础争议处理
```

### Phase 3: 开放市场（v0.3+）

**目标**：更开放的市场机制。

```yaml
deliverables:
  - 多方报价
  - 动态定价
  - 中介撮合
  - 高级信誉系统
  - 仲裁委员会

新增:
  - 现货竞价
  - 做市商机制
  - 衍生品（期权、期货）
```

## v0.1 原则

### 原则 1：先卖标准化资源

```yaml
v0.1 Tradable:
  - cpu.basic.shared
  - gpu.inference.*
  - sandbox.executor.standard
  - browser.pool.readonly

v0.1 Excluded:
  - service.github.private_account
  - service.gh_agent.identity_bound
  - outcome_services  # 结果型服务暂缓
```

### 原则 2：先做记账，不做真钱

```yaml
settlement_unit: "CU" (Compute Unit)

conversion:
  1 CU = 1 vcpu-minute
  1 CU = 0.01 gpu-hour
  1 CU = 10 capability_queries

真钱支持: v0.2+
```

### 原则 3：先做双边交易

```yaml
market_type: "bilateral"  # 双边

准入:
  - 需要联邦成员
  - 需要最低信誉分
  - 需要通过 KYC（如果用真钱）

公开市场: v0.3+
```

### 原则 4：先做固定价

```yaml
pricing_model: "fixed"

暂不支持:
  - 动态竞价
  - 现货交易
  - 期权/期货

复杂定价: v0.3+
```

### 原则 5：买能力，不买机器控制权

```yaml
buyer_gets:
  - task execution
  - result delivery
  - resource lease (temporary)

buyer_NEVER_gets:
  - machine login
  - shell access
  - persistent control
  - credential access
```

## 数据表汇总

```sql
-- 联邦层（已在 federation-protocol.md 定义）
-- federation_members, federation_charters, federation_audit_log

-- 市场层
CREATE TABLE offers (...);           -- 报价单
CREATE TABLE orders (...);           -- 订单
CREATE TABLE market_leases (...);    -- 租约
CREATE TABLE meter_records (...);    -- 计量记录
CREATE TABLE settlements (...);      -- 结算单
CREATE TABLE reputation_records (...); -- 信誉

-- 执行层（已有）
-- workers, tasks, leases

-- 审计层（已有）
-- audit_log, event_log
```

## 与现有架构的关系

| 现有组件 | 市场层扩展 |
|---------|-----------|
| Worker Registry | 增加 provider 属性 |
| Task Queue | 增加 order_id 关联 |
| Lease Manager | 复用为 market_leases |
| Audit Log | 增加计量与结算审计 |
| Reputation | 从联邦信誉扩展到市场信誉 |

## 成功指标

```yaml
v0.1_success_metrics:
  technical:
    - 计量准确率 > 99%
    - 结算一致性 = 100%
    - 争议响应时间 < 24h

  business:
    - 月度交易额 > 0
    - 活跃交易节点数 > 5
    - 重复交易率 > 60%

  trust:
    - 信誉系统准确率 > 90%
    - 恶意行为检测率 > 95%
    - 仲裁满意度 > 80%
```

## 参考资料

- [Federation Protocol](./federation-protocol.md) - 联邦层定义
- [Distributed Execution](./distributed-execution.md) - 租约与执行模型
- [Uber Marketplace](https://eng.uber.com/marketplace/) - 双边市场设计
- [AWS Spot Instances](https://aws.amazon.com/ec2/spot/) - 现货市场参考
- [Google Preemptible VMs](https://cloud.google.com/compute/docs/instances/preemptible) - 可抢占资源
- [Arbitrum DAO](https://docs.arbitrum.foundation/dao-governance) - DAO 仲裁机制

## 附录：术语对照

| 中文 | 英文 | 定义 |
|------|------|------|
| 联邦 | Federation | 节点间的外交关系与信任体系 |
| 市场 | Market | 资源交易与价值交换机制 |
| 报价单 | Offer | 资源提供方发布的商品信息 |
| 订单 | Order | 购买方发起的购买请求 |
| 租约 | Lease | 资源的临时占用权 |
| 计量 | Metering | 资源使用的测量与记录 |
| 结算 | Settlement | 订单完成后的账单与支付 |
| 信誉 | Reputation | 市场参与者的可信度评分 |
| 争议 | Dispute | 交易过程中的分歧与仲裁 |
| 计算单元 | CU (Compute Unit) | 联邦内的结算单位 |
