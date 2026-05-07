"""Structured Claude execution adapter routed through the Model Gateway."""

from __future__ import annotations

import json
import logging

from autoresearch.llm.gateway import create_gateway_backend

logger = logging.getLogger(__name__)


class ClaudeAPIAdapter:
    """Async execution adapter with Model Gateway and Secret Vault boundaries."""

    def __init__(self) -> None:
        self.model = "claude-3-5-sonnet"
        self.client = create_gateway_backend(provider="claude", model=self.model)

    async def execute(self, prompt: str, require_json: bool = False) -> str:
        logger.info("[API Executor] Model Gateway invocation requested (require_json=%s)", require_json)
        system_prompt = (
            "You are a core logic executor inside Autonomous Agent Stack. "
            "Return concise, objective engineering output."
        )
        if require_json:
            system_prompt += " Return only valid JSON."

        try:
            result_text = await self.client.generate(prompt, system=system_prompt, max_tokens=4096)
            if require_json:
                try:
                    json.loads(result_text)
                except json.JSONDecodeError:
                    logger.warning("[API Executor] Gateway output was not JSON.")
                    return json.dumps(
                        {"status": "error", "message": "Failed to parse JSON output", "raw": result_text}
                    )
            return result_text
        except TimeoutError:
            logger.error("[API Executor] Model Gateway timeout.")
            return json.dumps({"status": "error", "message": "Execution timeout limit reached."})
        except Exception as exc:
            logger.error("[API Executor] Model Gateway error: %s", exc)
            return json.dumps({"status": "error", "message": str(exc)})
