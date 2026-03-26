"""
Universal State Machine Bus v2.0
职责：取代脆弱的 Redis Pub/Sub，提供基于 SQLite 的持久化任务队列与状态机。
特性：零外部依赖、严格的事务锁、断电不丢消息、防并发争抢。
"""

import sqlite3
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StateMachineBus:
    """SQLite 持久化状态机事件总线"""
    
    def __init__(self, db_path: str = "data/event_bus.sqlite"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化底层的状态机存储表"""
        import os
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 优化查询性能的索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_status ON task_queue(topic, status)")
            conn.commit()
    
    async def publish(self, topic: str, payload: Dict[str, Any]) -> int:
        """
        发布任务（严格落盘，绝不丢失）
        
        Args:
            topic: 话题名称
            payload: 任务负载
            
        Returns:
            task_id: 任务 ID
        """
        payload_str = json.dumps(payload, ensure_ascii=False)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_queue (topic, payload) VALUES (?, ?)",
                (topic, payload_str)
            )
            conn.commit()
            task_id = cursor.lastrowid
            
            logger.info(f"[EventBus] 任务已持久化发布 -> Topic: {topic} | TaskID: {task_id}")
            return task_id
    
    async def consume(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        消费任务（带排他锁，防止多 Agent 并发争抢）
        
        由于 SQLite 不支持高级行锁，我们通过 UPDATE 状态来实现原子抢占
        
        Args:
            topic: 话题名称
            
        Returns:
            任务字典或 None（无任务或被抢占）
        """
        with sqlite3.connect(self.db_path) as conn:
            # 1. 寻找一个 PENDING 的任务
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, payload, retry_count FROM task_queue 
                WHERE topic = ? AND status = 'PENDING' 
                ORDER BY created_at ASC LIMIT 1
            """, (topic,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            task_id, payload_str, retry_count = row
            
            # 2. 原子性抢占任务，将其状态改为 PROCESSING
            cursor.execute("""
                UPDATE task_queue 
                SET status = 'PROCESSING', updated_at = CURRENT_TIMESTAMP 
                WHERE id = ? AND status = 'PENDING'
            """, (task_id,))
            
            # 如果影响行数为 0，说明被其他 Agent 抢走了
            if cursor.rowcount == 0:
                return None
            
            conn.commit()
            
            logger.info(f"[EventBus] 成功锁定任务进行消费 -> Topic: {topic} | TaskID: {task_id}")
            
            return {
                "task_id": task_id,
                "topic": topic,
                "payload": json.loads(payload_str),
                "retry_count": retry_count
            }
    
    async def mark_completed(self, task_id: int):
        """标记任务成功完成"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,)
            )
            conn.commit()
            logger.info(f"[EventBus] 任务流转完毕 (COMPLETED) | TaskID: {task_id}")
    
    async def mark_failed(self, task_id: int, max_retries: int = 3):
        """
        任务失败处理与死信队列（DLQ）降级
        
        Args:
            task_id: 任务 ID
            max_retries: 最大重试次数（默认 3 次）
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT retry_count FROM task_queue WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                retry_count = row[0]
                
                if retry_count < max_retries:
                    # 允许重试，退回 PENDING 状态
                    cursor.execute("""
                        UPDATE task_queue 
                        SET status = 'PENDING', retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (task_id,))
                    logger.warning(f"[EventBus] 任务执行失败，进入重试队列 ({retry_count+1}/{max_retries}) | TaskID: {task_id}")
                else:
                    # 彻底失败，进入死信状态
                    cursor.execute("""
                        UPDATE task_queue 
                        SET status = 'FAILED', updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (task_id,))
                    logger.error(f"❌ [EventBus] 任务重试耗尽，已转入死信队列 (FAILED) | TaskID: {task_id}")
                
                conn.commit()
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取任务队列统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 统计各状态的任务数
            cursor.execute("""
                SELECT status, COUNT(*) FROM task_queue GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # 统计总任务数
            cursor.execute("SELECT COUNT(*) FROM task_queue")
            total = cursor.fetchone()[0]
            
            return {
                "total_tasks": total,
                "pending": status_counts.get("PENDING", 0),
                "processing": status_counts.get("PROCESSING", 0),
                "completed": status_counts.get("COMPLETED", 0),
                "failed": status_counts.get("FAILED", 0),
            }
    
    async def get_failed_tasks(self, limit: int = 100) -> list[Dict[str, Any]]:
        """获取死信队列中的失败任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, topic, payload, retry_count, created_at, updated_at
                FROM task_queue
                WHERE status = 'FAILED'
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            return [
                {
                    "task_id": row[0],
                    "topic": row[1],
                    "payload": json.loads(row[2]),
                    "retry_count": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                }
                for row in rows
            ]
    
    async def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务（默认 7 天）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM task_queue
                WHERE status IN ('COMPLETED', 'FAILED')
                AND updated_at < datetime('now', ?)
            """, (f"-{days} days",))
            
            deleted = cursor.rowcount
            conn.commit()
            
            if deleted > 0:
                logger.info(f"[EventBus] 清理了 {deleted} 个旧任务（{days} 天前）")
            
            return deleted


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # 创建事件总线
        bus = StateMachineBus("data/test_event_bus.sqlite")
        
        # 测试发布任务
        task_id = await bus.publish("test_topic", {"message": "Hello, World!"})
        print(f"✅ 任务已发布: {task_id}")
        
        # 测试消费任务
        task = await bus.consume("test_topic")
        if task:
            print(f"✅ 任务已消费: {task}")
            
            # 标记完成
            await bus.mark_completed(task["task_id"])
            print(f"✅ 任务已完成: {task['task_id']}")
        
        # 测试失败重试
        task_id2 = await bus.publish("test_retry", {"message": "Retry test"})
        task2 = await bus.consume("test_retry")
        if task2:
            # 模拟失败
            await bus.mark_failed(task2["task_id"], max_retries=3)
            print(f"✅ 任务失败重试: {task2['task_id']}")
        
        # 获取统计信息
        stats = await bus.get_stats()
        print(f"📊 统计信息: {stats}")
    
    asyncio.run(test())
