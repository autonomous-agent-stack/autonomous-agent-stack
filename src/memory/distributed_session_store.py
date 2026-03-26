"""
Distributed Session Store - 分布式会话存储

支持跨节点的会话共享
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
import asyncpg
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """会话对象"""
    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


@dataclass
class Message:
    """消息对象"""
    message_id: int
    session_id: str
    role: str
    content: str
    tokens: int
    created_at: datetime


class DistributedSessionStore:
    """分布式会话存储（PostgreSQL + Redis）"""

    def __init__(
        self,
        pg_url: str = "postgresql://localhost/autoresearch",
        redis_url: str = "redis://localhost:6379/0",
        max_tokens: int = 128000
    ):
        self.pg_url = pg_url
        self.redis_url = redis_url
        self.max_tokens = max_tokens
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """连接数据库"""
        try:
            # PostgreSQL 连接池
            self.pg_pool = await asyncpg.create_pool(self.pg_url, min_size=5, max_size=20)

            # Redis 连接
            self.redis_client = redis.from_url(self.redis_url, encoding="utf-8")

            logger.info("[DistributedStore] ✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"[DistributedStore] ❌ 连接失败: {e}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("[DistributedStore] 🔌 已断开连接")

    async def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """创建新会话"""
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                session_id, user_id, json.dumps(metadata or {})
            )

        # 缓存到 Redis
        await self.redis_client.hset(
            f"session:{session_id}",
            mapping={
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )
        await self.redis_client.expire(f"session:{session_id}", 3600)  # 1 小时过期

        logger.info(f"[DistributedStore] 📝 会话已创建: {session_id}")
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
            tokens = len(content) // 4

        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (session_id, role, content, tokens, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                """,
                session_id, role, content, tokens
            )

            # 更新会话时间
            await conn.execute(
                """
                UPDATE sessions SET updated_at = NOW() WHERE session_id = $1
                """,
                session_id
            )

        # 清除 Redis 缓存
        await self.redis_client.delete(f"context:{session_id}")

        logger.debug(f"[DistributedStore] 💾 历史已保存: {session_id}")

    async def load_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """加载上下文（滑动窗口）"""
        max_tokens = max_tokens or self.max_tokens

        # 尝试从 Redis 读取缓存
        cached = await self.redis_client.get(f"context:{session_id}")
        if cached:
            logger.debug(f"[DistributedStore] 🚀 命中缓存: {session_id}")
            return json.loads(cached)

        # 从 PostgreSQL 读取
        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, tokens, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                """,
                session_id
            )

        messages = []
        total_tokens = 0

        for row in rows:
            tokens = row["tokens"]

            # 滑动窗口：超过最大 token 数时移除最早的消息
            if total_tokens + tokens > max_tokens and messages:
                messages.pop(0)
                total_tokens -= messages[0].get("tokens", 0) if messages else 0

            messages.append({
                "role": row["role"],
                "content": row["content"],
                "tokens": tokens,
                "created_at": row["created_at"].isoformat()
            })
            total_tokens += tokens

        # 缓存到 Redis
        await self.redis_client.setex(
            f"context:{session_id}",
            300,  # 5 分钟过期
            json.dumps(messages)
        )

        logger.debug(f"[DistributedStore] 📖 上下文已加载: {len(messages)} 条消息")
        return messages

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话信息"""
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT session_id, user_id, created_at, updated_at, metadata
                FROM sessions
                WHERE session_id = $1
                """,
                session_id
            )

        if row:
            return Session(
                session_id=row["session_id"],
                user_id=row["user_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
        return None

    async def clear_session(self, session_id: str):
        """清空会话历史"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM messages WHERE session_id = $1",
                session_id
            )

        # 清除 Redis 缓存
        await self.redis_client.delete(f"context:{session_id}")

        logger.info(f"[DistributedStore] 🗑️ 会话已清空: {session_id}")


# 单例实例
_distributed_store: Optional[DistributedSessionStore] = None


def get_distributed_store() -> DistributedSessionStore:
    """获取分布式存储单例"""
    global _distributed_store
    if _distributed_store is None:
        _distributed_store = DistributedSessionStore()
    return _distributed_store
