# OpenClaw Parity 回归测试套件

## 概述

这个测试套件用于验证自定义编排系统（E5/Paperclip/OpenSage）与原生 OpenClaw 的行为一致性。

**测试范围**：
- P0（核心功能）：Session 管理、Channel 适配、工具调用
- P1（重要功能）：Event 顺序、错误处理、并发控制、Tree 结构、富交互、工具 shim

**测试文件**：
- `test_openclaw_compat.py` - OpenClaw 兼容性回归测试
- `test_self_integration_protocol.py` - 自集成协议测试

## 快速开始

### 运行所有测试

```bash
# 使用虚拟环境中的 Python
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py tests/test_self_integration_protocol.py -v

# 运行特定测试套件
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py -v
tests/.venv/bin/python -m pytest tests/test_self_integration_protocol.py -v
```

### 运行特定测试类

```bash
# Session 管理测试（P0）
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py::TestSessionManagement -v

# 工具调用测试（P0）
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py::TestToolCalls -v

# Golden Tasks 测试
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py::TestGoldenTasks -v
```

### 运行特定优先级的测试

```bash
# P0 测试（核心功能）
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py::TestGoldenTasks::test_p0_basic_tool_calls -v

# P1 测试（复杂工作流）
tests/.venv/bin/python -m pytest tests/test_openclaw_compat.py::TestGoldenTasks::test_p1_complex_workflows -v
```

## 测试覆盖

### test_openclaw_compat.py

#### P0 测试（核心功能）

1. **TestSessionManagement** - Session 管理测试
   - `test_session_creation` - 创建 session
   - `test_session_context_persistence` - Session 上下文持久化
   - `test_session_state_transition` - Session 状态转换
   - `test_multi_session_isolation` - 多 session 隔离

2. **TestToolCalls** - 工具调用测试
   - `test_single_tool_call` - 单个工具调用
   - `test_multiple_tool_calls` - 多个工具调用
   - `test_tool_call_sequence_validation` - 工具调用序列验证
   - `test_partial_sequence_match` - 部分序列匹配

#### P1 测试（重要功能）

3. **TestEventOrdering** - 事件顺序测试
   - `test_event_sequence` - 事件序列
   - `test_event_timestamp_ordering` - 事件时间戳顺序
   - `test_event_data_preservation` - 事件数据保留

4. **TestErrorHandling** - 错误处理测试
   - `test_task_execution_failure` - 任务执行失败
   - `test_error_recovery_attempt` - 错误恢复尝试

5. **TestConcurrencyControl** - 并发控制测试
   - `test_concurrent_session_creation` - 并发 session 创建

6. **TestGoldenTasks** - Golden Tasks 集成测试
   - `test_p0_basic_tool_calls` - P0 基础工具调用（6个任务）
   - `test_p1_complex_workflows` - P1 复杂工作流（6个任务）

### test_self_integration_protocol.py

#### 模块导入协议

1. **TestImportProtocol** - 模块导入协议测试
   - `test_core_module_imports` - 核心模块导入
   - `test_module_interface_compliance` - 模块接口符合性
   - `test_module_dependencies` - 模块依赖关系

#### 树结构协议

2. **TestTreeProtocol** - 树结构协议测试（思维树 CoT）
   - `test_tree_creation` - 树创建
   - `test_tree_expansion` - 树展开（分支探索）
   - `test_tree_backtracking` - 树回溯
   - `test_tree_serialization` - 树序列化

#### 富交互协议

3. **TestRichInteractionProtocol** - 富交互协议测试
   - `test_button_creation` - 按钮创建
   - `test_card_creation` - 卡片创建
   - `test_card_button_limit` - 卡片按钮限制（最多5个）
   - `test_card_serialization` - 卡片序列化
   - `test_button_types` - 不同按钮类型（URL、Callback、Reply）

#### 工具 Shim 协议

4. **TestToolShimProtocol** - 工具 Shim 协议测试
   - `test_tool_registration` - 工具注册
   - `test_tool_call` - 工具调用
   - `test_tool_not_found` - 工具不存在
   - `test_parameter_validation` - 参数验证
   - `test_multiple_tools` - 多个工具

#### 集成协议检查

5. **TestIntegrationProtocol** - 集成协议检查
   - `test_module_protocol_compliance` - 模块协议符合性
   - `test_end_to_end_integration` - 端到端集成

6. **test_compliance_report** - 生成协议兼容性报告

## 测试结果分类

测试结果分为三种类型：

- **PASS**（完全通过）：输出格式完全一致，工具调用序列完全一致，Session 状态变化一致
- **PARTIAL**（部分通过）：输出内容语义一致但格式不同，工具调用序列相同但实现不同，Session 状态最终一致但中间状态不同
- **FAIL**（失败）：输出内容语义不一致，工具调用序列不同，Session 状态不一致，核心功能无法完成
- **SKIP**（跳过）：功能未实现

## Golden Tasks

Golden Tasks 是 20 个代表性任务，用于验证与原生 OpenClaw 的兼容性：

| 任务 ID | 名称 | 类别 | 优先级 |
|---------|------|------|--------|
| golden_task_001 | 简单问答 - 天气查询 | basic_tool_call | P0 |
| golden_task_002 | 文件读取 | basic_tool_call | P0 |
| golden_task_003 | 文件写入 | basic_tool_call | P0 |
| golden_task_004 | Web搜索 | basic_tool_call | P0 |
| golden_task_005 | 日历查询 | basic_tool_call | P0 |
| golden_task_006 | 消息发送 | basic_tool_call | P0 |
| golden_task_007 | 多步骤任务 - 文件分析 | complex_workflow | P0 |
| golden_task_008 | 条件分支 - 智能回复 | complex_workflow | P1 |
| golden_task_009 | 循环处理 - 批量文件 | complex_workflow | P1 |
| golden_task_010 | 批量操作 - 多个查询 | complex_workflow | P1 |
| golden_task_011 | 错误恢复 - 文件不存在 | complex_workflow | P1 |
| golden_task_012 | 跨工具协作 - 搜索并保存 | complex_workflow | P1 |
| golden_task_013 | 数据转换 - JSON处理 | complex_workflow | P1 |
| golden_task_014 | 状态管理 - 记忆测试 | complex_workflow | P1 |
| golden_task_015 | 复杂嵌套调用 - 深度测试 | complex_workflow | P1 |
| golden_task_016 | 图片分析 | media_handling | P2 |
| golden_task_017 | 文件上传处理 | media_handling | P2 |
| golden_task_018 | 音频处理 | media_handling | P2 |
| golden_task_019 | 工具超时处理 | error_handling | P1 |
| golden_task_020 | 权限错误处理 | error_handling | P1 |

## 验收标准

- ✅ 新增测试可跑
- ✅ 失败信息足够具体，能指导下一个 agent 修复
- ✅ 测试覆盖 P0 和 P1 关键路径
- ✅ 明确区分"完全通过 / 部分通过 / 失败"

## 下一步

1. 接入真实的 GraphEngine 和 ToolSynthesis
2. 实现 Session Manager
3. 实现工具注册表
4. 实现 Channel Adapter (Lark/Feishu Webhook)
5. 逐步实现 P0 功能，然后扩展到 P1

## 相关文档

- `docs/openclaw-parity-matrix.md` - 行为对齐矩阵
- `docs/openclaw-parity-test-plan.md` - 测试计划
- `tests/fixtures/openclaw_golden_tasks.json` - Golden Tasks 定义

## 维护者

- 创建：glm-4.7-4 Subagent (2026-03-26)
- 角色：回归测试与行为对比实现
