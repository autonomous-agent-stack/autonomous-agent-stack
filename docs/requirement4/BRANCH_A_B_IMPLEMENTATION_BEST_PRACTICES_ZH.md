# requirement-4 两分支实现最佳实践

## 1. 文档定位

这份文档是 requirement-4 的实现实践指南，用来指导工程同事如何真正落地分支 A / 分支 B。

- 它服务于工程落地，不定义真实业务规则
- 它与 `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md` 保持同一口径
- 它描述的是 **2 天压缩 pilot** 的最佳实践，不是 production complete 指南

如果与其他 requirement-4 文档发生冲突，以这两份文档为准：

- `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md`
- `docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md`

如果你是第一次进入 requirement-4，建议先看：

- `docs/requirement4/README_ZH.md`
- `docs/requirement4/CONFIDENTIAL_ASSET_STORAGE_DECISION_ZH.md`

---

## 2. 分支 A 最佳实践：开发维护链

分支 A 的目标不是“先把功能写出来再补契约”，而是先把资产和边界钉死，再实现 deterministic 程序。

### 2.1 业务资产落盘与 readiness review

业务资产必须先落到固定目录：

```text
tests/fixtures/requirement4_contracts/
tests/fixtures/requirement4_samples/
tests/fixtures/requirement4_golden/
```

先做 readiness review，再开始实现：

- 检查 4 类资产是否都存在
- 检查样本是否真能代表试点周期
- 检查 golden 是否可人工解释
- 检查契约是否足以形成硬字段映射

最小产出物：

- `docs/requirement4/ASSET_READINESS_REVIEW.md`
- `docs/requirement4/CONTRACT_SUMMARY.md`

### 2.2 如何判断资产是否足够

判断标准不是“文件数量够了”，而是下面 4 点同时成立：

- 输入文件角色能说清楚
- 输出文件清单能说清楚
- 关键字段映射能说清楚
- 关键歧义决策能说清楚

出现以下任一情况，都应判定为 `blocked_missing_assets`：

- 只有样本，没有字段契约
- 只有 golden，没有可解释的来源关系
- 提成规则存在口头约定，但未冻结成文档
- 同一字段在不同样本中含义不一致

### 2.3 如何使用深研报告

分支 A 实现时，应把以下文档作为方法论主参考：

- `docs/aas-claude-ecc-excel-best-practice-report.md`

正确用法是：

- 用它指导“开发维护链”和“生产算账链”的分离
- 用它指导 contract-first / deterministic / auditable 的实现方式
- 不要把它当成真实业务规则来源

### 2.4 如何用 Claude Code CLI + ECC 做 deterministic 实现

推荐顺序：

1. 先运行资产 sufficiency prompt，确认是否 `ready_for_pilot`
2. 再运行 deterministic implementation prompt
3. 只在现有 requirement-4 scaffold 上补 contract loading / normalization / validation / calculation / export / audit metadata
4. 每完成一个闭环就跑 focused tests

执行时必须守住这条红线：

- money path 不依赖 LLM 运行期推理
- LLM 只用于开发维护，不用于运行期金额计算

### 2.5 如何把程序封装成 CLI

分支 A 不应只交付 service 方法，必须交付一个可由 AAS 调用的 CLI。

CLI 至少要满足：

- 支持输入目录或文件参数
- 支持契约目录参数
- 支持输出目录参数
- 支持审计输出参数
- 支持 `dry-run`
- 支持 `validate-only`
- 返回明确退出码
- 生成结构化 JSON 摘要

### 2.6 如何做 fixture / golden 验证

最小验证要求：

- 至少 1 组真实样本能完成 deterministic 本地运行
- 至少 1 次 fixture vs golden 对比已执行
- 校验结果能解释差异来源，而不是只给 pass/fail

golden 设计不稳定时，不要硬改程序凑 golden。先判断是：

- 资产本身不稳定
- 契约不完整
- 规则解释尚未冻结

### 2.7 如何保证 money path 不依赖 LLM

以下能力必须落在固定程序中：

- 金额口径计算
- 规则选择
- 舍入与汇总
- 异常阻断
- 审计元数据生成

以下事情可以由 Claude Code CLI + ECC 辅助：

- 阅读契约
- 生成实现草稿
- 辅助补测试
- 生成文档和检查清单

### 2.8 如何做 safe-fail / blocked 状态

遇到以下情况不能静默继续：

- 契约缺失
- 样本缺失
- golden 不可用
- 关键字段无法映射
- 歧义决策未冻结

正确行为是：

- 明确返回 `blocked`
- 输出缺失项和影响
- 保留审计摘要，供人工复核

