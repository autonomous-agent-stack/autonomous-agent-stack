"""Telegram Webhook 处理器 - 无缝透传至 Blitz Router"""

from __future__ import annotations

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


class TelegramUpdate(BaseModel):
    """Telegram Update 模型"""
    update_id: int
    message: Dict[str, Any] = None
    edited_message: Dict[str, Any] = None


class TelegramWebhookResponse(BaseModel):
    """Telegram Webhook 响应"""
    status: str
    message: str
    blitz_task_id: str = None


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(update: TelegramUpdate):
    """Telegram Webhook 入口 - 透传至 Blitz Router
    
    流程：
    1. 接收 Telegram 消息
    2. 提取用户输入和会话信息
    3. 调用 /api/v1/blitz/execute
    4. 返回结果
    """
    try:
        # 提取消息
        message = update.message or update.edited_message
        if not message:
            return TelegramWebhookResponse(
                status="ignored",
                message="No message content"
            )
        
        # 提取用户输入
        text = message.get("text", "")
        if not text:
            return TelegramWebhookResponse(
                status="ignored",
                message="No text content"
            )
        
        # 提取会话信息
        chat_id = message.get("chat", {}).get("id", "unknown")
        user_id = message.get("from", {}).get("id", "unknown")
        session_id = f"telegram_{chat_id}_{user_id}"
        
        logger.info(f"📱 Telegram 消息: {text[:50]}... (session: {session_id})")
        
        # 调用 Blitz Router
        from bridge.unified_router import BlitzTask, run_blitz_task
        from fastapi import BackgroundTasks
        
        # 创建 Blitz 任务
        task = BlitzTask(
            session_id=session_id,
            prompt=text,
            use_claude_cli=True,  # 使用 Claude CLI
            enable_opensage=True,  # 启用 OpenSage
            context_depth=5  # 保留 5 轮对话
        )
        
        # 执行任务（同步）
        import asyncio
        result = await run_blitz_task(task, BackgroundTasks())
        
        logger.info(f"✅ Blitz 任务完成: {session_id}")
        
        # 返回结果
        return TelegramWebhookResponse(
            status="success",
            message="Task executed successfully",
            blitz_task_id=session_id
        )
    
    except Exception as e:
        logger.error(f"❌ Telegram Webhook 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def telegram_health():
    """Telegram API 健康检查"""
    return {"status": "ok", "service": "telegram"}
