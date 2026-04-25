from __future__ import annotations

from fastapi import APIRouter

from autoresearch.api.routers.admin._approvals import register_approval_routes
from autoresearch.api.routers.admin._config import register_config_routes
from autoresearch.api.routers.admin._skills import register_skill_routes
from autoresearch.api.routers.admin._ui import register_ui_routes


router = APIRouter(prefix="/api/v1/admin", tags=["admin-config"])


@router.get("/health")
def admin_health() -> dict[str, str]:
    return {"status": "ok"}


# Register all sub-routes
register_skill_routes(router)
register_approval_routes(router)
register_config_routes(router)
register_ui_routes(router)
