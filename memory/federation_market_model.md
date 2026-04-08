---
name: Federation + Market Model
description: 双层协作：联邦解决外交关系，市场解决资源交易
type: project
---

# Federation + Market Model

## 核心洞察

**联邦 ≠ 交易**

两个层正交设计，可以独立演进但协同工作：

| 层级 | 回答的问题 | 类似 |
|------|-----------|------|
| 联邦层 | 谁跟谁建交、能共享什么、边界在哪 | 外交关系 |
| 交易层 | 资源怎么定价、怎么买、怎么验收、怎么结算 | 商业贸易 |

> **联邦解决主权与互信，交易解决资源配置与价值交换。**

## 架构分层

```
Control Plane
    ├── Federation Layer（成员身份、建交、共享范围、吊销）
    ├── Market Layer（报价、订单、计量、结算、争议）
    └── Execution Layer（worker/agent 执行）

Audit Layer（日志、签名、账本、可追责）
```

## 可交易资源分类

### 1. 算力商品

最基础，最好起步：
- `cpu.basic.shared`
- `gpu.inference.a10.hourly`
- `browser.pool.readonly.minute`
- `sandbox.executor.standard`

### 2. 能力服务

卖的是"特殊能力"，而非裸算力：
- `service.github.content_kb.private_account`
- `service.gh_agent.identity_bound`
- `service.browser.automation`

### 3. 结果型服务

按交付物收费：
- `service.repo.analysis.full`
- `service.documentation.generate`

## 核心数据模型

### Offer（报价单）

资源提供方挂出来的商品：
- provider_node_id
- resource_type
- price_model / unit_price
- max_concurrency
- visibility / policy_constraints

### Order（订单）

购买方发起的请求：
- buyer_node_id
- target_offer_id
- requested_units
- budget_limit
- escrow_amount

### Lease（租约）

资源占用权，与分布式执行的 lease 一致

### Meter Record（计量记录）

结算依据，需要双边签名验证：
- actual_duration
- cpu_time / gpu_time
- provider / buyer / control_plane 签名

### Settlement（结算单）

订单结束后的账单：
- base_amount
- refund_amount
- penalty_amount
- final_amount

### Reputation（信誉）

市场健康度的关键：
- success_rate
- timeout_rate
- sla_compliance_rate
- dispute_count
- malicious_behavior_indicators

## 交易模式

### 1. 固定价（最适合起步）

- 沙箱 worker
- GPU 推理
- 标准能力服务

### 2. 协议价/合同价（联邦成员）

- 月度配额
- 超额折扣价
- 关键任务优先

### 3. 竞价/现货（后期再做）

- 高峰期算力
- 稀缺资源
- 可抢占任务

## 实施路线图

### Phase 0: 内部计量

- 资源计量框架
- 基础审计日志
- 使用统计

### Phase 1: 信用点/配额制（v0.1）

- credits/cu 记账
- 配额管理
- 资源互换
- **先记账，不结算真钱**

### Phase 2: 双边结算（v0.2）

- Offer/Order 系统
- 固定价交易
- 预付/押金
- 基础争议

### Phase 3: 开放市场（v0.3+）

- 多方报价
- 动态定价
- 中介撮合

## v0.1 核心原则

1. **先卖标准化资源**：CPU/GPU/沙箱，不包括身份绑定能力
2. **先做记账，不做真钱**：用 CU（Compute Unit）结算
3. **先做双边交易**：需要在联邦内，不是公开市场
4. **先做固定价**：不做动态竞价
5. **买能力，不买机器控制权**：task execution + result delivery

## 安全边界

### 适合进入市场

- 通用 CPU/GPU 算力
- 沙箱执行器
- 只读浏览器池
- 低风险自动化

### 需要严格限制

- 身份绑定 worker → 联邦内共享 / 白名单
- 持有个人登录态的能力 → 双边协定

### 永远不可交易

- 控制面写权限
- promotion gate 权限
- 其他节点的私钥
- 联邦成员身份

## 一句话总结

**store 是货架，federation 是外交，market 是贸易。**

## 文档

详见：`docs/rfc/federation-market-model.md`
