# Private Industry Package Demo / 私有行业包示例

## 中文

这是一个只使用假数据的公开示例，用来演示私有行业包如何通过 AAS public contracts 接入。它不包含真实客户、价格、人员、账号、供应商、路径、图片素材或行业私有实现。

示例文件：

- [`capability_manifest.json`](capability_manifest.json)：假 capability manifest。
- [`topology.json`](topology.json)：符合 `agent-topology/v1` 的假 topology snapshot。
- [`session_event.json`](session_event.json)：假 `SessionEvent`。
- [`artifact_ref.json`](artifact_ref.json)：假 `ArtifactRef`。
- [`policy_decision.json`](policy_decision.json)：假 `PolicyDecision`。
- [`approval.json`](approval.json)：假 `Approval`。

## English

This is a public fake-data example that demonstrates how a private industry package integrates through AAS public contracts. It does not contain real customer, price, personnel, account, vendor, path, image asset, or private industry implementation data.

Example files:

- [`capability_manifest.json`](capability_manifest.json): fake capability manifest.
- [`topology.json`](topology.json): fake topology snapshot conforming to `agent-topology/v1`.
- [`session_event.json`](session_event.json): fake `SessionEvent`.
- [`artifact_ref.json`](artifact_ref.json): fake `ArtifactRef`.
- [`policy_decision.json`](policy_decision.json): fake `PolicyDecision`.
- [`approval.json`](approval.json): fake `Approval`.

## 中文

## 边界

- 示例包只通过 `CapabilityManifest`、`SessionEvent`、`ArtifactRef`、`PolicyDecision` 和 `Approval` 与 AAS 对齐。
- 示例包不 import AAS private internals。
- 示例包不把业务逻辑放进 AAS core。
- 示例包不把 prompt-to-image MCP 暴露到 LAN 或 public network。

## English

## Boundaries

- The demo package aligns with AAS only through `CapabilityManifest`, `SessionEvent`, `ArtifactRef`, `PolicyDecision`, and `Approval`.
- The demo package does not import AAS private internals.
- The demo package does not put business logic into AAS core.
- The demo package does not expose prompt-to-image MCP to LAN or the public network.
