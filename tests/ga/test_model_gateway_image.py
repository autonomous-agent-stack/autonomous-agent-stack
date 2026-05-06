from __future__ import annotations

import pytest

from autoresearch.core.services.model_gateway import ModelGatewayDenied, ModelGatewayService, ModelProviderRead
from autoresearch.ga.contracts import (
    ImageGenerationRequest,
    ModelPolicyRead,
    PolicyDecisionRead,
    PolicyDecisionValue,
    PrincipalRead,
)


def _allow_decision() -> PolicyDecisionRead:
    principal = PrincipalRead(principal_id="designer")
    return PolicyDecisionRead(
        decision_id="pd-image-test",
        decision=PolicyDecisionValue.ALLOW,
        subject=principal,
        action="model.image.generate",
        resource="model://local-dev/image2",
        reason="test",
    )


def test_image_generation_is_governed_and_audited() -> None:
    gateway = ModelGatewayService(
        providers=[ModelProviderRead(provider_id="local-dev", enabled=True, models=["image2"])]
    )
    decision = _allow_decision()

    result = gateway.generate_image(
        ImageGenerationRequest(
            provider_id="local-dev",
            model_id="image2",
            prompt="Render a desk for customer alice@example.com at +1 415 555 1212.",
            session_id="session-image",
            policy_decision_id=decision.decision_id,
            policy=ModelPolicyRead(policy_id="policy-image", allowed_modalities=["image"]),
        ),
        policy_decision=decision,
    )

    assert result.design_prompt_audit.pii_redacted is True
    assert "alice@example.com" not in result.design_prompt_audit.redacted_prompt
    assert result.usage_ledger.modality == "image"
    assert result.session_event["event_type"] == "model.image.generated"
    assert result.session_event["artifact_refs"][0]["artifact_id"] == result.artifact.artifact_id


def test_image_generation_requires_image_policy() -> None:
    gateway = ModelGatewayService(
        providers=[ModelProviderRead(provider_id="local-dev", enabled=True, models=["image2"])]
    )

    with pytest.raises(ModelGatewayDenied):
        gateway.generate_image(
            ImageGenerationRequest(
                provider_id="local-dev",
                model_id="image2",
                prompt="Render a desk.",
                policy=ModelPolicyRead(policy_id="policy-text-only", allowed_modalities=["text"]),
            ),
            policy_decision=_allow_decision(),
        )
