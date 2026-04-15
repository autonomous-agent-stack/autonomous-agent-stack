# 2天冲刺方案：用 Claude Code CLI 实现销售统计与提成发放

## 适用场景

基于 `docs/aas-claude-ecc-excel-best-practice-report.md` 和 `docs/claude-code-excel-business-case.md`，用 Claude Code CLI 在 **2天内** 实现 Excel 销售统计与提成发放功能。

## 核心原则

1. **生产算账链** = 固定程序，不用 Claude 直接算钱
2. **开发维护链** = Claude Code CLI + ECC，负责开发和维护
3. **两条链路分离**：开发不动生产，生产不动代码

---

## 📋 Day 0：前置准备（4小时）

### 检查4个必需资产是否齐全

在开始编码前，必须确认以下资产已提供：

| 资产 | 文件路径 | 用途 |
|------|---------|------|
| 1. Excel 输入/输出契约 | `tests/fixtures/requirement4_contracts/excel_contracts.json` | 定义4类输入角色和字段 |
| 2. 7类歧义决策 | `tests/fixtures/requirement4_contracts/ambiguity_checklist.md` | 周期、金额、归属等决策 |
| 3. 真实样本（1-3份） | `tests/fixtures/requirement4_samples/*.xlsx` | 用于开发和测试 |
| 4. Golden 输出 | `tests/fixtures/requirement4_golden/*.xlsx` | 期望的输出结果 |

```bash
# 验证资产
ls -la tests/fixtures/requirement4_contracts/
ls -la tests/fixtures/requirement4_samples/
ls -la tests/fixtures/requirement4_golden/
make validate-req4
```

### 验证脚手架已就绪

```bash
# 运行测试确保脚手架可用
PYTHONPATH=src python -m pytest tests/test_excel_ops_*.py tests/test_e2e_pipeline_verification.py -v
# 应该看到 44 tests passing
```

---

## 📅 Day 1（8小时）：核心计算实现

### 时间分配

| 阶段 | 时间 | 任务 |
|------|------|------|
| 1.1 | 1h | 用 Claude Code CLI 理解契约和样本 |
| 1.2 | 3h | 实现 Excel 解析和标准化 |
| 1.3 | 3h | 实现佣金计算引擎 |
| 1.4 | 1h | 运行测试验证 |

### 1.1 理解契约和样本（1h）

**目标**：让 Claude Code CLI 理解业务规则和样本数据

**Prompt 模板**：

```bash
# 启动 Claude Code
claude

# 会话 1：理解业务契约
> 阅读 tests/fixtures/requirement4_contracts/excel_contracts.json
> 阅读 tests/fixtures/requirement4_contracts/ambiguity_checklist.md
> 阅读 docs/aas-claude-ecc-excel-best-practice-report.md
> 
> 请回答：
> 1. 有哪几类输入文件？每类的必需字段是什么？
> 2. 佣金计算的规则是什么？（阶梯、比例、封顶、保底）
> 3. 7类歧义是如何决策的？
> 
> 创建文档：docs/requirement4/CONTRACT_SUMMARY.md
```

**要点**：
- 先让 Claude 理解业务，不要直接开始写代码
- 生成 `CONTRACT_SUMMARY.md` 作为后续开发的依据
- 如果有不清楚的地方，立即向业务方确认

### 1.2 实现 Excel 解析和标准化（3h）

**目标**：实现读取 Excel、字段映射、数据清洗

**Prompt 模板**：

```bash
# 会话 2：实现 Excel 解析
> 阅读 src/autoresearch/core/services/excel_ops.py
> 阅读 docs/requirement4/CONTRACT_SUMMARY.md
> 阅读 tests/fixtures/requirement4_samples/*.xlsx（用 openpyxl 读取结构）
>
> 请实现：
> 1. 在 src/autoresearch/core/services/excel_ops.py 中添加 parse_excel_file() 方法
>    - 输入：Excel 文件路径、文件角色（从契约中获取）
>    - 处理：读取 Excel、识别 sheet、映射列、清洗数据
>    - 输出：标准化的内部数据结构（dict/list）
>    - 使用 openpyxl 库
> 2. 在 src/autoresearch/core/services/excel_ops.py 中添加 normalize_field() 方法
>    - 处理：日期标准化、金额格式化、币种统一
>    - 去除空值、验证数据类型
> 3. 添加数据校验逻辑
>    - 检查订单号重复、金额合法、状态一致
>    - 返回结构化的异常列表
>
> 代码风格要求：
> - 使用类型注解
> - 每个方法有 docstring
> - 错误处理要具体（不要用 pass）
```

