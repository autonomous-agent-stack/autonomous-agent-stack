from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RouteDecision:
    engine: str
    complexity_score: float
    estimated_tokens: int
    estimated_cost_usd: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "complexity_score": round(self.complexity_score, 3),
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "reason": self.reason,
        }


class HeterogeneousComputeRouter:
    """Route tasks to different engines based on complexity and budget.

    Goal:
    - High reasoning tasks -> claude/codex tier
    - Lightweight transform tasks -> glm tier
    """

    HIGH_COMPLEXITY_HINTS = {
        "架构", "architecture", "protocol", "设计", "设计方案", "rollback", "canary",
        "拓扑", "orchestr", "分布式", "安全审计", "refactor", "compiler",
    }
    LOW_COMPLEXITY_HINTS = {
        "清洗", "clean", "csv", "json", "提取", "格式化", "normalize", "去重", "统计", "汇总",
        "rename", "lint", "small fix", "简单",
    }

    # Rough relative costs per 1K tokens
    COST_PER_1K = {
        "glm": 0.0008,
        "claude": 0.0120,
        "codex": 0.0140,
    }

    SUPPORTED_ENGINES = {"glm", "claude", "codex"}

    def estimate_tokens(self, prompt: str) -> int:
        text = prompt.strip()
        if not text:
            return 1
        # Hybrid estimate: CJK ~2 chars/token, English ~4 chars/token.
        cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        latin_chars = len(text) - cjk_chars
        estimated = (cjk_chars // 2) + (latin_chars // 4)
        return max(1, estimated)

    def score_complexity(self, prompt: str, node_hint: str | None = None) -> float:
        text = prompt.strip().lower()
        if not text:
            return 0.1

        tokens = max(1, self.estimate_tokens(text))
        score = min(1.5, tokens / 600.0)

        high_hits = sum(1 for kw in self.HIGH_COMPLEXITY_HINTS if kw in text)
        low_hits = sum(1 for kw in self.LOW_COMPLEXITY_HINTS if kw in text)

        score += high_hits * 0.45
        score -= low_hits * 0.35

        if node_hint:
            hint = node_hint.lower()
            if hint in {"planner", "architect", "security", "evaluator"}:
                score += 0.5
            elif hint in {"etl", "cleaner", "formatter", "preprocess"}:
                score -= 0.4

        return max(0.05, min(score, 3.0))

    def route(
        self,
        *,
        prompt: str,
        node_hint: str | None = None,
        preferred_engine: str | None = None,
        budget_tier: str = "balanced",  # balanced | cost_saver | performance_first
    ) -> RouteDecision:
        tokens = self.estimate_tokens(prompt)
        complexity = self.score_complexity(prompt, node_hint=node_hint)

        normalized_budget = (budget_tier or "balanced").strip().lower()

        if preferred_engine:
            preferred = preferred_engine.strip().lower()
            if preferred in self.SUPPORTED_ENGINES:
                cost = self.COST_PER_1K[preferred] * (tokens / 1000.0)
                return RouteDecision(
                    engine=preferred,
                    complexity_score=complexity,
                    estimated_tokens=tokens,
                    estimated_cost_usd=cost,
                    reason=f"forced by preferred_engine={preferred}",
                )

        if complexity >= 2.2:
            engine = "codex"
            reason = "very high complexity"
        elif complexity >= 1.2:
            engine = "claude"
            reason = "medium/high reasoning complexity"
        else:
            engine = "glm"
            reason = "lightweight transform task"

        if normalized_budget == "cost_saver" and engine in {"claude", "codex"} and complexity < 2.5:
            engine = "glm"
            reason = f"downgraded by budget_tier={normalized_budget}"
        elif normalized_budget == "performance_first" and engine == "glm" and complexity >= 0.8:
            engine = "claude"
            reason = f"upgraded by budget_tier={normalized_budget}"

        cost = self.COST_PER_1K[engine] * (tokens / 1000.0)
        return RouteDecision(
            engine=engine,
            complexity_score=complexity,
            estimated_tokens=tokens,
            estimated_cost_usd=cost,
            reason=reason,
        )
