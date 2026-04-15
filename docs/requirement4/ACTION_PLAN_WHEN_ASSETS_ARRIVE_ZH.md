# 业务资产到达后的 2 天压缩试运行行动方案

## 当前定位

这不是“2 天做完整个 requirement #4 生产版”的计划。

这是一个 **单机版 requirement-4 pilot** 的压缩行动方案，目标是：

- 单团队
- 单模板
- 单规则集
- 单试点周期
- 人工审核
- Telegram 手动触发优先
- 定时任务后置

## 重要说明

> 本文档中的 JSON、Markdown、命令、目录示例只用于说明格式、流程和落点，不代表真实业务规则。
>
> 不要从示例中反推真实提成规则。真实规则只能来自业务资产、歧义决策和 golden 输出。
>
> 本文档是 **工程可执行 / 试运行可执行** 方案，不是“已生产就绪”声明。

---

## 1. 目标重定义

本次要落地的目标不是“2 天做完整需求 4”，而是：

**2 天做出一个可试运行的 requirement-4 pilot 闭环：**

- 分支 A：完成业务资产验收、确定性规则实现、CLI 封装
- 分支 B：完成单机版 AAS 安装验证、Telegram 接通、AAS 调用 CLI
- 最终：通过 Telegram 手动触发一次真实试运行

这次不追求：

- 多模板兼容
- 多规则版本并存
- 自动审批
- 正式生产调度
- 大规模并发
- 完整 UI

结论先写死：

- **2 天压缩版 = pilot ready**
- **不是 production complete**
- **定时任务不在 2 天关键路径内**

---

## 2. 前置条件

只有在以下条件全部满足时，才承诺 2 天压缩排期：

- [ ] 4 个业务资产已经齐全且质量合格
- [ ] 本次只支持 1 套输入/输出 Excel 模板契约
- [ ] 本次只支持 1 套提成规则
- [ ] 本次只支持 1 个试点业务周期
- [ ] 业务方当天有人可快速答疑，不跨天等待
- [ ] 单机版 AAS baseline 已可运行

### 4 个必需资产

仍然是这 4 类，路径不变：

| 资产 | 位置 | 本次用途 |
|------|------|----------|
| Excel 输入/输出契约 | `tests/fixtures/requirement4_contracts/excel_contracts.json` | 定义文件角色、sheet、字段映射、输出契约 |
| 7 类业务歧义清单 | `tests/fixtures/requirement4_contracts/ambiguity_checklist.md` | 冻结边界情况处理规则 |
| 真实样本 | `tests/fixtures/requirement4_samples/` | 驱动 deterministic 开发和本地验证 |
| Golden 输出 + 元数据 | `tests/fixtures/requirement4_golden/` | 驱动对比验证和人工审核 |

### 单机版 AAS 安装与验证最佳实践

推荐直接走仓库现有基线，而不是自己拼命令：

- `README.md`
- `docs/QUICK_START.md`
- `docs/runbooks/worker-schedules.md`（定时任务 runbook）

最小启动路径：

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack
make setup
make doctor
AUTORESEARCH_MODE=minimal make start

curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/docs
make smoke-local
```

如果这条基线不通，2 天试运行计划不成立。

---

## 3. 范围收缩

### 2 天内只做

- 把业务资产放进 fixtures 目录
- 检查资产是否足够支撑 requirement #4 的 pilot
- 生成 contract summary / asset readiness review
- 用 Claude Code CLI + ECC 在现有 scaffold 上实现确定性佣金程序
- 把程序封装成 CLI
- 安装并验证单机版 AAS
- 接通 Telegram 并完成手动触发调试
- 让 AAS 调用 CLI 跑一次真实试运行
- 输出可供人工审核的结果文件和审计摘要

### 2 天内明确不做

- 多模板支持
- 多版本规则引擎
- 自动审批
- 正式生产调度编排
- 大规模并发
- 精致 UI
- 可复用平台化抽象

---

## 4. 分支 A：开发维护链

分支 A 负责把 requirement #4 的业务逻辑真正做出来，但仍然保持：

- 运行期不用 LLM 算钱
- 缺契约就安全阻断
- 所有输出可审计、可回放、可人工复核

### A1. 资产落盘 + 完整性检查

先把业务资产放到固定目录：

```bash
tests/fixtures/requirement4_contracts/
├── excel_contracts.json
└── ambiguity_checklist.md

