from __future__ import annotations

from typing import Any

from pydantic import Field

from autoresearch.ga.contracts import (
    ModelInvocationRead,
    ModelInvocationRequest,
    PolicyDecisionRead,
    PolicyDecisionValue,
)
from autoresearch.shared.models import StrictModel
from autoresearch.shared.store import create_resource_id


class ModelGatewayDenied(PermissionError):
    pass


class ModelProviderRead(StrictModel):
    provider_id: str
    enabled: bool = False
    models: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelGatewayService:
    """Only allowed entrypoint for model invocations."""

    def __init__(self, providers: list[ModelProviderRead] | None = None) -> None:
        self._providers = {item.provider_id: item for item in providers or []}
        self._invocations: list[ModelInvocationRead] = []

    def list_providers(self) -> list[ModelProviderRead]:
        return sorted(self._providers.values(), key=lambda item: item.provider_id)

    def invoke(
        self,
        request: ModelInvocationRequest,
        *,
        policy_decision: PolicyDecisionRead | None = None,
    ) -> ModelInvocationRead:
        provider = self._providers.get(request.provider_id)
        if provider is None or not provider.enabled:
            raise ModelGatewayDenied(f"unknown or disabled model provider: {request.provider_id}")
        if request.model_id not in provider.models:
            raise ModelGatewayDenied(f"unknown model for provider {request.provider_id}: {request.model_id}")
        if policy_decision is None or policy_decision.decision != PolicyDecisionValue.ALLOW:
            raise ModelGatewayDenied("model invocation requires an allow PolicyDecision")
        invocation = ModelInvocationRead(
            invocation_id=create_resource_id("model_inv"),
            provider_id=request.provider_id,
            model_id=request.model_id,
            status="allowed",
            output="",
            policy_decision_id=policy_decision.decision_id,
            usage={"prompt_chars": len(request.prompt), "completion_chars": 0},
            metadata=dict(request.metadata),
        )
        self._invocations.append(invocation)
        return invocation

    def assert_no_direct_model_access(self, *, env_key: str | None = None) -> None:
        key = str(env_key or "").strip().upper()
        if key.endswith("_API_KEY") or key in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"}:
            raise ModelGatewayDenied("direct model key access is forbidden")

    def list_invocations(self) -> list[ModelInvocationRead]:
        return list(self._invocations)
