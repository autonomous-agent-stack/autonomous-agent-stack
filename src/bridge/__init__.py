"""Bridge package - 系统健康状态 + Blitz Router"""

from __future__ import annotations

from .router import router as health_router
from .unified_router import router as blitz_router

__all__ = ["health_router", "blitz_router"]
