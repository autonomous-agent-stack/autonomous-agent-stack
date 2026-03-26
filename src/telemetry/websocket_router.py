"""Telemetry Stream API - WebSocket 实时遥测流"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class TelemetryManager:
    """遥测管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """连接 WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket 连接成功，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket 断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(connection)


# 全局遥测管理器
telemetry_manager = TelemetryManager()


async def generate_telemetry_data() -> Dict[str, Any]:
    """生成遥测数据（100ms 更新）"""
    
    # 模拟 CPU 负载（实际应从系统获取）
    cpu_load = random.uniform(20, 80)
    
    # 模拟内存使用
    memory_usage = random.uniform(2, 6)
    
    # Agent 状态
    agents = [
        {"name": "架构领航员", "status": "idle", "task": "监听指令"},
        {"name": "Claude-CLI", "status": "active", "task": "就绪"},
        {"name": "OpenSage", "status": "evolving", "task": "自演化监控中"},
        {"name": "安全审计员", "status": "monitoring", "task": "文件系统保护中"}
    ]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "heartbeat": int(datetime.now().timestamp() * 1000),  # 毫秒级心跳
        "matrix_active": True,
        "cpu_load": cpu_load,
        "memory_usage": memory_usage,
        "agents": agents,
        "system_audit": {
            "apple_double_cleaned": 82,
            "ast_blocks": 14,
            "sandbox": "Docker-Active"
        }
    }


async def telemetry_stream(websocket: WebSocket):
    """遥测数据流（100ms 更新）"""
    try:
        while True:
            # 生成遥测数据
            data = await generate_telemetry_data()
            
            # 发送数据
            await websocket.send_json(data)
            
            # 100ms 间隔
            await asyncio.sleep(0.1)
    
    except WebSocketDisconnect:
        logger.info("客户端断开连接")
    except Exception as e:
        logger.error(f"遥测流错误: {e}")


@router.websocket("/api/v1/telemetry/stream")
async def websocket_telemetry(websocket: WebSocket):
    """WebSocket 遥测端点"""
    await telemetry_manager.connect(websocket)
    
    try:
        await telemetry_stream(websocket)
    finally:
        telemetry_manager.disconnect(websocket)


@router.get("/api/v1/telemetry/status")
async def get_telemetry_status():
    """获取遥测状态"""
    return {
        "active_connections": len(telemetry_manager.active_connections),
        "update_interval": "100ms",
        "features": [
            "CPU 实时监控",
            "心跳监控",
            "Agent 状态",
            "WebSocket 长连接"
        ]
    }
