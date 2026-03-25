import sqlite3
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class SessionManager:
    """多用户会话管理器（SQLite并发安全）"""
    
    def __init__(self, db_path: str = "data/sessions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库（WAL模式）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_id ON sessions(chat_id)")
    
    async def create_session(self, chat_id: str, initial_state: Dict[str, Any]) -> str:
        """创建新会话"""
        import uuid
        session_id = str(uuid.uuid4())
        
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO sessions (session_id, chat_id, state) VALUES (?, ?, ?)",
                    (session_id, chat_id, json.dumps(initial_state))
                )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id, chat_id, state FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return {"session_id": row[0], "chat_id": row[1], "state": json.loads(row[2])}
            return None
    
    async def update_session(self, session_id: str, new_state: Dict[str, Any]):
        """更新会话状态"""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE sessions SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (json.dumps(new_state), session_id)
                )
    
    async def list_sessions(self, chat_id: str) -> list:
        """列出用户的所有会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id, state, created_at FROM sessions WHERE chat_id = ?",
                (chat_id,)
            )
            return [
                {"session_id": row[0], "state": json.loads(row[1]), "created_at": row[2]}
                for row in cursor.fetchall()
            ]

if __name__ == "__main__":
    import asyncio
    
    async def test():
        sm = SessionManager()
        
        # 测试创建会话
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        print(f"✅ 创建会话: {session_id}")
        
        # 测试获取会话
        session = await sm.get_session(session_id)
        print(f"✅ 获取会话: {session}")
        
        # 测试更新会话
        await sm.update_session(session_id, {"goal": "updated", "progress": 50})
        print("✅ 更新会话成功")
        
        # 测试列出会话
        sessions = await sm.list_sessions("chat_123")
        print(f"✅ 列出会话: {len(sessions)} 个")
    
    asyncio.run(test())
