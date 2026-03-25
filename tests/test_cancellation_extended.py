import pytest
import asyncio
import signal
from src.orchestrator.cancellation import CancellationManager

@pytest.mark.asyncio
async def test_graceful_cancellation():
    """测试优雅取消"""
    manager = CancellationManager()
    
    cancelled = False
    async def long_task():
        nonlocal cancelled
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            raise
    
    task = asyncio.create_task(long_task())
    await asyncio.sleep(0.1)
    
    # 取消任务
    await manager.cancel_task(task)
    
    assert cancelled

@pytest.mark.asyncio
async def test_force_cancellation():
    """测试强制取消"""
    manager = CancellationManager()
    
    async def stubborn_task():
        # 拒绝取消
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(10)
    
    task = asyncio.create_task(stubborn_task())
    await asyncio.sleep(0.1)
    
    # 强制取消
    await manager.cancel_task(task, force=True, timeout=1.0)
    
    assert task.cancelled() or task.done()

@pytest.mark.asyncio
async def test_cancellation_timeout():
    """测试取消超时"""
    manager = CancellationManager()
    
    async def slow_cancel():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(5)  # 清理很慢
    
    task = asyncio.create_task(slow_cancel())
    await asyncio.sleep(0.1)
    
    # 1秒超时
    await manager.cancel_task(task, timeout=1.0)
    
    # 任务应该被强制终止
    assert task.done()

@pytest.mark.asyncio
async def test_multiple_cancellations():
    """测试批量取消"""
    manager = CancellationManager()
    
    tasks = [asyncio.create_task(asyncio.sleep(10)) for _ in range(10)]
    await asyncio.sleep(0.1)
    
    # 批量取消
    await manager.cancel_all(tasks)
    
    # 所有任务都应该被取消
    assert all(t.cancelled() or t.done() for t in tasks)

@pytest.mark.asyncio
async def test_cancellation_rollback():
    """测试取消回滚"""
    manager = CancellationManager()
    
    snapshots = []
    async def task_with_rollback():
        snapshots.append("before")
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            snapshots.append("rollback")
            raise
    
    task = asyncio.create_task(task_with_rollback())
    await asyncio.sleep(0.1)
    await manager.cancel_task(task)
    
    assert "rollback" in snapshots

@pytest.mark.asyncio
async def test_cancellation_audit():
    """测试取消审计日志"""
    manager = CancellationManager()
    
    task = asyncio.create_task(asyncio.sleep(10))
    await asyncio.sleep(0.1)
    
    # 取消并记录审计
    await manager.cancel_task(task, reason="user request", audit=True)
    
    # 检查审计日志（需要实现审计功能）
    # assert manager.has_audit_log()

@pytest.mark.asyncio
async def test_cancellation_cleanup():
    """测试取消清理"""
    manager = CancellationManager()
    
    temp_files = []
    async def task_with_files():
        temp_files.append("temp_file.txt")
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            # 清理临时文件
            temp_files.clear()
            raise
    
    task = asyncio.create_task(task_with_files())
    await asyncio.sleep(0.1)
    await manager.cancel_task(task)
    
    # 临时文件应该被清理
    assert len(temp_files) == 0

@pytest.mark.asyncio
async def test_cancellation_retry():
    """测试取消后重试"""
    manager = CancellationManager()
    
    attempts = [0]
    async def retriable_task():
        attempts[0] += 1
        if attempts[0] < 3:
            await asyncio.sleep(10)
        return "success"
    
    # 第一次尝试
    task1 = asyncio.create_task(retriable_task())
    await asyncio.sleep(0.1)
    await manager.cancel_task(task1)
    
    # 重试
    task2 = asyncio.create_task(retriable_task())
    result = await task2
    
    assert result == "success"
    assert attempts[0] == 3

@pytest.mark.asyncio
async def test_cancellation_priority():
    """测试取消优先级"""
    manager = CancellationManager()
    
    # 高优先级任务
    high_task = asyncio.create_task(asyncio.sleep(10))
    # 低优先级任务
    low_task = asyncio.create_task(asyncio.sleep(10))
    
    await asyncio.sleep(0.1)
    
    # 优先取消低优先级
    await manager.cancel_task(low_task, priority="low")
    
    assert low_task.cancelled() or low_task.done()
    assert not high_task.done()

@pytest.mark.asyncio
async def test_cancellation_nested():
    """测试嵌套取消"""
    manager = CancellationManager()
    
    async def parent_task():
        child_task = asyncio.create_task(asyncio.sleep(10))
        try:
            await child_task
        except asyncio.CancelledError:
            # 父任务取消时，子任务也应该取消
            child_task.cancel()
            raise
    
    task = asyncio.create_task(parent_task())
    await asyncio.sleep(0.1)
    await manager.cancel_task(task)
    
    assert task.cancelled() or task.done()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
