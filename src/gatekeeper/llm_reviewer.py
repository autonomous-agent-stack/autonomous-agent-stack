"""LLM 降维总结器 (C1, U1)

功能：
1. 将 PR Diff 发送给大模型
2. 强制输出标准 JSON 格式
3. 仅包含 3 个字段：purpose, performance, security
4. 严禁 LLM 输出废话
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMReview:
    """LLM 审查结果"""
    purpose: str
    performance: str
    security: str
    security_score: int  # 0-100
    raw_response: str


class LLM_Diff_Reviewer:
    """LLM 降维总结器"""
    
    # JSON 输出契约
    JSON_SCHEMA = {
        "purpose": "一句话说明目的",
        "performance": "对性能的实质影响",
        "security": "安全评级 0-100",
    }
    
    # Prompt 模板
    REVIEW_PROMPT = """你是代码审查专家。请分析以下 PR 代码改动，并输出标准 JSON 格式。

## 代码改动
```diff
{diff}
```

## 安全检测结果
{security_result}

## 测试结果
{test_result}

## 输出要求
**严格输出 JSON 格式，不要输出任何其他内容！**

```json
{{
  "purpose": "一句话说明这个 PR 做什么",
  "performance": "对系统性能的实质影响（提升/下降/无影响）",
  "security": "安全评级 0-100（0=极危险，100=完全安全）"
}}
```

