# OpenClaw Parity Test Plan

**目标**: 验证自定义编排系统（E5/Paperclip/OpenSage）与原生 OpenClaw 的行为一致性  
**版本**: 1.0  
**创建时间**: 2026-03-26  
**维护者**: glm-5-3 Subagent

---

## 📋 测试目标

### 核心问题
我们的自定义编排系统需要在哪些方面与原生 OpenClaw 保持一致？

### 测试范围

| 维度 | 原生 OpenClaw | 自定义系统 | 测试优先级 |
|------|--------------|-----------|-----------|
| 消息处理 | 通过 Lark/Feishu Webhook | Paperclip API | P0 |
| 工具调用 | 原生工具栈 | 自定义适配器 | P0 |
| Session 管理 | 内置 session 管理 | 自定义 session | P0 |
| 事件顺序 | 固定事件流 | 自定义事件流 | P1 |
| 错误处理 | 标准错误响应 | 自定义错误处理 | P1 |
| 重试机制 | 内置重试 | 自定义重试逻辑 | P1 |
| 媒体处理 | 原生媒体支持 | 自定义媒体处理 | P2 |

---

## 🎯 测试策略

### Phase 1: 基础行为一致性 (P0)

**目标**: 验证核心功能与原生 OpenClaw 行为一致

**测试方法**:
1. 对比测试: 相同输入 → 比较输出
2. Golden Tasks: 运行 20 个代表性任务
3. 事件流追踪: 记录完整执行过程

**通过标准**:
- ✅ 输出格式兼容
- ✅ 工具调用序列一致
- ✅ Session 状态变化一致
- ⚠️ 允许差异: 响应时间、日志格式

### Phase 2: 错误处理一致性 (P1)

**目标**: 验证异常情况的处理方式

**测试场景**:
1. 工具调用失败
2. 超时处理
3. 无效输入
4. 并发请求

**通过标准**:
- ✅ 错误类型一致
- ✅ 重试逻辑相似
- ✅ 降级策略合理

### Phase 3: 边界情况 (P2)

**目标**: 验证极端和边界情况

**测试场景**:
1. 大文件处理
2. 长文本处理
3. 复杂嵌套调用
4. 资源限制

---

## 🧪 Golden Tasks 设计

### 任务分类

#### 1. 基础工具调用 (6 个)
- 简单问答
- 文件读取
- 文件写入
- Web 搜索
- 日历查询
- 消息发送

#### 2. 复杂工作流 (8 个)
- 多步骤任务
- 条件分支
- 循环处理
- 批量操作
- 错误恢复
- 跨工具协作
- 数据转换
- 状态管理

#### 3. 媒体处理 (3 个)
- 图片分析
- 文件上传
- 音频处理

#### 4. 错误场景 (3 个)
- 工具超时
- 权限错误
- 格式错误

---

## 📊 观测维度

### 输入维度
```json
{
  "task_id": "golden_task_001",
  "input": {
    "type": "message",
    "content": "今天天气怎么样？",
    "channel": "webchat",
    "timestamp": "2026-03-26T00:00:00Z"
  }
}
```

### Session 变化维度
```json
{
  "session_before": {
    "messages_count": 0,
    "context": {},
    "state": "idle"
  },
  "session_after": {
    "messages_count": 1,
    "context": {"weather_checked": true},
    "state": "completed"
  }
}
```

### Event 顺序维度
```json
{
  "events": [
    {"type": "message_received", "timestamp": "..."},
    {"type": "tool_call", "tool": "weather", "timestamp": "..."},
    {"type": "tool_response", "status": "success", "timestamp": "..."},
    {"type": "message_sent", "timestamp": "..."}
  ]
}
```

### 输出格式维度
```json
{
  "output": {
    "type": "text",
    "content": "今天天气晴...",
    "format": "markdown",
    "media": []
  }
}
```

### Cancel/Retry 维度
```json
{
  "cancel": {
    "supported": true,
    "cleanup": "full",
    "timeout": 30
  },
  "retry": {
    "max_attempts": 3,
    "backoff": "exponential",
    "retryable_errors": ["timeout", "network"]
  }
}
```

