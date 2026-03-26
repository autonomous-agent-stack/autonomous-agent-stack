"""
Telegram Webhook Handler - 指令拦截与工作流触发
"""

import asyncio
import logging
import re
from typing import Dict, Any
from fastapi import APIRouter, Request

from workflow.workflow_engine import run_workflow

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram Webhook 处理器"""
    try:
        data = await request.json()

        # 提取消息内容
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = message.get("from", {}).get("id")

        logger.info(f"[Webhook] 收到消息: {text[:50]}...")

        # 指令拦截：GitHub 深度审查
        if "执行审查" in text or "#1" in text:
            logger.info("[Webhook] 拦截到审查指令，启动工作流...")

            # 提取仓库名
            repo_match = re.search(r'执行审查[:\s]+([^\s]+)', text)
            if not repo_match:
                repo_match = re.search(r'#1[:\s]+([^\s]+)', text)

            if repo_match:
                target_repo = repo_match.group(1).strip()

                # 启动工作流（异步执行）
                asyncio.create_task(
                    execute_and_deliver_workflow(target_repo, chat_id)
                )

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
        report_text = await run_workflow(
            "repo_analysis",
            {"repo": target_repo}
        )

        logger.info(f"[Workflow] 工作流执行完成，准备投递...")

        # TODO: 投递到 #市场情报 频道
        # 这里需要调用 Telegram Bot API 发送消息
        # 示例代码（需要实际实现）:
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # 发送到 #市场情报 频道
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": report_text,
                "parse_mode": "Markdown",
                "message_thread_id": 4  # #市场情报 Topic ID
            }
            
            async with session.post(url, json=payload) as resp:
                result = await resp.json()
                logger.info(f"[Telegram] 消息已投递: {result}")
        """

        logger.info(f"[Workflow] ✅ 报告已生成（{len(report_text)} 字符）")

    except Exception as e:
        logger.error(f"[Workflow] 执行失败: {e}")


# 指令帮助
WORKFLOW_COMMANDS = {
    "执行审查": {
        "syntax": "执行审查: owner/repo",
        "example": "执行审查: srxly888-creator/autonomous-agent-stack",
        "description": "深度审查 GitHub 代码库",
        "workflow": "repo_analysis"
    },
    "#1": {
        "syntax": "#1 owner/repo",
        "example": "#1 srxly888-creator/autonomous-agent-stack",
        "description": "快捷指令 - 代码库审查",
        "workflow": "repo_analysis"
    }
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
