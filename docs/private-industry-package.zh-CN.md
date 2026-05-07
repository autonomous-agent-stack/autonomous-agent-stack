# 私有行业包接入 / Private Industry Package Integration

## 中文

**状态**：Draft  
**范围**：公开接入规范  
**不包含**：任何真实行业实现、客户数据、价格数据、人员数据或私有路径

私有行业包是 AAS 之外的私有扩展包。公开 AAS 仓库只定义接入合同、治理边界和示例假数据；行业知识、客户策略、业务流程、定价逻辑和专有 prompt 必须留在私有包或私有部署环境中。

[English / bilingual version](private-industry-package.md)

## English

**Status**: Draft  
**Scope**: public integration specification  
**Excluded**: any real industry implementation, customer data, price data, personnel data, or private paths

A private industry package is a private extension package outside AAS. The public AAS repository only defines integration contracts, governance boundaries, and fake-data examples. Industry knowledge, customer policies, business workflows, pricing logic, and proprietary prompts must remain inside the private package or private deployment environment.

[English / bilingual version](private-industry-package.md)

## 中文

## 核心规则

- 通过 `CapabilityManifest` 声明 capability，不通过私有 import 暴露能力。
- 通过 `SessionEvent` 记录事实，不在公开仓库沉淀私有业务记录。
- 通过 `ArtifactRef` 引用产物，不直接嵌入真实客户、价格、人员或账号数据。
- 通过 `PolicyDecision` 接受 AAS 治理，不在私有包内创建平行 policy 权威。
- 通过 `Approval` 处理敏感读取、外部写入和高风险动作，不绕过人工确认。

## English

## Core Rules

- Declare capabilities through `CapabilityManifest`, not private imports.
- Record facts through `SessionEvent`, not private business records in the public repository.
- Reference outputs through `ArtifactRef`, without embedding real customer, price, personnel, or account data.
- Accept AAS governance through `PolicyDecision`, without creating a parallel policy authority inside the private package.
- Handle sensitive reads, external writes, and high-risk actions through `Approval`, without bypassing human confirmation.

## 中文

## 禁止事项

- 私有包不得 import AAS private internals。
- 行业业务逻辑不得进入 AAS core。
- 公开仓库不得包含真实客户、价格、人员、合同、账号、供应商或专有 prompt 数据。
- 私有包不得替代 AAS 的 `SessionEvent`、`ArtifactRef`、`PolicyDecision` 或 `Approval`。
- 私有包不得绕过 tool broker、model gateway、artifact ledger、approval gate 或 runtime isolation。

## English

## Prohibitions

- Private packages must not import AAS private internals.
- Industry business logic must not enter AAS core.
- The public repository must not contain real customer, price, personnel, contract, account, vendor, or proprietary prompt data.
- Private packages must not replace AAS `SessionEvent`, `ArtifactRef`, `PolicyDecision`, or `Approval`.
- Private packages must not bypass the tool broker, model gateway, artifact ledger, approval gate, or runtime isolation.

## 中文

## 示例

假数据示例位于 [`examples/private_industry_package_demo/`](../examples/private_industry_package_demo/)。

## English

## Example

The fake-data example lives in [`examples/private_industry_package_demo/`](../examples/private_industry_package_demo/).
