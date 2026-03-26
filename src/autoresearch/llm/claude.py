"""Claude LLM Backend - Anthropic API 集成"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, AsyncIterator, List, Optional

import httpx

from .base import LLMBackend


class ClaudeBackend(LLMBackend):
    """Claude API 后端.

    使用 Anthropic Messages API 进行文本生成与流式输出。
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: Optional[str] = None,
        timeout: float = 45.0,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.base_url = (base_url or os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        self.timeout = timeout

    def _has_real_key(self) -> bool:
        if not self.api_key:
            return False
        lowered = self.api_key.lower().strip()
        fake_markers = {"test", "test_key", "dummy", "placeholder", "changeme"}
        return lowered not in fake_markers and not lowered.startswith("test_")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        """生成文本响应。"""
        if not self._has_real_key():
            return f"[Claude] Generated response for: {prompt[:50]}..."

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        payload.update(kwargs)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{self.base_url}/v1/messages"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            data = response.json()
            text_chunks = [
                block.get("text", "")
                for block in data.get("content", [])
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "".join(text_chunks).strip()
            return content or "[Claude] Empty response."
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            return f"[Claude][error] {exc}"

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式生成文本响应。"""
        if not self._has_real_key():
            yield f"[Claude] Streaming: {prompt[:50]}..."
            return

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if system:
            payload["system"] = system
        payload.update(kwargs)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{self.base_url}/v1/messages"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if not data_str or data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        event_type = event.get("type")
                        if event_type == "content_block_delta":
                            delta = event.get("delta") or {}
                            text = delta.get("text")
                            if text:
                                yield text
                        elif event_type == "message_stop":
                            break
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            yield f"[Claude][error] {exc}"

    async def embed(self, text: str) -> List[float]:
        """生成文本嵌入向量.

        Claude 目前没有官方嵌入 API。这里返回稳定哈希向量用于降级场景。
        """
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector: list[float] = []
        for i in range(1536):
            value = digest[i % len(digest)]
            vector.append((value / 255.0) * 2.0 - 1.0)
        return vector

    async def count_tokens(self, text: str) -> int:
        """计算 token 数量（粗略估算）."""
        return len(text) // 4
