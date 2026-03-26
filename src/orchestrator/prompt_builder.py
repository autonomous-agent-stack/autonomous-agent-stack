from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrchestrationStep:
    """编排步骤定义。"""

    node_id: str
    node_type: str
    description: str = ""


@dataclass(frozen=True)
class OrchestrationEdge:
    """编排边定义。"""

    source: str
    target: str
    condition: str | None = None


@dataclass
class PromptOrchestrationPlan:
    """由 prompt 解析出来的可执行编排计划。"""

    goal: str
    steps: list[OrchestrationStep]
    edges: list[OrchestrationEdge]
    max_steps: int = 32
    max_concurrency: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [
                {"node_id": step.node_id, "node_type": step.node_type, "description": step.description}
                for step in self.steps
            ],
            "edges": [
                {"source": edge.source, "target": edge.target, "condition": edge.condition}
                for edge in self.edges
            ],
            "max_steps": self.max_steps,
            "max_concurrency": self.max_concurrency,
            "metadata": self.metadata,
        }


class PromptBuilder:
    """Prompt 组装与编排计划解析。"""

    FACTORY_WORDS = ["工厂", "批量", "流水线", "生产线", "规模化", "工业化"]
    PROFESSIONAL_KEYWORDS = ["专业", "精准", "高端", "定制", "匠心"]
    CORE_SELLING_POINTS = {
        "玛露6g罐装遮瑕膏": ["持妆", "免调色", "高遮瑕", "12小时", "一抹成型"],
    }

    NODE_ALIASES = {
        "planner": "planner",
        "plan": "planner",
        "规划": "planner",
        "计划": "planner",
        "generator": "generator",
        "generate": "generator",
        "生成": "generator",
        "executor": "executor",
        "execute": "executor",
        "执行": "executor",
        "evaluator": "evaluator",
        "evaluate": "evaluator",
        "评估": "evaluator",
        "评价": "evaluator",
    }

    DEFAULT_NODE_CHAIN = ("planner", "generator", "executor", "evaluator")

    @classmethod
    def build(cls, task: str) -> str:
        """构建专业 Prompt。"""
        prompt = f"任务: {task}\n\n要求:\n"
        prompt += "1. 使用专业、精准的语气\n"
        prompt += "2. 避免模板化、流水线式的表述\n"
        prompt += "3. 突出产品的核心卖点\n\n"

        for product, points in cls.CORE_SELLING_POINTS.items():
            if product in task:
                prompt += f"核心卖点: {', '.join(points)}\n"

        return prompt

    @classmethod
    def validate_tone(cls, text: str) -> dict[str, float]:
        """验证文案语气。"""
        factory_count = sum(1 for word in cls.FACTORY_WORDS if word in text)
        professional_count = sum(1 for word in cls.PROFESSIONAL_KEYWORDS if word in text)
        selling_points = 0
        for points in cls.CORE_SELLING_POINTS.values():
            selling_points += sum(1 for point in points if point in text)

        return {
            "factory_score": max(0, 1 - factory_count * 0.5),
            "professional_score": min(1, professional_count * 0.3),
            "selling_points_coverage": selling_points / 5,
            "overall_score": (1 - factory_count * 0.5) + professional_count * 0.3 + selling_points * 0.1,
        }

    @classmethod
    def build_orchestration_plan(
        cls,
        prompt: str,
        *,
        fallback_goal: str | None = None,
    ) -> PromptOrchestrationPlan:
        """
        从 prompt 解析图编排计划。

        支持两种输入：
        1. 结构化 prompt（推荐）：
           - goal: xxx
           - nodes: planner -> generator -> executor -> evaluator
           - retry: evaluator -> generator when decision == 'retry'
           - max_steps: 16
           - max_concurrency: 3
        2. 自然语言 prompt（自动兜底）：
           - 自动抽取目标、节点链和重试策略。
        """
        normalized_prompt = prompt.strip()
        goal = cls._extract_goal(normalized_prompt) or fallback_goal or normalized_prompt
        node_chain = cls._extract_node_chain(normalized_prompt) or list(cls.DEFAULT_NODE_CHAIN)
        max_steps = cls._extract_max_steps(normalized_prompt) or 32
        max_concurrency = cls._extract_max_concurrency(normalized_prompt) or 3

        steps = [OrchestrationStep(node_id=node, node_type=node) for node in node_chain]
        edges = [
            OrchestrationEdge(source=node_chain[idx], target=node_chain[idx + 1])
            for idx in range(len(node_chain) - 1)
        ]

        retry_edge = cls._extract_retry_edge(normalized_prompt, node_chain)
        if retry_edge is not None:
            edges.append(retry_edge)

        return PromptOrchestrationPlan(
            goal=goal,
            steps=steps,
            edges=edges,
            max_steps=max_steps,
            max_concurrency=max_concurrency,
            metadata={"source": "prompt_builder", "prompt": normalized_prompt},
        )

    @classmethod
    def _extract_goal(cls, prompt: str) -> str | None:
        goal_match = re.search(r"(?im)^\s*(?:goal|目标|任务)\s*[:：]\s*(.+)$", prompt)
        if goal_match:
            return goal_match.group(1).strip()
        return None

    @classmethod
    def _extract_node_chain(cls, prompt: str) -> list[str] | None:
        explicit_nodes_match = re.search(r"(?im)^\s*(?:nodes|流程|编排)\s*[:：]\s*(.+)$", prompt)
        candidate = explicit_nodes_match.group(1).strip() if explicit_nodes_match else prompt

        chain_match = re.search(
            r"(?i)(planner|plan|规划|计划|generator|generate|生成|executor|execute|执行|evaluator|evaluate|评估|评价)"
            r"(?:\s*->\s*(planner|plan|规划|计划|generator|generate|生成|executor|execute|执行|evaluator|evaluate|评估|评价))+",
            candidate,
        )

        tokens: list[str] = []
        if chain_match:
            raw_chain = chain_match.group(0)
            raw_tokens = [part.strip() for part in raw_chain.split("->")]
            tokens = [cls._normalize_node_name(token) for token in raw_tokens]
        else:
            raw_tokens = re.findall(
                r"(?i)planner|plan|规划|计划|generator|generate|生成|executor|execute|执行|evaluator|evaluate|评估|评价",
                candidate,
            )
            tokens = [cls._normalize_node_name(token) for token in raw_tokens]

        deduped: list[str] = []
        for token in tokens:
            if token and token not in deduped:
                deduped.append(token)

        return deduped or None

    @classmethod
    def _extract_max_steps(cls, prompt: str) -> int | None:
        step_match = re.search(r"(?im)^\s*(?:max_steps|最大步数)\s*[:：=]\s*(\d+)\s*$", prompt)
        if not step_match:
            return None

        value = int(step_match.group(1))
        return max(1, min(value, 256))

    @classmethod
    def _extract_max_concurrency(cls, prompt: str) -> int | None:
        concurrency_match = re.search(
            r"(?im)^\s*(?:max_concurrency|最大并发)\s*[:：=]\s*(\d+)\s*$",
            prompt,
        )
        if not concurrency_match:
            return None

        value = int(concurrency_match.group(1))
        return max(1, min(value, 32))

    @classmethod
    def _extract_retry_edge(
        cls,
        prompt: str,
        node_chain: list[str],
    ) -> OrchestrationEdge | None:
        if "evaluator" not in node_chain or "generator" not in node_chain:
            return None

        retry_match = re.search(
            r"(?im)^\s*retry\s*[:：]\s*(.+?)(?:\s+when\s+(.+))?\s*$",
            prompt,
        )
        if retry_match:
            route_expr = retry_match.group(1)
            condition_expr = retry_match.group(2) or "decision == 'retry'"
            source, target = cls._parse_edge_route(route_expr)
            if source and target:
                return OrchestrationEdge(source=source, target=target, condition=condition_expr.strip())

        if re.search(r"(?i)\bretry\b|重试|失败回滚|失败重跑", prompt):
            return OrchestrationEdge(
                source="evaluator",
                target="generator",
                condition="decision == 'retry'",
            )

        return None

    @classmethod
    def _parse_edge_route(cls, route_expr: str) -> tuple[str | None, str | None]:
        parts = [segment.strip() for segment in route_expr.split("->")]
        if len(parts) != 2:
            return None, None

        source = cls._normalize_node_name(parts[0])
        target = cls._normalize_node_name(parts[1])
        if not source or not target:
            return None, None
        return source, target

    @classmethod
    def _normalize_node_name(cls, token: str) -> str | None:
        return cls.NODE_ALIASES.get(token.strip().lower())

# 测试
if __name__ == "__main__":
    builder = PromptBuilder()
    
    # 构建Prompt
    prompt = builder.build("推销玛露6g罐装遮瑕膏")
    print("生成的Prompt:")
    print(prompt)
    
    # 验证语气
    test_text = """
    玛露6g罐装遮瑕膏，专业级遮瑕效果，持妆12小时不脱妆。
    免调色设计，一抹成型，精准遮盖瑕疵。
    """
    score = builder.validate_tone(test_text)
    print("\n语气评分:")
    print(f"  工厂化程度: {score['factory_score']:.2f}")
    print(f"  专业度: {score['professional_score']:.2f}")
    print(f"  卖点覆盖率: {score['selling_points_coverage']:.2f}")
    print(f"  综合评分: {score['overall_score']:.2f}")
    
    assert score["factory_score"] >= 0.8
    assert score["overall_score"] >= 1.0
    print("\n✅ 玛露业务验收测试通过")