**红线**：
- 如果检测到危险代码（os.system, eval 等），security 必须 <= 20
- 如果测试失败，purpose 必须说明"测试未通过"
- 不要输出任何解释，只输出 JSON
"""

    def __init__(
        self,
        model: str = "codex",  # codex / claude / glm
        max_diff_length: int = 2000,
        temperature: float = 0.3,
    ):
        self.model = model
        self.max_diff_length = max_diff_length
        self.temperature = temperature
    
    async def review_pr(
        self,
        pr_diff: str,
        security_result: Dict[str, Any],
        test_result: Dict[str, Any],
    ) -> LLMReview:
        """审查 PR
        
        Args:
            pr_diff: PR 代码差异
            security_result: 安全检测结果
            test_result: 测试结果
            
        Returns:
            LLMReview
        """
        logger.info(f"🔍 开始 LLM 审查 (model={self.model})")
        
        # 1. 截断过长的 diff
        diff = self._truncate_diff(pr_diff)
        
        # 2. 构建 Prompt
        prompt = self.REVIEW_PROMPT.format(
            diff=diff,
            security_result=json.dumps(security_result, ensure_ascii=False, indent=2),
            test_result=json.dumps(test_result, ensure_ascii=False, indent=2),
        )
        
        # 3. 调用 LLM
        response = await self._call_llm(prompt)
        
        # 4. 解析 JSON
        review = self._parse_response(response, security_result, test_result)
        
        logger.info(f"✅ LLM 审查完成: security={review.security_score}")
        return review
    
    def _truncate_diff(self, diff: str) -> str:
        """截断过长的 diff"""
        if len(diff) > self.max_diff_length:
            truncated = diff[:self.max_diff_length]
            logger.warning(f"Diff 过长，已截断: {len(diff)} -> {len(truncated)}")
            return truncated + "\n...[truncated]"
        return diff
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM
        
        Args:
            prompt: 提示词
            
        Returns:
            LLM 响应
        """
        # TODO: 实现真实 LLM 调用
        # 目前返回模拟结果
        
        # 模拟 Codex/Claude 调用
        if self.model == "codex":
            return await self._call_codex(prompt)
        elif self.model == "claude":
            return await self._call_claude(prompt)
        elif self.model == "glm":
            return await self._call_glm(prompt)
        else:
            return await self._call_mock(prompt)
    
    async def _call_codex(self, prompt: str) -> str:
        """调用 Codex（通过 OpenAI API）"""
        # TODO: 实现真实调用
        # api_key = os.getenv("OPENAI_API_KEY")
        # ...
        return await self._call_mock(prompt)
    
    async def _call_claude(self, prompt: str) -> str:
        """调用 Claude（通过 Anthropic API）"""
        # TODO: 实现真实调用
        # api_key = os.getenv("ANTHROPIC_API_KEY")
        # ...
        return await self._call_mock(prompt)
    
    async def _call_glm(self, prompt: str) -> str:
        """调用 GLM（通过智谱 API）"""
        # TODO: 实现真实调用
        # api_key = os.getenv("ZHIPU_API_KEY")
        # ...
        return await self._call_mock(prompt)
    
    async def _call_mock(self, prompt: str) -> str:
        """模拟 LLM 响应（测试用）"""
        # 提取代码部分（## 代码改动 和 ## 安全检测结果 之间）
        import re
        code_match = re.search(r'## 代码改动\n```diff\n(.*?)\n```', prompt, re.DOTALL)
        code = code_match.group(1) if code_match else ""
        
        # 只在代码部分检测危险函数（不检测示例文本）
        if "os.system" in code or "subprocess." in code or "eval(" in code or "exec(" in code:
            return json.dumps({
                "purpose": "包含危险代码，建议打回",
                "performance": "未知",
                "security": "15"
            }, ensure_ascii=False)
        
        # 检测测试失败（更精确的检测）
        # 注意：'"safe": true' 不应该被匹配
        if '"safe": false' in prompt or '"success": false' in prompt:
            return json.dumps({
                "purpose": "安全检测或测试未通过，建议打回",
                "performance": "未知",
                "security": "30"
            }, ensure_ascii=False)
        
        # 正常情况
        return json.dumps({
            "purpose": "集成新功能或修复 Bug",
            "performance": "无明显影响",
            "security": "95"
        }, ensure_ascii=False)
    
    def _parse_response(
        self,
        response: str,
        security_result: Dict[str, Any],
        test_result: Dict[str, Any],
    ) -> LLMReview:
        """解析 LLM 响应"""
        try:
            # 提取 JSON（处理可能的额外文本）
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                raise ValueError("未找到 JSON")
            
            # 提取字段
            purpose = data.get("purpose", "未知")
            performance = data.get("performance", "未知")
            security_str = data.get("security", "50")
            
            # 解析安全分数
            try:
                security_score = int(security_str)
            except ValueError:
                # 如果是文字描述，转换为分数
                security_score = self._security_text_to_score(security_str)
            
            # 根据实际检测结果调整分数
            if not security_result.get("safe", True):
                security_score = min(security_score, 20)
            
            # 生成安全评级文本
            security_text = self._security_score_to_text(security_score)
            
            return LLMReview(
                purpose=purpose,
                performance=performance,
                security=security_text,
                security_score=security_score,
                raw_response=response,
            )
            
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            
            # 降级处理：返回默认值
            return LLMReview(
                purpose="LLM 解析失败",
                performance="未知",
                security="中",
                security_score=50,
                raw_response=response,
            )
    
    def _security_text_to_score(self, text: str) -> int:
        """将安全文本转换为分数"""
        text = text.lower()
        
        if "高" in text or "high" in text or "安全" in text:
            return 90
        elif "中" in text or "medium" in text:
            return 60
        elif "低" in text or "low" in text or "危险" in text:
            return 20
        else:
            return 50
    
    def _security_score_to_text(self, score: int) -> str:
        """将安全分数转换为文本"""
        if score >= 80:
            return "高"
        elif score >= 50:
            return "中"
        else:
            return "低"


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        reviewer = LLM_Diff_Reviewer()
        
        # 测试正常 PR
        review = await reviewer.review_pr(
            pr_diff="print('hello')",
            security_result={"safe": True},
            test_result={"success": True},
        )
        print(f"✅ 正常 PR: {review.purpose}")
        print(f"安全: {review.security} ({review.security_score})")
        
        # 测试危险 PR
        review = await reviewer.review_pr(
            pr_diff="os.system('rm -rf /')",
            security_result={"safe": False, "violations": ["os.system"]},
            test_result={"success": False},
        )
        print(f"❌ 危险 PR: {review.purpose}")
        print(f"安全: {review.security} ({review.security_score})")
    
    asyncio.run(test())
