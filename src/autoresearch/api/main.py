from __future__ import annotations

import logging
import os
from typing import Any

import logging
logger = logging.getLogger(__name__)

from fastapi import FastAPI

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
from autoresearch.api.webauthn_interceptor import demo_router  # WebAuthn 演示页面

# Telegram Webhook 处理器
try:
    from gateway.telegram_webhook import router as telegram_blitz_router
except ImportError:
    telegram_blitz_router = None

logger = logging.getLogger(__name__)


app = FastAPI(
    title="autoresearch API",
    version=__version__,
    description=(
        "API-first orchestration layer for evaluation, reporting, variant generation, "
        "optimization, and experiment management."
    ),
)

app.include_router(evaluations.router)
app.include_router(admin.router)
app.include_router(gateway_telegram.router)
app.include_router(generators.router)
app.include_router(executors.router)
app.include_router(synthesis.router)
app.include_router(loops.router)
app.include_router(orchestration.router)
app.include_router(openclaw.router)
app.include_router(panel.router)
app.include_router(integrations.router)
app.include_router(reports.router)
app.include_router(variants.router)
app.include_router(optimizations.router)
app.include_router(experiments.router)
app.include_router(streaming.router)
app.include_router(webauthn.router)  # WebAuthn 生物识别认证
app.include_router(demo_router)  # WebAuthn 演示页面
app.include_router(cluster.router)  # Cluster 管理

# Bridge API（系统健康状态 + Blitz Router）
try:
    from bridge import blitz_router, health_router

    app.include_router(health_router, tags=["bridge"])
    app.include_router(blitz_router, tags=["blitz"])
    logger.info("Bridge API integrated (/api/v1/system/health, /api/v1/blitz)")
except Exception as exc:
    logger.warning("Bridge API integration skipped: %s", exc)


@app.get("/", tags=["meta"])
def read_root() -> dict[str, Any]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "docs_url": app.docs_url,
    }


@app.get("/healthz", tags=["meta"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", tags=["meta"])
def healthcheck_legacy() -> dict[str, str]:
    """Legacy alias preserved for old clients and examples."""
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    host = os.getenv("AUTORESEARCH_API_HOST", "127.0.0.1")
    allow_unsafe_bind = _env_bool("AUTORESEARCH_API_ALLOW_UNSAFE_BIND", default=False)
    assert_safe_bind_host(host=host, allow_unsafe=allow_unsafe_bind)
    port = int(os.getenv("AUTORESEARCH_API_PORT", "8000"))
    uvicorn.run("autoresearch.api.main:app", host=host, port=port, reload=False)

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
