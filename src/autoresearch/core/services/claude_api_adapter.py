"""
Universal API Execution Engine v2.0
职责：全面接管大模型网络 I/O，提供防挂死、可重试、结构化的底层通信能力。
取代脆弱的 subprocess CLI 封装。
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic, APITimeoutError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


class ClaudeAPIAdapter:
    """原生异步 API 引擎 - 防挂死、可重试、结构化输出"""
    
    def __init__(self):
        # 强制要求环境变量注入，解耦对本地环境的依赖
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 启动失败: 缺少 ANTHROPIC_API_KEY。原生 API 引擎需要明确的授权凭证。")
        
        # 初始化官方异步客户端，建立工程级护城河
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            timeout=45.0,  # 强制 45 秒超时，绝不允许永久挂起
            max_retries=3  # 内置 3 次防抖与指数退避重试机制
        )
        self.model = "claude-3-5-sonnet-20241022"  # 生产级稳定模型
    
    async def execute(self, prompt: str, require_json: bool = False) -> str:
        """
        核心执行流：原生 HTTP/2 异步调用，彻底消灭管道死锁
        """
        logger.info(f"[API Executor] 发起原生模型调用 (Require JSON: {require_json})")
        
        system_prompt = (
            "你是一个运行在 Autonomous Agent Stack 中的核心逻辑执行器。"
            "必须保持客观、冷静的工程语境，拒绝任何废话和客套。"
        )
        
        if require_json:
            system_prompt += " 你必须且只能输出合法的 JSON 格式数据，不要包裹在 Markdown 代码块中。"
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result_text = response.content[0].text
            
            # JSON 强制校验拦截器
            if require_json:
                try:
                    json.loads(result_text)
                except json.JSONDecodeError:
                    logger.warning("[API Executor] 模型输出非标准 JSON，启动容错清洗。")
                    return json.dumps({"status": "error", "message": "Failed to parse JSON output", "raw": result_text})
            
            return result_text
        
        except APITimeoutError:
            logger.error("❌ [API Executor] Anthropic API 45秒超时熔断。")
            return json.dumps({"status": "error", "message": "Execution timeout limit reached."})
        except RateLimitError:
            logger.error("⚠️ [API Executor] 触发速率限制，请检查并发拓扑。")
            return json.dumps({"status": "error", "message": "Rate limit exceeded."})
        except Exception as e:
            logger.error(f"❌ [API Executor] 底层通信异常: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})
