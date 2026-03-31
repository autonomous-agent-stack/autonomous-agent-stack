"""
Legacy Telegram webhook compatibility handler.

This module exists only for backward compatibility with the old
workflow-driven `/telegram/webhook` path. New Telegram integration work
must target `autoresearch.api.routers.gateway_telegram`.
"""

import asyncio
import logging
import os
import re

import httpx
from fastapi import APIRouter, Request

from workflow.workflow_engine import run_workflow

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Legacy Telegram webhook handler.

    Deprecated: keep this path stable for existing callers, but do not
    extend it with new product behavior. The mainline Telegram entrypoint
    lives under `/api/v1/gateway/telegram/webhook`.
    """
    try:
        data = await request.json()

        # 提取消息内容
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        logger.warning(
            "[Legacy Telegram Webhook] compatibility path hit; prefer /api/v1/gateway/telegram/webhook"
        )
        logger.info(f"[Webhook] 收到消息: {text[:50]}...")

        # 指令拦截：GitHub 深度审查
        if "执行审查" in text or "#1" in text:
            logger.info("[Webhook] 拦截到审查指令，启动工作流...")

            # 提取仓库名
            repo_match = re.search(r"执行审查[:\s]+([^\s]+)", text)
            if not repo_match:
                repo_match = re.search(r"#1[:\s]+([^\s]+)", text)

            if repo_match:
                target_repo = repo_match.group(1).strip()

                # 启动工作流（异步执行）
                asyncio.create_task(execute_and_deliver_workflow(target_repo, chat_id))

                return {"status": "workflow_started", "repo": target_repo}
            else:
                return {"status": "error", "message": "未指定仓库"}

        # 其他指令...
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[Webhook] 处理失败: {e}")
        return {"status": "error", "message": str(e)}


async def execute_and_deliver_workflow(target_repo: str, chat_id: int):
    """执行工作流并投递结果

    Args:
        target_repo: 目标仓库
        chat_id: Telegram Chat ID
    """
    try:
        logger.info(f"[Workflow] 启动审查流水线: {target_repo}")

        # 执行工作流
        report_text = await run_workflow("repo_analysis", {"repo": target_repo})

        logger.info("[Workflow] 工作流执行完成，准备投递...")
        delivery_ok = await _deliver_report_to_telegram(chat_id=chat_id, report_text=report_text)
        if delivery_ok:
            logger.info("[Workflow] ✅ 报告已投递 Telegram（%s 字符）", len(report_text))
        else:
            logger.warning(
                "[Workflow] ⚠️ 报告投递失败或未配置 Telegram（%s 字符）", len(report_text)
            )

    except Exception as e:
        logger.error(f"[Workflow] 执行失败: {e}")


async def _deliver_report_to_telegram(chat_id: int, report_text: str) -> bool:
    """投递报告到 Telegram #市场情报话题."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return False

    thread_id = int(os.getenv("TG_TOPIC_INTELLIGENCE", "4"))
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": report_text[:3900],  # Telegram 文本上限约 4096
        "message_thread_id": thread_id,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
        data = response.json()
        return bool(data.get("ok"))
    except (httpx.HTTPError, ValueError):
        return False


# 指令帮助
WORKFLOW_COMMANDS = {
    "执行审查": {
        "syntax": "执行审查: owner/repo",
        "example": "执行审查: srxly888-creator/autonomous-agent-stack",
        "description": "深度审查 GitHub 代码库",
        "workflow": "repo_analysis",
    },
    "#1": {
        "syntax": "#1 owner/repo",
        "example": "#1 srxly888-creator/autonomous-agent-stack",
        "description": "快捷指令 - 代码库审查",
        "workflow": "repo_analysis",
    },
}


def get_workflow_help() -> str:
    """获取工作流帮助文本"""
    help_text = "🔧 可用工作流指令:\n\n"

    for cmd, info in WORKFLOW_COMMANDS.items():
        help_text += f"**{cmd}**\n"
        help_text += f"  语法: `{info['syntax']}`\n"
        help_text += f"  示例: `{info['example']}`\n"
        help_text += f"  说明: {info['description']}\n\n"

    return help_text
