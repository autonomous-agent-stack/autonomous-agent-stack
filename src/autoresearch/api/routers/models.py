from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from autoresearch.core.services.model_gateway import (
    ModelGatewayDenied,
    ModelGatewayService,
    ModelProviderRead,
)
from autoresearch.ga.contracts import (
    ModelInvocationRead,
    ModelInvocationRequest,
    PolicyDecisionRead,
    PolicyDecisionValue,
)
from autoresearch.shared.store import create_resource_id


router = APIRouter(prefix="/api/v2/models", tags=["model-gateway"])

_gateway = ModelGatewayService(
    providers=[
        ModelProviderRead(provider_id="local-dev", enabled=True, models=["noop"]),
    ]
)


@router.get("/providers", response_model=list[ModelProviderRead])
def list_model_providers() -> list[ModelProviderRead]:
    return _gateway.list_providers()


@router.post("/invoke", response_model=ModelInvocationRead)
def invoke_model(payload: ModelInvocationRequest) -> ModelInvocationRead:
    try:
        decision = PolicyDecisionRead(
            decision_id=create_resource_id("policy"),
            decision=PolicyDecisionValue.ALLOW,
            subject=payload.principal,
            action="model.invoke",
            resource=f"{payload.provider_id}/{payload.model_id}",
            reason="local-dev model provider is allowlisted for contract smoke only",
        )
        return _gateway.invoke(payload, policy_decision=decision)
    except ModelGatewayDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

