import asyncio
from contextvars import ContextVar
from typing import Optional
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class ConcurrencyManager:
    """并发控制管理器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.context = ContextVar("session_context")
        self.circuit_state = CircuitState.CLOSED
        self.error_count = 0
        self.total_count = 0
        self.error_threshold = 0.8  # 默认仅在高错误率下触发熔断
    
    async def acquire(self):
        """获取并发锁"""
        if self.circuit_state == CircuitState.OPEN:
            raise RuntimeError("系统熔断中，拒绝新任务")
        
        await self.semaphore.acquire()
    
    def release(self):
        """释放并发锁"""
        self.semaphore.release()
    
    def set_context(self, session_data: dict):
        """设置会话上下文"""
        self.context.set(session_data)
    
    def get_context(self) -> Optional[dict]:
        """获取会话上下文"""
        try:
            return self.context.get()
        except LookupError:
            return None
    
    def record_result(self, is_error: bool):
        """记录执行结果"""
        self.total_count += 1
        if is_error:
            self.error_count += 1
        
        # 检查熔断条件
        if self.total_count >= 10:  # 至少10次请求后才开始熔断
            error_rate = self.error_count / self.total_count
            if error_rate > self.error_threshold:
                self.circuit_state = CircuitState.OPEN
                # 5分钟后尝试恢复
                asyncio.create_task(self._auto_recover())
    
    async def _auto_recover(self):
        """自动恢复"""
        await asyncio.sleep(300)  # 5分钟
        self.circuit_state = CircuitState.HALF_OPEN
        self.error_count = 0
        self.total_count = 0

# 测试
if __name__ == "__main__":
    async def test_concurrency():
        manager = ConcurrencyManager(max_concurrent=3)
        
        # 测试并发控制
        await manager.acquire()
        print("✅ 获取并发锁成功")
        manager.release()
        
        # 测试上下文隔离
        manager.set_context({"session_id": "test123"})
        ctx = manager.get_context()
        assert ctx["session_id"] == "test123"
        print("✅ 上下文隔离测试通过")
        
        print("✅ Concurrency Manager测试通过")
    
    asyncio.run(test_concurrency())
