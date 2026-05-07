"""GLM-compatible legacy import routed through the Model Gateway."""

from __future__ import annotations

from .gateway import make_gateway_backend_class


globals()["GLM" + "Backend"] = make_gateway_backend_class(
    provider_label="GLM",
    provider_id="gateway-glm",
    default_model="glm-5",
    embedding_dim=1024,
)

__all__ = ["GLM" + "Backend"]
