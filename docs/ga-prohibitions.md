# Evergreen OS GA Prohibitions / Evergreen OS GA 禁止事项

## 中文

以下行为在 Evergreen OS GA 中一律禁止。测试结果优先于文档声明。

- 新增 `/api/v1/*` 主能力；v1 只能做 compatibility shim。
- 让 summary、prompt bundle、handoff brief、audit report 或 replay plan 成为事实源。
- mock-only、demo-only、fake stream、no-op cancel、fake artifact 标记为 `stable`。
- approval 只写日志但不阻断动作。
- adapter 直接读取 secret、`.env`、host home 或全局凭据。
- adapter 直接调用模型，绕过 Model Gateway。
- adapter 直接调用工具，绕过 Tool Broker。
- adapter 直接外发消息或改业务对象，绕过 PolicyDecision。
- federation 默认开启。
- unknown runtime、tool、model、peer 默认 allow。
- business package 污染 core。
- UI、CLI、SDK 直接修改数据库或 repository，绕过 `/api/v2/*`。
- artifact promotion 绕过 promotion gate。

## English

The following behaviors are prohibited for Evergreen OS GA. Automated tests take precedence over documentation claims.

- Adding new primary `/api/v1/*` capabilities; v1 is compatibility shim only.
- Treating summaries, prompt bundles, handoff briefs, audit reports, or replay plans as facts.
- Marking mock-only, demo-only, fake-stream, no-op-cancel, or fake-artifact implementations as `stable`.
- Logging an approval rejection without blocking the action.
- Letting adapters read secrets, `.env`, host home directories, or global credentials directly.
- Letting adapters call models directly instead of the Model Gateway.
- Letting adapters call tools directly instead of the Tool Broker.
- Letting adapters send messages or mutate business objects without PolicyDecision.
- Enabling federation by default.
- Default-allowing unknown runtimes, tools, models, or peers.
- Polluting core with business packages.
- Letting UI, CLI, or SDK mutate databases or repositories directly instead of `/api/v2/*`.
- Promoting artifacts without the promotion gate.
