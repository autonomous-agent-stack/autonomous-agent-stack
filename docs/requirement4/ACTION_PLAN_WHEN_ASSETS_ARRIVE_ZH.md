# 业务资产到达后的行动指南

## 当前状态

✅ **工程脚手架已完成** - 44 个测试全部通过
❌ **等待业务提供 4 个必需资产**

---

> 📌 **重要说明**
>
> 本文档中的所有 JSON、Markdown 示例均用于**说明格式和结构**，不代表真实的业务规则。业务方提供的资产应基于实际业务需求填写。
>
> 示例中的字段名称、数值、决策内容等仅供参考，请勿直接套用。

## 业务方需要提供的 4 个资产

### 1. Excel 输入/输出契约 (`excel_contracts.json`)

**用途**：定义 Excel 文件的结构和映射规则

**应包含**：

> ⚠️ **注意**：以下 JSON 结构仅为**示例格式**，用于说明应包含哪些字段。实际内容应根据真实业务规则填写。

```json
{
  "input_files": [
    {
      "role": "source_data",
      "filename_pattern": "*.xlsx",
      "required_sheets": ["销售数据", "代理信息"],
      "column_mappings": {
        "代理ID": "agent_id",
        "销售额": "sales_amount",
        "产品类别": "product_category"
      }
    },
    {
      "role": "rate_table",
      "filename_pattern": "费率表.xlsx",
      "required_sheets": ["费率"],
      "column_mappings": {
        "级别": "tier",
        "佣金率": "commission_rate"
      }
    }
  ],
  "output_file": {
    "filename": "佣金计算结果.xlsx",
    "required_sheets": ["佣金明细", "汇总"],
    "column_definitions": {
      "代理ID": "字符串",
      "应付佣金": "数值，保留2位小数",
      "计算依据": "字符串"
    }
  }
}
```

**业务方需要回答**：
- 有哪几个输入 Excel 文件？分别叫什么？
- 每个 Excel 文件有哪些工作表（sheet）？
- 每个工作表有哪些关键列？
- 输出结果需要包含哪些列？

---

### 2. 7 类业务歧义检查清单 (`ambiguity_checklist.md`)

**用途**：预先决策边界情况的处理规则

**应包含的 7 个类别**：

> ⚠️ **注意**：以下决策内容仅为**示例**，用于说明应考虑哪些边界情况。实际决策应由业务方根据真实业务规则确定。

#### 类别 1：数据完整性
```
问题：如果某些字段缺失或为空怎么办？
决策（示例）：
- 代理ID缺失：跳过该条记录
- 销售额为空：视为 0
- 产品类别缺失：使用"未分类"
```

#### 类别 2：数据验证
```
问题：如何发现和处理异常数据？
决策（示例）：
- 销售额为负数：记录警告，计入"异常金额"
- 代理ID不存在于代理表：报错并终止
- 费率超过上限：使用上限值，记录警告
```

#### 类别 3：计算规则
```
问题：复杂的计算场景如何处理？
决策（示例）：
- 多个产品的佣金是否累加：是
- 是否有封顶：有，最高不超过销售额的 20%
- 退货如何处理：从当期销售额中扣除
```

#### 类别 4：代理映射
```
问题：代理关系的边界情况？
决策（示例）：
- 一个销售有多个代理：按贡献比例分配
- 代理层级：只计算直接上级的佣金
- 代理离职：计算至离职日期
```

#### 类别 5：时间段处理
```
问题：时间相关的计算规则？
决策（示例）：
- 计算周期：按自然月
- 截止时间：每月最后一天 23:59:59
- 跨期订单：计入下单日期所在月
```

#### 类别 6：费率档位
```
问题：费率如何应用？
决策（示例）：
- 档位划分：
  - 0-10万：1%
  - 10-50万：2%
  - 50万以上：3%
- 累进 vs 超额：超额累进
- 特殊产品：使用特定费率表
```

#### 类别 7：调整项
```
问题：哪些情况需要人工调整？
决策（示例）：
- 新产品试销期：费率翻倍（前3个月）
- 大客户折扣：从佣金中扣除
- 数据更正：支持人工调整并记录原因
```

---

### 3. 真实 Excel 样本文件 (`tests/fixtures/requirement4_samples/`)

**用途**：用于开发和测试的真实数据

**应提供**：
- 1-3 个真实的 Excel 输入文件
- 文件应包含真实或逼真的数据
- 覆盖主要的业务场景

**示例**：
```
tests/fixtures/requirement4_samples/
├── 销售数据_202601.xlsx        # 实际输入文件
├── 代理列表.xlsx               # 实际输入文件
└── 费率表.xlsx                 # 实际输入文件
```

