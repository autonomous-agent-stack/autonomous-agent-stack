"""OpenAI LLM Backend - OpenAI API 集成"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, AsyncIterator, List, Optional

import httpx

from .base import LLMBackend


class OpenAIBackend(LLMBackend):
    """OpenAI API 后端.

    支持标准 chat completions、streaming、embeddings。
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        timeout: float = 45.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
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
            return f"[OpenAI] Generated response for: {prompt[:50]}..."

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            data = response.json()
            content = (
                (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
            )
            if isinstance(content, list):
                text_parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ]
                content = "".join(text_parts)
            return str(content).strip() or "[OpenAI] Empty response."
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            return f"[OpenAI][error] {exc}"

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
            yield f"[OpenAI] Streaming: {prompt[:50]}..."
            return

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        choices = event.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        text = delta.get("content")
                        if isinstance(text, str) and text:
                            yield text
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            yield f"[OpenAI][error] {exc}"

    async def embed(self, text: str) -> List[float]:
        """生成文本嵌入向量。"""
        if not self._has_real_key():
            return self._fallback_embedding(text, dim=1536)

        payload = {
            "model": "text-embedding-3-small",
            "input": text,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/embeddings"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            data = response.json()
            embedding = (((data.get("data") or [{}])[0]).get("embedding") or [])
            if isinstance(embedding, list) and embedding:
                return [float(value) for value in embedding]
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            pass
        return self._fallback_embedding(text, dim=1536)

    @staticmethod
    def _fallback_embedding(text: str, dim: int) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(dim)]

    async def count_tokens(self, text: str) -> int:
        """计算 token 数量（粗略估算）。"""
        return len(text) // 4
