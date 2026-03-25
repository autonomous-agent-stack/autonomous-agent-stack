import pytest
import asyncio
from src.orchestrator.concurrency import ConcurrencyManager, CircuitState

@pytest.mark.asyncio
async def test_semaphore_limit():
    """测试信号量限制"""
    manager = ConcurrencyManager(max_concurrent=3)
    
    active_count = 0
    max_active = 0
    
    async def task():
        nonlocal active_count, max_active
        await manager.acquire()
        active_count += 1
        max_active = max(max_active, active_count)
        await asyncio.sleep(0.1)
        active_count -= 1
        manager.release()
    
    # 启动10个任务
    await asyncio.gather(*[task() for _ in range(10)])
    
    # 最大并发应该是3
    assert max_active == 3

@pytest.mark.asyncio
async def test_circuit_breaker_open():
    """测试熔断器打开"""
    manager = ConcurrencyManager(max_concurrent=3)
    
    # 记录10次错误
    for _ in range(10):
        manager.record_result(is_error=True)
    
    # 熔断器应该打开
    assert manager.circuit_state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_reject():
    """测试熔断器拒绝"""
    manager = ConcurrencyManager(max_concurrent=3)
    
    # 触发熔断
    for _ in range(10):
        manager.record_result(is_error=True)
    
    # 尝试获取锁应该失败
    with pytest.raises(RuntimeError, match="系统熔断中"):
        await manager.acquire()

@pytest.mark.asyncio
async def test_context_isolation():
    """测试上下文隔离"""
    manager = ConcurrencyManager()
    
    # 设置上下文
    manager.set_context({"session_id": "test123", "user": "alice"})
    
    # 获取上下文
    ctx = manager.get_context()
    
    assert ctx["session_id"] == "test123"
    assert ctx["user"] == "alice"

@pytest.mark.asyncio
async def test_context_none():
    """测试空上下文"""
    manager = ConcurrencyManager()
    
    # 未设置上下文
    ctx = manager.get_context()
    
    assert ctx is None

@pytest.mark.asyncio
async def test_context_override():
    """测试上下文覆盖"""
    manager = ConcurrencyManager()
    
    manager.set_context({"id": 1})
    manager.set_context({"id": 2})
    
    ctx = manager.get_context()
    assert ctx["id"] == 2

@pytest.mark.asyncio
async def test_error_rate_calculation():
    """测试错误率计算"""
    manager = ConcurrencyManager()
    
    # 7次错误，3次成功
    for _ in range(7):
        manager.record_result(is_error=True)
    for _ in range(3):
        manager.record_result(is_error=False)
    
    # 错误率应该是70%
    assert manager.total_count == 10
    assert manager.error_count == 7

@pytest.mark.asyncio
async def test_circuit_breaker_threshold():
    """测试熔断阈值"""
    manager = ConcurrencyManager()
    manager.error_threshold = 0.5  # 50%错误率
    
    # 6次错误，4次成功（60%错误率）
    for _ in range(6):
        manager.record_result(is_error=True)
    for _ in range(4):
        manager.record_result(is_error=False)
    
    # 应该触发熔断
    assert manager.circuit_state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_closed():
    """测试熔断器关闭"""
    manager = ConcurrencyManager()
    
    # 3次成功，7次错误（70%错误率，但总数<10）
    for _ in range(3):
        manager.record_result(is_error=False)
    for _ in range(7):
        manager.record_result(is_error=True)
    
    # 不应该熔断（总数<10）
    assert manager.circuit_state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_semaphore_multiple_acquire():
    """测试多次获取信号量"""
    manager = ConcurrencyManager(max_concurrent=3)
    
    # 获取3次
    await manager.acquire()
    await manager.acquire()
    await manager.acquire()
    
    # 第4次应该等待
    task = asyncio.create_task(manager.acquire())
    await asyncio.sleep(0.1)
    
    # 任务应该还在运行
    assert not task.done()
    
    # 清理
    manager.release()
    manager.release()
    manager.release()
    await task
    manager.release()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
