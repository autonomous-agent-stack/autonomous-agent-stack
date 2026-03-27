"""Bridge package - 系统健康状态 + Blitz Router"""

from __future__ import annotations

from .api import BridgeAPI, CredentialsRef
from .router import router as system_router
from .unified_router import router as blitz_router

# Backward-compatible alias for older imports.
health_router = system_router

__all__ = [
    "BridgeAPI",
    "CredentialsRef",
    "system_router",
    "health_router",
    "blitz_router",
]
