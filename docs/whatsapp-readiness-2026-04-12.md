# WhatsApp 接入可用性评估（2026-04-12）

## 结论（TL;DR）

- **单机版 AAS 现在是「Telegram 可用、通道抽象存在但未落地 WhatsApp provider」的状态。**
- 以当前主干代码估算，接入 WhatsApp 到「可内测」大约还差 **2~4 天工程量**（1 人，熟悉 FastAPI/Python）。
- 若目标是「可生产」并包含风控、审计、回放、重试与监控，建议按 **1~2 周**预算。

## 现状证据

1. 主 API 入口显式挂载了 Telegram gateway，且描述文本仍以 Telegram 为主入口。
2. 配置层是 Telegram 专用（`AUTORESEARCH_TELEGRAM_*`），通知服务也是 Telegram Bot API 直连。
3. 管理面存在 channel 配置模型，但 provider 枚举仅 `telegram/webhook/http/custom`，未出现 `whatsapp`。
4. README（stable 模式）把 Telegram 集成标记为需额外 bot token，不属于开箱即用。
5. 当前测试里，主线 Telegram webhook guard 用例存在失败，说明“当前分支即时可用性”还需补稳。

## 最短落地路径（建议）

### Phase 1（先打通，1~2 天）

- 增加 `WhatsAppSettings`（环境变量前缀 `AUTORESEARCH_WHATSAPP_*`）。
- 新增 `WhatsAppNotifierService`（发送消息、基础重试、请求超时）。
- 新建路由：`/api/v1/gateway/whatsapp/webhook`。
- 复用既有会话模型：新增 `build_whatsapp_session_identity`，保持 `AssistantScope/ActorRole` 不变。
- 在 `main.py` 挂载 WhatsApp router（与 Telegram 并行，不改现有主路径）。

### Phase 2（可运营，1~2 天）

- 在 admin channel provider 中加入 `whatsapp`（前后端表单、校验、默认 key）。
- 把“渠道发送”从 Telegram 直调改成 provider dispatch（至少支持 telegram + whatsapp）。
- 增加 focused tests：webhook 签名校验、消息去重、channel secret 解析。

### Phase 3（可生产，3~5 天）

- 完整 webhook 签名验签与重放保护。
- 死信与重试策略（429/5xx）。
- 观测与审计：按 channel 打点、失败分类、告警阈值。

## 风险与前置条件

- 需要你确认 WhatsApp 具体接入形态（Cloud API / BSP / Twilio）。
- 若先走 `provider="webhook"` 代理模式可更快上线，但长期维护成本高于原生 provider。
- 建议先把 Telegram 主线 failing test 修稳后再并行接 WhatsApp，避免把不稳定基线复制到新通道。

## 验收标准（建议）

- `POST /api/v1/gateway/whatsapp/webhook` 可完成：验签 → 会话识别 → 任务触发 → 回消息。
- admin 可创建 `provider=whatsapp` channel 并成功轮转 secret。
- 关键链路测试通过：
  - webhook 鉴权
  - 去重与限流
  - 通知发送与失败重试

