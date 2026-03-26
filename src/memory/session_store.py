"""Session Store - 连贯对话记忆管理

基于 SQLite 的会话存储，支持滑动上下文窗口
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


class SessionStore:
    """会话存储管理器"""
    
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = Path(db_path)
        self.max_tokens = 128000  # 上下文窗口大小
        self._init_db()
        
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # 消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    async def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """创建新会话"""
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, metadata) VALUES (?, ?, ?)",
            (session_id, user_id, json.dumps(metadata or {}))
        )
        
        conn.commit()
        conn.close()
        
        return session_id
        
    async def save_history(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: Optional[int] = None
    ):
        """保存对话历史"""
        if tokens is None:
            # 简单估算：平均每 4 个字符 = 1 token
            tokens = len(content) // 4
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, tokens) VALUES (?, ?, ?, ?)",
            (session_id, role, content, tokens)
        )
        
        # 更新会话时间
        cursor.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,)
        )
        
        conn.commit()
        conn.close()
        
    async def load_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """加载上下文（滑动窗口）"""
        max_tokens = max_tokens or self.max_tokens
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有消息
        cursor.execute(
            "SELECT role, content, tokens FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        
        messages = []
        total_tokens = 0
        
        for row in cursor.fetchall():
            role, content, tokens = row
            
            # 滑动窗口：如果超过最大 token 数，移除最早的消息
            if total_tokens + tokens > max_tokens and messages:
                messages.pop(0)
                total_tokens -= messages[0].get("tokens", 0) if messages else 0
                
            messages.append({
                "role": role,
                "content": content,
                "tokens": tokens
            })
            total_tokens += tokens
            
        conn.close()
        
        return messages
        
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT session_id, user_id, created_at, updated_at, metadata FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "session_id": row[0],
                "user_id": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "metadata": json.loads(row[4]) if row[4] else {}
            }
        return None
        
    async def clear_session(self, session_id: str):
        """清空会话历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()


# 单例实例
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取会话存储单例"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