### 媒体维度
```json
{
  "media": {
    "types": ["image", "audio", "video", "document"],
    "max_size_mb": 25,
    "supported_formats": ["jpg", "png", "mp3", "mp4", "pdf"]
  }
}
```

### 按钮维度
```json
{
  "buttons": {
    "interactive": true,
    "types": ["url", "callback", "reply"],
    "max_buttons": 5
  }
}
```

### 工具调用维度
```json
{
  "tool_calls": [
    {
      "tool": "weather",
      "parameters": {"location": "Beijing"},
      "result": {"temp": 20, "condition": "sunny"},
      "duration_ms": 245
    }
  ]
}
```

### 错误处理维度
```json
{
  "errors": [
    {
      "type": "tool_timeout",
      "tool": "weather",
      "message": "Request timeout",
      "recovered": true,
      "retry_attempt": 2
    }
  ]
}
```

---

## ✅ 通过标准

### 完全通过 (PASS)
- 输出格式完全一致
- 工具调用序列完全一致
- Session 状态变化一致
- 错误处理一致
- 性能指标在合理范围内（±20%）

### 部分通过 (PARTIAL)
- 输出内容语义一致但格式不同
- 工具调用序列相同但实现不同
- Session 状态最终一致但中间状态不同
- 错误被正确处理但方式不同

### 失败 (FAIL)
- 输出内容语义不一致
- 工具调用序列不同
- Session 状态不一致
- 错误未被处理或处理不当
- 核心功能无法完成

---

## 🤖 自动化建议

### 可自动化 (pytest)
- ✅ 基础工具调用测试
- ✅ 输入输出格式验证
- ✅ Session 状态变化检查
- ✅ 工具调用序列验证
- ✅ 错误类型检查

### 需要手工比对
- ⚠️ 输出内容语义一致性
- ⚠️ 复杂工作流的中间状态
- ⚠️ UI 交互（按钮、卡片）
- ⚠️ 媒体内容质量

### 需要录屏或日志
- 📹 完整用户交互流程
- 📊 性能分析（响应时间、资源使用）
- 📝 详细的调试日志
- 🔍 Event 流的完整记录

---

## 📈 测试覆盖率目标

| 测试类型 | 覆盖率目标 | 当前状态 |
|---------|-----------|---------|
| Golden Tasks | 100% (20/20) | 0% |
| 工具调用 | 90% | 0% |
| 错误处理 | 80% | 0% |
| 边界情况 | 60% | 0% |

---

## 🚀 实施计划

### 第一阶段 (1 周)
- [ ] 创建 Golden Tasks 列表
- [ ] 实现基础测试框架
- [ ] 完成基础工具调用测试 (6/20)

### 第二阶段 (2 周)
- [ ] 完成复杂工作流测试 (8/20)
- [ ] 完成媒体处理测试 (3/20)
- [ ] 完成错误场景测试 (3/20)

### 第三阶段 (1 周)
- [ ] 分析测试结果
- [ ] 修复发现的问题
- [ ] 生成测试报告

---

## 📝 报告格式

### 测试结果摘要
```markdown
## Golden Task 001: 简单问答

- 状态: PASS
- 输入: "今天天气怎么样？"
- 预期输出: 天气信息
- 实际输出: "今天北京天气晴，温度 20°C"
- 工具调用: weather ✓
- Session 变化: ✓
- 耗时: 245ms (目标: <500ms)
```

### 汇总报告
```markdown
## Parity Test Summary

- 总任务数: 20
- 通过: 15 (75%)
- 部分通过: 3 (15%)
- 失败: 2 (10%)
- 覆盖率: 85%

### 主要发现
1. 工具调用序列 100% 一致
2. 输出格式 95% 兼容
3. 错误处理需要改进 (3 处)
```

---

## 🔗 相关文档

- Golden Tasks 列表: `tests/fixtures/openclaw_golden_tasks.json`
- 测试实施指南: `docs/openclaw-parity-test-implementation.md`
- 测试报告模板: `docs/openclaw-parity-test-report-template.md`

---

**下一步**: 创建 Golden Tasks JSON 文件
