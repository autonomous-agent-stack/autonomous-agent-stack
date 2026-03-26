"""
WebAuthn 物理验证触发器

提供基于 WebAuthn 的物理验证能力，确保敏感操作需要用户物理在场确认。
"""

import asyncio
import logging
import time
import hashlib
import secrets
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """验证状态"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class VerificationRequest:
    """验证请求"""
    request_id: str
    reason: str
    created_at: datetime
    expires_at: datetime
    status: VerificationStatus = VerificationStatus.PENDING
    verified_at: Optional[datetime] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """验证结果"""
    success: bool
    request_id: str
    status: VerificationStatus
    message: str
    verified_at: Optional[datetime] = None


class WebAuthnTrigger:
    """
    WebAuthn 物理验证触发器
    
    功能：
    - 生成验证请求
    - 等待用户物理确认
    - 管理验证会话
    - 超时处理
    """
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 60
    
    # 活跃的验证请求
    _pending_requests: Dict[str, VerificationRequest] = {}
    
    # 验证回调
    _verification_callback: Optional[Callable] = None
    
    @staticmethod
    async def request_verification(
        reason: str,
        timeout: int = DEFAULT_TIMEOUT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        触发 WebAuthn 物理验证
        
        Args:
            reason: 验证原因
            timeout: 超时时间（秒）
            metadata: 附加元数据
            
        Returns:
            True if verified, False otherwise
        """
        trigger = WebAuthnTrigger()
        return await trigger._execute_verification(reason, timeout, metadata)
    
    @staticmethod
    def set_verification_callback(callback: Callable) -> None:
        """
        设置验证回调函数
        
        Args:
            callback: 异步回调函数，签名: async (request_id: str, reason: str) -> bool
        """
        WebAuthnTrigger._verification_callback = callback
        logger.info("[Agent-Stack-Bridge] WebAuthn verification callback set")
    
    @staticmethod
    def confirm_verification(request_id: str, success: bool = True) -> None:
        """
        确认验证（由外部验证器调用）
        
        Args:
            request_id: 请求 ID
            success: 是否验证成功
        """
        if request_id in WebAuthnTrigger._pending_requests:
            request = WebAuthnTrigger._pending_requests[request_id]
            request.status = VerificationStatus.VERIFIED if success else VerificationStatus.FAILED
            request.verified_at = datetime.now()
            logger.info(
                f"[Agent-Stack-Bridge] WebAuthn verification: "
                f"{request_id} -> {request.status.value}"
            )
    
    @staticmethod
    def cancel_verification(request_id: str) -> None:
        """取消验证"""
        if request_id in WebAuthnTrigger._pending_requests:
            WebAuthnTrigger._pending_requests[request_id].status = VerificationStatus.CANCELLED
            logger.info(f"[Agent-Stack-Bridge] WebAuthn verification cancelled: {request_id}")
    
    @staticmethod
    def get_pending_requests() -> list:
        """获取待处理的验证请求"""
        return [
            {
                "request_id": req.request_id,
                "reason": req.reason,
                "status": req.status.value,
                "created_at": req.created_at.isoformat(),
                "expires_at": req.expires_at.isoformat()
            }
            for req in WebAuthnTrigger._pending_requests.values()
            if req.status == VerificationStatus.PENDING
        ]
    
    async def _execute_verification(
        self,
        reason: str,
        timeout: int,
        metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """执行验证流程"""
        # 生成请求
        request = self._create_request(reason, timeout, metadata)
        WebAuthnTrigger._pending_requests[request.request_id] = request
        
        logger.info(
            f"[Agent-Stack-Bridge] WebAuthn verification requested: "
            f"{request.request_id} - {reason}"
        )
        
        # 触发验证
        try:
            result = await self._wait_for_verification(request, timeout)
            return result.success
        except asyncio.TimeoutError:
            request.status = VerificationStatus.TIMEOUT
            logger.warning(
                f"[Agent-Stack-Bridge] WebAuthn verification timeout: {request.request_id}"
            )
            return False
        finally:
            # 清理过期请求
            self._cleanup_expired_requests()
    
    def _create_request(
        self,
        reason: str,
        timeout: int,
        metadata: Optional[Dict[str, Any]]
    ) -> VerificationRequest:
        """创建验证请求"""
        now = datetime.now()
        request_id = self._generate_request_id()
        
        return VerificationRequest(
            request_id=request_id,
            reason=reason,
            created_at=now,
            expires_at=now + timedelta(seconds=timeout),
            metadata=metadata or {}
        )
    
    def _generate_request_id(self) -> str:
        """生成请求 ID"""
        timestamp = str(time.time()).encode()
        random_bytes = secrets.token_bytes(16)
        return hashlib.sha256(timestamp + random_bytes).hexdigest()[:16]
    
    async def _wait_for_verification(
        self,
        request: VerificationRequest,
        timeout: int
    ) -> VerificationResult:
        """等待验证完成"""
        # 如果有回调，使用回调进行验证
        if WebAuthnTrigger._verification_callback:
            try:
                callback_result = await WebAuthnTrigger._verification_callback(
                    request.request_id,
                    request.reason
                )
                if callback_result:
                    request.status = VerificationStatus.VERIFIED
                    request.verified_at = datetime.now()
                    return VerificationResult(
                        success=True,
                        request_id=request.request_id,
                        status=VerificationStatus.VERIFIED,
                        message="验证成功",
                        verified_at=request.verified_at
                    )
            except Exception as e:
                logger.error(f"[WebAuthnTrigger] 回调执行失败: {e}")
        
        # 轮询等待验证
        start_time = time.time()
        poll_interval = 0.5  # 500ms
        
        while time.time() - start_time < timeout:
            # 检查请求状态
            if request.status == VerificationStatus.VERIFIED:
                return VerificationResult(
                    success=True,
                    request_id=request.request_id,
                    status=VerificationStatus.VERIFIED,
                    message="验证成功",
                    verified_at=request.verified_at
                )
            elif request.status == VerificationStatus.FAILED:
                return VerificationResult(
                    success=False,
                    request_id=request.request_id,
                    status=VerificationStatus.FAILED,
                    message="验证失败"
                )
            elif request.status == VerificationStatus.CANCELLED:
                return VerificationResult(
                    success=False,
                    request_id=request.request_id,
                    status=VerificationStatus.CANCELLED,
                    message="验证已取消"
                )
            
            # 模拟外部验证（演示模式）
            # 在实际部署中，这会被真实的 WebAuthn 流程替代
            if await self._simulate_user_verification(request):
                request.status = VerificationStatus.VERIFIED
                request.verified_at = datetime.now()
                return VerificationResult(
                    success=True,
                    request_id=request.request_id,
                    status=VerificationStatus.VERIFIED,
                    message="验证成功（演示模式）",
                    verified_at=request.verified_at
                )
            
            await asyncio.sleep(poll_interval)
        
        # 超时
        request.status = VerificationStatus.TIMEOUT
        return VerificationResult(
            success=False,
            request_id=request.request_id,
            status=VerificationStatus.TIMEOUT,
            message="验证超时"
        )
    
    async def _simulate_user_verification(self, request: VerificationRequest) -> bool:
        """
        模拟用户验证（演示模式）
        
        在实际部署中，这个方法应该被替换为真实的 WebAuthn 流程：
        1. 生成 challenge
        2. 发送到客户端
        3. 等待客户端响应
        4. 验证签名
        
        当前实现：返回 False，让轮询继续，直到外部调用 confirm_verification
        """
        # 演示模式：不自动验证
        return False
    
    def _cleanup_expired_requests(self) -> None:
        """清理过期请求"""
        now = datetime.now()
        expired_ids = [
            req_id
            for req_id, req in WebAuthnTrigger._pending_requests.items()
            if req.expires_at < now and req.status == VerificationStatus.PENDING
        ]
        
        for req_id in expired_ids:
            WebAuthnTrigger._pending_requests[req_id].status = VerificationStatus.TIMEOUT
            del WebAuthnTrigger._pending_requests[req_id]
        
        if expired_ids:
            logger.debug(f"[WebAuthnTrigger] 清理了 {len(expired_ids)} 个过期请求")


class MockWebAuthnTrigger(WebAuthnTrigger):
    """
    模拟 WebAuthn 触发器（用于测试）
    
    自动批准所有验证请求
    """
    
    _auto_approve: bool = True
    _delay: float = 0.1
    
    @classmethod
    def set_auto_approve(cls, approve: bool) -> None:
        """设置是否自动批准"""
        cls._auto_approve = approve
    
    @classmethod
    def set_delay(cls, delay: float) -> None:
        """设置延迟时间（秒）"""
        cls._delay = delay
    
    async def _simulate_user_verification(self, request: VerificationRequest) -> bool:
        """模拟用户验证"""
        await asyncio.sleep(self._delay)
        return self._auto_approve


if __name__ == "__main__":
    import sys
    
    async def demo():
        """演示 WebAuthn 验证"""
        print("WebAuthn 验证演示")
        print("-" * 40)
        
        # 设置自动验证回调（演示）
        async def auto_verify(request_id: str, reason: str) -> bool:
            print(f"收到验证请求: {request_id}")
            print(f"原因: {reason}")
            print("等待用户确认...")
            await asyncio.sleep(1)  # 模拟用户操作
            print("用户已确认！")
            return True
        
        WebAuthnTrigger.set_verification_callback(auto_verify)
        
        # 请求验证
        result = await WebAuthnTrigger.request_verification(
            reason="敏感操作: 删除生产数据",
            timeout=10
        )
        
        print(f"\n验证结果: {'成功' if result else '失败'}")
    
    asyncio.run(demo())
