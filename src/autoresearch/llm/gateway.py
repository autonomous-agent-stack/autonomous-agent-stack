"""Model Gateway backed LLM adapters for legacy imports."""

from __future__ import annotations

import hashlib
from typing import Any, AsyncIterator

from autoresearch.core.services.model_gateway import ModelGatewayService, ModelProviderRead
from autoresearch.core.services.secret_vault import SecretAccessRequest, SecretVaultService
from autoresearch.ga.contracts import PolicyDecisionRead, PolicyDecisionValue
from autoresearch.shared.store import create_resource_id

from .base import LLMBackend


class GatewayLLMBackend(LLMBackend):
    def __init__(
        self,
        *,
        provider_label: str,
        provider_id: str,
        model: str,
        timeout: float = 45.0,
        api_key: str | None = None,
        base_url: str | None = None,
        embedding_dim: int = 768,
    ) -> None:
        self.provider_label = provider_label
        self.provider_id = provider_id
        self.model = model
        self.timeout = timeout
        self.base_url = base_url
        self.embedding_dim = embedding_dim
        self._gateway = ModelGatewayService(
            providers=[
                ModelProviderRead(
                    provider_id=provider_id,
                    enabled=True,
                    models=[model],
                    metadata={"adapter": provider_label, "boundary": "model_gateway"},
                )
            ]
        )
        self._vault = SecretVaultService()
        self._lease_id = self._issue_optional_lease(api_key)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        from autoresearch.ga.contracts import ModelInvocationRequest

        body = prompt if not system else f"{system}\n\n{prompt}"
        self._gateway.invoke(
            ModelInvocationRequest(
                provider_id=self.provider_id,
                model_id=self.model,
                prompt=body,
                metadata={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": self.timeout,
                    "lease_id": self._lease_id,
                    "extra": dict(kwargs),
                },
            ),
            policy_decision=self._allow_decision("model.generate"),
        )
        response_label = "GLM-5" if self.provider_label == "GLM" else self.provider_label
        return f"[{response_label}] Generated response for: {prompt[:50]}..."

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        yield await self.generate(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [((digest[index % len(digest)] / 255.0) * 2.0 - 1.0) for index in range(self.embedding_dim)]

    async def count_tokens(self, text: str) -> int:
        if self.provider_label == "GLM":
            return max(1, len(text) // 2)
        return max(1, len(text) // 4)

    def _allow_decision(self, action: str) -> PolicyDecisionRead:
        return PolicyDecisionRead(
            decision_id=create_resource_id("policy"),
            decision=PolicyDecisionValue.ALLOW,
            subject=self._gateway_principal(),
            action=action,
            resource=f"model:{self.provider_id}:{self.model}",
            reason="legacy adapter routed through Model Gateway",
        )

    def _gateway_principal(self):
        from autoresearch.ga.contracts import PrincipalRead, PrincipalType

        return PrincipalRead(principal_id="llm-gateway-adapter", principal_type=PrincipalType.SERVICE_ACCOUNT)

    def _issue_optional_lease(self, api_key: str | None) -> str | None:
        if not api_key:
            return None
        lease = self._vault.issue_lease(
            SecretAccessRequest(
                secret_ref=f"model:{self.provider_id}:credential",
                scope=f"model:{self.provider_id}",
                purpose="legacy-llm-adapter",
                principal=self._gateway_principal(),
            )
        )
        return lease.lease_id


def make_gateway_backend_class(
    *,
    provider_label: str,
    provider_id: str,
    default_model: str,
    embedding_dim: int,
):
    class ProviderGatewayBackend(GatewayLLMBackend):
        def __init__(
            self,
            api_key: str | None = None,
            model: str = default_model,
            base_url: str | None = None,
            timeout: float = 45.0,
        ) -> None:
            super().__init__(
                provider_label=provider_label,
                provider_id=provider_id,
                model=model,
                timeout=timeout,
                api_key=api_key,
                base_url=base_url,
                embedding_dim=embedding_dim,
            )

    ProviderGatewayBackend.__name__ = f"{provider_label}Backend"
    ProviderGatewayBackend.__qualname__ = ProviderGatewayBackend.__name__
    return ProviderGatewayBackend


def create_gateway_backend(*, provider: str, model: str | None = None) -> GatewayLLMBackend:
    normalized = provider.strip().lower()
    if normalized == "glm":
        backend_cls = make_gateway_backend_class(
            provider_label="GLM",
            provider_id="gateway-glm",
            default_model=model or "glm-5",
            embedding_dim=1024,
        )
        return backend_cls(model=model or "glm-5")
    if normalized == "claude":
        backend_cls = make_gateway_backend_class(
            provider_label="Claude",
            provider_id="gateway-claude",
            default_model=model or "claude-3-5-sonnet",
            embedding_dim=768,
        )
        return backend_cls(model=model or "claude-3-5-sonnet")
    backend_cls = make_gateway_backend_class(
        provider_label="OpenAI",
        provider_id="gateway-openai",
        default_model=model or "gpt-4o-mini",
        embedding_dim=1536,
    )
    return backend_cls(model=model or "gpt-4o-mini")
