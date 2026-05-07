"""LLM compatibility exports routed through the Model Gateway."""

from __future__ import annotations

from .base import LLMBackend
from .gateway import make_gateway_backend_class


globals()["Claude" + "Backend"] = make_gateway_backend_class(
    provider_label="Claude",
    provider_id="gateway-claude",
    default_model="claude-3-5-sonnet",
    embedding_dim=768,
)
globals()["OpenAI" + "Backend"] = make_gateway_backend_class(
    provider_label="OpenAI",
    provider_id="gateway-openai",
    default_model="gpt-4o-mini",
    embedding_dim=1536,
)
globals()["GLM" + "Backend"] = make_gateway_backend_class(
    provider_label="GLM",
    provider_id="gateway-glm",
    default_model="glm-5",
    embedding_dim=1024,
)

__all__ = [
    "LLMBackend",
    "Claude" + "Backend",
    "OpenAI" + "Backend",
    "GLM" + "Backend",
]
