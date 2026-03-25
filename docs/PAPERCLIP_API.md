# Paperclip 协同 API

外部企业管理系统双向接口，用于预算指令下发和执行结果回调。

---

## POST /api/v1/paperclip/budget

接收目标预算指令，触发 Agent 系统执行流程。

### 请求

```bash
curl -X POST http://localhost:8000/api/v1/paperclip/budget \
  -H "Content-Type: application/json" \
  -d '{
    "department": "玛露美妆销售部",
    "target_budget": 100000
  }'
```

### 参数

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `department` | string | ✅ | 部门名称 |
| `target_budget` | float | ✅ | 目标预算金额 |

### 响应

```json
{
  "status": "accepted",
  "message": "预算指令已接收，部门：玛露美妆销售部，目标预算：¥100,000.00",
  "department": "玛露美妆销售部",
  "target_budget": 100000.0,
  "timestamp": "2026-03-25T23:35:00",
  "request_id": "budget_20260325_233500_1234"
}
```

---

## POST /api/v1/paperclip/callback

接收 Agent 执行结果的 ROI 和 Token 消耗数据。

### 请求

```bash
curl -X POST http://localhost:8000/api/v1/paperclip/callback \
  -H "Content-Type: application/json" \
  -d '{
    "roi": 2.5,
    "token_used": 50000,
    "timestamp": "2026-03-25T23:35:00Z",
    "department": "玛露美妆销售部"
  }'
```

### 参数

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `roi` | float | ✅ | 投资回报率 |
| `token_used` | int | ✅ | 消耗的 Token 数量 |
| `timestamp` | string | ✅ | 执行时间戳 (ISO 8601) |
| `department` | string | ❌ | 部门名称（可选） |

### 响应

```json
{
  "status": "received",
  "message": "执行结果已接收 - ROI: 2.5x, Token: 50,000, 效率: 0.05 ROI/1K tokens",
  "received_at": "2026-03-25T23:35:00"
}
```

---

## 完整示例：玛露美妆销售部

### 步骤 1：下发预算指令

```bash
curl -X POST http://localhost:8000/api/v1/paperclip/budget \
  -H "Content-Type: application/json" \
  -d '{
    "department": "玛露美妆销售部",
    "target_budget": 50000
  }'
```

### 步骤 2：Agent 执行（内部流程）

系统自动触发预算执行流程，生成营销方案。

### 步骤 3：接收执行结果

```bash
curl -X POST http://localhost:8000/api/v1/paperclip/callback \
  -H "Content-Type: application/json" \
  -d '{
    "roi": 3.2,
    "token_used": 125000,
    "timestamp": "2026-03-25T23:40:00Z",
    "department": "玛露美妆销售部"
  }'
```

### 步骤 4：查询记录（调试用）

```bash
# 查询所有预算指令
curl http://localhost:8000/api/v1/paperclip/budgets

# 查询所有回调记录
curl http://localhost:8000/api/v1/paperclip/callbacks
```

---

## 数据流

```
外部企业管理系统
       │
       ▼ POST /budget
┌──────────────────┐
│  OpenClaw Agent  │
│     系统         │
└──────────────────┘
       │
       ▼ POST /callback
外部企业管理系统
```
