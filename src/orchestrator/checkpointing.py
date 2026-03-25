import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class NodeState(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_USER = "waiting_user"  # HITL等待状态

class GraphCheckpointManager:
    """图节点级断点续传管理器"""
    
    def __init__(self, db_path: str = "data/checkpoints.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_state TEXT NOT NULL,
                    node_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_id ON checkpoints(graph_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node_id ON checkpoints(node_id)")
    
    async def save_checkpoint(self, graph_id: str, node_id: str, 
                             state: NodeState, data: Optional[Dict[str, Any]] = None) -> str:
        """保存节点检查点"""
        import uuid
        checkpoint_id = str(uuid.uuid4())
        
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO checkpoints 
                       (checkpoint_id, graph_id, node_id, node_state, node_data, updated_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (checkpoint_id, graph_id, node_id, state.value, 
                     json.dumps(data) if data else None)
                )
        
        return checkpoint_id
    
    async def load_checkpoint(self, graph_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """加载节点检查点"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT node_state, node_data, updated_at 
                   FROM checkpoints 
                   WHERE graph_id = ? AND node_id = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (graph_id, node_id)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "state": NodeState(row[0]),
                    "data": json.loads(row[1]) if row[1] else None,
                    "timestamp": row[2]
                }
            return None
    
    async def get_latest_checkpoint(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """获取图的最新检查点"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT node_id, node_state, node_data, updated_at
                   FROM checkpoints
                   WHERE graph_id = ? AND node_state = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (graph_id, NodeState.RUNNING.value)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "node_id": row[0],
                    "state": NodeState(row[1]),
                    "data": json.loads(row[2]) if row[2] else None,
                    "timestamp": row[3]
                }
            return None
    
    async def resume_from_checkpoint(self, graph_id: str) -> Optional[str]:
        """从检查点恢复执行"""
        checkpoint = await self.get_latest_checkpoint(graph_id)
        if checkpoint:
            # 返回中断的节点ID
            return checkpoint["node_id"]
        return None
    
    async def clear_checkpoints(self, graph_id: str):
        """清除检查点（任务完成后）"""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM checkpoints WHERE graph_id = ?",
                    (graph_id,)
                )

# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        cm = GraphCheckpointManager()
        
        # 保存检查点
        checkpoint_id = await cm.save_checkpoint(
            "graph_123", "node_planner", 
            NodeState.RUNNING, {"progress": 50}
        )
        print(f"✅ 保存检查点: {checkpoint_id}")
        
        # 加载检查点
        checkpoint = await cm.load_checkpoint("graph_123", "node_planner")
        print(f"✅ 加载检查点: {checkpoint}")
        
        # 获取最新检查点
        latest = await cm.get_latest_checkpoint("graph_123")
        print(f"✅ 最新检查点: {latest}")
    
    asyncio.run(test())
