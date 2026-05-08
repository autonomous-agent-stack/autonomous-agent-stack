from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from autoresearch import __version__
from autoresearch.build_label import get_build_label
from autoresearch.api.settings import TelegramIngressMode, get_runtime_settings
from autoresearch.core.services.panel_access import assert_safe_bind_host
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.personal_packages import (
    PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID,
    PERSONAL_STUDY_WORKSPACE_PACKAGE_ID,
)


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
    import asyncio
    import signal

    settings = get_runtime_settings()
    assert_safe_bind_host(host=settings.api_host, allow_unsafe=settings.api_allow_unsafe_bind)
    mode_label = "MINIMAL (stable)" if settings.is_minimal_mode else "FULL (experimental)"
    logger.info(
        "Autonomous Agent Stack startup [build=%s] [package=%s] [mode=%s]",
        get_build_label(),
        __version__,
        mode_label,
    )
    schedule_daemon = None
    shutdown_event = asyncio.Event()

    if settings.enable_worker_schedule_daemon:
        from autoresearch.api.dependencies import get_worker_schedule_service
        from autoresearch.core.services.worker_schedule_service import WorkerScheduleDaemon

        schedule_daemon = WorkerScheduleDaemon(
            service=get_worker_schedule_service(),
            poll_seconds=settings.worker_schedule_poll_seconds,
        )
        await schedule_daemon.start()
        logger.info(
            "Worker schedule daemon started [poll_seconds=%s]",
            settings.worker_schedule_poll_seconds,
        )
    polling_daemon = None
    recovery_daemon = None
    if settings.enable_worker_recovery_daemon:
        from autoresearch.api.dependencies import get_worker_scheduler_service
        from autoresearch.core.services.worker_recovery_service import WorkerRecoveryDaemon

        recovery_daemon = WorkerRecoveryDaemon(
            scheduler=get_worker_scheduler_service(),
            poll_seconds=settings.worker_recovery_poll_seconds,
        )
        await recovery_daemon.start()
        logger.info(
            "Worker recovery daemon started [poll_seconds=%s]",
            settings.worker_recovery_poll_seconds,
        )
    try:
        from autoresearch.api.settings import get_telegram_settings
        tg_settings = get_telegram_settings()
        ingress_mode = tg_settings.ingress_mode
        if ingress_mode == TelegramIngressMode.POLLING and tg_settings.polling_enabled and tg_settings.bot_token:
            from autoresearch.core.services.telegram_polling import TelegramPollingDaemon
            polling_daemon = TelegramPollingDaemon()
            polling_daemon.start()
            logger.info("Telegram polling daemon started [ingress_mode=%s]", ingress_mode.value)
        elif tg_settings.polling_enabled and tg_settings.bot_token and ingress_mode != TelegramIngressMode.POLLING:
            logger.info(
                "Telegram polling daemon skipped [ingress_mode=%s, expected=polling]",
                ingress_mode.value,
            )
    except Exception:
        logger.exception("Failed to start Telegram polling daemon")

    def _handle_shutdown(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, initiating graceful shutdown...", sig_name)
        shutdown_event.set()

    # Register signal handlers for graceful shutdown (may fail in non-main threads)
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _handle_shutdown, sig, None)
    except (ValueError, RuntimeError):
        logger.debug("Signal handlers not registered (non-main thread or unsupported)")

    try:
        yield
    finally:
        logger.info("Lifespan teardown: cleaning up resources...")
        if recovery_daemon is not None:
            await recovery_daemon.stop()
            logger.info("Worker recovery daemon stopped")
        if polling_daemon is not None:
            polling_daemon.stop()
            logger.info("Telegram polling daemon stopped")
        if schedule_daemon is not None:
            await schedule_daemon.stop()
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


def _load_v1_compat_shims() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parents[3] / "configs" / "ga" / "v1_compat_shims.yaml"
    payload = load_yaml_object(path) if path.exists() else {}
    raw_shims = payload.get("compat_shims") if isinstance(payload, dict) else {}
    shims: dict[str, dict[str, str]] = {}
    if not isinstance(raw_shims, dict):
        return shims
    for route, metadata in raw_shims.items():
        if not isinstance(metadata, dict):
            continue
        shims[str(route)] = {
            "successor": str(metadata.get("successor") or ""),
            "owner": str(metadata.get("owner") or ""),
            "sunset_policy": str(metadata.get("sunset_policy") or ""),
        }
    return shims


def _match_v1_compat_shim(path: str, shims: dict[str, dict[str, str]]) -> dict[str, str] | None:
    for route in sorted(shims, key=len, reverse=True):
        if path == route or path.startswith(f"{route}/"):
            return shims[route]
    return None


