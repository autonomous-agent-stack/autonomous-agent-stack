# 使用 Claude Code CLI 实现需求 #4

## 概述

本指南解释如何在提供业务资产后使用 **Claude Code CLI** 实现需求 #4（Excel 佣金处理）。

## 前置条件

1. **已安装 Claude Code CLI**
   ```bash
   # 通过 npm 安装
   npm install -g @anthropic-ai/claude-code

   # 或通过 homebrew（macOS）
   brew install claude-code
   ```

2. **检出分支**
   ```bash
   git checkout feat/single-machine-aas-ready-for-req4
   git pull origin feat/single-machine-aas-ready-for-req4
   ```

3. **环境设置**
   ```bash
   make setup
   make doctor
   ```

## 步骤 1：验证基线

在开始实现之前，验证脚手架已就绪：

```bash
make validate-req4
```

预期输出：所有检查应通过并显示 ✅ 指示器。

## 步骤 2：接收业务资产

当业务方提供所需的 4 个资产时：

```bash
# 将资产放入 fixture 目录
tests/fixtures/requirement4_contracts/
├── excel_contracts.json          # 业务方提供
└── ambiguity_checklist.md        # 业务方提供

tests/fixtures/requirement4_samples/
└── *.xlsx                        # 业务方提供（1-3 个文件）

tests/fixtures/requirement4_golden/
├── *.xlsx                        # 业务方提供
└── golden_metadata.json          # 业务方提供
```

## 步骤 3：初始化 Claude Code 会话

在仓库中启动 Claude Code 会话：

```bash
cd /path/to/autonomous-agent-stack
claude
```

## 步骤 4：上下文加载策略

分阶段加载上下文，避免让 Claude 不堪重负：

### 阶段 1：加载架构（第一次会话）
```
请阅读以下文件以了解架构：
1. docs/requirement4/ENGINEERING_PREP_PLAN.md
2. docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md
3. src/autoresearch/core/services/commission_engine.py
4. src/autoresearch/core/repositories/excel_jobs.py
5. src/autoresearch/core/services/excel_ops.py
```

### 阶段 2：加载契约（第二次会话）
```
现在阅读业务契约：
1. tests/fixtures/requirement4_contracts/excel_contracts.json
2. tests/fixtures/requirement4_contracts/ambiguity_checklist.md
3. tests/fixtures/requirement4_golden/golden_metadata.json
```

### 阶段 3：加载样本（第三次会话）
```
现在检查样本 Excel 文件：
1. tests/fixtures/requirement4_samples/*.xlsx
2. tests/fixtures/requirement4_golden/*.xlsx
```

## 步骤 5：实现提示词

### 5.1 理解契约
```
基于 tests/fixtures/requirement4_contracts/ 中的契约：

1. 输入文件角色是什么？（例如：source_data、rate_table、agent_list）
2. 每个输入文件中预期有哪些列？
3. 定义了哪些计算规则？
4. 应用哪些验证规则？

创建摘要文档：docs/requirement4/CONTRACT_SUMMARY.md
```

### 5.2 实现佣金引擎
```
在 src/autoresearch/core/services/commission_engine.py 中实现佣金计算逻辑：

要求：
1. 从 tests/fixtures/requirement4_contracts/excel_contracts.json 加载契约
2. 从 tests/fixtures/requirement4_samples/ 解析 Excel 文件
3. 根据歧义检查清单应用计算规则
4. 以 CommissionCalculationResult 格式返回结果
5. 计算路径中无 LLM 调用（仅确定性）

使用 openpyxl 进行 Excel 解析。根据契约实现验证。
```

### 5.3 实现 Excel 解析
```
在 src/autoresearch/core/services/excel_ops.py 中添加 Excel 文件解析：

1. 从 job.input_files 读取输入文件
2. 根据 excel_contracts.json 映射列
3. 根据 ambiguity_checklist.md 验证数据
4. 规范化为 CommissionCalculationRequest 格式
5. 使用显式错误处理缺失/无效数据
```

### 5.4 实现验证
```
在 src/autoresearch/core/services/excel_ops.py 中实现验证：

1. 添加 validate_job() 方法
2. 根据金标准输出检查结果
3. 验证在 golden_metadata.json 中的容差范围内
4. 返回带有发现结果的 ExcelValidationResult
```

## 步骤 6：测试策略

### 6.1 运行契约测试
```bash
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v
```

