/**
 * 混合编排引擎使用示例
 * 演示如何在 Claude CLI 和 OpenClaw 之间桥接
 */

const { TraceManager, TokenAndStateManager } = require('./hybrid-orchestrator-core');

// 示例：模拟 Anthropic SDK 客户端
const mockLLMClient = {
  messages: {
    create: async ({ model, max_tokens, temperature, messages }) => {
      // 模拟压缩响应
      return {
        content: [{
          text: JSON.stringify({
            completed_tasks: [
              "完成了合规性审查",
              "识别了 3 个逻辑漏洞"
            ],
            decisions: [
              "采用零温度压缩策略",
              "使用 JSON Lines 日志格式"
            ],
            pending_work: [
              "等待架构影响分析完成",
              "需要生成最终报告"
            ],
            context_summary: "多智能体代码审查工作流，包含合规性、逻辑和架构三个维度的并行分析。"
          })
        }]
      };
    }
  }
};

/**
 * ==========================================
 * 场景 1: 基础追踪使用
 * ==========================================
 */
async function example1_basicTracing() {
  console.log('\n=== 场景 1: 基础追踪使用 ===\n');
  
  const tracer = new TraceManager();
  
  // 启动追踪
  const { tracedTask, spanId, traceId } = tracer.startTrace(
    'compliance-arbiter',
    '检查代码是否符合 CLAUDE.md 规范'
  );
  
  console.log('\n--- 注入了追踪上下文的任务描述 ---');
  console.log(tracedTask);
  
  // 模拟任务执行
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // 结束追踪
  tracer.endTrace(spanId, { error: null, tokens: 1500 });
  
  console.log('\n--- 检查 JSON Lines 日志输出 ---');
  console.log('你可以用以下命令过滤日志：');
  console.log('  grep "trace_id" logs.jsonl');
  console.log('  jq \'. | select(.event=="SUCCESS")\' logs.jsonl');
}

/**
 * ==========================================
 * 场景 2: Token 监控与自动压缩
 * ==========================================
 */
async function example2_tokenMonitoring() {
  console.log('\n=== 场景 2: Token 监控与自动压缩 ===\n');
  
  const stateManager = new TokenAndStateManager(10000, 0.75); // 降低阈值便于演示
  
  const chatHistory = [
    { role: 'user', content: '请审查这段代码...' },
    { role: 'assistant', content: '我发现了以下问题...' },
    { role: 'user', content: '继续分析...' }
  ];
  
  // 模拟多次对话，直到触发压缩阈值
  for (let i = 1; i <= 8; i++) {
    const tokens = 1200;
    const needsCompression = stateManager.trackAndCheck(tokens);
    
    if (needsCompression) {
      console.log('\n⚠️  Token 压力过大，触发状态压缩！');
      
      const compressedState = await stateManager.compressState(chatHistory, mockLLMClient);
      
      console.log('\n--- 压缩后的核心状态 ---');
      console.log(JSON.stringify(compressedState, null, 2));
      
      console.log('\n✅ 状态已压缩，可以启动新的 OpenClaw 会话继续工作');
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}

/**
 * ==========================================
 * 场景 3: 完整工作流（追踪 + 状态管理）
 * ==========================================
 */
async function example3_completeWorkflow() {
  console.log('\n=== 场景 3: 完整工作流 ===\n');
  
  const tracer = new TraceManager();
  const stateManager = new TokenAndStateManager();
  
  // 定义多智能体工作流
  const agents = [
    { id: 'compliance-arbiter', task: '检查代码规范' },
    { id: 'logic-minesweeper', task: '扫描逻辑漏洞' },
    { id: 'architecture-tracer', task: '分析架构影响' }
  ];
  
  const rootTraceId = null;
  let totalTokens = 0;
  
  for (const agent of agents) {
    // 启动追踪
    const { tracedTask, spanId, traceId } = tracer.startTrace(
      agent.id,
      agent.task,
      rootTraceId
    );
    
    // 模拟任务执行
    console.log(`\n--- 执行代理: ${agent.id} ---`);
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const tokensUsed = Math.floor(Math.random() * 2000) + 1000;
    totalTokens += tokensUsed;
    
    // 检查是否需要压缩
    const needsCompression = stateManager.trackAndCheck(tokensUsed);
    
    // 结束追踪
    tracer.endTrace(spanId, { error: null, tokens: tokensUsed });
    
    if (needsCompression) {
      console.log('\n⚠️  触发状态压缩，准备迁移到 OpenClaw...');
      
      // 这里可以调用 stateManager.compressState()
      // 然后使用 sessions_spawn() 启动 OpenClaw 工作流
      break;
    }
  }
  
  console.log(`\n--- 工作流完成 ---`);
  console.log(`总 Token 消耗: ${totalTokens}`);
}

/**
 * ==========================================
 * 场景 4: 错误追踪与调试
 * ==========================================
 */
async function example4_errorTracking() {
  console.log('\n=== 场景 4: 错误追踪与调试 ===\n');
  
  const tracer = new TraceManager();
  
  const { tracedTask, spanId } = tracer.startTrace(
    'failing-agent',
    '这个任务会失败'
  );
  
  // 模拟任务失败
  await new Promise(resolve => setTimeout(resolve, 200));
  
  const error = new Error('数据库连接超时');
  tracer.endTrace(spanId, { error: error.message, tokens: 500 });
  
  console.log('\n--- 错误已记录到 JSON Lines 日志 ---');
  console.log('使用以下命令过滤错误：');
  console.log('  grep "ERROR" logs.jsonl | jq .');
}

/**
 * ==========================================
 * 运行所有示例
 * ==========================================
 */
async function runAllExamples() {
  try {
    await example1_basicTracing();
    await example2_tokenMonitoring();
    await example3_completeWorkflow();
    await example4_errorTracking();
    
    console.log('\n\n=== ✅ 所有示例运行完成 ===\n');
    console.log('接下来你可以：');
    console.log('1. 将此模块集成到你的 OpenClaw 项目中');
    console.log('2. 使用 sessions_spawn() 调用压缩后的状态');
    console.log('3. 将 JSON Lines 日志导入到 ELK/Datadog');
    
  } catch (error) {
    console.error('\n❌ 示例运行失败:', error);
  }
}

// 运行示例
runAllExamples();
