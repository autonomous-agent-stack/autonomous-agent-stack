"""
业务护城河验证器 (QA1, QA2)

功能：
1. Docker 沙盒测试
2. 玛露业务红线验证
3. 文案语义断言
"""

import re
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from src.gatekeeper.sandbox_runner import Sandbox_Test_Runner, SandboxTestResult

@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    missing_keywords: List[str]
    forbidden_found: List[str]
    test_passed: bool
    test_details: Dict

class BusinessTDD_Enforcer:
    """业务护城河验证器"""
    
    def __init__(
        self,
        sandbox_runner: Optional[Sandbox_Test_Runner] = None,
        llm_backend: Any | None = None,
    ):
        """初始化
        
        Args:
            sandbox_runner: 沙盒测试运行器实例（可选）
        """
        self.sandbox_runner = sandbox_runner or Sandbox_Test_Runner()
        self.llm_backend = llm_backend

        # 玛露必需关键词
        self.malu_keywords = [
            "挑战游泳级别持妆",
            "不用调色",
            "遮瑕力强"
        ]
        
        # 禁止术语（工厂化行话）
        self.forbidden_terms = [
            "平替",
            "代工厂",
            "流水线",
            "廉价",
            "批量化",
            "标准化生产",
            "批发",
            "清仓",
            "甩卖",
        ]
    
    async def validate_malu_copy(self, generated_copy: str) -> ValidationResult:
        """验证玛露文案"""
        result = ValidationResult(
            valid=True,
            missing_keywords=[],
            forbidden_found=[],
            test_passed=True,
            test_details={}
        )
        
        # 1. 检查必需关键词
        for keyword in self.malu_keywords:
            if keyword not in generated_copy:
                result.valid = False
                result.missing_keywords.append(keyword)
        
        # 2. 检查禁止术语
        for term in self.forbidden_terms:
            if term in generated_copy:
                result.valid = False
                result.forbidden_found.append(term)
        
        # 3. 语义断言（关键词覆盖率 + 语气约束 + 可选 LLM）
        semantic_result = await self._semantic_check(generated_copy)
        result.test_details["semantic"] = semantic_result
        if not semantic_result.get("semantic_ok", True):
            result.valid = False
            result.test_passed = False
        
        return result
    
    async def run_sandbox_tests(self, pr_branch: str, repo_path: str = ".") -> Dict:
        """在 Docker 沙盒中运行测试
        
        Args:
            pr_branch: PR 分支名
            repo_path: 仓库路径
            
        Returns:
            测试结果字典
        """
        # 使用 Sandbox_Test_Runner
        result: SandboxTestResult = await self.sandbox_runner.run_tests_in_sandbox(
            pr_branch=pr_branch,
            repo_path=repo_path,
        )
        
        return {
            "success": result.success,
            "logs": result.logs,
            "test_results": {
                "passed": result.test_passed,
                "failed": result.test_failed,
            },
            "malu_business_check": result.malu_business_check,
            "violations": result.violations,
        }
    
    async def _semantic_check(self, text: str) -> Dict[str, Any]:
        """语义检查（调用 LLM）"""
        lowered = text.lower()
        normalized = re.sub(r"\s+", "", text)

        required_hits = [keyword for keyword in self.malu_keywords if keyword in text]
        forbidden_hits = [term for term in self.forbidden_terms if term in text]

        score = 1.0
        score -= (len(self.malu_keywords) - len(required_hits)) * 0.25
        score -= len(forbidden_hits) * 0.4

        # 语义风格约束：尽量避免过度营销促销语
        promo_terms = ["秒杀", "最低价", "亏本", "抢购", "包邮", "福利", "冲量"]
        promo_hits = [term for term in promo_terms if term in normalized]
        if promo_hits:
            score -= min(len(promo_hits) * 0.1, 0.3)

        # 可选 LLM 复核（仅在注入后端时启用）
        llm_assessment: Dict[str, Any] | None = None
        if self.llm_backend is not None and hasattr(self.llm_backend, "generate"):
            prompt = (
                "请审查以下玛露产品文案，返回 JSON："
                '{"semantic_ok": true/false, "semantic_score": 0-1, "reason": "..."}。\n'
                f"文案：{text}"
            )
            try:
                response = await self.llm_backend.generate(
                    prompt,
                    system="你是品牌审查器，只输出 JSON。",
                    temperature=0.1,
                    max_tokens=300,
                )
                match = re.search(r"\{[\s\S]*\}", str(response))
                if match:
                    payload = json.loads(match.group(0))
                    llm_assessment = {
                        "semantic_ok": bool(payload.get("semantic_ok", True)),
                        "semantic_score": float(payload.get("semantic_score", 1.0)),
                        "reason": str(payload.get("reason", "")),
                    }
            except Exception:
                llm_assessment = None

        score = max(0.0, min(1.0, score))
        semantic_ok = (
            len(required_hits) == len(self.malu_keywords)
            and not forbidden_hits
            and score >= 0.7
        )
        if llm_assessment is not None:
            semantic_ok = semantic_ok and llm_assessment.get("semantic_ok", True)
            score = min(score, float(llm_assessment.get("semantic_score", score)))

        return {
            "semantic_ok": semantic_ok,
            "semantic_score": round(score, 3),
            "required_hits": required_hits,
            "forbidden_hits": forbidden_hits,
            "promo_hits": promo_hits,
            "llm_assessment": llm_assessment,
        }

# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        enforcer = BusinessTDD_Enforcer()
        
        # 测试正常文案
        result = await enforcer.validate_malu_copy(
            "玛露6g遮瑕膏，挑战游泳级别持妆，不用调色，遮瑕力强"
        )
        print(f"✅ 正常文案: {result.valid}")
        
        # 测试缺失关键词
        result = await enforcer.validate_malu_copy("这是一个测试文案")
        print(f"❌ 缺失关键词: {result.valid}")
        print(f"缺失: {result.missing_keywords}")
        
        # 测试禁止术语
        result = await enforcer.validate_malu_copy(
            "工厂化生产，挑战游泳级别持妆，不用调色，遮瑕力强"
        )
        print(f"❌ 包含禁止术语: {result.valid}")
        print(f"禁止: {result.forbidden_found}")
    
    asyncio.run(test())
