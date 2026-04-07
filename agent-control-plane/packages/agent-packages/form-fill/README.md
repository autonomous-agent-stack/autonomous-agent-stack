# 影刀表单录入 Agent

> **Agent Package ID**: yingdao_form_fill_agent_v0
> **版本**: 0.1.0
> **风险级别**: high

---

## 功能描述

自动录入客户订单信息到 ERP 系统。

**适用场景**:
- 客户订单批量录入
- 财务系统数据录入
- ERP 系统表单填写

**不适用场景**:
- 需要复杂判断的订单
- 需要人工审核的订单
- 金额超过 1000 元的订单 (需审批)

---

## 输入参数

### customer_name (必需)
- **类型**: string
- **长度**: 2-100 字符
- **说明**: 客户姓名

### order_id (必需)
- **类型**: string
- **格式**: ORD + 8位数字 (例: ORD20260331)
- **说明**: 订单号

### amount (必需)
- **类型**: number
- **范围**: 0.01 - 999999.99
- **说明**: 订单金额

### priority (可选)
- **类型**: string
- **枚举**: normal | urgent | critical
- **默认值**: normal
- **说明**: 优先级

---

## 输出结果

### success
- **类型**: boolean
- **说明**: 是否成功

### receipt
- **类型**: object
- **字段**:
  - `erp_id`: ERP 系统内的记录 ID
  - `timestamp`: 录入时间戳
  - `operator`: 操作员

### artifacts
- **类型**: array
- **包含**:
  - screenshot (PNG)
  - log (JSON)
  - receipt (JSON)

---

## 使用示例

### 标准订单录入

```json
{
  "customer_name": "张三",
  "order_id": "ORD20260331",
  "amount": 1500.00
}
```

**预期输出**:
```json
{
  "success": true,
  "receipt": {
    "erp_id": "ERP123456",
    "timestamp": "2026-03-31T15:20:00Z",
    "operator": "yingdao_worker"
  },
  "artifacts": [
    {
      "type": "screenshot",
      "path": "/artifacts/screenshot_001.png"
    },
    {
      "type": "log",
      "path": "/artifacts/log_001.json"
    },
    {
      "type": "receipt",
      "path": "/artifacts/receipt_001.json"
    }
  ]
}
```

---

## 治理规则

### 风险级别
**high** - 涉及写操作，需要审批

### 审批规则
- 写操作需要审批
- 删除操作需要审批
- 需要至少 1 个审批人
- 自动批准条件:
  - 金额 ≤ 1000 元
  - 来源为 internal_system 或 verified_api

### 权限边界
- 最大执行时间: 300 秒
- 最大重试次数: 3 次

---

## 失败处理

### Fallback 策略
**manual** - 失败后转人工处理

### 重试策略
- 最大重试: 2 次
- 重试延迟: 5000ms
- 退避乘数: 2
- 可重试错误:
  - NETWORK_ERROR
  - TIMEOUT
  - ERP_BUSY

### 升级策略
- 重试失败后升级
- 升级到: manual
- 升级超时: 60000ms

---

## 执行流程

```
1. 打开 ERP 系统
2. 导航到订单录入页面
3. 填写表单:
   - 客户姓名: customer_name
   - 订单号: order_id
   - 金额: amount
   - 优先级: priority
4. 点击"提交"按钮
5. 等待确认消息 (最多 30 秒)
6. 截图保存
7. 提取回执信息:
   - ERP ID
   - 时间戳
   - 操作员
8. 记录日志
9. 返回结果
```

---

## 错误处理

### 网络错误
- **错误码**: NETWORK_ERROR
- **重试**: 是
- **延迟**: 5000ms

### 元素未找到
- **错误码**: ELEMENT_NOT_FOUND
- **重试**: 否
- **建议**: 转人工

### 验证失败
- **错误码**: VALIDATION_FAILED
- **重试**: 否
- **建议**: 转人工

### ERP 繁忙
- **错误码**: ERP_BUSY
- **重试**: 是
- **延迟**: 5000ms

---

## 验证

### 验证 manifest

```bash
cd agent-control-plane
node scripts/validate-package.js packages/agent-packages/form-fill/manifest.json
```

### 测试运行

```bash
cd agent-control-plane
npm test -- form-fill
```

---

## 依赖

### 平台
- win_yingdao ≥ 3.0.0

### 工具
- flow_runner
- screenshot
- file_system

---

## 质量指标

- 平均成功率: 95%
- 平均执行时间: 15000ms
- 总执行次数: 0
- 最后更新: 2026-03-31

---

## 许可证

MIT

---

## 作者

Agent Control Plane Team
