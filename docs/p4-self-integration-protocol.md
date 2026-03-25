# P4 设计文档：自主集成协议（Self-Integration Protocol）

> 版本：Draft v0.1（2026-03-26）  
> 目标：让底座具备“发现外部框架 -> 生成适配器原型 -> 受控升级”的最小闭环能力。

---

## 1. 设计目标

1. 支持输入外部 Repo URL / API 文档 URL，自动形成集成候选。
2. 在不破坏现有稳定链路前提下，输出 Adapter 原型计划（先计划，后执行）。
3. 在推广阶段提供拓扑变更预览与回滚方案，避免盲目热替换。

---

## 2. 范围界定（P4 最小骨架）

### 已包含

- API 三步流：
  - `POST /api/v1/integrations/discover`
  - `POST /api/v1/integrations/prototype`
  - `POST /api/v1/integrations/promote`
- SQLite 持久化：
  - `integration_discoveries`
  - `integration_prototypes`
  - `integration_promotions`
- 风险控制信息：
  - 预设沙盒验证检查项
  - 拓扑变更预览
  - 回滚计划模板

### 暂不包含（后续迭代）

- 自动拉取并解析远程仓库代码
- 自动在 Docker 中执行真实 Adapter 代码生成
- 自动修改生产拓扑并在线切换流量

---

## 3. 核心流程

```text
discover (发现候选)
   -> prototype (生成原型计划 + 安全检查清单)
      -> promote (生成推广计划 + 拓扑预览 + 回滚模板)
```

状态说明（当前骨架）：
- 默认写入为 `created`（代表“计划已建立，待执行”）
- 真实执行状态（`running/completed/failed`）将在下一阶段接入执行引擎后启用

---

## 4. API 契约（最小版）

## 4.1 Discover

`POST /api/v1/integrations/discover`

请求示例：

```json
{
  "source_url": "https://github.com/openclaw/openclaw",
  "source_kind": "repository",
  "ref": "main",
  "metadata": {
    "trigger": "telegram"
  }
}
```

返回重点字段：
- `discovery_id`
- `candidate_adapter_id`
- `detected_capabilities`
- `summary`

## 4.2 Prototype

`POST /api/v1/integrations/prototype`

请求示例：

```json
{
  "discovery_id": "disc_xxx",
  "adapter_name": "openclaw_v2_adapter",
  "sandbox_backend": "docker",
  "dry_run": true
}
```

返回重点字段：
- `prototype_id`
- `planned_files`
- `validation_checks`
- `summary`

## 4.3 Promote

`POST /api/v1/integrations/promote`

请求示例：

```json
{
  "prototype_id": "proto_xxx",
  "rollout_mode": "shadow"
}
```

返回重点字段：
- `promotion_id`
- `topology_patch_preview`
- `rollback_plan`
- `decision`（当前默认 `pending`）

---

## 5. 安全与治理约束

1. **执行前清理**：所有未来会进入沙盒执行的产物，必须先走 `._*` 与 `.DS_Store` 清理。
2. **默认隔离**：原型执行默认目标是 Docker/Colima 沙盒，不直接在宿主执行动态代码。
3. **灰度升级**：`promote` 阶段先生成拓扑预览，默认建议 `shadow` 模式。
4. **强回滚**：每次推广都必须携带回滚步骤，不允许“不可逆”变更。

---

## 6. 下一步实现建议（P4.1）

1. 在 `discover` 阶段接入 Claude CLI 分析器，自动提取外部框架 I/O 协议。
2. 在 `prototype` 阶段接入真实沙盒执行器，自动生成并烟测 AdapterNode。
3. 在 `promote` 阶段接入 A/B 对照压测数据，根据阈值自动审批或拒绝切换。
4. 将三阶段指标接入看板（发现数、原型通过率、推广通过率、回滚次数）。
