# Claude Code CLI 业务落地案例：销售统计表与提成发放表

这份文档把前面的判断落成 repo 内可复用的开发案例，目标不是继续抽象比较“方案 1 vs 方案 2”，而是回答两件事：

1. 这 5 类业务在当前仓库里应该怎么分层承接。
2. 怎样用 Claude Code CLI 开发、维护“销售统计表 / 提成发放表 / 各种 Excel 处理与统计”这类强规则业务。

## 一句话结论

- 当前主线：用 `process driver + 固定程序` 承接 Excel/统计/提成。
- 后续扩展：在稳定执行层之上，逐步补 `skill / agent` 能力层。
- Claude Code CLI 的定位：优先做“开发与维护执行器”，不是“每次运行时都亲自算提成的 runtime agent”。

这和仓库当前主干一致：

- `make agent-run` / AEP 适合受控执行固定开发任务。
- `process driver lane` 已成熟，适合先交付第 4 类业务。
- `openclaw runtime` 更适合后续把通用能力做成 skill，再按需 runtime 化。

## 重型 Claude Code 工作台和 OpenHands 的关系

如果你的目标不是“单次调用 Claude Code CLI”，而是打造一整套重型 Claude Code 工作台，那么它和 OpenHands 最合理的关系不是替代，而是分层协作：

- 重型 Claude Code 工作台
  - 主入口
  - 长期上下文
  - rules / hooks / memory / skills
  - review / QA / release 流程
- OpenHands
  - 受控执行器
  - 隔离 workspace 内的实现手
  - bounded task 的 patch 产出器
- `autonomous-agent-stack`
  - control plane
  - 任务路由、policy merge、validation、promotion

可以把它理解成：

`你 -> Claude Code 工作台 -> AAS control plane -> OpenHands / Claude Code adapters -> validators -> promotion`

对应到当前仓库的已有边界：

- `ARCHITECTURE.md` 明确把 OpenHands 视为 constrained worker，而不是 control plane。
- `docs/agent-execution-protocol.md` 明确规定 agent 只是 driver adapter。
- `README.md` 也已经把 OpenHands 的角色收口到隔离执行，而不是长期工作台。

所以答案是：

- 可以用 OpenHands 开发，而且适合做受控实现任务。
- 但不建议让 OpenHands 承担“重型 Claude Code 工作台”的长期职责。
- 最佳做法是让 Claude Code 工作台做主脑，OpenHands 做执行手。

## 对应到当前仓库，应该挂哪条链

如果是“开发和维护 Excel 处理程序”，优先挂当前已经稳定的这条链：

`task brief -> scripts/agent_run.py -> src/autoresearch/executions/runner.py -> validators -> patch review`

这条链的特点是：

- 任务边界清楚
- workspace 隔离
- 有 patch gate
- 适合让 Claude Code CLI 改代码、补测试、改文档

如果是后续要补“异常解释、模板识别、摘要生成”这类运行期辅助能力，再考虑挂到：

`src/autoresearch/core/services/openclaw_runtime.py`

也就是：

- Excel 核心计算先走 `process driver`
- 非核心解释能力后续再走 `runtime skill`

## 5 类业务的统一承接方式

| 业务方向 | 当前主承接 | 为什么这样落 | 后续怎么长 |
|---|---|---|---|
| 1. 阿里国际站智能客服 | `skill + agent` | 多语言、会话上下文、风险控制、渠道接口多 | 在控制面上叠加知识检索、风控、人审 gate |
| 2. 海外社媒跟进和回复 | `skill + agent` | 渠道多、内容生成多、品牌约束强 | 逐步沉淀成渠道抓取、回复草拟、审批发布能力 |
| 3. 公司官网客服 | `skill + agent` | FAQ、留资、转人工、知识检索天然是能力组合 | 先从 FAQ / lead capture / handoff 三类 skill 起步 |
| 4. Excel / 销售统计 / 提成发放 | `固定程序 + process driver` | 规则强、结果必须可复核、数字必须稳定 | 后续只把“解释、识别、模板推荐”补成 skill，不把计算核心 agent 化 |
| 5. 设计图 / 效果图 | `skill` 为主 | 更像外部模型能力接入，不是固定规则流水线 | 后续可叠加 agent 做多轮修改与渠道适配 |

结论不是二选一，而是分层：

1. 底层执行主干先走方案 2。
2. 通用能力层逐步补方案 1。
3. 第 4 类先拿确定性交付，1/2/3/5 再复用能力层扩出去。

## 为什么 Excel 场景必须先走固定程序

“销售统计表和提成发放表”这类业务不是通用聊天，不是创意写作，而是确定性计算。

它的核心要求通常是：

- 输入文件结构杂，但输出数字必须稳。
- 规则可以复杂，但每条规则都要能回放。
- 异常必须能解释，不能只给一个“模型觉得不对”。
- 导出的工资/提成结果需要人审与审计留痕。

所以第一阶段不应该让 agent 在运行期自由决定“怎么算”，而应该把运行期收口成：

