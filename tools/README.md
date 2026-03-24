# OpenClaw 混合编排引擎核心模块

**版本**: 1.0  
**作者**: 基于用户需求工程化实现  
**创建时间**: 2026-03-24

---

## 📋 概述

这是一个生产级的 Node.js 工具库，用于在 Claude CLI 和 OpenClaw 之间建立桥接。解决了多智能体协作的三大核心问题：

1. **Token 爆炸** → 自动状态压缩
2. **调试困难** → 分布式追踪
3. **上下文迁移** → JSON 状态切片

---

## 🎯 核心设计亮点

### 1. 纯净的 JSON Lines 日志

```json
{"timestamp":"2026-03-24T07:17:00Z","trace_id":"abc-123","span_id":"def456","event":"SUCCESS","message":"Agent task completed","duration_ms":1500}
```

**优势**：
- ✅ 可直接导入 ELK、Datadog
- ✅ 支持 `grep` 快速过滤
- ✅ 兼容 OpenTelemetry 标准

### 2. 零温度压缩 (Temperature = 0)

```javascript
const response = await llmClient.messages.create({
  model: "claude-3-5-sonnet-20241022",
  max_tokens: 4096,
  temperature: 0, // 确保压缩结果的确定性和一致性
  messages: [...]
});
```

**优势**：
- ✅ 压缩结果可重现
- ✅ 避免信息失真
- ✅ 适合工程化场景

### 3. 容错解析

```javascript
const rawText = response.content[0].text;
const jsonMatch = rawText.match(/\{[\s\S]*\}/);
const compressedState = jsonMatch ? JSON.parse(jsonMatch[0]) : JSON.parse(rawText);
```

**优势**：
- ✅ 自动剥离 Markdown 代码块
- ✅ 容错性强
- ✅ 避免解析崩溃

---

## 🚀 快速开始

### 安装

```bash
# 复制核心模块到你的项目
cp hybrid-orchestrator-core.js your-project/tools/

# 安装依赖（如果还没有）
npm install crypto
```

### 基础使用

```javascript
const { TraceManager, TokenAndStateManager } = require('./hybrid-orchestrator-core');

// 1. 初始化
const tracer = new TraceManager();
const stateManager = new TokenAndStateManager(100000, 0.8);

// 2. 启动追踪
const { tracedTask, spanId } = tracer.startTrace(
  'compliance-arbiter',
  '检查代码规范'
);

// 3. 执行任务
const result = await executeAgent(tracedTask);

// 4. 检查 Token 压力
const needsCompression = stateManager.trackAndCheck(result.tokens);

// 5. 如果需要压缩
if (needsCompression) {
  const compressedState = await stateManager.compressState(chatHistory, llmClient);
  // 迁移到 OpenClaw...
}

// 6. 结束追踪
tracer.endTrace(spanId, { error: null, tokens: result.tokens });
```

---

## 📊 API 文档

### TraceManager

#### `startTrace(agentId, taskDescription, parentTraceId)`

启动一个新的追踪节点。

**参数**：
- `agentId` (string): 代理 ID
- `taskDescription` (string): 任务描述
- `parentTraceId` (string, 可选): 父级 Trace ID

**返回**：
```javascript
{
  tracedTask: string,  // 注入了上下文的任务字符串
  spanId: string,      // 生成的 Span ID
  traceId: string      // Trace ID
}
```

#### `endTrace(spanId, result)`

记录任务完成并输出性能日志。

**参数**：
- `spanId` (string): Span ID
- `result` (object): 结果对象
  ```javascript
  {
    error: string | null,
    tokens: number
  }
  ```

---

### TokenAndStateManager

#### `trackAndCheck(tokenCount)`

记录 Token 并检查是否需要熔断压缩。

**参数**：
- `tokenCount` (number): 本次消耗的 Token 数

**返回**：
- `boolean`: 是否需要触发状态压缩

#### `compressState(chatHistory, llmClient)`

调用 LLM 进行状态压缩。

**参数**：
- `chatHistory` (Array): 原始对话数组
- `llmClient` (Object): LLM 客户端实例

**返回**：
```javascript
{
  completed_tasks: string[],
  decisions: string[],
  pending_work: string[],
  context_summary: string
}
```

---

## 🔧 集成到 OpenClaw

### 方法 1: 作为中间件