### 2.9 小白推荐执行顺序

如果你是第一次做 requirement-4，不要自己组织步骤，直接按这个顺序走：

1. 先确认本地基线能跑：`make setup && make doctor`
2. 把 4 类业务资产放进 `tests/fixtures/requirement4_*`
3. 把 Prompt A1 贴给 Claude Code CLI，先做资产 readiness review
4. 如果结论不是 `ready_for_pilot`，先停，不写代码
5. 如果结论是 `ready_for_pilot`，再贴 Prompt A2，实现 deterministic 主链
6. 实现结束后，先在本地跑 fixture / golden focused tests
7. 再贴 Prompt A3，把结果封装成 CLI
8. CLI 本地独立跑通后，再把交付物交给分支 B

最重要的纪律只有一条：

- **先确认资产够不够，再实现；先本地跑通 CLI，再接 AAS**

### 2.10 分支 A 可直接复制的 Prompt 套餐

下面 3 段是给 Claude Code CLI 的直接可用版。小白不要自己改写意图，直接复制。

#### Prompt A1：先检查 4 个业务资产是否足够

用途：

- 判断 requirement-4 是否已经具备 2 天试运行开发条件
- 生成 readiness review，而不是直接开始写代码

直接复制：

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

你期待看到的正确结果：

- 明确结论是 `ready_for_pilot` 或 `blocked_missing_assets`
- 不是“差不多可以”
- 不是“我猜应该够了”

#### Prompt A2：用 Claude Code CLI + ECC 实现 deterministic requirement #4

用途：

- 在现有 scaffold 上做确定性实现
- 保证 money path 不依赖 LLM 运行期推理

直接复制：

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

你实现后必须自己检查：

- 至少 1 组真实样本能本地跑通
- 至少 1 次 golden 对比已执行
- 缺契约时不是 silent fail，而是 blocked

#### Prompt A3：把程序封装成 CLI 供 AAS 调度

用途：

- 让分支 A 的实现变成分支 B 可接入的最小交付物

直接复制：

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

你交给分支 B 之前必须确认：

- CLI 脱离 AAS 也能独立执行
- 结果文件能给人看
- JSON 摘要能给程序读
- 非 0 退出码能明确表达失败或 blocked

### 2.11 分支 A 执行时的最小命令清单

如果你不知道什么时候该跑什么命令，就用下面这组：

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack

make setup
make doctor
make validate-req4

ls -la tests/fixtures/requirement4_contracts/
ls -la tests/fixtures/requirement4_samples/
ls -la tests/fixtures/requirement4_golden/

PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v
PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v
```

命令的含义：

- `make validate-req4`：先看 requirement-4 scaffold 是否还在
- `ls -la ...`：确认资产真的落盘，不要假设文件已经放好
- `pytest ...`：先跑 focused tests，不要一上来跑全仓库测试

---

## 3. 分支 B 最佳实践：单机运行链

分支 B 的目标不是“把一切自动化”，而是让单机版 AAS 能稳定调起分支 A 交付的 CLI。

### 3.1 单机版 AAS 安装与验证顺序

推荐顺序固定为：

1. `make setup`
2. `make doctor`
3. `AUTORESEARCH_MODE=minimal make start`
4. 检查 `/health`
5. 检查 `/docs`
6. 跑 `make smoke-local`

先验证控制面基线，再接 Telegram，再接 requirement-4 CLI。

### 3.2 Windows 主链与非 Windows 的边界说明

当前仓库已经支持原生 Windows 的最小主链：

- `make setup`
- `make doctor`
- `make start`
- `setup.cmd`
- `doctor.cmd`
- `start.cmd`

但这只表示**原生 Windows 最小主链已可用**。不要把它扩大理解为：

- 所有 Bash target 都已 Windows 可用
- 所有 worker / 平台脚本都已 Windows 可用
- 仓库已经完成全量 Windows parity

### 3.3 Telegram 接入与调试顺序

Telegram 调试顺序应是：

1. 先确认 AAS API 已稳定启动
2. 再确认 Telegram token / webhook 或 polling 配置正确
3. 再验证 Telegram 能触发 job 创建
4. 最后再验证 job 是否真正调起 requirement-4 CLI

不要把“Telegram 收到消息”误判成“requirement-4 已可运行”。

### 3.4 如何让 AAS 调用 CLI

接入前，B 必须先拿到 A 的最小交付物：

- 可本地独立执行的 CLI
- 可人工审阅的输出样例
- 明确的退出码约定
- 结构化 JSON 摘要

接入时重点验证：

- AAS 是否真的调用了 CLI，而不是只创建了 job
- CLI 失败时是否能把 blocked / error 原样带回
- 输出目录和审计目录是否可查看

### 3.5 为什么先手动触发，再考虑 schedule

因为手动触发更容易定位问题来源：

- 是 Telegram 问题
- 是 AAS job 问题
- 是 CLI 参数问题
- 还是 deterministic 规则问题

如果 schedule 过早介入，会把“时间触发问题”和“业务计算问题”混在一起。

### 3.6 schedule 的正确启用顺序

当前 main 仓库已经有 requirement-4 可复用的单机 schedule 主链，但正确顺序仍然是：

1. 先完成 Telegram 手动触发闭环
2. 先通过人工审核
3. 再按需启用 schedule
4. 再做 schedule smoke test 和运行观察

在 schedule 真正落地前，不要把它写进 pilot 验收标准。

### 3.7 输出和审计材料如何人工复核

人工复核至少要能拿到：

- 结果文件
- 审计摘要
- 输入样本标识
- 契约版本标识
- golden 对比结果
- blocked / gap 清单

如果 AAS 调起了 CLI，但人工看不懂输出，这条链仍然不算可用。

---

## 4. 两分支之间的交接点

### 4.1 A 交给 B 的最小交付物

- 一个能独立运行的 CLI
- 一组最小真实样本
- 一次可解释的 golden 对比结果
- CLI 用法说明
- 错误码与 blocked 行为说明

### 4.2 CLI 至少要满足什么接口

- 输入路径参数
- 契约路径参数
- 输出路径参数
- 审计路径参数
- `dry-run`
- `validate-only`
- JSON 摘要输出
- 非 0 退出码表示失败或 blocked

### 4.3 B 在接入前必须验证什么

- CLI 脱离 AAS 也能本地跑通
- 输出可人工复核
- 至少 1 次 golden 对比已执行
- 契约缺失时会 blocked，而不是静默继续

### 4.4 A / B 的责任边界

属于 A 的责任：

- 契约装载
- 数据标准化
- deterministic 计算
- export
- audit metadata
- fixture / golden 验证

属于 B 的责任：

- 单机 AAS 启动
- Telegram 调试
- AAS 到 CLI 的参数编排
- 手动触发闭环
- 输出回传到人工审核路径

---

## 5. 常见失败模式

### 5.1 资产看似齐全，但契约不硬

症状：

- 文件都在，但字段含义说不清
- 同名字段在不同样本里语义不一致

处理：

- 阻断实现
- 回到 readiness review

### 5.2 golden 不稳定

症状：

- 同一组样本多次比对结果不一致
- golden 无法解释来源

处理：

- 先修正资产和契约
- 不要硬改程序凑结果

### 5.3 Telegram 通了，但 CLI 不可审计

症状：

- 能触发
- 但没有结构化结果和审计摘要

处理：

- 回到 A 补 CLI 审计输出

### 5.4 AAS 能调用，但结果不可人工复核

症状：

- job 成功
- 但输出文件无法给业务审核

处理：

- 补输出说明、审计摘要、gap 清单

### 5.5 schedule 过早介入导致问题难定位

症状：

- 失败时分不清是定时触发问题还是计算问题

处理：

- 回退到手动触发闭环

---

## 6. 推荐执行顺序

推荐最小顺序固定为：

1. 先 A，后 B
2. 先 readiness review，后 deterministic 实现
3. 先手动触发，后 schedule
4. 先 pilot，后 productionization

---

## 7. 检查清单

### 7.1 A 分支完成检查

- [ ] 4 类业务资产已落盘
- [ ] `ASSET_READINESS_REVIEW.md` 已产出
- [ ] `CONTRACT_SUMMARY.md` 已产出
- [ ] deterministic CLI 已可独立执行
- [ ] 至少 1 组真实样本已跑通
- [ ] 至少 1 次 golden 对比已执行
- [ ] 缺契约时能 blocked / safe-fail

### 7.2 B 分支完成检查

- [ ] 单机版 AAS baseline 已验证
- [ ] Telegram 已接通
- [ ] AAS 能调用 requirement-4 CLI
- [ ] CLI 结果与审计摘要可查看
- [ ] 失败时可定位到 Telegram / AAS / CLI 中的具体一层

### 7.3 联调完成检查

- [ ] Telegram 手动触发试运行成功
- [ ] 输出结果可人工审核
- [ ] gap 清单已记录
- [ ] 文档明确标注 NOT production complete
- [ ] schedule 仍作为后续项，而非本次主验收项