def _install_v1_compat_middleware(app: FastAPI) -> None:
    shims = _load_v1_compat_shims()

    @app.middleware("http")
    async def v1_compat_metadata(request, call_next):
        shim = _match_v1_compat_shim(request.url.path, shims)
        response = await call_next(request)
        if shim is None:
            return response

        response.headers["x-aas-legacy"] = "true"
        response.headers["x-aas-successor"] = shim["successor"]
        response.headers["x-aas-sunset-policy"] = shim["sunset_policy"]
        response.headers["x-aas-shim-owner"] = shim["owner"]

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        original_headers = dict(response.headers)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=original_headers,
                media_type=response.media_type,
                background=response.background,
            )
        if not isinstance(payload, dict):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=original_headers,
                media_type=response.media_type,
                background=response.background,
            )

        payload.setdefault("legacy", True)
        payload.setdefault("successor", shim["successor"])
        payload.setdefault(
            "compatibility",
            {
                "legacy": True,
                "successor": shim["successor"],
                "owner": shim["owner"],
                "sunset_policy": shim["sunset_policy"],
            },
        )
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response.headers["content-length"] = str(len(encoded))

        return Response(
            content=encoded,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type="application/json",
            background=response.background,
        )


def create_app() -> FastAPI:
    settings = get_runtime_settings()
    is_minimal = settings.is_minimal_mode

    # Core routers required for stable single-machine operation
    core_routers = [
        ("autoresearch.api.routers.control_plane_v2", "console_router", "control plane console"),
        ("autoresearch.api.routers.control_plane_v2", "router", "control plane v2"),
        ("autoresearch.api.routers.butler_governance", "router", "butler governance"),
        ("autoresearch.api.routers.security_audit", "router", "security audit"),
        ("autoresearch.api.routers.governance_core", "router", "governance core"),
        ("autoresearch.api.routers.governance_core", "api_router", "governance core api"),
        ("autoresearch.api.routers.capabilities", "router", "capabilities"),
        ("autoresearch.api.routers.approvals", "router", "approvals"),
        ("autoresearch.api.routers.sessions", "router", "sessions"),
        ("autoresearch.api.routers.usage", "router", "usage"),
        ("autoresearch.api.routers.mcp", "router", "governed mcp"),
        ("autoresearch.api.routers.federation", "router", "federation"),
        ("autoresearch.api.routers.a2a", "router", "a2a"),
        ("autoresearch.api.routers.workers", "router", "workers"),
        ("autoresearch.api.routers.worker_runs", "router", "worker runs"),
        ("autoresearch.api.routers.worker_schedules", "router", "worker schedules"),
        ("autoresearch.api.routers.panel", "router", "panel api"),
        ("autoresearch.api.routers.ga", "router", "evergreen ga"),
        ("autoresearch.api.routers.models", "router", "model gateway"),
        ("autoresearch.api.routers.secrets", "router", "secret vault"),
        ("autoresearch.api.routers.connectors", "router", "connectors"),
        ("autoresearch.api.routers.packages", "router", "packages"),
        ("autoresearch.api.routers.health_evergreen", "router", "evergreen health"),
    ]

    # Optional routers - allowed to fail in minimal mode
    optional_routers = [
        ("autoresearch.api.routers.evaluations", "router", "evaluations"),
        ("autoresearch.api.routers.excel_audit", "router", "excel audit"),
        ("autoresearch.api.routers.excel_ops", "router", "excel ops (requirement #4 scaffold)"),
        ("autoresearch.api.routers.generators", "router", "generators"),
        ("autoresearch.api.routers.executors", "router", "executors"),
        ("autoresearch.api.routers.autoresearch_plans", "router", "autoresearch plans"),
        ("autoresearch.api.routers.manager_agent", "router", "manager agent"),
        ("autoresearch.api.routers.synthesis", "router", "synthesis"),
        ("autoresearch.api.routers.loops", "router", "loops"),
        ("autoresearch.api.routers.orchestration", "router", "orchestration"),
        ("autoresearch.api.routers.runtime", "router", "runtime"),
        ("autoresearch.api.routers.openclaw", "router", "openclaw"),
        ("autoresearch.api.routers.butler", "router", "butler"),
        ("autoresearch.api.routers.github_assistant", "router", "github assistant"),
        ("autoresearch.api.routers.github_ops", "router", "github ops"),
        ("autoresearch.api.routers.github_admin", "router", "github admin"),
        ("autoresearch.api.routers.gateway_telegram", "router", "telegram gateway"),
        ("autoresearch.api.routers.integrations", "router", "integrations"),
        ("autoresearch.api.routers.reports", "router", "reports"),
        ("autoresearch.api.routers.youtube", "router", "youtube"),
        ("autoresearch.api.routers.variants", "router", "variants"),
        ("autoresearch.api.routers.optimizations", "router", "optimizations"),
        ("autoresearch.api.routers.experiments", "router", "experiments"),
        ("autoresearch.api.routers.streaming", "router", "streaming"),
        ("autoresearch.api.routers.knowledge_graph", "router", "knowledge graph"),
        ("autoresearch.api.routers.content_kb", "router", "content kb"),
    ]

    app = FastAPI(
        title="Autonomous Agent Stack",
        version=__version__,
        description="Unified API entrypoint for Telegram, OpenClaw compatibility, and panel control.",
        lifespan=lifespan,
    )
    _install_v1_compat_middleware(app)

    # Mount core routers (always required)
    for module_path, attribute, message in core_routers:
        _include_router(app, module_path=module_path, attribute=attribute, required=True, message=message)

    # Mount optional routers (required in full mode, optional in minimal mode)
    for module_path, attribute, message in optional_routers:
        _include_router(
            app,
            module_path=module_path,
            attribute=attribute,
            required=not is_minimal,
            message=message,
        )

    if is_minimal:
        logger.info("Running in MINIMAL mode - optional routers are non-blocking")

    if settings.enable_admin:
        _include_router(
            app,
            module_path="autoresearch.api.routers.admin",
            attribute="router",
            required=not is_minimal,
            message="admin",
        )

    if settings.enable_webauthn:
        _include_router(
            app,
            module_path="autoresearch.api.routers.webauthn",
            attribute="router",
            required=not is_minimal,
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
            required=not is_minimal,
            message="legacy telegram compat",
        )

    if settings.enable_cluster:
        _include_router(
            app,
            module_path="autoresearch.api.routers.cluster",
            attribute="router",
            required=not is_minimal,
            message="cluster",
        )

    if settings.is_personal_package_enabled(PERSONAL_STUDY_WORKSPACE_PACKAGE_ID):
        _include_router(
            app,
            module_path="autoresearch.api.routers.study_workbench",
            attribute="router",
            required=True,
            message="study workbench personal package",
        )
        _include_router(
            app,
            module_path="autoresearch.api.routers.study_dashboard",
            attribute="router",
            required=True,
            message="study dashboard personal package",
        )
    else:
        logger.info("Study workspace personal package disabled; study routers not mounted")

    if settings.is_personal_package_enabled(PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID):
        _include_router(
            app,
            module_path="autoresearch.api.routers.youtube_oauth",
            attribute="router",
            required=True,
            message="youtube oauth personal package",
        )
    else:
        logger.info("Entertainment curator personal package disabled; YouTube OAuth router not mounted")

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
    async def healthcheck() -> dict[str, Any]:
        from datetime import datetime, timezone

        checks: dict[str, Any] = {}
        overall = "ok"

        # DB reachability
        try:
            import sqlite3

            db_path = str(get_runtime_settings().api_db_path)
            with sqlite3.connect(db_path, timeout=2) as conn:
                conn.execute("SELECT 1")
            checks["db"] = {"status": "ok", "path": db_path}
        except Exception as exc:
            overall = "degraded"
            checks["db"] = {"status": "error", "error": str(exc)}

        # Worker inventory (optional — may not be available in minimal mode)
        inventory = None
        try:
            from autoresearch.api.dependencies import get_worker_inventory_service

            inventory_svc = get_worker_inventory_service()
            inventory = inventory_svc.list_workers()
            summary = inventory_svc.summary()
            checks["workers"] = {
                "status": "ok",
                "total": summary.total_workers,
                "online": summary.online_workers,
                "busy": summary.busy_workers,
                "degraded": summary.degraded_workers,
                "offline": summary.offline_workers,
            }
            active_workers = summary.online_workers + summary.busy_workers
            if active_workers == 0 and summary.total_workers > 0:
                overall = "degraded"
        except Exception:
            checks["workers"] = {"status": "unavailable"}

        try:
            from autoresearch.api.dependencies import get_hermes_gateway_transport
            from autoresearch.core.services.hermes_readiness import (
                build_hermes_interactive_callback_check,
                should_include_hermes_interactive_health,
            )

            runtime_settings = get_runtime_settings()
            hermes_transport = get_hermes_gateway_transport()
            workers = list(inventory.workers) if inventory is not None else []
            if should_include_hermes_interactive_health(hermes_transport=hermes_transport, workers=workers):
                hermes_check = build_hermes_interactive_callback_check(
                    api_db_path=runtime_settings.api_db_path,
                    hermes_transport=hermes_transport,
                    workers=workers,
                    probe_gateway=False,
                )
                checks["hermes_interactive"] = {
                    "status": hermes_check.status,
                    "detail": hermes_check.detail,
                    **hermes_check.metadata,
                }
                if hermes_check.status != "ok":
                    overall = "degraded"
        except Exception as exc:
            checks["hermes_interactive"] = {"status": "unavailable", "error": str(exc)}

        return {
            "status": overall,
            "version": __version__,
            "build": get_build_label(),
            "mode": "minimal" if is_minimal else "full",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/healthz", tags=["meta"])
    async def healthcheck_alias() -> dict[str, Any]:
        return await healthcheck()

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_runtime_settings()
    uvicorn.run(
        "autoresearch.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    run()
