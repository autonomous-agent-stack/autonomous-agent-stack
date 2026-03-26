from __future__ import annotations

import logging
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Ensure `src/` is importable no matter whether app is launched as
# `autoresearch.api.main:app` or `src.autoresearch.api.main:app`.
_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

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
try:
    app.mount("/panel", StaticFiles(directory="panel/out", html=True), name="panel")
    logger.info("✅ 视觉看板已成功挂载至 /panel")
except Exception as e:
    logger.warning(f"⚠️ 视觉看板挂载跳过 (目录未就绪): {e}")

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
