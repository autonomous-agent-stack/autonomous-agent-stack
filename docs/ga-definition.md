# Evergreen OS GA Definition / Evergreen OS GA 定义

## 中文

Evergreen OS GA 不是“接口存在”、不是“文档完整”、也不是“demo 能跑”。任何能力、adapter、connector、package、runtime 或平台模块只有同时满足以下条件，才可以标记为 `stable`：

- `stable contract`：有版本化 Pydantic 合同、JSON Schema、example payload 和兼容说明。
- `production implementation`：连接真实执行路径；不能只有 mock、fixture、demo string 或占位返回。
- `migration path`：有从旧数据或旧接口投影到 GA 合同的迁移路径。
- `rollback path`：失败回滚不得破坏 SessionEvent facts。
- `security boundary`：受 Identity、Secret Vault、PolicyDecision、Model Gateway、Tool Broker、Runtime Isolation 约束。
- `bypass tests`：有自动化测试证明不能绕过模型、工具、凭据、审批、artifact promotion 和 API。
- `live integration path`：有 live test 文件、环境变量说明、doctor；缺凭据可以 skip，但不能缺测试入口。
- `observability`：写入 SessionEvent、audit、usage/cost 或 health report。
- `failure recovery`：有 timeout、retry、lease、dead-letter 或 handoff 语义。
- `compatibility matrix`：通过机器可读 certification matrix。

禁止把只有 schema、只有文档、只有 mock、只有 demo 的能力标为 `stable`。未通过全部阻断门禁的能力必须标为 `beta` 或 `experimental`，并在认证矩阵写清缺项。

## English

Evergreen OS GA does not mean "the endpoint exists", "the docs are complete", or "the demo runs." A capability, adapter, connector, package, runtime, or platform module may be marked `stable` only when all of the following are true:

- `stable contract`: versioned Pydantic contract, JSON Schema, example payload, and compatibility notes.
- `production implementation`: wired to a real execution path, not only mocks, fixtures, demo strings, or placeholder returns.
- `migration path`: old data or old endpoints can project into the GA contract.
- `rollback path`: rollback does not destroy SessionEvent facts.
- `security boundary`: governed by Identity, Secret Vault, PolicyDecision, Model Gateway, Tool Broker, and Runtime Isolation.
- `bypass tests`: automated tests prove model, tool, secret, approval, artifact promotion, and API paths cannot be bypassed.
- `live integration path`: live test file, environment variable documentation, and doctor entrypoint exist; missing credentials may skip live tests, but the entrypoint must exist.
- `observability`: writes SessionEvent, audit, usage/cost, or health report data.
- `failure recovery`: timeout, retry, lease, dead-letter, or handoff semantics exist.
- `compatibility matrix`: passes the machine-readable certification matrix.

Capabilities with only schema, docs, mocks, or demos must not be marked `stable`. Anything that does not pass every blocking gate must be marked `beta` or `experimental`, with gaps recorded in the certification matrix.
