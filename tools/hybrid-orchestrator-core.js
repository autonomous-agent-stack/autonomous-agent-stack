const crypto = require('crypto');

/**
 * ==========================================
 * 阶段 2: 分布式追踪系统 (Distributed Tracing)
 * ==========================================
 */
class TraceManager {
  constructor() {
    // 使用 Map 存储进行中的 Span，避免内存泄漏
    this.activeSpans = new Map(); 
  }

  /**
   * 启动一个新的追踪节点
   * @param {string} agentId - 代理 ID
   * @param {string} taskDescription - 任务描述
   * @param {string} [parentTraceId] - 可选的父级 Trace ID
   * @returns {Object} 包含注入了上下文的任务字符串和生成的 spanId
   */
  startTrace(agentId, taskDescription, parentTraceId = null) {
    const traceId = parentTraceId || crypto.randomUUID();
    const spanId = crypto.randomBytes(8).toString('hex');
    const startTime = Date.now();

    this.activeSpans.set(spanId, {
      traceId,
      agentId,
      startTime
    });

    const tracedTask = `
[SYSTEM_TRACE_CONTEXT]
trace_id: ${traceId}
span_id: ${spanId}
[/SYSTEM_TRACE_CONTEXT]

${taskDescription}
    `.trim();

    this._log(traceId, spanId, agentId, 'START', 'Agent task started');

    return { tracedTask, spanId, traceId };
  }

  /**
   * 记录任务完成并输出性能日志
   */
  endTrace(spanId, result = { error: null, tokens: 0 }) {
    const span = this.activeSpans.get(spanId);
    if (!span) return;

    const duration = Date.now() - span.startTime;
    const status = result.error ? 'ERROR' : 'SUCCESS';

    this._log(span.traceId, spanId, span.agentId, status, 'Agent task completed', {
      duration_ms: duration,
      tokens_used: result.tokens,
      error_detail: result.error || undefined
    });

    this.activeSpans.delete(spanId);
  }

  /**
   * 结构化日志输出 (JSON Lines 格式，方便 grep 和收集)
   */
  _log(traceId, spanId, agentId, event, message, metadata = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      trace_id: traceId,
      span_id: spanId,
      agent_id: agentId,
      event,
      message,
      ...metadata
    };
    console.log(JSON.stringify(logEntry));
  }
}

/**
 * ==========================================
 * 阶段 1: 状态压缩器与 Token 监控
 * ==========================================
 */
class TokenAndStateManager {
  constructor(maxTokens = 100000, threshold = 0.8) {
    this.currentTokens = 0;
    this.maxTokens = maxTokens;
    this.threshold = threshold;
  }

  /**
   * 记录 Token 并检查是否需要熔断压缩
   * @returns {boolean} 是否需要触发状态压缩
   */
  trackAndCheck(tokenCount) {
    this.currentTokens += tokenCount;
    const ratio = this.currentTokens / this.maxTokens;
    
    // 浅色终端背景下，可以使用更温和的日志提示
    console.log(`[Token Monitor] 进度: ${(ratio * 100).toFixed(1)}% (${this.currentTokens}/${this.maxTokens})`);
    
    return ratio >= this.threshold;
  }

  /**
   * 调用 LLM 进行状态压缩 (伪代码，需替换为你实际的 SDK 调用)
   * @param {Array} chatHistory - 原始对话数组
   * @param {Object} llmClient - LLM 客户端实例 (如 Anthropic SDK)
   */
  async compressState(chatHistory, llmClient) {
    console.log('[State Compressor] 正在提取核心状态，准备释放上下文压力...');
    
    const prompt = `
请作为系统架构师，分析以下多智能体协作对话历史。
提取核心上下文并输出为纯 JSON 格式。无需任何解释。

需要提取的字段：
1. "completed_tasks": 已经得出的结论或完成的代码
2. "decisions": 关键架构或逻辑决策
3. "pending_work": 尚未解决的问题或下一步计划
4. "context_summary": 200字以内的全局背景摘要

对话历史：
${JSON.stringify(chatHistory)}
    `;

    try {
      // 假设使用 Claude SDK
      const response = await llmClient.messages.create({
        model: "claude-3-5-sonnet-20241022",
        max_tokens: 4096,
        temperature: 0, // 压缩状态需要绝对的确定性
        messages: [{ role: "user", content: prompt }]
      });

      // 解析 JSON (处理可能的 markdown 代码块包裹)
      const rawText = response.content[0].text;
      const jsonMatch = rawText.match(/\{[\s\S]*\}/);
      const compressedState = jsonMatch ? JSON.parse(jsonMatch[0]) : JSON.parse(rawText);

      // 重置 Token 计数器（因为我们即将开启新会话）
      this.currentTokens = 0; 
      
      return compressedState;
    } catch (error) {
      console.error('[State Compressor] 状态压缩失败:', error);
      throw error;
    }
  }
}

module.exports = {
  TraceManager,
  TokenAndStateManager
};
