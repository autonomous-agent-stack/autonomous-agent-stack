# Private Industry Package Integration / 私有行业包接入

## 中文

**状态**：Draft  
**范围**：公开接入规范  
**不包含**：任何真实行业实现、客户数据、价格数据、人员数据或私有路径

私有行业包是 AAS 之外的私有扩展包。公开 AAS 仓库只定义接入合同、治理边界和示例假数据；行业知识、客户策略、业务流程、定价逻辑和专有 prompt 必须留在私有包或私有部署环境中。

[简体中文版本](private-industry-package.zh-CN.md)

## English

**Status**: Draft  
**Scope**: public integration specification  
**Excluded**: any real industry implementation, customer data, price data, personnel data, or private paths

A private industry package is a private extension package outside AAS. The public AAS repository only defines integration contracts, governance boundaries, and fake-data examples. Industry knowledge, customer policies, business workflows, pricing logic, and proprietary prompts must remain inside the private package or private deployment environment.

[Simplified Chinese version](private-industry-package.zh-CN.md)

## 中文

## 接入原则

私有行业包只能通过公开合同接入 AAS：

- `CapabilityManifest` 描述包能提供什么 capability。
- `SessionEvent` 记录执行事实和审计时间线。
- `ArtifactRef` 引用包产出的报告、计划、图片、补丁或合规证据。
- `PolicyDecision` 记录 AAS 对执行、网络、工具、模型和数据边界的治理结果。
- `Approval` 记录敏感读取、外部写入、高风险动作或人工确认。

私有包可以拥有自己的业务代码、行业 schema、内部知识库和供应商适配器，但这些内容不得进入 AAS core 或公开仓库。

## English

## Integration Principles

A private industry package may integrate with AAS only through public contracts:

- `CapabilityManifest` describes which capabilities the package provides.
- `SessionEvent` records execution facts and the audit timeline.
- `ArtifactRef` references reports, plans, images, patches, or compliance evidence emitted by the package.
- `PolicyDecision` records AAS governance decisions for execution, network, tools, models, and data boundaries.
- `Approval` records sensitive reads, external writes, high-risk actions, or human confirmations.

The private package may own its business code, industry schemas, internal knowledge base, and vendor adapters, but those assets must not enter AAS core or the public repository.

## 中文

## Contract 映射

| AAS 合同 | 私有包责任 | AAS 责任 |
| --- | --- | --- |
| `CapabilityManifest` | 声明 capability id、输入输出 schema、risk tier、artifact types 和 policy refs。 | 注册、展示、治理和调度 capability。 |
| `SessionEvent` | 通过 AAS API 回报可审计事实，不写入私有数据库细节。 | 维护 append-only 事实时间线。 |
| `ArtifactRef` | 输出可引用 artifact，不把大对象或私有数据直接塞进事件。 | 记录 artifact 引用、hash 和治理证据。 |
| `PolicyDecision` | 在执行前遵守 AAS 给出的 allow、deny 或 approval-required 决策。 | 统一执行 policy、network、tool、model 和 data 边界。 |
| `Approval` | 对需要人工确认的动作等待 approval，不自行绕过。 | 创建、过期、批准、拒绝和审计 approval。 |

## English

## Contract Mapping

| AAS Contract | Private Package Responsibility | AAS Responsibility |
| --- | --- | --- |
| `CapabilityManifest` | Declare capability id, input/output schemas, risk tier, artifact types, and policy refs. | Register, display, govern, and schedule capabilities. |
| `SessionEvent` | Report auditable facts through AAS APIs without writing private database details. | Maintain the append-only factual timeline. |
| `ArtifactRef` | Emit referenceable artifacts instead of embedding large objects or private data in events. | Record artifact references, hashes, and governance evidence. |
| `PolicyDecision` | Respect allow, deny, or approval-required decisions before execution. | Enforce policy, network, tool, model, and data boundaries consistently. |
| `Approval` | Wait for approval for human-confirmed actions and never bypass it. | Create, expire, approve, reject, and audit approvals. |

## 中文

## 接入流程草案