```javascript
// 在你的 OpenClaw 会话中
const { TraceManager, TokenAndStateManager } = require('./hybrid-orchestrator-core');

async function orchestrateWorkflow(task, agents) {
  const tracer = new TraceManager();
  const stateManager = new TokenAndStateManager();
  
  // 启动根追踪
  const rootTrace = tracer.startTrace('orchestrator', '工作流开始');
  
  for (const agent of agents) {
    // 启动子追踪
    const { tracedTask, spanId } = tracer.startTrace(
      agent.id,
      agent.task,
      rootTrace.traceId
    );
    
    // 调用 OpenClaw 子代理
    const result = await sessions_spawn({
      agentId: agent.id,
      task: tracedTask
    });
    
    // 检查 Token 压力
    const needsCompression = stateManager.trackAndCheck(result.tokens);
    
    if (needsCompression) {
      // 压缩状态并迁移
      const compressedState = await stateManager.compressState(
        getChatHistory(),
        llmClient
      );
      
      // 启动新的 OpenClaw 会话
      return await sessions_spawn({
        agentId: 'workflow-continuator',
        task: `继续执行任务，初始状态：${JSON.stringify(compressedState)}`,
        attachments: [{
          name: 'initial-state.json',
          content: JSON.stringify(compressedState),
          encoding: 'utf8'
        }]
      });
    }
    
    // 结束追踪
    tracer.endTrace(spanId, { error: null, tokens: result.tokens });
  }
  
  // 结束根追踪
  tracer.endTrace(rootTrace.spanId, { error: null, tokens: 0 });
}
```

### 方法 2: 作为全局工具

```javascript
// 在 OpenClaw 配置中注册为全局工具
module.exports = {
  tools: {
    hybridOrchestrator: {
      enabled: true,
      path: './tools/hybrid-orchestrator-core.js'
    }
  }
};
```

---

## 📈 性能监控

### 查看实时日志

```bash
# 实时查看所有追踪
tail -f logs.jsonl | grep "trace_id"

# 过滤错误
cat logs.jsonl | grep "ERROR" | jq .

# 统计 Token 消耗
cat logs.jsonl | grep "tokens_used" | jq '.tokens_used' | awk '{sum+=$1} END {print sum}'
```

### 生成追踪报告

```javascript
// 从 JSON Lines 日志生成报告
const fs = require('fs');
const logs = fs.readFileSync('logs.jsonl', 'utf8')
  .split('\n')
  .filter(Boolean)
  .map(JSON.parse);

const report = {
  totalTraces: logs.filter(l => l.event === 'START').length,
  successRate: logs.filter(l => l.event === 'SUCCESS').length / logs.filter(l => l.event === 'START').length,
  avgDuration: logs.filter(l => l.duration_ms).reduce((a, b) => a + b.duration_ms, 0) / logs.filter(l => l.duration_ms).length,
  errors: logs.filter(l => l.event === 'ERROR')
};

console.log(JSON.stringify(report, null, 2));
```

---

## 🧪 测试

```bash
# 运行示例
node hybrid-orchestrator-example.js

# 预期输出
# - 场景 1: 基础追踪使用
# - 场景 2: Token 监控与自动压缩
# - 场景 3: 完整工作流
# - 场景 4: 错误追踪与调试
```

---

## 🔍 故障排查

### 问题 1: JSON 解析失败

**症状**:
```
SyntaxError: Unexpected token in JSON
```

**解决**:
```javascript
// 使用容错解析
const jsonMatch = rawText.match(/\{[\s\S]*\}/);
const state = jsonMatch ? JSON.parse(jsonMatch[0]) : {};
```

### 问题 2: Token 计数不准确

**症状**:
```
[Token Monitor] 进度: 120.0%
```

**解决**:
```javascript
// 检查 maxTokens 设置
const stateManager = new TokenAndStateManager(100000, 0.8); // 确保 maxTokens 正确

// 手动重置
stateManager.currentTokens = 0;
```

### 问题 3: 追踪 ID 丢失

**症状**:
```
trace_id: undefined
```

**解决**:
```javascript
// 确保传递 parentTraceId
const { traceId } = tracer.startTrace(agent.id, task, parentTraceId);
```

---

## 📚 参考资料

- [OpenTelemetry 标准](https://opentelemetry.io/)
- [JSON Lines 格式](https://jsonlines.org/)
- [Claude API 文档](https://docs.anthropic.com/)

---

## 🚀 下一步

1. **第 1 周**: 测试核心模块，集成到现有项目
2. **第 2 周**: 接入 ELK/Datadog 日志系统
3. **第 3 周**: 实现可视化仪表盘

---

**维护者**: OpenClaw 社区  
**许可证**: MIT  
**版本**: 1.0