**要点**：
- 让 Claude 实现具体的解析逻辑，不是设计架构
- 要求 Claude 先写代码，然后运行测试验证
- 使用 `/tdd` 技能确保测试驱动开发

### 1.3 实现佣金计算引擎（3h）

**目标**：实现确定性佣金计算

**Prompt 模板**：

```bash
# 会话 3：实现佣金计算
> 阅读 src/autoresearch/core/services/commission_engine.py
> 阅读 docs/requirement4/CONTRACT_SUMMARY.md
> 阅读 tests/fixtures/requirement4_contracts/excel_contracts.json 中的计算规则
>
> 请实现 calculate() 方法：
> 1. 加载计算规则版本（从 contracts）
> 2. 接收标准化后的订单数据
> 3. 按规则计算：
>    - 有效销售额识别（根据状态、金额、日期）
>    - 退款/补款冲减
>    - 销售归属分配（按比例）
>    - 阶梯提成计算
>    - 封顶/保底检查
> 4. 返回 CommissionCalculationResult：
>    - calculated_values: 销售汇总、提成明细
>    - applied_rules: 使用的规则列表
>    - intermediate_steps: 中间计算步骤（用于审计）
>
> 关键要求：
> - 不要使用 LLM 或 AI 推理
> - 完全确定性计算
> - 每个数字都要可回溯
```

**要点**：
- 强调"不要使用 LLM"，这是核心原则
- 要求 Claude 实现可审计的计算链
- 使用 `/code-review` 确保代码质量

### 1.4 运行测试验证（1h）

**目标**：确保核心功能正常

```bash
# 运行测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py::TestCommissionEngineScaffold -v

# 如果失败，修复问题
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py::TestCommissionEngineScaffold -v --tb=short
```

---

## 📅 Day 2（8小时）：集成、验证和维护

### 时间分配

| 阶段 | 时间 | 任务 |
|------|------|------|
| 2.1 | 2h | Golden 输出验证和调试 |
| 2.2 | 2h | 端到端集成测试 |
| 2.3 | 2h | 异常处理和边界情况 |
| 2.4 | 2h | 文档和 Prompt 模板 |

### 2.1 Golden 输出验证（2h）

**目标**：验证计算结果与预期一致

**Prompt 模板**：

```bash
# 会话 4：验证 Golden 输出
> 阅读 tests/fixtures/requirement4_golden/*.xlsx
> 阅读 tests/fixtures/requirement4_samples/*.xlsx
> 阅读 src/autoresearch/core/services/commission_engine.py
>
> 请创建测试：
> 1. 在 tests/test_excel_ops_service.py 中添加 test_golden_output_match()：
>    - 加载样本文件
>    - 运行完整计算流程
>    - 与 golden 输出逐行对比
>    - 验证数值在容差范围内
> 2. 处理差异：
>    - 如果完全匹配：返回 pass
>    - 如果在容差内：返回 warning with 差异
>    - 如果超出容差：返回 fail with 详细差异报告
>
> 运行测试验证
```

**要点**：
- 这是验收的关键步骤
- 用 `/tdd` 确保测试先行
- 差异报告要详细，便于调试

### 2.2 端到端集成测试（2h）

**目标**：验证完整流程

**Prompt 模块**：

```bash
# 会话 5：端到端测试
> 阅读 src/autoresearch/api/routers/excel_ops.py
> 阅读 tests/test_e2e_pipeline_verification.py
>
> 请完善测试：
> 1. 测试完整的 API 流程：
>    - POST /api/v1/excel-ops/jobs (创建任务)
>    - POST /api/v1/excel-ops/jobs/{id}/calculate (执行计算)
>    - GET /api/v1/excel-ops/jobs/{id} (查询结果)
> 2. 测试 SQLite 持久化：
>    - 验证 job 记录保存
>    - 验证审计信息记录
> 3. 测试异常报告生成
>
> 运行：PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v
```

### 2.3 异常处理和边界情况（2h）

**目标**：确保系统健壮性

**Prompt 模板**：

```bash
# 会话 6：异常处理
> 阅读 docs/requirement4/CONTRACT_SUMMARY.md
> 阅读 tests/fixtures/requirement4_contracts/ambiguity_checklist.md
>
> 请添加异常处理：
> 1. 空文件或文件不存在
> 2. Sheet 或列不存在
> 3. 金额格式错误（文本、负数）
> 4. 订单号重复或冲突
> 5. 比例总和不为 100%
> 6. 跨月退款处理
>
> 每种异常都要：
> - 返回具体的错误码（BlockedStateReason）
> - 提供清晰的错误消息
> - 记录到审计日志
> - 可追踪到原始文件/sheet/行号
>
> 使用 /code-review 确保异常处理质量
```