`Excel 输入 -> 规范化 -> 确定性规则计算 -> 异常报告 -> 审核 -> 导出结果`

Claude Code CLI 更适合承担：

- 生成和维护解析器
- 生成和维护规则代码
- 补测试
- 修适配器
- 更新 task brief 和文档

而不是承担：

- 每次上线后直接自由计算佣金
- 对同一份表在不同时间给出不同数字
- 用自然语言临时决定某列是什么意思

## 具体开发案例

### 业务场景

一个外贸团队每月需要处理 4 类 Excel 文件：

1. 平台导出的订单明细表
2. 销售跟单汇总表
3. 退款 / 作废 / 补款调整表
4. 员工与提成规则映射表

最终要产出 4 份结果：

1. 标准化后的订单明细
2. 异常清单
3. 销售统计汇总表
4. 提成发放表

### 第一阶段的目标

先把下面这条链路做成稳定程序：

1. 读取多来源 Excel
2. 识别 sheet 和列头
3. 统一字段命名
4. 做数据校验和去重
5. 按确定性规则计算销售额、回款额、有效订单、退款冲减
6. 按岗位 / 区域 / 渠道 / 阶梯规则计算提成
7. 生成异常报告和最终发放表
8. 把本次运行使用的规则版本、输入文件、输出摘要写入审计记录

### 明确不做

第一阶段不要做这些：

- 不做“让大模型直接读表后给最终数字”
- 不做“自由问答式提成计算”
- 不做多 agent runtime 编排
- 不做自动打款
- 不做无人审核直接出正式发放结果

## 在当前仓库里的推荐落地形态

按这个仓库现有的 `router + service + repository + shared models + tests` 风格，推荐这样起：

```text
src/autoresearch/api/routers/excel_ops.py
src/autoresearch/core/services/excel_ops.py
src/autoresearch/core/services/commission_engine.py
src/autoresearch/core/repositories/excel_jobs.py
src/autoresearch/shared/models.py
tests/test_excel_ops_service.py
tests/test_commission_engine.py
tests/test_excel_ops_router.py
docs/claude-code-excel-business-case.md
```

职责建议：

- `excel_ops.py`
  - 收件、作业创建、文件路径检查、调用 service
- `commission_engine.py`
  - 只做确定性计算，不碰渠道、不碰聊天
- `excel_jobs.py`
  - 用 SQLite 记录 job、输入摘要、规则版本、异常数、输出路径、审批状态
- `shared/models.py`
  - 定义 job request、job result、异常项、统计摘要
- `tests/*`
  - 用固定样例表和 golden 结果做回归

## 推荐的数据与规则分层

Excel 业务里最容易失控的是“把解析、业务规则、导出格式混在一起”。应该拆成三层：

### 1. 输入适配层

负责：

- 识别工作簿和 sheet
- 列名别名映射
- 日期、金额、币种、订单号标准化
- 空值、重复值、非法值预校验

这一层可以接受“格式很多”，但输出必须统一成内部 schema。

### 2. 规则计算层

负责：

- 有效销售额计算
- 退款 / 作废冲减
- 归属销售识别
- 阶梯提成计算
- 特殊奖励 / 扣减

这一层必须是纯确定性逻辑。建议把“规则定义”和“规则执行”拆开：

- 规则定义可版本化
- 规则执行固定由 Python 代码完成

### 3. 导出与审计层

负责：

- 写出统计表和提成表
- 生成异常报告
- 记录规则版本、输入文件 hash、输出文件路径、汇总摘要
- 供人工复核与审批

## SQLite first 的建议

这条线优先遵守当前工作区默认策略：`SQLite first`。

至少记录这些表或等价模型：

- `excel_jobs`
  - job_id、created_at、created_by、status、rule_version、input_digest
- `excel_job_files`
  - job_id、file_role、original_name、stored_path、sha256
- `excel_job_anomalies`
  - job_id、row_ref、field_name、severity、reason_code、detail
- `excel_job_outputs`
  - job_id、output_type、path、sha256、row_count
- `excel_job_approvals`
  - job_id、approval_status、approved_by、approved_at、note

如果后面规则越来越复杂，可以再加：

- `commission_rule_sets`
- `commission_rule_versions`

但第一阶段不必先做成完整规则平台。

## Claude Code CLI 在这条线里的正确用法

### 用在开发期和维护期

适合交给 Claude Code CLI 的工作：

1. 新接一种 Excel 模板
2. 新增一套提成规则
3. 修复列名映射或格式兼容问题
4. 补异常分类
5. 补测试样例和 golden 输出
6. 更新接口文档、runbook、task brief

### 不用在运行期算账

正式跑月度提成时，不建议让 Claude Code CLI 实时读取表格后自由生成结果。

正式运行应该由固定 Python 程序执行，Claude Code CLI 只负责：

- 写程序
- 改程序
- 补测试
- 审查边界

## 推荐的开发维护流程

### 场景 A：新增一种销售表模板

