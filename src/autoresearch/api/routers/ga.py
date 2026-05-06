from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from autoresearch.ga.certification import AdapterCertificationRegistry
from autoresearch.ga.contracts import GAStatusRead, ReleaseGateReportRead
from autoresearch.core.services.release_gate import ReleaseGateService


router = APIRouter(prefix="/api/v2/ga", tags=["evergreen-ga"])

_REPO_ROOT = Path(__file__).resolve().parents[4]


@router.get("/adapters", response_model=list[GAStatusRead])
def list_adapter_certification() -> list[GAStatusRead]:
    registry = AdapterCertificationRegistry(_REPO_ROOT / "configs/certification/adapters.yaml")
    return registry.list_statuses()


@router.get("/release-gate", response_model=ReleaseGateReportRead)
def get_release_gate() -> ReleaseGateReportRead:
    return ReleaseGateService(repo_root=_REPO_ROOT).run()

