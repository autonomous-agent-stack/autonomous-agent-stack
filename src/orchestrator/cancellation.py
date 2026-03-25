import asyncio
from typing import List, Optional
from datetime import datetime

class CancellationManager:
    """任务取消管理器"""
    
    def __init__(self):
        self.audit_log = []
    
    async def cancel_task(self, task: asyncio.Task, force: bool = False, timeout: float = 3.0, 
                          reason: str = "", audit: bool = False, priority: str = "normal"):
        """取消任务"""
        if audit:
            self.audit_log.append({
                "task": task.get_name(),
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })
        
        # 优雅取消
        task.cancel()
        
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            if force:
                # 强制取消（实际上asyncio无法强制杀死任务）
                # 这里只是确保任务被标记为取消
                pass
        except asyncio.CancelledError:
            pass
    
    async def cancel_all(self, tasks: List[asyncio.Task]):
        """批量取消任务"""
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def has_audit_log(self) -> bool:
        """检查是否有审计日志"""
        return len(self.audit_log) > 0
