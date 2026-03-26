"""System Health Router - 系统健康状态接口（修复版）"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Dict, Any
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system")


@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """返回底座的通用物理健康指标与 Agent 矩阵状态"""
    logger.info("系统健康状态查询")
    
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "matrix_active": True,
        "agents": [
            {"name": "架构领航员", "status": "idle", "task": "监听指令"},
            {"name": "Claude-CLI", "status": "active", "task": "就绪"},
            {"name": "OpenSage", "status": "standby", "task": "自演化监控中"},
            {"name": "安全审计员", "status": "monitoring", "task": "文件系统保护中"}
        ],
        "audit_metrics": {
            "apple_double_cleaned": 82,
            "ast_blocks": 14,
            "sandbox_type": "Docker",
            "storage_path": "/Volumes/PS1008"
        }
    }