tests/fixtures/requirement4_samples/
└── *.xlsx

tests/fixtures/requirement4_golden/
├── *.xlsx
└── golden_metadata.json
```

然后先做 readiness review，而不是立刻写代码：

```bash
ls -la tests/fixtures/requirement4_contracts/
ls -la tests/fixtures/requirement4_samples/
ls -la tests/fixtures/requirement4_golden/
make validate-req4
```

产出物：

- `docs/requirement4/ASSET_READINESS_REVIEW.md`
- `docs/requirement4/CONTRACT_SUMMARY.md`

### A2. 用 Claude Code CLI + ECC 实现 deterministic 程序

实现时必须以这份深研报告为主参考：

- `docs/aas-claude-ecc-excel-best-practice-report.md`

执行原则：

- 只把 Claude Code CLI + ECC 放在“开发维护链”
- 正式算账链仍然是固定程序
- 优先复用现有 requirement-4 scaffold

建议优先检查并复用这些落点：

- `src/autoresearch/core/services/commission_engine.py`
- `src/autoresearch/core/services/excel_ops.py`
- `src/autoresearch/api/routers/excel_ops.py`
- `src/autoresearch/core/repositories/excel_jobs.py`
- `tests/test_excel_ops_service.py`
- `tests/test_e2e_pipeline_verification.py`

本阶段必须补齐：

- contract loading
- data normalization
- validation
- deterministic commission calculation
- export
- audit metadata
- fixture vs golden focused tests

### A3. 封装为 CLI，供 AAS 调度

不要把 requirement #4 逻辑只留在 service 内部。

必须把它封装成可由 AAS 调用的 CLI，至少支持：

- 输入目录或文件参数
- 契约目录参数
- golden 目录参数（可选）
- 输出目录参数
- 审计输出参数
- `dry-run`
- `validate-only`

CLI 层要求：

- 明确退出码
- 结构化 JSON 摘要
- 可供人工审核的结果文件
- 对缺失契约 / 缺失样本 / golden 校验失败返回清晰错误

本阶段结束标准：

- 本地命令能独立跑通
- 至少 1 组真实样本能完成 deterministic 本地运行
- 至少 1 次 golden 对比可执行

---

## 5. 分支 B：单机运行链

分支 B 负责把“已经做好的 CLI”接到单机版 AAS 和 Telegram 上。

### B1. 安装并验证单机版 AAS

推荐走现有单机基线：

```bash
make setup
make doctor
AUTORESEARCH_MODE=minimal make start

curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/api/v1/excel-ops/status/requirement4
make smoke-local
```

如果需要 worker 执行链，再启动现有 Mac worker：

```bash
./scripts/start-mac-worker.sh
```

### B2. 接通 Telegram，调通手动触发

本次只做 Telegram 手动触发路径，不做正式定时任务投产。

目标是打通：

`Telegram -> AAS -> requirement-4 CLI -> 结果文件 + 审计摘要`

验收重点：

- Telegram 消息可以触发 job
- AAS 能正常创建 job / enqueue run
- 返回结果能回到人工审核路径

### B3. 用 AAS 试运行分支 A 的 CLI

这一步只看最小闭环，不追求架构扩张：

- AAS 能调用 CLI
- CLI 能输出结果文件
- 结果与审计摘要可查看
- 失败时能 blocked / safe-fail

---

## 6. 两天排期

## Day 1

- [ ] 验收 4 个业务资产
- [ ] 运行资产完整性检查
- [ ] 产出 `ASSET_READINESS_REVIEW.md`
- [ ] 产出 `CONTRACT_SUMMARY.md`
- [ ] 完成 deterministic commission CLI MVP
- [ ] 完成 fixture / golden 基础验证

Day 1 结束时必须至少拿到：

- 资产是否足够的明确结论
- MVP CLI 的调用方式
- 至少 1 组样本跑通或明确 blocked 原因

## Day 2

- [ ] 验证单机版 AAS baseline
- [ ] 接入 Telegram
- [ ] 接入 AAS -> CLI 调用链
- [ ] 完成一次 Telegram 手动触发试运行
- [ ] 输出试运行结果、审计说明、剩余 gap 清单

Day 2 结束时必须拿到：

- 手动触发闭环证据
- 人工审核材料
- 明确写明“未生产就绪”

---

## 7. 验收标准

2 天压缩 pilot 的验收标准应是：

- [ ] CLI 能在本地独立跑通
- [ ] 至少 1 组真实样本完成 deterministic local run
- [ ] 至少 1 次 golden 对比已执行
- [ ] AAS 能成功调用 CLI
- [ ] Telegram 能手动触发一次试运行
- [ ] 输出结果可供人工审核
- [ ] 文档和结果中明确标注 **NOT production complete**

明确不是本次验收标准的内容：

- 自动审批
- 生产级定时任务
- 多模板兼容
- 多规则集并行
- 高并发压测

---

## 8. 后续项：定时任务

### 当前是否支持单机版定时任务

**支持，但不应放进本次 2 天关键路径。**

当前单机版 AAS 已有最小定时任务能力：

- `once`
- `interval`
- APScheduler-backed 时间触发
- SQLite 持久化
- `/api/v1/worker-schedules`
- 可选后台 schedule daemon

相关 runbook：

- `docs/runbooks/worker-schedules.md`

打开方式：

```bash
export AUTORESEARCH_ENABLE_WORKER_SCHEDULE_DAEMON=1
export AUTORESEARCH_WORKER_SCHEDULE_POLL_SECONDS=30
AUTORESEARCH_MODE=minimal make start
```

### 为什么仍然不放进 2 天主范围

因为这次的主目标是先证明：

`Telegram 手动触发 -> AAS -> CLI -> 输出 + 审计 -> 人工审核`

只有在以下条件满足后，才应该给 requirement-4 pilot 加 schedule：

- 手动触发路径稳定通过
- 输出审核已被业务接受
- 业务确认 pilot 行为正确

换句话说：

- **现在已经可以支持单机 schedule**
- **但 requirement #4 不应一开始就靠 schedule 验收**

---

## 9. Claude Code CLI Prompt 模板

以下 prompt 建议直接用于 `feat/single-machine-aas-ready-for-req4` 分支。

### Prompt 1：检查 4 个业务资产是否足够

```text
请先不要实现业务逻辑。

阅读以下文件与目录：
- tests/fixtures/requirement4_contracts/excel_contracts.json
- tests/fixtures/requirement4_contracts/ambiguity_checklist.md
- tests/fixtures/requirement4_samples/
- tests/fixtures/requirement4_golden/

任务：
1. 判断这 4 类业务资产是否已经足够支持 requirement #4 的 2 天试运行版开发。
2. 如果不够，按“缺失项 / 影响 / 必须补充什么”列出清单。
3. 如果足够，输出：
   - 输入文件角色清单
   - 输出文件清单
   - 关键字段映射
   - 关键业务歧义决策
   - golden 校验范围
4. 生成：
   docs/requirement4/ASSET_READINESS_REVIEW.md

要求：
- 不猜业务规则
- 不发明缺失字段
- 缺什么就明确写什么
- 输出结论必须是：
  - ready_for_pilot
  或
  - blocked_missing_assets
```

### Prompt 2：用 Claude Code CLI + ECC 实现 requirement #4

```text
请基于以下资料实现 requirement #4 的 2 天试运行版，仅做确定性逻辑：

