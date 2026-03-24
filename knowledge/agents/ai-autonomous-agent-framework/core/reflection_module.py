# knowledge/agents/ai-autonomous-agent-framework/core/reflection_module.py

"""
反思模块

评估执行结果并生成修正建议
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json


@dataclass
class Assessment:
    """评估结果"""
    is_complete: bool
    quality_score: float  # 0-10
    issues: List[str]
    suggestions: List[str]
    should_refine: bool
    feedback: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_complete": self.is_complete,
            "quality_score": self.quality_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "should_refine": self.should_refine,
            "feedback": self.feedback
        }


class ReflectionModule:
    """
    反思模块

    评估执行结果并生成修正建议
    """

    def __init__(self, llm_client=None):
        """
        初始化反思模块

        Args:
            llm_client: LLM 客户端，用于智能评估
        """
        self.llm_client = llm_client

    def assess(
        self,
        goal: str,
        results: List[Any],
        memory: 'MemorySystem'
    ) -> Assessment:
        """
        评估执行结果

        Args:
            goal: 原始目标
            results: 执行结果列表
            memory: 记忆系统

        Returns:
            评估结果
        """
        # 使用 LLM 进行智能评估
        if self.llm_client:
            return self._llm_assess(goal, results, memory)
        else:
            # 使用规则基评估
            return self._rule_based_assess(goal, results, memory)

    def _llm_assess(
        self,
        goal: str,
        results: List[Any],
        memory: 'MemorySystem'
    ) -> Assessment:
        """使用 LLM 进行智能评估"""
        prompt = self._build_assessment_prompt(goal, results, memory)

        response = self.llm_client.generate(prompt)
        return self._parse_assessment(response)

    def _rule_based_assess(
        self,
        goal: str,
        results: List[Any],
        memory: 'MemorySystem'
    ) -> Assessment:
        """规则基评估"""
        # 检查失败的任务
        failed_tasks = []
        issues = []

        for result in results:
            if result.status == "failed":
                failed_tasks.append(result.task_id)
                issues.append(f"任务 {result.task_id} 失败: {result.error}")

        # 检查目标达成度
        is_complete = len(failed_tasks) == 0

        # 计算质量分数
        quality_score = self._calculate_quality_score(results)

        # 生成建议
        suggestions = []
        if failed_tasks:
            suggestions.append(f"重新执行失败的任务: {', '.join(failed_tasks)}")
        if quality_score < 7:
            suggestions.append("提高任务执行质量")

        return Assessment(
            is_complete=is_complete,
            quality_score=quality_score,
            issues=issues,
            suggestions=suggestions,
            should_refine=not is_complete or quality_score < 7,
            feedback=self._generate_feedback(goal, results, is_complete, quality_score)
        )

    def _build_assessment_prompt(
        self,
        goal: str,
        results: List[Any],
        memory: 'MemorySystem'
    ) -> str:
        """构建评估提示"""
        results_summary = "\n".join([
            f"- {result.task_id}: {result.status}"
            for result in results
        ])

        return f"""请评估以下执行结果：

原始目标: {goal}

执行结果:
{results_summary}

请评估:
1. 目标是否达成
2. 执行质量如何 (0-10分)
3. 存在哪些问题
4. 有什么改进建议

返回格式:
{{
  "is_complete": true/false,
  "quality_score": 0-10,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"],
  "should_refine": true/false,
  "feedback": "总体反馈"
}}
"""

    def _parse_assessment(self, response: str) -> Assessment:
        """解析评估结果"""
        try:
            data = json.loads(response)
            return Assessment(
                is_complete=data.get("is_complete", False),
                quality_score=data.get("quality_score", 0),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                should_refine=data.get("should_refine", False),
                feedback=data.get("feedback", "")
            )
        except:
            return Assessment(
                is_complete=False,
                quality_score=0,
                issues=[],
                suggestions=[],
                should_refine=True,
                feedback="无法解析评估结果"
            )

    def _calculate_quality_score(self, results: List[Any]) -> float:
        """计算质量分数"""
        if not results:
            return 0.0

        success_count = sum(1 for r in results if r.status == "success")
        total_count = len(results)

        base_score = (success_count / total_count) * 10

        # 考虑执行时间
        avg_time = sum(r.execution_time for r in results) / total_count
        if avg_time > 10:
            base_score *= 0.8

        return round(base_score, 2)

    def _generate_feedback(
        self,
        goal: str,
        results: List[Any],
        is_complete: bool,
        quality_score: float
    ) -> str:
        """生成反馈"""
        if is_complete and quality_score >= 8:
            return "目标达成，执行质量优秀。"
        elif is_complete and quality_score >= 6:
            return "目标达成，但执行质量有待提高。"
        elif not is_complete:
            return "目标未达成，需要继续执行。"
        else:
            return "执行存在较多问题，需要重新规划。"


if __name__ == "__main__":
    from executor import ExecutionResult

    reflection = ReflectionModule()

    # 模拟执行结果
    results = [
        ExecutionResult(
            task_id="task_1",
            status="success",
            output="完成",
            error=None,
            execution_time=2.5,
            metadata={}
        ),
        ExecutionResult(
            task_id="task_2",
            status="failed",
            output=None,
            error="工具不可用",
            execution_time=1.0,
            metadata={}
        ),
    ]

    # 评估结果
    assessment = reflection.assess(
        goal="完成项目开发",
        results=results,
        memory={}
    )

    print(f"目标完成: {assessment.is_complete}")
    print(f"质量分数: {assessment.quality_score}/10")
    print(f"问题: {assessment.issues}")
    print(f"建议: {assessment.suggestions}")
    print(f"反馈: {assessment.feedback}")