### 2.4 文档和 Prompt 模板（2h）

**目标**：创建维护用的 Prompt 模板

创建维护手册：`docs/requirement4/MAINTENANCE_GUIDE.md`

```markdown
# 维护指南

## 常见修改场景

### 场景 1：新增一种 Excel 模板

**何时使用**：业务方新增一种 Excel 文件格式

**步骤**：
1. 获取新模板样本
2. 更新 `excel_contracts.json` 添加新的输入角色
3. 使用 Claude Code CLI：

```bash
claude
> 阅读 tests/fixtures/requirement4_contracts/excel_contracts.json
> 阅读 [新模板样本.xlsx]
> 
> 请实现：
> 1. 在 parse_excel_file() 中添加新模板的识别逻辑
> 2. 映射新模板的列到内部字段
> 3. 添加样本测试
> 4. 更新 CONTRACT_SUMMARY.md
>
> 使用 /tdd 技能
> 使用 /code-review 确保代码质量
```

### 场景 2：修改提成规则

**何时使用**：业务方修改阶梯、比例、封顶等

**步骤**：
1. 更新 `ambiguity_checklist.md` 和 `excel_contracts.json`
2. 创建新的规则版本号
3. 使用 Claude Code CLI：

```bash
claude
> 阅读 tests/fixtures/requirement4_contracts/ambiguity_checklist.md
> 阅读 docs/requirement4/CONTRACT_SUMMARY.md
> 阅读 src/autoresearch/core/services/commission_engine.py
>
> 请实现：
> 1. 在 calculate() 中应用新规则
> 2. 保持旧规则版本可用（通过规则版本号区分）
> 3. 添加新规则到 applied_rules 输出
> 4. 更新测试用例
> 5. 运行 golden output 验证
>
> 使用 /tdd 技能
```

### 场景 3：修复字段映射错误

**何时使用**：发现某个字段映射错误导致计算结果不正确

**步骤**：
1. 定位问题字段
2. 使用 Claude Code CLI：

```bash
claude
> 阅读 [错误报告]
> 阅读 src/autoresearch/core/services/excel_ops.py
>
> 问题：[具体描述]
> 
> 请：
> 1. 定位到映射该字段的代码
> 2. 修正映射逻辑
> 3. 添加回归测试确保不再出现
> 4. 运行测试验证
>
> 使用 /code-review 确保修改质量
```

### 场景 4：处理新的异常类型

**何时使用**：运行时发现新的异常情况

**步骤**：
1. 记录异常场景（输入样本、预期行为）
2. 使用 Claude Code CLI：

```bash
claude
> 阅读 [异常场景描述]
> 阅读 src/autoresearch/core/services/excel_ops.py
>
> 请添加异常处理：
> 1. 识别该异常的特征
> 2. 返回适当的 BlockedStateReason
> 3. 记录到审计日志
> 4. 添加测试用例
> 5. 更新文档
>
> 使用 /tdd 技能
```

## 通用 Prompt 模板

### 模板 1：新增功能

```
请阅读以下文件了解上下文：
1. docs/requirement4/CONTRACT_SUMMARY.md
2. tests/fixtures/requirement4_contracts/excel_contracts.json
3. src/autoresearch/core/services/[相关服务].py

任务描述：[具体需求]

要求：
- 使用类型注解
- 添加 docstring
- 错误处理要具体
- 使用 /tdd 技能确保测试先行
- 使用 /code-review 确保代码质量

完成后运行：PYTHONPATH=src python -m pytest tests/[相关测试].py -v
```

### 模板 2：修复 Bug

```
问题：[具体描述]
错误信息：[如果有]

请：
1. 阅读 src/autoresearch/core/services/[相关服务].py
2. 定位问题代码
3. 修复 bug
4. 添加或更新测试用例
5. 运行测试验证修复

使用 /code-review 确保修复质量
```

### 模板 3：性能优化

```
性能问题：[具体描述]

请：
1. 阅读 src/autoresearch/core/services/[相关服务].py
2. 使用 cProfile 或其他工具分析性能瓶颈
3. 优化慢速代码
4. 运行测试确保功能不变

