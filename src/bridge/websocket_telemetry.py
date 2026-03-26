"""
WebSocket Telemetry - 实时遥测管道

100ms 频率广播系统遥测数据
"""

import asyncio
import json
import logging
import psutil
from typing import Dict, Any, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """遥测数据收集器"""

    def __init__(self):
        self.agent_status: Dict[str, Dict[str, Any]] = {}
        self.log_buffer: list = []

    def update_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """更新 Agent 状态"""
        self.agent_status[agent_id] = {
            **status,
            "timestamp": datetime.now().isoformat()
        }

    def add_log(self, log: Dict[str, Any]):
        """添加日志"""
        self.log_buffer.append(log)
        # 保留最近 100 条
        if len(self.log_buffer) > 100:
            self.log_buffer.pop(0)

    async def collect(self) -> Dict[str, Any]:
        """收集系统遥测数据"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存使用率
            memory = psutil.virtual_memory()

            # 磁盘使用率
            disk = psutil.disk_usage("/")

            # 网络流量
            network = psutil.net_io_counters()

            # Agent 心跳
            agent_heartbeats = {}
            for agent_id, status in self.agent_status.items():
                agent_heartbeats[agent_id] = {
                    "status": status.get("status", "unknown"),
                    "last_beat": status.get("timestamp"),
                    "tokens_used": status.get("tokens_used", 0)
                }

            telemetry = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": memory.used / (1024 ** 3),
                    "disk_percent": disk.percent,
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv
                },
                "agents": agent_heartbeats,
                "logs": self.log_buffer[-10:]  # 最近 10 条日志
            }

            return telemetry

        except Exception as e:
            logger.error(f"[TelemetryCollector] ❌ 收集失败: {e}")
            return {}


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.collector = TelemetryCollector()
        self._broadcasting = False

    async def connect(self, websocket: WebSocket):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[WebSocket] 📡 新连接，当前连接数: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        logger.info(f"[WebSocket] 🔌 已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast_telemetry(self):
        """广播遥测数据（100ms 频率）"""
        self._broadcasting = True

        while self._broadcasting and self.active_connections:
            try:
                # 收集遥测数据
                telemetry = await self.collector.collect()

                # 广播给所有客户端
                message = json.dumps(telemetry)

                for connection in list(self.active_connections):
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        logger.warning(f"[WebSocket] ⚠️ 发送失败: {e}")
                        await self.disconnect(connection)

                # 100ms 间隔
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WebSocket] ❌ 广播错误: {e}")
                await asyncio.sleep(1)

        logger.info("[WebSocket] 📡 遥测广播已停止")

    def stop_broadcasting(self):
        """停止广播"""
        self._broadcasting = False

    def update_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """更新 Agent 状态"""
        self.collector.update_agent_status(agent_id, status)

    def add_log(self, log: Dict[str, Any]):
        """添加日志"""
        self.collector.add_log(log)


# 单例实例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """获取 WebSocket 管理器单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
