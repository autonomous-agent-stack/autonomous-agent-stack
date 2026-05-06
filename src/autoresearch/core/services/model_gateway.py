from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import Field

from autoresearch.ga.contracts import (
    DesignPromptAuditRead,
    ImageGenerationArtifactRead,
    ImageGenerationRead,
    ImageGenerationRequest,
    ModelPolicyRead,
    ModelInvocationRead,
    ModelInvocationRequest,
    ModelUsageLedgerRead,
    PolicyDecisionRead,
    PolicyDecisionValue,
)
from autoresearch.shared.models import SessionEventCreateRequest, StrictModel
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
        self._usage_ledger: list[ModelUsageLedgerRead] = []
        self._image_artifacts: list[ImageGenerationArtifactRead] = []
        self._design_prompt_audits: list[DesignPromptAuditRead] = []

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

    def generate_image(
        self,
        request: ImageGenerationRequest,
        *,
        policy_decision: PolicyDecisionRead | None = None,
    ) -> ImageGenerationRead:
        policy = request.policy or ModelPolicyRead(
            policy_id=create_resource_id("model_policy"),
            allowed_modalities=["image"],
            metadata={"source": "default-image-policy"},
        )
        if "image" not in policy.allowed_modalities:
            raise ModelGatewayDenied("model policy does not allow image generation")
        if len(request.prompt) > policy.max_prompt_chars:
            raise ModelGatewayDenied("image prompt exceeds model policy limit")
        redacted_prompt, pii_redacted = redact_design_prompt(request.prompt)
        invocation = self.invoke(
            ModelInvocationRequest(
                provider_id=request.provider_id,
                model_id=request.model_id,
                prompt=redacted_prompt,
                principal=request.principal,
                session_id=request.session_id,
                policy_decision_id=request.policy_decision_id,
                metadata={
                    **request.metadata,
                    "modality": "image",
                    "policy_id": policy.policy_id,
                    "pii_redacted": pii_redacted,
                },
            ),
            policy_decision=policy_decision,
        )
        prompt_hash = _sha256(redacted_prompt)
        artifact = ImageGenerationArtifactRead(
            artifact_id=create_resource_id("img_art"),
            invocation_id=invocation.invocation_id,
            session_id=request.session_id,
            uri=f"artifact://model-gateway/images/{invocation.invocation_id}.png",
            prompt_hash=prompt_hash,
            content_hash=_sha256(f"{invocation.invocation_id}:{prompt_hash}"),
            metadata={
                "provider_id": request.provider_id,
                "model_id": request.model_id,
                "dry_run": request.metadata.get("dry_run", True),
            },
        )
        audit = DesignPromptAuditRead(
            audit_id=create_resource_id("design_audit"),
            invocation_id=invocation.invocation_id,
            session_id=request.session_id,
            original_prompt=request.prompt,
            redacted_prompt=redacted_prompt,
            pii_redacted=pii_redacted,
            policy_id=policy.policy_id,
            metadata={"cost_center": policy.cost_center},
        )
        usage = ModelUsageLedgerRead(
            usage_id=create_resource_id("model_usage"),
            invocation_id=invocation.invocation_id,
            provider_id=request.provider_id,
            model_id=request.model_id,
            modality="image",
            session_id=request.session_id,
            policy_id=policy.policy_id,
            cost_units=max(1, len(redacted_prompt) // 200),
            metadata={"cost_center": policy.cost_center, "dry_run": request.metadata.get("dry_run", True)},
        )
        session_event = SessionEventCreateRequest(
            session_id=request.session_id or "model-gateway",
            source="model_gateway",
            event_type="model.image.generated",
            role="status",
            content="governed image generation artifact created",
            payload={
                "invocation_id": invocation.invocation_id,
                "artifact_id": artifact.artifact_id,
                "usage_id": usage.usage_id,
                "audit_id": audit.audit_id,
            },
            artifact_refs=[artifact.model_dump(mode="json")],
            policy_decision_id=policy_decision.decision_id if policy_decision is not None else None,
            idempotency_key=f"model-image:{invocation.invocation_id}",
        ).model_dump(mode="json")
        self._image_artifacts.append(artifact)
        self._design_prompt_audits.append(audit)
        self._usage_ledger.append(usage)
        return ImageGenerationRead(
            invocation=invocation,
            artifact=artifact,
            design_prompt_audit=audit,
            usage_ledger=usage,
            session_event=session_event,
        )

    def assert_no_direct_model_access(self, *, env_key: str | None = None) -> None:
        key = str(env_key or "").strip().upper()
        if key.endswith("_API_KEY") or key in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"}:
            raise ModelGatewayDenied("direct model key access is forbidden")

    def list_invocations(self) -> list[ModelInvocationRead]:
        return list(self._invocations)

    def list_usage_ledger(self) -> list[ModelUsageLedgerRead]:
        return list(self._usage_ledger)

    def list_image_artifacts(self) -> list[ImageGenerationArtifactRead]:
        return list(self._image_artifacts)

    def list_design_prompt_audits(self) -> list[DesignPromptAuditRead]:
        return list(self._design_prompt_audits)


def redact_design_prompt(prompt: str) -> tuple[str, bool]:
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", prompt)
    redacted = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[REDACTED_PHONE]", redacted)
    redacted = re.sub(
        r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr)\b",
        "[REDACTED_ADDRESS]",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted, redacted != prompt


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