1. 收集 1 到 3 份真实样例
2. 人工标注期望字段映射和期望输出
3. 写 task brief，限定只改 Excel 相关模块
4. 用 Claude Code CLI 实现解析与测试
5. 跑 focused tests
6. 人工打开输出表抽查
7. 再合并

### 场景 B：提成规则变更

1. 明确生效日期、适用团队、计算口径
2. 给一份旧规则结果和一份新规则期望结果
3. 让 Claude Code CLI 修改规则执行层和测试
4. 回放至少两个月历史样本
5. 对比差异清单
6. 人工批准后再上线

### 场景 C：线上发现异常行

1. 保留原始 Excel 和运行产物
2. 在 task brief 中附异常行定位信息
3. 让 Claude Code CLI 先补回归测试，再修代码
4. 用同一批样例重跑，确认只修该类问题，没有误伤别的规则

## 推荐的 Task Brief 写法

Excel 这类任务不要给 Claude 一句“帮我处理这个表”。要把合同写死。

推荐最少包含：

- 目标
- 输入文件角色
- 期望输出文件
- 规则版本或规则变化
- 允许改动的文件路径
- 必跑测试
- 人工复核点

示例：

```md
# Task Brief

## Goal
支持 2026Q2 新版销售汇总表，新增“渠道经理”和“区域经理”两级提成计算。

## Context
旧版仅支持销售个人提成；本次需要兼容新模板列名，并新增两级汇总。

## Likely Files
- `src/autoresearch/core/services/excel_ops.py`
- `src/autoresearch/core/services/commission_engine.py`
- `src/autoresearch/shared/models.py`
- `tests/test_excel_ops_service.py`
- `tests/test_commission_engine.py`

## Constraints
- 不要修改非 Excel 业务模块
- 保持现有输出字段兼容
- 先补回归测试，再实现
- 所有金额计算保留两位小数并固定舍入规则

## Validation
- `python -m pytest tests/test_excel_ops_service.py tests/test_commission_engine.py tests/test_excel_ops_router.py`
- 用 `fixtures/excel/q2_sales_template.xlsx` 重放并核对 golden 输出

## Manual Follow-up
- 人工抽查 10 笔订单、3 个销售、2 个管理岗汇总结果
```

## Claude Code CLI 调用方式

沿用仓库当前推荐模式，把执行边界收在 repo 和 task brief 上：

```bash
cd /path/to/autonomous-agent-stack
claude -p "请先阅读 CLAUDE.md、README.md、docs/task-brief-guide.md、docs/claude-code-excel-business-case.md，再完成 docs/briefs/excel-q2-commission.md 里的要求。最后只输出 files changed / verification / manual follow-up。"
```

如果是通过当前仓库外环来发起，则仍建议走：

`task brief -> AEP job -> isolated workspace -> validators -> patch review`

不要把“自然语言任务”直接变成生产期算账逻辑。

## 验证策略

Excel / 提成场景至少要有 4 层验证：

1. 单元测试
   - 列映射
   - 金额计算
   - 阶梯提成
   - 异常分类
2. 样例回放
   - 固定输入 Excel
   - 固定 golden 输出
3. 差异对比
   - 新旧规则的金额差异报告
4. 人工抽查
   - 重点抽查高金额订单、退款订单、跨月订单、特殊奖励

## 人工审核点

下面这些点不要自动跳过：

- 提成规则版本切换
- 异常行强行忽略
- 最终发放表出正式版
- 历史月份重算覆盖
- 任何会影响员工收入的规则改动

## 第二阶段怎么接到 skill / agent 层

当第一阶段稳定后，可以把“非核心计算能力”逐步 skill 化：

- `excel_template_detector`
  - 判断这份表更像哪个模板
- `excel_anomaly_explainer`
  - 用自然语言解释某行为什么被判异常
- `commission_diff_explainer`
  - 解释新旧规则下某个销售差异的来源
- `payout_summary_writer`
  - 把本次统计结果整理成给业务负责人看的摘要

但核心边界不变：

- 最终数字仍由固定程序计算
- skill 只做解释、推荐、辅助录入
- agent 不拥有最终发放结果的写死权

## 交付节奏建议

### Phase 1

- 先做单一模板
- 单团队
- 单币种
- 单月处理
- 人工审核后导出

### Phase 2

- 扩多模板
- 扩多团队
- 增加退款/补款/跨月修正
- 增加 job 审计和历史回放

### Phase 3

- 增加 skill 化解释层
- 增加模板识别与异常解释
- 增加管理摘要自动生成

## 最终判断

对“销售统计表和提成发放表等各种 Excel 表的处理和统计”这类需求，当前最稳的路线是：

1. 用 Claude Code CLI 开发和维护固定 Python 程序。
2. 用当前仓库的 AEP / process driver 主干来受控执行开发任务。
3. 用 SQLite 和 focused tests 保证可回放、可审计、可追责。
4. 等第 4 类场景跑稳，再把解释类、推荐类、渠道类能力抽成 skill / agent。

也就是：

`方案 2 打底，方案 1 增长。`