**业务方需要确保**：
- 文件格式与 `excel_contracts.json` 中定义的一致
- 包含正常场景和边界情况的数据
- 数据已脱敏（如需要）

---

### 4. 金标准输出 + 审批闭环 (`tests/fixtures/requirement4_golden/`)

**用途**：验证计算正确性的预期结果

**应提供**：

#### 4.1 金标准 Excel 输出
```
tests/fixtures/requirement4_golden/
└── 佣金计算结果_预期.xlsx       # 手工计算或系统导出的正确结果
```

**应包含**：
- 与样本输入对应的正确输出
- 覆盖所有测试场景的预期结果
- 明确标注每条结果的计算依据

#### 4.2 金标准元数据 (`golden_metadata.json`)

> ⚠️ **注意**：以下 JSON 结构仅为**示例格式**。实际容差阈值、审批人员和测试用例应由业务方根据真实需求确定。

```json
{
  "tolerances": {
    "数值比较精度": 0.01,
    "允许的舍入误差": "四舍五入到2位小数"
  },
  "audit_loop": {
    "approval_required": true,
    "approvers": ["财务经理", "业务总监"],
    "approval_criteria": {
      "单笔差异阈值": 100,
      "总差异阈值": 1000,
      "警告阈值": 500
    }
  },
  "test_cases": [
    {
      "name": "正常销售场景",
      "input_file": "销售数据_202601.xlsx",
      "expected_output": "佣金计算结果_预期.xlsx",
      "key_metrics": {
        "总记录数": 150,
        "总佣金": 123456.78
      }
    },
    {
      "name": "有退货场景",
      "input_file": "销售数据_退货测试.xlsx",
      "expected_output": "佣金计算结果_退货测试_预期.xlsx",
      "key_metrics": {
        "总记录数": 100,
        "总佣金": -5000.00
      }
    }
  ]
}
```

**业务方需要定义**：
- 可接受的计算误差范围
- 谁需要审批计算结果
- 什么样的差异需要警告

---

## 资产提供后的实施步骤

### 第 1 天：资产验收与映射

```bash
# 1. 将资产放入指定目录
tests/fixtures/requirement4_contracts/
├── excel_contracts.json          # 业务方提供
└── ambiguity_checklist.md        # 业务方提供

tests/fixtures/requirement4_samples/
└── *.xlsx                        # 业务方提供

tests/fixtures/requirement4_golden/
├── *.xlsx                        # 业务方提供
└── golden_metadata.json          # 业务方提供

# 2. 验证脚手架仍然就绪
make validate-req4

# 3. 确认资产完整
ls -la tests/fixtures/requirement4_*/
```

**工程方需要做的**：
- 审查契约是否清晰完整
- 确认样本文件可正常打开
- 验证金标准输出与输入对应
- 记录任何需要澄清的问题

---

### 第 1 周：业务规则实现

#### 步骤 1：使用 Claude Code CLI 理解契约

```bash
# 启动 Claude Code
claude

# 加载并理解契约
> 阅读 tests/fixtures/requirement4_contracts/excel_contracts.json
> 阅读 tests/fixtures/requirement4_contracts/ambiguity_checklist.md
> 总结：有哪些输入文件？每个文件有哪些列？计算规则是什么？
> 创建 docs/requirement4/CONTRACT_SUMMARY.md
```

#### 步骤 2：实现佣金计算引擎

```bash
# 在 Claude Code 中
> 阅读 src/autoresearch/core/services/commission_engine.py
> 根据 CONTRACT_SUMMARY.md 实现以下功能：
>   1. 加载契约
>   2. 解析 Excel 文件（使用 openpyxl）
>   3. 应用计算规则
>   4. 返回计算结果
>   5. 不使用 LLM，仅确定性计算
```

#### 步骤 3：实现验证逻辑

```bash
> 在 src/autoresearch/core/services/excel_ops.py 中添加：
>   1. validate_job() 方法
>   2. 与金标准输出比较
>   3. 检查是否在容差范围内
>   4. 返回详细验证结果
```

#### 步骤 4：运行测试

```bash
# 运行契约测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v

# 运行端到端测试
PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v
```

---

### 第 2 周：金标准验证与集成

#### 步骤 1：金标准对比测试

```bash
# 创建对比测试
> 在 tests/test_excel_ops_service.py 中添加：
>   test_golden_output_match():
>     1. 加载测试 fixtures/requirement4_samples/*.xlsx
>     2. 运行佣金计算
>     3. 与 tests/fixtures/requirement4_golden/*.xlsx 比较
>     4. 验证在容差范围内

# 运行测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py::test_golden_output_match -v
```

