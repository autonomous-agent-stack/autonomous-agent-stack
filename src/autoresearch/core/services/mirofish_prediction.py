from __future__ import annotations

from typing import Iterable

from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    MiroFishPredictionRead,
    MiroFishPredictionRequest,
    utc_now,
)


class MiroFishPredictionService:
    """
    Lightweight MiroFish-style sidecar predictor.
    Used as a fail-fast gate before expensive execution.
    """

    def __init__(self, engine: str = "mirofish_heuristic_v1") -> None:
        self.engine = engine

    def evaluate(self, request: MiroFishPredictionRequest) -> MiroFishPredictionRead:
        prompt = request.prompt
        lowered = prompt.lower()
        score = 0.72
        reasons: list[str] = []

        length = len(prompt)
        if length > 3000:
            score -= 0.20
            reasons.append("prompt is very long; execution drift risk increases")
        elif length > 1500:
            score -= 0.10
            reasons.append("prompt length is high; token and ambiguity risk")

        risky_keywords = (
            "rm -rf",
            "drop table",
            "sudo ",
            "disable security",
            "bypass",
            "kill -9",
        )
        risk_hits = self._hits(lowered, risky_keywords)
        if risk_hits:
            score -= min(0.45, 0.12 * len(risk_hits))
            reasons.append(f"risky keywords detected: {', '.join(risk_hits)}")

        stable_keywords = (
            "test",
            "retry",
            "refactor",
            "documentation",
            "analyze",
            "summarize",
        )
        stable_hits = self._hits(lowered, stable_keywords)
        if stable_hits:
            score += min(0.12, 0.03 * len(stable_hits))
            reasons.append(f"stable intent signals: {', '.join(stable_hits)}")

        score = max(0.0, min(1.0, round(score, 4)))
        if score >= 0.65:
            decision = "allow"
        elif score >= 0.40:
            decision = "review"
        else:
            decision = "reject"

        metadata = dict(request.metadata)
        metadata.update(
            {
                "prompt_length": length,
                "risk_hits": risk_hits,
                "stable_hits": stable_hits,
            }
        )
        return MiroFishPredictionRead(
            engine=self.engine,
            score=score,
            decision=decision,
            reasons=reasons,
            created_at=utc_now(),
            metadata=metadata,
        )

    def evaluate_agent_request(self, request: ClaudeAgentCreateRequest) -> MiroFishPredictionRead:
        return self.evaluate(
            MiroFishPredictionRequest(
                task_name=request.task_name,
                prompt=request.prompt,
                metadata=request.metadata,
            )
        )

    def _hits(self, text: str, keywords: Iterable[str]) -> list[str]:
        return [keyword for keyword in keywords if keyword in text]