1. 私有包发布自己的 `CapabilityManifest`，只包含公开 capability 元数据和 schema。
2. AAS 通过 registry 或配置读取 manifest，不 import 私有包内部模块。
3. AAS 根据 policy 生成 `PolicyDecision`；若需要人工确认，则创建 `Approval`。
4. AAS runtime 或 worker 在受控边界内调用 capability。
5. 私有包返回 `ArtifactRef` 和状态摘要，不返回真实客户、价格、人员或账号数据。
6. AAS 追加 `SessionEvent`，把执行结果、artifact 引用、policy decision 和 approval 串成可审计时间线。

## English

## Draft Integration Flow

1. The private package publishes its `CapabilityManifest` with only public capability metadata and schemas.
2. AAS reads the manifest through a registry or configuration; it does not import private package internals.
3. AAS produces a `PolicyDecision`; if human confirmation is required, AAS creates an `Approval`.
4. An AAS runtime or worker invokes the capability inside the governed boundary.
5. The private package returns `ArtifactRef` values and status summaries, not real customer, price, personnel, or account data.
6. AAS appends `SessionEvent` records that link execution result, artifact references, policy decisions, and approvals into an auditable timeline.

## 中文

## 禁止事项

- 私有包不得 import AAS private internals；只能使用 public contracts、API、manifest 和 adapter boundary。
- 行业业务逻辑不得进入 AAS core、GA gate、runtime scheduler 或公共 router。
- 公开仓库不得包含真实客户、价格、人员、合同、账号、供应商或专有 prompt 数据。
- 私有包不得把 AAS 的 `PolicyDecision`、`Approval`、`SessionEvent` 或 `ArtifactRef` 换成自己的平行事实源。
- 私有包不得绕过 AAS 的 tool broker、model gateway、artifact ledger、approval gate 或 runtime isolation。

## English

## Prohibitions

- Private packages must not import AAS private internals; they may only use public contracts, APIs, manifests, and adapter boundaries.
- Industry business logic must not enter AAS core, GA gates, runtime schedulers, or public routers.
- The public repository must not contain real customer, price, personnel, contract, account, vendor, or proprietary prompt data.
- Private packages must not replace AAS `PolicyDecision`, `Approval`, `SessionEvent`, or `ArtifactRef` with parallel sources of truth.
- Private packages must not bypass the AAS tool broker, model gateway, artifact ledger, approval gate, or runtime isolation.

## 中文

## 最小 manifest 形状

```json
{
  "capability_id": "demo.industry.report",
  "kind": "workflow",
  "provided_by": "example-private-industry-package",
  "display_name": "Demo Industry Report",
  "description": "Fake-data demonstration capability only.",
  "enabled": true,
  "risk_tier": "common_read",
  "input_schema": {
    "type": "object",
    "properties": {
      "brief": {
        "type": "string"
      }
    },
    "required": ["brief"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "artifact_refs": {
        "type": "array"
      }
    }
  },
  "artifact_types": ["report", "compliance"],
  "policy_refs": ["policy/private-package/public-contract-only"],
  "metadata": {
    "data_classification": "fake_demo_data"
  }
}
```

## English

## Minimal Manifest Shape

```json
{
  "capability_id": "demo.industry.report",
  "kind": "workflow",
  "provided_by": "example-private-industry-package",
  "display_name": "Demo Industry Report",
  "description": "Fake-data demonstration capability only.",
  "enabled": true,
  "risk_tier": "common_read",
  "input_schema": {
    "type": "object",
    "properties": {
      "brief": {
        "type": "string"
      }
    },
    "required": ["brief"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "artifact_refs": {
        "type": "array"
      }
    }
  },
  "artifact_types": ["report", "compliance"],
  "policy_refs": ["policy/private-package/public-contract-only"],
  "metadata": {
    "data_classification": "fake_demo_data"
  }
}
```

## 中文

## 示例

假数据示例位于 [`examples/private_industry_package_demo/`](../examples/private_industry_package_demo/)。

## English

## Example

The fake-data example lives in [`examples/private_industry_package_demo/`](../examples/private_industry_package_demo/).