#### 步骤 2：连接服务

```bash
# 在 src/autoresearch/api/dependencies.py 中：
> 导入 ExcelOpsService, ExcelJobsRepository, CommissionEngine
> 创建数据库：artifacts/api/excel_jobs.db
> 初始化服务实例
> 连接到 get_excel_ops_service 依赖

# 在 src/autoresearch/api/routers/excel_ops.py 中：
> 移除 HTTPException 501
> 让路由使用真实服务
```

#### 步骤 3：冒烟测试

```bash
# 运行完整测试套件
PYTHONPATH=src python -m pytest tests/test_excel_ops_*.py tests/test_e2e_pipeline_verification.py -v

# 运行基线验证
make validate-req4

# 运行冒烟测试
make smoke-local
```

---

### 上线：试点部署

```bash
# 1. 合并到主分支
git checkout main
git merge feat/single-machine-aas-ready-for-req4

# 2. 启动服务（最小模式）
export AUTORESEARCH_MODE=minimal
make start

# 3. 验证 API 端点
curl http://localhost:8001/api/v1/excel-ops/status/requirement4

# 4. 提交给业务方验证
# 业务方通过 UI 或 API 提交测试任务
# 比对计算结果与金标准
# 确认差异在容差范围内
```

---

## 预计时间线

| 阶段 | 时间 | 负责方 | 前置条件 |
|------|------|--------|----------|
| 资产准备 | 待定 | 业务方 | - |
| 资产验收 | 1 天 | 工程方 | 4 个资产已提供且质量合格 |
| 业务规则实现 | 5-7 天 | 工程方 | 资产验收通过，无需反复澄清 |
| 金标准验证 | 2-3 天 | 工程方 + 业务方 | 业务规则实现完成 |
| 试点部署 | 1-2 天 | 工程方 | 金标准验证通过 |
| **总计** | **7-12 天** | 从资产到就绪 | **在 4 个业务资产质量合格且无需反复澄清的前提下** |

> ⚠️ **注意**：7-12 天的时间线基于以下假设：
> 1. 业务方提供的 4 个资产完整、准确、无需大幅修改
> 2. 契约和歧义决策清单清晰明确，无需反复澄清
> 3. 工程方在实现过程中无重大技术阻塞
>
> 如果资产需要反复补充或澄清，时间线可能会延长。

---

## 验收标准

### 工程脚手架验收（当前已完成）✅
- [x] 44 个测试全部通过
- [x] `make validate-req4` 通过
- [x] `make smoke-local` 通过
- [x] 路由已注册并可访问
- [x] 阻塞状态明确具体

### 业务逻辑验收（资产到达后）
- [ ] 所有计算结果与金标准一致（在容差范围内）
- [ ] 测试覆盖率 ≥ 80%
- [ ] 性能满足要求（单次计算 < 5 秒）
- [ ] 业务方确认计算逻辑正确
- [ ] 审批工作流已配置

---

## 常见问题

**Q: 为什么不能先实现业务逻辑，再要资产？**
A: 因为没有真实的契约和样本，我们无法知道具体的计算规则。如果自己发明规则，很可能与业务需求不符，需要全部重写。

**Q: 金标准输出必须是手工计算的吗？**
A: 不一定。可以是手工计算，也可以是现有系统的导出结果，关键是要确保它是"正确的"。

**Q: 容差范围应该如何设定？**
A: 由业务方根据实际需求设定。通常金额类精确到分（0.01），百分比可以略有浮动。

**Q: 如果计算结果与金标准不一致怎么办？**
A: 首先检查是否在容差范围内。如果是，记录警告并通过；如果不是，需要排查原因，可能是：
- 实现错误
- 金标准本身有误
- 契约有歧义

---

## 参考文档

- **Claude Code CLI 实施指南**：`docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md`
- **准备计划**：`docs/requirement4/ENGINEERING_PREP_PLAN.md`
- **实施检查清单**：`docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md`
- **加固计划**：`docs/requirement4/BASELINE_HARDENING_PLAN.md`

---

## 📝 文档同步说明

**重要**：本分支包含中英文双语文档。如需修改命令、路径、配置等内容，请同时更新英文和中文版本，以保持文档一致性：

- `PR_SUMMARY.md` ↔ `PR_SUMMARY_ZH.md`
- `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES.md` ↔ `docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md`
- `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md` (中文独有，对应英文版在后续迭代中补充)
