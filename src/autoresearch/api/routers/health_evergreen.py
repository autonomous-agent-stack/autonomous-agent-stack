from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from autoresearch.core.services.release_gate import ReleaseGateService
from autoresearch.ga.contracts import ReleaseGateReportRead


router = APIRouter(prefix="/api/v2/health", tags=["evergreen-health"])

_REPO_ROOT = Path(__file__).resolve().parents[4]


@router.get("/evergreen", response_model=ReleaseGateReportRead)
def evergreen_health() -> ReleaseGateReportRead:
    return ReleaseGateService(repo_root=_REPO_ROOT).run()

