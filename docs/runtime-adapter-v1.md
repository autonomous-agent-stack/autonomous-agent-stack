# RuntimeAdapter v1 / RuntimeAdapter v1

## 中文

RuntimeAdapter v1 把所有执行面统一成同一个合同：`create_session`、`run`、`stream`、`cancel`、`status` 和 `doctor`。Hermes、OpenClaw、OpenHands、CrewAI、Haystack、LangGraph 和 A2A 都通过 `configs/runtime_agents/*.yaml` 注册。

AAS 不依赖任一 runtime 的内部对象。Adapter 只负责把 AAS `RuntimeRunRequest` / AEP `JobSpec` 转成目标框架可执行的输入，并把结果映射回 `RuntimeRunRead`、`RuntimeStreamEvent`、`DriverResult` 和 `ArtifactRef`。

## English

RuntimeAdapter v1 normalizes all execution surfaces into one contract: `create_session`, `run`, `stream`, `cancel`, `status`, and `doctor`. Hermes, OpenClaw, OpenHands, CrewAI, Haystack, LangGraph, and A2A are registered through `configs/runtime_agents/*.yaml`.

AAS does not depend on any runtime's internal objects. Each adapter only translates AAS `RuntimeRunRequest` / AEP `JobSpec` into the target framework input, then maps the result back to `RuntimeRunRead`, `RuntimeStreamEvent`, `DriverResult`, and `ArtifactRef`.