必读：
- docs/aas-claude-ecc-excel-best-practice-report.md
- docs/requirement4/ASSET_READINESS_REVIEW.md
- tests/fixtures/requirement4_contracts/excel_contracts.json
- tests/fixtures/requirement4_contracts/ambiguity_checklist.md
- tests/fixtures/requirement4_samples/
- tests/fixtures/requirement4_golden/

目标：
实现一个单模板、单规则集、单周期的 deterministic commission pipeline。

要求：
1. 不使用 LLM 参与运行期金额计算
2. 缺契约时必须安全阻断
3. 使用 openpyxl / 现有 repo 方式解析 Excel
4. 在现有 requirement-4 scaffold 上实现：
   - contract loading
   - data normalization
   - validation
   - commission calculation
   - export
   - audit metadata
5. 增加 fixture vs golden 测试
6. 输出变更文件、测试结果、剩余风险

范围限制：
- 不做多模板支持
- 不做多版本规则引擎
- 不做调度自动化
- 不做生产化 UI
```

### Prompt 3：把程序封装成 CLI 供 AAS 调度

```text
请把 requirement #4 的实现封装成一个可由 AAS 调用的 CLI。

目标：
提供一个稳定、可审计、适合单机版 AAS 调度的命令行入口。

CLI 至少支持：
- 输入目录或文件参数
- 契约目录参数
- golden 目录参数（可选）
- 输出目录参数
- 审计输出参数
- dry-run / validate-only 模式

要求：
1. 返回明确退出码
2. 生成结构化 JSON 摘要
3. 生成可供人工审核的结果文件
4. 对缺失契约/缺失样本/校验失败给出明确错误
5. 补充 README 或 docs 中的 CLI 用法说明
6. 增加最小 CLI smoke test

输出：
- CLI 文件位置
- 示例命令
- AAS 后续如何调用
```

### Prompt 4：接入 AAS + Telegram 做手动触发试运行

```text
请在不扩大范围的前提下，将 requirement #4 CLI 接入单机版 AAS 的试运行路径。

目标：
实现 Telegram 手动触发 -> AAS 创建 job -> 调用 requirement #4 CLI -> 输出结果与审计摘要。

要求：
1. 优先复用现有 single-machine AAS baseline
2. 只做手动触发路径
3. 不做正式定时任务
4. 输出结果必须可人工审核
5. 保留 blocked / safe-fail 行为
6. 增加最小端到端 smoke test

验收：
- 本机 AAS 可启动
- Telegram 可触发一次试运行
- AAS 能调用 CLI
- 结果文件和审计摘要可查看
- 文档说明清楚后续如何再加定时任务
```

---

## 10. 风险与残余问题

即使工期压到 2 天，仍然存在这些风险：

- 业务资产可能“看起来齐全，但字段定义不够硬”
- 同一个 Excel 字段可能仍有业务歧义
- golden 输出可能本身不稳定或不够覆盖边界情况
- Telegram 打通不代表 requirement-4 结果已经可发放
- 单机 schedule 已支持，也不代表 requirement-4 适合立即自动跑

所以最后一句必须保留：

**2 天可以做成“试运行版闭环”，不能承诺“生产版闭环”。**

---

## 参考文档

- `docs/aas-claude-ecc-excel-best-practice-report.md`
- `README.md`
- `docs/QUICK_START.md`
- `docs/runbooks/worker-schedules.md`
- `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md`
- `docs/requirement4/ENGINEERING_PREP_PLAN.md`
- `docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md`

---

## 📝 文档同步说明

**重要**：本分支包含中英文双语文档。如需修改命令、路径、配置等内容，请同时更新英文和中文版本，以保持文档一致性：

- `PR_SUMMARY.md` ↔ `PR_SUMMARY_ZH.md`
- `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES.md` ↔ `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md`
- `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md`（中文独有；若后续补英文版，需同步口径）
