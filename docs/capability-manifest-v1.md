# CapabilityManifest v1 / CapabilityManifest v1

## 中文

CapabilityManifest v1 把“能做什么”和“由哪个框架执行”解耦。能力配置放在 `configs/capabilities/*.yaml`，核心字段包括 `capability_id`、`provided_by`、`input_schema`、`output_schema`、`risk_tier`、`policy_refs`、`artifact_types` 和 `lease_enabled`。

本地用户和联邦 peer 都通过 capability 调用能力。AAS 根据 capability 找到 runtime，再执行权限、额度、审批、审计和产物交付。

## English

CapabilityManifest v1 decouples "what this can do" from "which framework runs it". Capability configs live in `configs/capabilities/*.yaml`; core fields include `capability_id`, `provided_by`, `input_schema`, `output_schema`, `risk_tier`, `policy_refs`, `artifact_types`, and `lease_enabled`.

Local users and federation peers both invoke capabilities. AAS resolves the runtime from the capability, then applies permission, quota, approval, audit, and artifact delivery.
