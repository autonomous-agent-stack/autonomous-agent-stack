"""
State Machine Bus Tests - 测试状态机事件总线的可靠性
"""

import pytest
import asyncio
import os
import sys
import tempfile
import sqlite3

# 添加 src 到路径
sys.path.insert(0, '/Volumes/PS1008/Github/autonomous-agent-stack/src')


# ========================================================================
# Test 1: 基础发布/消费测试
# ========================================================================

class TestStateMachineBus:
    """测试状态机事件总线"""
    
    @pytest.mark.asyncio
    async def test_publish_task(self):
        """测试发布任务"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        # 使用临时数据库
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布任务
            task_id = await bus.publish("test_topic", {"message": "Hello"})
            
            assert task_id > 0
        
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_consume_task(self):
        """测试消费任务"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布任务
            task_id = await bus.publish("test_topic", {"message": "Test"})
            
            # 消费任务
            task = await bus.consume("test_topic")
            
            assert task is not None
            assert task["task_id"] == task_id
            assert task["topic"] == "test_topic"
            assert task["payload"]["message"] == "Test"
        
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_consume_empty_queue(self):
        """测试消费空队列"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 消费空队列
            task = await bus.consume("empty_topic")
            
            assert task is None
        
        finally:
            os.unlink(db_path)


# ========================================================================
# Test 2: 状态流转测试
# ========================================================================

class TestStateTransitions:
    """测试状态流转"""
    
    @pytest.mark.asyncio
    async def test_mark_completed(self):
        """测试标记完成"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布并消费任务
            task_id = await bus.publish("test", {"data": "test"})
            task = await bus.consume("test")
            
            # 标记完成
            await bus.mark_completed(task["task_id"])
            
            # 验证状态
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM task_queue WHERE id = ?", (task_id,))
                status = cursor.fetchone()[0]
                
                assert status == "COMPLETED"
        
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_mark_failed_retry(self):
        """测试失败重试（3 次）"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布并消费任务
            task_id = await bus.publish("test", {"data": "test"})
            task = await bus.consume("test")
            
            # 模拟失败 3 次
            for i in range(3):
                await bus.mark_failed(task["task_id"], max_retries=3)
                
                # 验证重试次数
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT retry_count, status FROM task_queue WHERE id = ?", (task_id,))
                    retry_count, status = cursor.fetchone()
                    
                    if i < 2:
                        # 前 2 次应该退回 PENDING
                        assert status == "PENDING"
                        assert retry_count == i + 1
                    else:
                        # 第 3 次应该进入 FAILED
                        assert status == "FAILED"
                        assert retry_count == 3
        
        finally:
            os.unlink(db_path)


# ========================================================================
# Test 3: 并发争抢测试
# ========================================================================

class TestConcurrency:
    """测试并发争抢"""
    
    @pytest.mark.asyncio
    async def test_concurrent_consume(self):
        """测试并发消费（只有一个能成功）"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布一个任务
            task_id = await bus.publish("test", {"data": "test"})
            
            # 并发消费（模拟 3 个 Agent 同时抢）
            async def consume_agent(agent_id: int):
                task = await bus.consume("test")
                if task:
                    await asyncio.sleep(0.1)  # 模拟处理时间
                    await bus.mark_completed(task["task_id"])
                    return agent_id
                return None
            
            # 并发执行
            results = await asyncio.gather(
                consume_agent(1),
                consume_agent(2),
                consume_agent(3),
            )
            
            # 只有一个 Agent 能成功
            successful_agents = [r for r in results if r is not None]
            assert len(successful_agents) == 1
        
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_sequential_consume(self):
        """测试顺序消费（先进先出）"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布 3 个任务
            task_ids = []
            for i in range(3):
                task_id = await bus.publish("test", {"order": i})
                task_ids.append(task_id)
            
            # 顺序消费
            consumed_order = []
            for i in range(3):
                task = await bus.consume("test")
                if task:
                    consumed_order.append(task["payload"]["order"])
                    await bus.mark_completed(task["task_id"])
            
            # 验证顺序
            assert consumed_order == [0, 1, 2]
        
        finally:
            os.unlink(db_path)


# ========================================================================
# Test 4: 持久化测试
# ========================================================================

class TestPersistence:
    """测试持久化"""
    
    @pytest.mark.asyncio
    async def test_persistence_after_restart(self):
        """测试重启后数据不丢失"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            # 创建第一个实例
            bus1 = StateMachineBus(db_path)
            
            # 发布任务
            task_id = await bus1.publish("test", {"data": "persistent"})
            
            # 模拟重启（创建新实例）
            bus2 = StateMachineBus(db_path)
            
            # 消费任务（应该能消费到）
            task = await bus2.consume("test")
            
            assert task is not None
            assert task["task_id"] == task_id
            assert task["payload"]["data"] == "persistent"
        
        finally:
            os.unlink(db_path)


# ========================================================================
# Test 5: 统计与清理测试
# ========================================================================

class TestStatsAndCleanup:
    """测试统计与清理"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计信息"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布 5 个任务
            for i in range(5):
                await bus.publish("test", {"data": i})
            
            # 消费 2 个任务
            task1 = await bus.consume("test")
            task2 = await bus.consume("test")
            
            # 完成 1 个，失败 1 个
            await bus.mark_completed(task1["task_id"])
            await bus.mark_failed(task2["task_id"], max_retries=0)  # 立即失败
            
            # 获取统计
            stats = await bus.get_stats()
            
            assert stats["total_tasks"] == 5
            assert stats["pending"] == 3
            assert stats["processing"] == 0
            assert stats["completed"] == 1
            assert stats["failed"] == 1
        
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_get_failed_tasks(self):
        """测试获取失败任务"""
        from autoresearch.core.services.state_machine_bus import StateMachineBus
        
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        
        try:
            bus = StateMachineBus(db_path)
            
            # 发布并失败 3 个任务
            for i in range(3):
                task_id = await bus.publish("test", {"data": i})
                task = await bus.consume("test")
                await bus.mark_failed(task["task_id"], max_retries=0)
            
            # 获取失败任务
            failed_tasks = await bus.get_failed_tasks()
            
            assert len(failed_tasks) == 3
        
        finally:
            os.unlink(db_path)


# ========================================================================
# 运行测试
# ========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
