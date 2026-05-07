# Prompt-to-Image MCP Connector / Prompt-to-Image MCP 接入

## 中文

**状态**：Draft  
**范围**：通用 MCP 接入、安全边界和 artifact 记录  
**不包含**：真实账号、真实本机路径、供应商密钥、客户素材或私有 prompt

本文描述 prompt-to-image MCP connector 如何作为受治理工具接入 AAS。它只定义通用边界：localhost-only、AAS-issued policy、`ArtifactRef` 输出和 `DesignPromptAudit` 审计记录。

## English

**Status**: Draft  
**Scope**: generic MCP integration, safety boundary, and artifact recording  
**Excluded**: real accounts, real local paths, vendor secrets, customer assets, or private prompts

This document describes how a prompt-to-image MCP connector integrates with AAS as a governed tool. It only defines generic boundaries: localhost-only exposure, AAS-issued policy, `ArtifactRef` outputs, and `DesignPromptAudit` audit records.

## 中文

## 接入模型

prompt-to-image MCP 必须作为工具边界接入，而不是作为 AAS core 模块接入。

- MCP server 只监听 `127.0.0.1` 或等价 localhost。
- AAS 通过 tool broker 或 runtime adapter 调用 MCP capability。
- MCP connector 返回 `ArtifactRef`，不把图片二进制或私有 prompt 直接塞进 `SessionEvent`。
- AAS 用 `PolicyDecision` 判断是否允许生成、是否需要 approval、是否允许读取输入素材。
- 高风险或外部写入动作必须先获得 `Approval`。

## English

## Integration Model

prompt-to-image MCP must integrate as a tool boundary, not as an AAS core module.

- The MCP server only listens on `127.0.0.1` or an equivalent localhost address.
- AAS invokes MCP capabilities through the tool broker or runtime adapter.
- The MCP connector returns `ArtifactRef` values and does not embed image binaries or private prompts directly in `SessionEvent`.
- AAS uses `PolicyDecision` to decide whether generation is allowed, whether approval is required, and whether input asset reads are allowed.
- High-risk or external-write actions must receive `Approval` first.

## 中文

## localhost-only 边界

prompt-to-image MCP 不得暴露到 LAN 或 public network。

允许：

- `127.0.0.1`
- `localhost`
- 仅当前机器可访问的 Unix domain socket

禁止：

- `0.0.0.0`
- 真实 LAN IP
- public IP
- 公网 tunnel
- 未经 AAS policy allowlist 的远端 callback

## English

## localhost-only Boundary

prompt-to-image MCP must not be exposed to LAN or the public network.

Allowed:

- `127.0.0.1`
- `localhost`
- Unix domain socket reachable only from the current machine

Prohibited:

- `0.0.0.0`
- real LAN IP
- public IP
- public tunnel
- remote callbacks not allowlisted by AAS policy

## 中文

## ArtifactRef 输出

图片结果必须通过 `ArtifactRef` 引用：

```json
{
  "name": "demo-image-preview",
  "kind": "custom",
  "uri": "artifact://session-demo/run-demo/generated/demo-image-preview.png",
  "sha256": "example-sha256-placeholder"
}
```

`uri` 应指向 AAS 授权 artifact root 下的产物引用。公开文档和示例不得包含真实本机路径、客户素材路径或账号目录。

## English

## ArtifactRef Output

Image results must be referenced through `ArtifactRef`:

```json
{
  "name": "demo-image-preview",
  "kind": "custom",
  "uri": "artifact://session-demo/run-demo/generated/demo-image-preview.png",
  "sha256": "example-sha256-placeholder"
}
```

The `uri` should point to an artifact reference under the AAS-authorized artifact root. Public docs and examples must not contain real local paths, customer asset paths, or account directories.

## 中文

## DesignPromptAudit

`DesignPromptAudit` 是建议的审计 payload，用于记录 prompt-to-image 调用的治理证据。它不是事实源；事实源仍是 `SessionEvent`。

建议字段：

| 字段 | 含义 |
| --- | --- |
| `audit_id` | 审计记录 id。 |
| `session_id` | AAS session id。 |
| `run_id` | AAS run id。 |
| `capability_id` | 触发的 MCP capability。 |
| `prompt_classification` | `safe_demo`、`customer_asset`、`restricted_brand` 等分类。 |
| `input_artifact_refs` | 输入素材引用，不放真实路径。 |
| `output_artifact_refs` | 输出图片或报告引用。 |
| `policy_decision_id` | 关联的 `PolicyDecision`。 |
| `approval_id` | 如需要人工确认，则记录 approval。 |
| `redaction_summary` | 已移除的敏感字段摘要。 |

## English

## DesignPromptAudit

`DesignPromptAudit` is a recommended audit payload for governance evidence around prompt-to-image calls. It is not a source of truth; the source of truth remains `SessionEvent`.

Recommended fields:

| Field | Meaning |
| --- | --- |
| `audit_id` | Audit record id. |
| `session_id` | AAS session id. |
| `run_id` | AAS run id. |
| `capability_id` | MCP capability invoked. |
| `prompt_classification` | Classification such as `safe_demo`, `customer_asset`, or `restricted_brand`. |
| `input_artifact_refs` | Input asset references, without real paths. |
| `output_artifact_refs` | Output image or report references. |
| `policy_decision_id` | Linked `PolicyDecision`. |
| `approval_id` | Approval record when human confirmation is required. |
| `redaction_summary` | Summary of sensitive fields removed. |

## 中文

## 禁止事项

- prompt-to-image MCP 不得绑定 `0.0.0.0`、LAN IP 或 public IP。
- 公开仓库不得出现真实账号、供应商 token、本机私有路径、客户素材路径或私有 prompt。
- MCP connector 不得直接读取全局凭据、`.env`、host home 或系统 keychain。
- MCP connector 不得绕过 AAS `PolicyDecision`、`Approval`、tool broker、artifact ledger 或 runtime isolation。
- 生成结果不得直接写入外部系统；外部写入必须走 AAS approval 和 governed connector。

## English

## Prohibitions

- prompt-to-image MCP must not bind to `0.0.0.0`, LAN IPs, or public IPs.
- The public repository must not contain real accounts, vendor tokens, private local paths, customer asset paths, or private prompts.
- The MCP connector must not directly read global credentials, `.env`, host home directories, or system keychains.
- The MCP connector must not bypass AAS `PolicyDecision`, `Approval`, the tool broker, artifact ledger, or runtime isolation.
- Generation results must not be written directly to external systems; external writes must go through AAS approval and a governed connector.
