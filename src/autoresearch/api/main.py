from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from autoresearch import __version__
from autoresearch.api.settings import get_runtime_settings
from autoresearch.core.services.panel_access import assert_safe_bind_host


_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_PANEL_NOT_READY_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Panel Not Built</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 24px; line-height: 1.5; }
      code { background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }
      .box { border: 1px solid #d1d5db; border-radius: 12px; padding: 16px; max-width: 800px; }
      h1 { margin-top: 0; }
      ul { padding-left: 20px; }
      a { color: #2563eb; }
    </style>
  </head>
  <body>
    <div class="box">
      <h1>/panel is not built yet</h1>
      <p>The API is running, but static panel assets were not found.</p>
      <p>You can use these pages right now:</p>
      <ul>
        <li><a href="/api/v1/admin/view">Admin View</a></li>
        <li><a href="/docs">Swagger API Docs</a></li>
        <li><a href="/health">Health Check</a></li>
      </ul>
    </div>
  </body>
</html>
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_runtime_settings()
    assert_safe_bind_host(host=settings.api_host, allow_unsafe=settings.api_allow_unsafe_bind)
    logger.info("Autonomous Agent Stack %s startup initialized", __version__)
    yield
    logger.info("Autonomous Agent Stack shutdown complete")


def _include_router(
    app: FastAPI,
    *,
    module_path: str,
    attribute: str = "router",
    required: bool = True,
    message: str | None = None,
) -> None:
    try:
        module = import_module(module_path)
        router = getattr(module, attribute)
        app.include_router(router)
        logger.info("Mounted %s", message or f"{module_path}:{attribute}")
    except Exception as exc:
        if required:
            logger.exception("Failed to mount required router %s", module_path)
            raise
        logger.warning("Skipped optional router %s: %s", module_path, exc)


def _include_bridge_routers(app: FastAPI) -> None:
    try:
        from bridge import blitz_router, system_router

        app.include_router(system_router, tags=["bridge"])
        app.include_router(blitz_router, tags=["blitz"])
        logger.info("Mounted bridge routers")
    except Exception as exc:
        logger.warning("Skipped optional bridge routers: %s", exc)


def _mount_panel_surface(app: FastAPI) -> None:
    panel_static_dir = get_runtime_settings().panel_static_dir
    if panel_static_dir.exists():
        app.mount("/panel", StaticFiles(directory=str(panel_static_dir), html=True), name="panel")
        logger.info("Mounted static panel assets from %s", panel_static_dir)
        return

    @app.get("/panel", include_in_schema=False, response_class=HTMLResponse)
    async def panel_not_ready() -> HTMLResponse:
        return HTMLResponse(_PANEL_NOT_READY_HTML, status_code=200)

    @app.get("/panel/", include_in_schema=False, response_class=HTMLResponse)
    async def panel_not_ready_with_slash() -> HTMLResponse:
        return HTMLResponse(_PANEL_NOT_READY_HTML, status_code=200)

    logger.warning("Static panel assets not found at %s", panel_static_dir)


def create_app() -> FastAPI:
    settings = get_runtime_settings()
    app = FastAPI(
        title="Autonomous Agent Stack",
        version=__version__,
        description="Unified API entrypoint for Telegram, OpenClaw compatibility, and panel control.",
        lifespan=lifespan,
    )

    required_routers = [
        ("autoresearch.api.routers.evaluations", "router", "evaluations"),
        ("autoresearch.api.routers.generators", "router", "generators"),
        ("autoresearch.api.routers.executors", "router", "executors"),
        ("autoresearch.api.routers.synthesis", "router", "synthesis"),
        ("autoresearch.api.routers.loops", "router", "loops"),
        ("autoresearch.api.routers.orchestration", "router", "orchestration"),
        ("autoresearch.api.routers.openclaw", "router", "openclaw"),
        ("autoresearch.api.routers.panel", "router", "panel api"),
        ("autoresearch.api.routers.capabilities", "router", "capabilities"),
        ("autoresearch.api.routers.approvals", "router", "approvals"),
        ("autoresearch.api.routers.gateway_telegram", "router", "telegram gateway"),
        ("autoresearch.api.routers.integrations", "router", "integrations"),
        ("autoresearch.api.routers.reports", "router", "reports"),
        ("autoresearch.api.routers.variants", "router", "variants"),
        ("autoresearch.api.routers.optimizations", "router", "optimizations"),
        ("autoresearch.api.routers.experiments", "router", "experiments"),
        ("autoresearch.api.routers.streaming", "router", "streaming"),
        ("autoresearch.api.routers.knowledge_graph", "router", "knowledge graph"),
    ]
    for module_path, attribute, message in required_routers:
        _include_router(app, module_path=module_path, attribute=attribute, required=True, message=message)

    if settings.enable_admin:
        _include_router(
            app,
            module_path="autoresearch.api.routers.admin",
            attribute="router",
            required=True,
            message="admin",
        )

    if settings.enable_webauthn:
        _include_router(
            app,
            module_path="autoresearch.api.routers.webauthn",
            attribute="router",
            required=True,
            message="webauthn",
        )
        _include_router(
            app,
            module_path="autoresearch.api.webauthn_interceptor",
            attribute="demo_router",
            required=False,
            message="webauthn demo",
        )

    if settings.enable_legacy_telegram_webhook:
        _include_router(
            app,
            module_path="autoresearch.api.routers.gateway_telegram",
            attribute="compat_router",
            required=True,
            message="legacy telegram compat",
        )

    if settings.enable_cluster:
        _include_router(
            app,
            module_path="autoresearch.api.routers.cluster",
            attribute="router",
            required=True,
            message="cluster",
        )

    _include_bridge_routers(app)
    _mount_panel_surface(app)

    @app.get("/", tags=["meta"])
    async def read_root() -> dict[str, Any]:
        return {
            "name": app.title,
            "version": app.version,
            "status": "ok",
            "docs_url": app.docs_url,
        }

    @app.get("/health", tags=["meta"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/healthz", tags=["meta"])
    async def healthcheck_alias() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_runtime_settings()
    uvicorn.run("autoresearch.api.main:app", host=settings.api_host, port=settings.api_port, reload=False)


if __name__ == "__main__":
    run()
