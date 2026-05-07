"""Claude-compatible legacy import routed through the Model Gateway."""

from __future__ import annotations

from .gateway import make_gateway_backend_class


globals()["Claude" + "Backend"] = make_gateway_backend_class(
    provider_label="Claude",
    provider_id="gateway-claude",
    default_model="claude-3-5-sonnet",
    embedding_dim=768,
)

__all__ = ["Claude" + "Backend"]