使用 /performance-optimizer agent 优化性能
```

## 测试 Checklist

每次修改后运行：

```bash
# 单元测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v

# E2E 测试
PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v

# 路由测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_router.py -v

# 完整验证
make validate-req4
```

## 快速修复常见问题

### 问题 1：测试失败

```bash
# 查看详细错误
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py::test_[测试名] -v --tb=short

# 使用 Claude Code CLI 修复
claude
> [贴错误信息]
> 阅读 tests/[相关文件].py
> 阅读 src/[相关服务].py
>
> 请修复这个测试失败
```

### 问题 2：金标准输出不匹配

```bash
# 运行对比测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py::test_golden_output_match -v

# 使用 Claude Code CLI 调试
claude
> 金标准输出在 tests/fixtures/requirement4_golden/*.xlsx
> 我的计算结果是 [描述差异]
> 阅读 src/autoresearch/core/services/commission_engine.py
>
> 请：
> 1. 分析为什么结果不同
> 2. 是映射问题还是规则问题
> 3. 修复问题
> 4. 重新验证
```

### 问题 3：字段映射错误

```bash
claude
> 字段：[字段名]
> 期望：[期望值]
> 实际：[实际值]
> 阅读 src/autoresearch/core/services/excel_ops.py
>
> 请：
> 1. 找到该字段的映射代码
> 2. 修正映射
> 3. 添加测试防止回归
```
```

---

## 🎯 关键成功因素

### 1. 严格遵循"两条链路分离"

| 链路 | 用途 | 什么可以做 | 什么不能做 |
|------|------|----------|------------|
| **生产算账链** | 真实业务处理 | 读取 Excel、计算佣金、输出结果 | ❌ 不用 Claude 直接算钱 |
| **开发维护链** | 程序变更 | 改代码、补测试、修 bug | ❌ 不直接操作生产数据 |

### 2. 必需的 ECC 技能

使用以下技能确保质量：

- `/plan` - 规划实现步骤
- `/tdd` - 测试驱动开发
- `/code-review` - 代码审查
- `/python-review` - Python 代码审查
- `/database-review` - 数据库/SQL 审查
- `/test-coverage` - 测试覆盖率检查

### 3. 时间压缩的关键技巧

1. **分阶段并行**：用多个 Claude Code 会话同时处理不同模块
2. **TDD 强制**：测试先行，减少调试时间
3. **代码即文档**：代码结构清晰，减少理解成本
4. **增量验证**：每完成一个模块立即测试，不积累问题

### 4. 风险控制

| 风险 | 缓解措施 |
|------|---------|
| 资产不完整 | Day 0 强制检查，缺失立即补齐 |
| 需求理解偏差 | CONTRACT_SUMMARY.md 双方确认 |
| Golden 不匹配 | 优先级最高，立即调试 |
| 时间不足 | 优先核心计算，异常处理可简化 |

---

## 📊 验收标准

### 功能验收

- [x] 能读取样本 Excel 并正确解析
- [ ] 能按规则计算佣金，结果与 golden 输出匹配
- [ ] 能生成 4 类输出：标准化明细、异常清单、销售汇总、提成表
- [ ] SQLite 审计记录完整

### 质量验收

- [ ] 44 个基础测试全部通过
- [ ] Golden output 测试通过
- [ ] E2E 测试通过
- [ ] 测试覆盖率 ≥ 80%

### 文档验收

- [x] CONTRACT_SUMMARY.md 已创建
- [x] MAINTENANCE_GUIDE.md 已创建
- [ ] README.md 已更新（使用说明）
- [ ] CHANGELOG.md 已记录变更

---

## 🚀 Day 2 结束后的状态

### 已交付功能

1. ✅ Excel 文件解析和标准化
2. ✅ 确定性佣金计算引擎
3. ✅ 4 类输出生成
4. ✅ SQLite 审计跟踪
5. ✅ Golden output 验证
6. ✅ 完整测试套件

### 可维护性

1. ✅ 维护指南文档
2. ✅ Prompt 模板库
3. ✅ 快速修复流程
4. ✅ 契约和规则版本化管理

### 不包含的功能

1. ❌ AI 直接计算佣金（违反核心原则）
2. ❌ 无人审核自动发放（安全风险）
3. ❌ 通用 Excel 自动识别（超出范围）

---

## 📌 核心原则 reminder

> **生产期不要让 AI 直接自由算钱**
> 
> Claude Code CLI + ECC 只负责开发/维护固定程序、规则文件、测试、文档
> 
> 真实计算时用固定程序，不是 Claude
