import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

class HITLAction(Enum):
    """HITL操作类型"""
    SEND_API = "send_api"  # 发送API
    CONSUME_TOKEN = "consume_token"  # 消耗Token
    SENSITIVE_OPERATION = "sensitive_operation"  # 敏感操作

class HITLInterceptor:
    """Human-in-the-Loop拦截器"""
    
    def __init__(self, telegram_adapter=None):
        self.telegram_adapter = telegram_adapter
        self.pending_approvals: Dict[str, asyncio.Future] = {}
        self.sensitive_actions = [
            HITLAction.SEND_API,
            HITLAction.CONSUME_TOKEN,
        ]
    
    async def intercept(self, action: HITLAction, context: Dict[str, Any]) -> bool:
        """拦截敏感操作"""
        if action not in self.sensitive_actions:
            # 非敏感操作，直接通过
            return True
        
        # 生成审批ID
        import uuid
        approval_id = str(uuid.uuid4())
        
        # 创建Future等待用户响应
        future = asyncio.Future()
        self.pending_approvals[approval_id] = future
        
        # 发送审批请求到Telegram
        if self.telegram_adapter:
            await self._send_approval_request(approval_id, action, context)
        
        try:
            # 等待用户响应（超时5分钟）
            approved = await asyncio.wait_for(future, timeout=300)
            return approved
        except asyncio.TimeoutError:
            # 超时默认拒绝
            del self.pending_approvals[approval_id]
            return False
    
    async def _send_approval_request(self, approval_id: str, 
                                     action: HITLAction, context: Dict[str, Any]):
        """发送审批请求到Telegram"""
        message = f"""
🔔 **需要审批**

**操作**: {action.value}
**描述**: {context.get('description', '无描述')}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请选择：
/approve_{approval_id[:8]} - 通过
/reject_{approval_id[:8]} - 拒绝
"""
        # 实际实现需要调用Telegram API
        print(f"📤 发送审批请求: {approval_id}")
        print(message)
    
    async def approve(self, approval_id: str):
        """用户批准"""
        if approval_id in self.pending_approvals:
            future = self.pending_approvals[approval_id]
            future.set_result(True)
            del self.pending_approvals[approval_id]
    
    async def reject(self, approval_id: str):
        """用户拒绝"""
        if approval_id in self.pending_approvals:
            future = self.pending_approvals[approval_id]
            future.set_result(False)
            del self.pending_approvals[approval_id]
    
    def is_waiting(self, approval_id: str) -> bool:
        """检查是否在等待审批"""
        return approval_id in self.pending_approvals

# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        interceptor = HITLInterceptor()
        
        # 测试非敏感操作
        approved = await interceptor.intercept(
            HITLAction.SENSITIVE_OPERATION, 
            {"description": "测试操作"}
        )
        print(f"✅ 非敏感操作: {approved}")
        
        # 测试敏感操作（会超时）
        try:
            approved = await asyncio.wait_for(
                interceptor.intercept(
                    HITLAction.SEND_API,
                    {"description": "发送消息"}
                ),
                timeout=2  # 2秒超时
            )
            print(f"✅ 敏感操作: {approved}")
        except asyncio.TimeoutError:
            print("✅ 敏感操作等待超时（预期行为）")
    
    asyncio.run(test())
