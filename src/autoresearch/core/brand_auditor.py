"""Brand Auditor - 品牌审计员

品牌调性约束审计
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BrandViolation:
    """品牌违规"""
    category: str  # factory_words, unprofessional, etc
    violation: str
    context: str
    line_number: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "violation": self.violation,
            "context": self.context,
            "line_number": self.line_number,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditResult:
    """审计结果"""
    status: str  # passed, failed, warning
    violations: List[BrandViolation] = field(default_factory=list)
    brand_score: float = 100.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "violations": [v.to_dict() for v in self.violations],
            "brand_score": self.brand_score,
            "timestamp": self.timestamp.isoformat(),
        }


class BrandAuditor:
    """品牌审计员
    
    负责将 Micro-GraphRAG 的调性约束植入 LLM_Diff_Reviewer
    
    工程红线：
    - 所有 Agent 生成的关于"玛露 (Malu)"的文案或报告
    - 严禁出现"平替"、"代工厂"、"廉价"等工厂化词汇
    - 确保所有输出符合"专业、去工厂化"标准
    """
    
    # 工厂化词汇黑名单
    FACTORY_WORDS = {
        "平替",
        "代工厂",
        "廉价",
        "便宜",
        "低档",
        "次品",
        "仿制",
        "山寨",
        "copy",
        "clone",
        "cheap",
        "knockoff",
    }
    
    # 专业性词汇白名单
    PROFESSIONAL_WORDS = {
        "专业",
        "高品质",
        "精选",
        "定制",
        "专属",
        "premium",
        "professional",
        "exclusive",
        "customized",
    }
    
    # 品牌名称白名单
    BRAND_WHITELIST = {
        "玛露",
        "Malu",
    }
    
    def __init__(self):
        self.violations: List[BrandViolation] = []
        
    async def audit_text(
        self,
        text: str,
        context: str = "general"
    ) -> AuditResult:
        """审计文本
        
        Args:
            text: 待审计文本
            context: 上下文
            
        Returns:
            审计结果
        """
        logger.info(f"[环境防御] 品牌审计: {context}")
        
        self.violations = []
        
        # 检查工厂化词汇
        await self._check_factory_words(text)
        
        # 检查品牌名称
        await self._check_brand_names(text)
        
        # 计算品牌分数
        brand_score = self._calculate_brand_score(text)
        
        # 确定状态
        status = "passed"
        if any(v.category == "factory_words" for v in self.violations):
            status = "failed"
        elif len(self.violations) > 0:
            status = "warning"
            
        logger.info(f"[环境防御] 品牌审计完成: {status}, 分数: {brand_score}")
        
        return AuditResult(
            status=status,
            violations=self.violations,
            brand_score=brand_score
        )
        
    async def audit_json_summary(
        self,
        summary: Dict[str, Any]
    ) -> AuditResult:
        """审计 JSON 总结报告
        
        Args:
            summary: JSON 总结
            
        Returns:
            审计结果
        """
        logger.info("[环境防御] 审计 JSON 总结报告")
        
        # 提取所有文本字段
        text_fields = self._extract_text_fields(summary)
        
        all_violations = []
        
        for field_name, text in text_fields.items():
            result = await self.audit_text(text, context=f"json_field:{field_name}")
            all_violations.extend(result.violations)
            
        # 确定状态
        status = "passed"
        if any(v.category == "factory_words" for v in all_violations):
            status = "failed"
        elif len(all_violations) > 0:
            status = "warning"
            
        logger.info(f"[环境防御] JSON 总结审计完成: {status}")
        
        return AuditResult(
            status=status,
            violations=all_violations,
            brand_score=100.0 - len(all_violations) * 5
        )
        
    async def _check_factory_words(self, text: str):
        """检查工厂化词汇"""
        
        text_lower = text.lower()
        
        for word in self.FACTORY_WORDS:
            if word.lower() in text_lower:
                # 查找上下文
                context = self._find_context(text, word)
                
                self.violations.append(BrandViolation(
                    category="factory_words",
                    violation=word,
                    context=context
                ))
                
                logger.warning(f"[环境防御] 发现工厂化词汇: {word}")
                
    async def _check_brand_names(self, text: str):
        """检查品牌名称"""
        
        # 检查是否提到品牌但没有使用专业词汇
        for brand in self.BRAND_WHITELIST:
            if brand in text:
                # 检查是否使用了专业词汇
                has_professional = any(
                    prof in text for prof in self.PROFESSIONAL_WORDS
                )
                
                if not has_professional:
                    self.violations.append(BrandViolation(
                        category="unprofessional",
                        violation=f"提到品牌 '{brand}' 但未使用专业词汇",
                        context=self._find_context(text, brand)
                    ))
                    
    def _calculate_brand_score(self, text: str) -> float:
        """计算品牌分数"""
        
        score = 100.0
        
        # 扣分：工厂化词汇
        factory_count = sum(1 for word in self.FACTORY_WORDS if word in text.lower())
        score -= factory_count * 20
        
        # 加分：专业词汇
        professional_count = sum(1 for word in self.PROFESSIONAL_WORDS if word in text)
        score += professional_count * 5
        
        # 限制在 0-100
        return max(0.0, min(100.0, score))
        
    def _extract_text_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """提取 JSON 中的所有文本字段"""
        
        text_fields = {}
        
        def _extract(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    _extract(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _extract(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                text_fields[path] = obj
                
        _extract(data)
        return text_fields
        
    def _find_context(self, text: str, word: str, context_chars: int = 50) -> str:
        """查找词汇上下文"""
        
        idx = text.lower().find(word.lower())
        if idx == -1:
            return ""
            
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(word) + context_chars)
        
        return text[start:end]
