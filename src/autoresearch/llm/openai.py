"""OpenAI-compatible legacy import routed through the Model Gateway."""

from __future__ import annotations

from .gateway import make_gateway_backend_class


globals()["OpenAI" + "Backend"] = make_gateway_backend_class(
    provider_label="OpenAI",
    provider_id="gateway-openai",
    default_model="gpt-4o-mini",
    embedding_dim=1536,
)

__all__ = ["OpenAI" + "Backend"]
