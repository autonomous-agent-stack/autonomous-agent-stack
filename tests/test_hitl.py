import pytest
import asyncio
from src.orchestrator.hitl import HITLInterceptor, HITLAction

@pytest.mark.asyncio
async def test_non_sensitive_action():
    """测试非敏感操作"""
    interceptor = HITLInterceptor()
    
    approved = await interceptor.intercept(
        HITLAction.SENSITIVE_OPERATION,
        {"description": "测试"}
    )
    
    assert approved is True

@pytest.mark.asyncio
async def test_sensitive_action_timeout():
    """测试敏感操作超时"""
    interceptor = HITLInterceptor()
    
    # 启动拦截任务
    task = asyncio.create_task(
        interceptor.intercept(
            HITLAction.SEND_API,
            {"description": "发送消息"}
        )
    )
    
    # 等待超时
    await asyncio.sleep(0.5)
    
    # 验证在等待
    assert len(interceptor.pending_approvals) > 0
    
    # 取消任务
    task.cancel()

@pytest.mark.asyncio
async def test_user_approve():
    """测试用户批准"""
    interceptor = HITLInterceptor()
    
    # 启动拦截任务
    async def intercept_task():
        return await interceptor.intercept(
            HITLAction.SEND_API,
            {"description": "发送消息"}
        )
    
    task = asyncio.create_task(intercept_task())
    
    # 等待拦截开始
    await asyncio.sleep(0.1)
    
    # 获取approval_id
    approval_id = list(interceptor.pending_approvals.keys())[0]
    
    # 用户批准
    await interceptor.approve(approval_id)
    
    # 等待结果
    approved = await task
    
    assert approved is True

@pytest.mark.asyncio
async def test_user_reject():
    """测试用户拒绝"""
    interceptor = HITLInterceptor()
    
    # 启动拦截任务
    async def intercept_task():
        return await interceptor.intercept(
            HITLAction.SEND_API,
            {"description": "发送消息"}
        )
    
    task = asyncio.create_task(intercept_task())
    
    # 等待拦截开始
    await asyncio.sleep(0.1)
    
    # 获取approval_id
    approval_id = list(interceptor.pending_approvals.keys())[0]
    
    # 用户拒绝
    await interceptor.reject(approval_id)
    
    # 等待结果
    approved = await task
    
    assert approved is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
