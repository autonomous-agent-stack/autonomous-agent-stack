from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI

# 初始化日志（必须在最前面）
logger = logging.getLogger(__name__)

from autoresearch import __version__
from autoresearch.core.services.panel_access import assert_safe_bind_host
from autoresearch.api.routers import (
    admin,
    evaluations,
    executors,
    experiments,
    gateway_telegram,
    generators,
    integrations,
    knowledge_graph,
    loops,
    orchestration,
    optimizations,
    openclaw,
    panel,
    reports,
    streaming,
    synthesis,
    variants,
    webauthn,  # WebAuthn 生物识别认证
    cluster,  # Cluster 管理
)

# ... 其他代码保持不变 ...

# ========================================================================
# Bridge API（系统健康状态 + Blitz Router）
# ========================================================================

try:
    from bridge import system_router, blitz_router
    app.include_router(system_router, tags=["bridge"])
    app.include_router(blitz_router, tags=["blitz"])
    logger.info("✅ Bridge API 已集成（/api/v1/system/health, /api/v1/blitz）")
except Exception as e:
    logger.warning(f"⚠️ Bridge API 集成失败: {e}")