### 6.2 运行端到端测试
```bash
PYTHONPATH=src python -m pytest tests/test_e2e_pipeline_verification.py -v
```

### 6.3 金标准输出比较
```
创建测试以验证：
1. 从 tests/fixtures/requirement4_samples/ 加载样本文件
2. 通过 CommissionEngine 运行计算
3. 与 tests/fixtures/requirement4_golden/*.xlsx 比较输出
4. 验证在 golden_metadata.json 的容差范围内

添加到 tests/test_excel_ops_service.py 作为 test_golden_output_match()
```

## 步骤 7：连接服务（验证后）

测试通过金标准输出后：

```
在 src/autoresearch/api/dependencies.py 中连接 excel_ops 服务：

1. 导入 ExcelOpsService、ExcelJobsRepository、CommissionEngine
2. 创建数据库路径：artifacts/api/excel_jobs.db
3. 初始化服务实例
4. 连接到 get_excel_ops_service 依赖
5. 从路由中移除 HTTPException 501
```

## 步骤 8：最终验证

```bash
# 运行所有测试
PYTHONPATH=src python -m pytest tests/test_excel_ops_*.py tests/test_e2e_pipeline_verification.py -v

# 验证基线
make validate-req4

# 冒烟测试
make smoke-local
```

## 最佳实践

### 应该做 ✅
- 分阶段加载上下文，而不是一次性全部加载
- 在提示词中使用具体的文件路径
- 在编码之前要求 Claude 创建摘要文档
- 每个实现步骤后运行测试
- 在连接服务之前验证金标准输出
- 保持计算确定性（生产路径中无 LLM）

### 不应该做 ❌
- 不要要求 Claude "阅读整个代码库"
- 不要在实现前跳过契约审查
- 不要在验证通过前连接服务
- 不要使用 LLM 进行计算（使用 Python/openpyxl）
- 不要在不理解的情况下修改核心架构
- 不要跳过与金标准输出的测试

## 示例会话流程

```
# 会话 1：架构审查
claude
> 阅读 docs/requirement4/ENGINEERING_PREP_PLAN.md
> 阅读 src/autoresearch/core/services/commission_engine.py
> 总结阻塞状态及其存在原因

# 会话 2：契约审查
claude
> 阅读 tests/fixtures/requirement4_contracts/excel_contracts.json
> 创建 docs/requirement4/CONTRACT_SUMMARY.md，包含：
>   - 输入文件角色和模式
>   - 计算规则
>   - 验证要求

# 会话 3：实现
claude
> 阅读 src/autoresearch/core/services/commission_engine.py
> 阅读 docs/requirement4/CONTRACT_SUMMARY.md
> 实现 calculate() 方法以：
>   1. 解析样本 Excel 文件
>   2. 应用佣金规则
>   3. 返回 CommissionCalculationResult
>   4. 无 LLM 调用

# 会话 4：测试
claude
> 运行：PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v
> 如果测试失败，修复实现
> 创建金标准输出比较测试

# 会话 5：集成
claude
> 阅读 src/autoresearch/api/dependencies.py
> 连接 excel_ops 服务
> 运行冒烟测试
```

## 故障排除

### 问题：实现后测试失败
**解决方案**：
```bash
# 检查测试输出中的具体失败
PYTHONPATH=src python -m pytest tests/test_excel_ops_service.py -v --tb=short

# 手动与金标准输出比较
python -c "
import pandas as pd
expected = pd.read_excel('tests/fixtures/requirement4_golden/output.xlsx')
actual = pd.read_excel('artifacts/test_output.xlsx')
print(expected.compare(actual))
"
```

### 问题：佣金引擎被阻塞
**解决方案**：确保契约文件已就位：
```bash
ls -la tests/fixtures/requirement4_contracts/
# 应该看到 excel_contracts.json 和 ambiguity_checklist.md
```

### 问题：服务返回 501
**解决方案**：在 dependencies.py 中连接服务，并从路由中移除 HTTPException。

## 实现后的后续步骤

1. **业务审查**：与业务方分享结果以获得批准
2. **试点部署**：在最小模式下部署进行试点测试
3. **监控**：跟踪计算准确性和性能
4. **迭代**：修复试点期间发现的问题

## 参考文档

- **准备计划**：`docs/requirement4/ENGINEERING_PREP_PLAN.md`
- **后续步骤**：`docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md`
- **检查清单**：`docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md`
- **加固**：`docs/requirement4/BASELINE_HARDENING_PLAN.md`
