# Paperclip 原型 API / Paperclip Prototype API

## 状态 / Status

中文：
本页只描述 `src/api/paperclip_router.py` 当前原型的请求/响应形状。Paperclip 与 AAS 的职责边界、信任模型、API 充分性判断与推荐演进方向，以 [PAPERCLIP_INTEGRATION.md](PAPERCLIP_INTEGRATION.md) 为准。

English:
This page only describes the current request/response shape of the prototype in `src/api/paperclip_router.py`. For boundaries, trust model, API adequacy, and recommended evolution, see [PAPERCLIP_INTEGRATION.md](PAPERCLIP_INTEGRATION.md).

中文：
当前默认主应用 `src/autoresearch/api/main.py` 没有挂载该 router，因此这些端点不是默认启动链路已经承诺的稳定产品接口。

English:
The default main application in `src/autoresearch/api/main.py` does not currently mount this router, so these endpoints are not a stable product API guaranteed by the default startup path.

## 原型端点 / Prototype Endpoints

### `POST /api/v1/paperclip/budget`

中文：
接收一个最小预算指令，在进程内内存中记录请求，并返回自动生成的 `request_id`。当前不会创建 AAS `session`、`run` 或消息投递。

English:
Accepts a minimal budget instruction, stores it in process-local memory, and returns a generated `request_id`. It does not currently create an AAS `session`, `run`, or queue dispatch.

请求字段 / Request fields:

| 字段 / Field | 类型 / Type | 必填 / Required | 说明 / Meaning |
|---|---|---|---|
| `department` | `string` | Yes | 部门名称 / Department name |
| `target_budget` | `float` | Yes | 目标预算金额 / Target budget amount |

响应示例 / Response example:

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

### `POST /api/v1/paperclip/callback`

中文：
接收一个最小执行结果回调，在进程内内存中记录 ROI 与 token 消耗，并返回一条派生的效率字符串。当前不会关联具体 `run_id`、`session_id` 或晋升决策。

English:
Accepts a minimal execution callback, stores ROI and token usage in process-local memory, and returns a derived efficiency string. It does not currently correlate to a concrete `run_id`, `session_id`, or promotion decision.

请求字段 / Request fields:

| 字段 / Field | 类型 / Type | 必填 / Required | 说明 / Meaning |
|---|---|---|---|
| `roi` | `float` | Yes | 投资回报率 / Return on investment |
| `token_used` | `int` | Yes | 消耗的 Token 数量 / Token count used |
| `timestamp` | `string` | Yes | 执行时间戳（ISO 8601）/ Execution timestamp (ISO 8601) |
| `department` | `string` | No | 部门名称 / Department name |

响应示例 / Response example:

```json
{
  "status": "received",
  "message": "执行结果已接收 - ROI: 2.5x, Token: 50,000, 效率: 0.05 ROI/1K tokens",
  "received_at": "2026-03-25T23:35:00"
}
```

### 调试端点 / Debug Endpoints

中文：
以下端点仅用于查看当前进程内内存中的原型记录：

- `GET /api/v1/paperclip/budgets`
- `GET /api/v1/paperclip/callbacks`

English:
The following endpoints are only for inspecting process-local prototype records:

- `GET /api/v1/paperclip/budgets`
- `GET /api/v1/paperclip/callbacks`

## 当前限制 / Current Limitations

中文：

- 无 durable storage
- 无 `run_id` / `session_id`
- 无 lifecycle events
- 无签名、幂等与重试契约
- 默认主应用未挂载

English:

- no durable storage
- no `run_id` / `session_id`
- no lifecycle events
- no signing, idempotency, or retry contract
- not mounted in the default main application
