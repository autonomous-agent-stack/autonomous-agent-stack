"""P4 自我进化协议：人类审批流模块

功能：
1. 生成测试报告
2. 推送到 Telegram
3. 等待人类审批
4. 处理审批结果
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ApprovalDecision:
    """审批决策"""
    approved: bool
    approver_id: str
    timestamp: datetime
    comment: Optional[str] = None


class HITLApproval:
    """人类审批流模块"""
    
    def __init__(
        self,
        admin_chat_id: str,
        telegram_bot_token: str,
    ):
        self.admin_chat_id = admin_chat_id
        self.telegram_bot_token = telegram_bot_token
        self._updates_offset: int | None = None
        self._auto_approve_without_telegram = os.getenv(
            "HITL_AUTO_APPROVE_WITHOUT_TELEGRAM", "1"
        ).strip().lower() in {"1", "true", "yes", "on"}
    
    async def request_approval(
        self,
        adapter: Any,
        timeout_hours: int = 24,
    ) -> ApprovalDecision:
        """请求人类审批
        
        Args:
            adapter: 适配器
            timeout_hours: 超时时间（小时）
            
        Returns:
            ApprovalDecision
        """
        logger.info(f"📋 请求审批: {adapter.id}")
        
        # 1. 生成测试报告
        report = self._generate_test_report(adapter)
        
        # 2. 推送到 Telegram
        message_id = await self._send_telegram_message(
            chat_id=self.admin_chat_id,
            text=report,
            buttons=[
                {"text": "✅ 同意接入", "callback_data": f"approve:{adapter.id}"},
                {"text": "❌ 拒绝", "callback_data": f"reject:{adapter.id}"},
            ],
        )
        
        # 3. 等待审批
        decision = await self._wait_for_approval(
            message_id=message_id,
            timeout=timedelta(hours=timeout_hours),
        )
        
        logger.info(f"✅ 审批完成: {decision.approved}")
        return decision
    
    def _generate_test_report(self, adapter: Any) -> str:
        """生成测试报告"""
        return f"""
🤖 新适配器待审批

📦 项目：{adapter.spec.name}
✅ 测试通过率：{adapter.test_result.success_rate:.2%}
⏱️ 执行时间：{adapter.test_result.duration}s
🐛 错误数：{len(adapter.test_result.errors)}

点击按钮审批：
"""
    
    async def _send_telegram_message(
        self,
        chat_id: str,
        text: str,
        buttons: List[Dict[str, str]],
    ) -> str:
        """发送 Telegram 消息"""
        logger.info(f"📤 发送 Telegram 消息: {chat_id}")

        if not self.telegram_bot_token.strip():
            logger.warning("⚠️ Telegram Token 未配置，返回模拟消息 ID")
            return f"mock_{int(datetime.utcnow().timestamp())}"

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": button["text"],
                        "callback_data": button["callback_data"],
                    }
                ]
                for button in buttons
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
        }
        endpoint = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise ValueError(f"Telegram API error: {data}")
            result = data.get("result") or {}
            return str(result.get("message_id", f"msg_{int(datetime.utcnow().timestamp())}"))
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            logger.error("❌ Telegram 消息发送失败: %s", exc)
            return f"mock_{int(datetime.utcnow().timestamp())}"
    
    async def _wait_for_approval(
        self,
        message_id: str,
        timeout: timedelta,
    ) -> ApprovalDecision:
        """等待审批"""
        logger.info(f"⏳ 等待审批: {message_id}")

        if message_id.startswith("mock_"):
            approved = self._auto_approve_without_telegram
            comment = (
                "自动批准（无 Telegram 配置）"
                if approved
                else "自动拒绝（无 Telegram 配置）"
            )
            return ApprovalDecision(
                approved=approved,
                approver_id="system",
                timestamp=datetime.utcnow(),
                comment=comment,
            )

        deadline = datetime.utcnow() + timeout
        while datetime.utcnow() < deadline:
            decision = await self._poll_for_callback(message_id)
            if decision is not None:
                return decision
            await asyncio.sleep(2)

        return ApprovalDecision(
            approved=False,
            approver_id="timeout",
            timestamp=datetime.utcnow(),
            comment=f"审批超时: {timeout}",
        )

    async def _poll_for_callback(self, message_id: str) -> ApprovalDecision | None:
        if not self.telegram_bot_token.strip():
            return None

        endpoint = f"https://api.telegram.org/bot{self.telegram_bot_token}/getUpdates"
        params: Dict[str, Any] = {"timeout": 5}
        if self._updates_offset is not None:
            params["offset"] = self._updates_offset

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            logger.warning("⚠️ 轮询 Telegram updates 失败: %s", exc)
            return None

        if not data.get("ok"):
            return None

        updates = data.get("result") or []
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._updates_offset = update_id + 1

            callback_query = update.get("callback_query") or {}
            callback_message = callback_query.get("message") or {}
            callback_data = str(callback_query.get("data", ""))
            callback_message_id = str(callback_message.get("message_id", ""))
            if callback_message_id != str(message_id):
                continue

            from_user = callback_query.get("from") or {}
            approver_id = str(from_user.get("id", "unknown"))
            if callback_data.startswith("approve:"):
                return ApprovalDecision(
                    approved=True,
                    approver_id=approver_id,
                    timestamp=datetime.utcnow(),
                    comment=callback_data,
                )
            if callback_data.startswith("reject:"):
                return ApprovalDecision(
                    approved=False,
                    approver_id=approver_id,
                    timestamp=datetime.utcnow(),
                    comment=callback_data,
                )

        return None


# 全局实例（需要配置）
hitl_approval = None


def init_hitl_approval(
    admin_chat_id: str,
    telegram_bot_token: str,
) -> HITLApproval:
    """初始化人类审批流"""
    global hitl_approval
    hitl_approval = HITLApproval(
        admin_chat_id=admin_chat_id,
        telegram_bot_token=telegram_bot_token,
    )
    return hitl_approval


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    from dataclasses import dataclass
    
    @dataclass
    class MockAdapter:
        id: str
        spec: Any
        test_result: Any
    
    @dataclass
    class MockSpec:
        name: str
    
    @dataclass
    class MockTestResult:
        success_rate: float
        duration: float
        errors: List[str]
    
    async def test():
        approval = HITLApproval(
            admin_chat_id="123456",
            telegram_bot_token="test_token",
        )
        
        adapter = MockAdapter(
            id="adapter_123",
            spec=MockSpec(name="example-protocol"),
            test_result=MockTestResult(
                success_rate=0.98,
                duration=5.2,
                errors=[],
            ),
        )
        
        decision = await approval.request_approval(adapter)
        
        print(f"审批结果: {decision.approved}")
        print(f"审批人: {decision.approver_id}")
    
    asyncio.run(test())
