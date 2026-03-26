# autonomous-agent-stack 对上游框架演进的可更新性评估

**日期**：2026-03-26  
**范围**：OpenClaw 升级可更新性 + 多框架接入可替换性（替换/并存）

## 结论摘要

从代码结构与已有“迁移脚手架”来看，项目具备一定“可替换/可适配”基础：

1. OpenClaw 相关能力集中在兼容层与技能加载服务（如 `OpenClawCompatService`、`OpenClawSkillService`）。
2. 底层存储通过 `Repository` 协议与 `SQLiteModelRepository` 抽象，支持局部替换。
3. 已存在 `migration/openclaw` 目录，包含环境映射模板、smoke 脚本、旧数据探测与一键验证脚本。

同时也存在会影响升级效率的耦合点：

1. 技能格式约定（`SKILL.md` + frontmatter + `metadata.openclaw.skillKey`）对 OpenClaw 模式依赖较强。
2. MCP 工具注册默认绑定到特定域名/endpoint，存在实现层硬耦合。
3. CI/回归护栏可见性不足，升级时自动化风险控制偏弱。

因此整体判断：

1. **OpenClaw 小版本迭代（协议不变）**：整体较易升级，主要成本是同步上游并执行 smoke/回归。
2. **OpenClaw 大版本迭代（协议变化）**：可升级，但需改兼容层、共享模型、迁移脚本和测试，不是零成本。
3. **引入其他优秀开源框架（替换/并存）**：架构已具备 adapter 空间，但需制度化边界（契约测试、版本矩阵、插件入口、配置化发现）。

## OpenClaw 更新：好改与卡点

### 好改部分

1. **会话兼容边界清晰**：`OpenClawCompatService` 聚焦会话读写与事件处理，依赖 `shared.models` 与 `Repository` 抽象，改动可局部化。
2. **技能来源双根支持**：`OpenClawSkillService` 支持本仓库 `skills/` 与 sibling `../openclaw/skills/`，上游技能内容更新可低摩擦吸收。
3. **迁移验证脚手架存在**：`migration/openclaw` 的 smoke/verify 降低升级不确定性。

### 容易卡住部分

1. **技能入口与字段强约定**：当前解析链路绑定 `SKILL.md` 与 `skillKey` 提取位置，一旦上游改 manifest 或 namespace，会触发解析层改造。
2. **记忆文件约定潜在耦合**：若上游从文件式持久化转向数据库/结构化协议，需要引入 `MemoryAdapter` 端口化抽象以降低重构成本。
3. **缺少契约回归闭环**：若无样例夹具与契约测试，升级将偏人工回归，试错成本上升。

## 引入其他框架：替换面评估

### 替换执行与编排引擎

已有抽象基础：

1. MCP 上下文与工具注册（如 `MCPContextBlock`、`MCPToolRegistry`）已提供可替换雏形。
2. `mcp_endpoint` 参数显示设计上考虑了可切换性。

当前短板：

1. 默认 registry endpoint 硬编码，切换 MCP server 需改代码，未形成纯配置路径。
2. 工具热更新流程虽有骨架，但广播/审计等能力仍待补齐。

建议做法：

1. 将外部框架视为 `Engine Provider`，统一映射到本系统 `job/session/audit/permission/tool-contract`。
2. 在 adapter 层做输入输出映射，避免深耦合到外部框架内部抽象。

### 替换渠道接入与技能生态

现状：

1. 已有迁移脚手架（env mapping + smoke test）是正确工程方向。
2. 技能体系存在“双轨”：`skills/*/skill.json + main.py` 与 OpenClaw 风格 `SKILL.md`。

建议：

1. 建立统一内部 `Skill Descriptor`（`name/intent/permissions/io_schema/version/source`）。
2. 外部格式先转换为内部 descriptor，再交给 workflow engine 编排，避免多轨长期分叉维护。

## 升级难度分级（成本预估）

### 低成本（1-2 天）

1. OpenClaw skills 内容更新。
2. 轻量 schema 扩展（新增可选字段）。
3. 前提：`SKILL.md` 与 `skillKey` 约定不变。

执行路径：同步 sibling OpenClaw 仓库 + 运行 `migration/openclaw` verify/smoke。

### 中成本（3-7 天）

1. 技能格式变更。
2. session 事件结构调整。
3. 新增鉴权字段。

主要改动：`OpenClawSkillService` 解析逻辑、`shared.models` 兼容结构、契约测试。

### 高成本（>2 周）

1. 上游记忆/会话/工具协议整体重构。
2. 或计划切换到另一套执行语义（编排引擎级迁移）。

主要工作：分层 ports 抽象（记忆/工具/审计/权限/执行器）+ 契约测试体系 + CI 护栏建设。

## 优先改造建议（保持当前方向）

1. **冻结 OpenClaw 兼容契约 v1**
   - 将 `OpenClawSession*`、`OpenClawSkill*` 视为内部稳定 API。
   - 为每个模型准备 5-10 个 golden JSON 夹具。

2. **技能加载解耦为可插拔 provider**
   - 将当前 `OpenClawSkillService` 的“找源/读文件/解析/渲染”拆为：
     - `SkillSourceProvider`
     - `SkillParser`
   - 便于后续支持 `SKILL.md`、`skill.json`、manifest 等多格式并存。

3. **MCP registry 与 endpoint 配置化**
   - 默认 registry 改为从 `.env` / SQLite / 管理面读取。
   - 从“硬编码 endpoint”转为“注册发现”，降低切换成本。

## 待确认范围（用于落地升级 checklist）

1. OpenClaw 升级目标边界：
   - 仅兼容 `skills + session`，还是扩展到 `记忆文件/agent runtime/安全策略`？
2. 外部框架接入层级：
   - 编排引擎（workflow）/ 执行器（sandbox/executor）/ 技能生态（tools/skills）？

---

该评估可直接转化为升级执行清单（文件改动映射、脚本执行顺序、回归集合、验收门槛）。
