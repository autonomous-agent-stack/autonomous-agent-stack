from __future__ import annotations

import logging
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Ensure `src/` is importable no matter whether app is launched as
# `autoresearch.api.main:app` or `src.autoresearch.api.main:app`.
_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PANEL_OUT_DIR = _REPO_ROOT / "panel" / "out"

# ========================================================================
# 1. 核心日志配置 (前置初始化)
# ========================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================================================
# 2. 生命周期与 App 初始化
# ========================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌐 Autonomous Agent Stack v1.2.0 启动序列初始化...")
    yield
    logger.info("🛑 服务正在安全关闭...")

app = FastAPI(
    title="Autonomous Agent Stack",
    version="1.2.0-autonomous-genesis",
    lifespan=lifespan
)

# ========================================================================
# 3. 核心 API 路由挂载 (Bridge + Blitz)
# ========================================================================
try:
    # 绝对路径导入，避免包冲突
    from bridge import system_router, blitz_router
    app.include_router(system_router, tags=["system_health"])
    app.include_router(blitz_router, tags=["blitz_core"])
    logger.info("✅ Bridge API 已集成 (/api/v1/system/health, /api/v1/blitz)")
except Exception as e:
    logger.error(f"⚠️ Bridge API 集成失败，请检查导入路径: {e}")

try:
    from autoresearch.api.routers.integrations import router as integrations_router

    app.include_router(integrations_router)
    logger.info("✅ Self-Integration API 已集成 (/api/v1/integrations/*)")
except Exception as e:
    logger.error(f"⚠️ Self-Integration API 集成失败: {e}")

try:
    from autoresearch.api.routers.evaluations import router as evaluations_router

    app.include_router(evaluations_router)
    logger.info("✅ Evaluations API 已集成 (/api/v1/evaluations/*)")
except Exception as e:
    logger.error(f"⚠️ Evaluations API 集成失败: {e}")

try:
    from autoresearch.api.routers.openclaw import router as openclaw_router

    app.include_router(openclaw_router)
    logger.info("✅ OpenClaw API 已集成 (/api/v1/openclaw/*)")
except Exception as e:
    logger.error(f"⚠️ OpenClaw API 集成失败: {e}")

try:
    from autoresearch.api.routers.admin import router as admin_router

    app.include_router(admin_router)
    logger.info("✅ Admin API 已集成 (/api/v1/admin/*)")
except Exception as e:
    logger.error(f"⚠️ Admin API 集成失败: {e}")

# ========================================================================
# 4.5. Telegram Webhook 挂载（优先新网关，兼容旧路由）
# ========================================================================
try:
    from autoresearch.api.routers.gateway_telegram import router as telegram_gateway_router

    app.include_router(telegram_gateway_router)
    logger.info("✅ Telegram Gateway 已集成 (/api/v1/gateway/telegram/*)")
except Exception as e:
    logger.error(f"⚠️ Telegram Gateway 集成失败: {e}")

try:
    # 兼容历史路径 /telegram/webhook
    from gateway.telegram_webhook import router as legacy_telegram_router

    app.include_router(legacy_telegram_router, tags=["telegram_webhook_legacy"])
    logger.info("✅ Legacy Telegram Webhook 已集成 (/telegram/webhook)")
except Exception as e:
    logger.warning(f"⚠️ Legacy Telegram Webhook 挂载跳过: {e}")

# ========================================================================
# 4. 视觉看板挂载 (Dashboard)
# ========================================================================
if _PANEL_OUT_DIR.exists():
    app.mount("/panel", StaticFiles(directory=str(_PANEL_OUT_DIR), html=True), name="panel")
    logger.info("✅ 视觉看板已成功挂载至 /panel")
else:
    logger.warning(f"⚠️ 视觉看板挂载跳过 (目录未就绪): {_PANEL_OUT_DIR}")

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
      <p>Expected directory: <code>panel/out</code></p>
      <p>You can use these pages right now:</p>
      <ul>
        <li><a href="/api/v1/admin/view">Admin View</a></li>
        <li><a href="/docs">Swagger API Docs</a></li>
        <li><a href="/health">Health Check</a></li>
      </ul>
      <p>If you plan to serve a static panel, build/export it to <code>panel/out</code> first.</p>
    </div>
  </body>
</html>
"""

    @app.get("/panel", include_in_schema=False, response_class=HTMLResponse)
    async def panel_not_ready() -> HTMLResponse:
        return HTMLResponse(_PANEL_NOT_READY_HTML, status_code=200)

    @app.get("/panel/", include_in_schema=False, response_class=HTMLResponse)
    async def panel_not_ready_with_slash() -> HTMLResponse:
        return HTMLResponse(_PANEL_NOT_READY_HTML, status_code=200)

# ========================================================================
# 5. 健康检查端点
# ========================================================================
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "1.2.0-autonomous-genesis"}

@app.get("/")
async def root():
    """根端点"""
    return {
        "name": "Autonomous Agent Stack",
        "version": "1.2.0-autonomous-genesis",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "blitz": "/api/v1/blitz/status",
        "panel": "/panel"
    }

# ========================================================================
# 6. 守护进程启动
# ========================================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 正在拉起 P4 级别执行节点...")
    uvicorn.run("autoresearch.api.main:app", host="127.0.0.1", port=8001, reload=False)
