from __future__ import annotations

import re
from typing import Any

from autoresearch.api.settings import load_telegram_settings
from autoresearch.core.services.telegram_identity import TelegramSessionIdentityRead
from autoresearch.shared.models import ActorRole, AssistantScope

_SHORT_AFFIRMATIVE_RE = re.compile(r"^(好|好的|好啊|好呀|行|行啊|行呀|可以|可以啊|可以呀|开始|开始吧|来吧|继续|确认|是|是的|嗯|嗯嗯)\s*[.!。！？~～]*$")
_YOUTUBE_PROCESS_CONFIRM_RE = re.compile(r"(现在)?触发(?:一次)?(?:视频)?(?:字幕)?处理")


def _extract_telegram_message(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if isinstance(message, dict):
        chat = message.get("chat", {})
        from_user = message.get("from", {})

        # 提取图片信息
        photos = message.get("photo", [])
        image_urls = []
        if photos:
            # 获取最大尺寸的图片（最后一个）
            largest_photo = photos[-1] if photos else None
            if largest_photo:
                file_id = largest_photo.get("file_id")
                if file_id:
                    # 构造图片 URL（需要 Bot Token）
                    bot_token = load_telegram_settings().bot_token or ""
                    if bot_token:
                        image_urls.append(f"telegram://{file_id}")

        return {
            "chat_id": _safe_str(chat.get("id")),
            "chat_type": _safe_str(chat.get("type")),
            "text": (message.get("text") or message.get("caption") or "").strip(),
            "message_id": message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
            "from_id": from_user.get("id"),
            "reply_to_user_id": _safe_int(((message.get("reply_to_message") or {}).get("from") or {}).get("id")),
            "reply_to_username": _safe_str(((message.get("reply_to_message") or {}).get("from") or {}).get("username")),
            "reply_to_is_bot": bool(((message.get("reply_to_message") or {}).get("from") or {}).get("is_bot")),
            "message_thread_id": message.get("message_thread_id"),
            "is_topic_message": bool(message.get("is_topic_message", False)),
            "reply_to_message_id": message.get("reply_to_message", {}).get("message_id") if isinstance(message.get("reply_to_message"), dict) else None,
            "raw_type": "message",
            "images": image_urls,
        }

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        callback_message = callback.get("message", {})
        chat = callback_message.get("chat", {})
        from_user = callback.get("from", {})
        return {
            "chat_id": _safe_str(chat.get("id")),
            "chat_type": _safe_str(chat.get("type")),
            "text": (callback.get("data") or "").strip(),
            "message_id": callback_message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
            "from_id": from_user.get("id"),
            "reply_to_user_id": None,
            "reply_to_username": None,
            "reply_to_is_bot": False,
            "message_thread_id": callback_message.get("message_thread_id"),
            "is_topic_message": bool(callback_message.get("is_topic_message", False)),
            "reply_to_message_id": None,
            "raw_type": "callback_query",
        }
    return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_status_query(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized.startswith("/status"):
        return True
    if normalized.startswith("/panel"):
        return True
    if normalized in {
        "status",
        "task status",
        "任务状态",
        "状态",
        "查询状态",
        "查看状态",
        "进度",
        "面板",
        "在哪",
        "在哪儿",
        "你在哪",
        "你在哪儿",
        "worker",
        "workers",
        "worker状态",
        "worker 状态",
        "worker情况",
        "worker 情况",
        "有哪些worker",
        "有哪些 worker",
        "几个worker",
        "几个 worker",
    }:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "在哪台电脑",
            "在哪个电脑",
            "在哪台机器",
            "在哪个机器",
            "在哪台主机",
            "在哪个主机",
            "在哪里运行",
            "在哪运行",
            "mac还是linux",
            "mac 还是 linux",
            "which computer",
            "what host",
            "where are you running",
            "who is online",
            "who is busy",
            "worker inventory",
            "worker status",
            "worker heartbeat",
            "心跳如何",
            "谁在线",
            "谁在忙",
            "aAS 当前 worker 情况".lower(),
            "当前worker情况",
            "当前 worker 情况",
        )
    )


def _is_help_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"/help", "/start", "help", "帮助"}


def _is_task_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/task" or normalized.startswith("/task ")


def _is_approve_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/approve" or normalized.startswith("/approve ")


def _is_mode_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/mode" or normalized.startswith("/mode ")


def _is_memory_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return (
        lowered == "/memory"
        or lowered.startswith("/memory ")
        or normalized.startswith("记住")
        or lowered.startswith("remember ")
        or lowered.startswith("remember this:")
    )


def _is_skills_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return lowered == "/skills" or lowered.startswith("/skills ")


def _is_reset_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return lowered == "/reset" or normalized == "重置会话"


def _extract_mode_target(text: str) -> AssistantScope | None:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/mode":
        return None
    if not lowered.startswith("/mode "):
        return None
    target = normalized.split(" ", 1)[1].strip().lower()
    if target == "personal":
        return AssistantScope.PERSONAL
    if target == "shared":
        return AssistantScope.SHARED
    return None


def _extract_memory_content(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/memory":
        return ""
    if lowered.startswith("/memory "):
        return normalized.split(" ", 1)[1].strip()
    if normalized.startswith("记住"):
        return normalized[2:].lstrip(" ：:").strip()
    if lowered.startswith("remember this:"):
        return normalized[len("remember this:") :].strip()
    if lowered.startswith("remember "):
        return normalized[len("remember ") :].strip()
    return ""


def _extract_approve_query(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/approve":
        return ""
    if lowered.startswith("/approve "):
        return normalized.split(" ", 1)[1].strip()
    return ""


def _extract_task_query(text: str) -> str:
    return _parse_task_command(text)[0]


def _extract_skill_query(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/skills":
        return ""
    if lowered.startswith("/skills "):
        return normalized.split(" ", 1)[1].strip()
    return ""


def _parse_task_command(text: str) -> tuple[str, bool]:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/task":
        return "", False
    if lowered.startswith("/task "):
        payload = normalized.split(" ", 1)[1].strip()
        approval_requested = False
        if payload.startswith("--approve"):
            approval_requested = True
            payload = payload[len("--approve") :].strip()
        return payload, approval_requested
    return "", False


def _parse_approve_query(query: str) -> tuple[str, str | None, str]:
    normalized = query.strip()
    if not normalized:
        return "", None, ""
    parts = normalized.split(None, 2)
    approval_id = parts[0].strip()
    if len(parts) < 2:
        return approval_id, None, ""
    action = parts[1].strip().lower()
    if action not in {"approve", "reject"}:
        return approval_id, None, ""
    note = parts[2].strip() if len(parts) > 2 else ""
    return approval_id, action, note


def _extract_issue_task_parts(task_query: str) -> tuple[str, str]:
    normalized = task_query.strip()
    if not normalized.casefold().startswith("issue "):
        raise ValueError("issue task must start with `issue `")
    remainder = normalized[6:].strip()
    if not remainder:
        raise ValueError("missing GitHub issue reference")
    issue_reference, _, operator_note = remainder.partition(" ")
    return issue_reference.strip(), operator_note.strip()


def _can_telegram_task_self_approve(
    *,
    session_identity: TelegramSessionIdentityRead,
) -> bool:
    return session_identity.actor.role in {ActorRole.OWNER, ActorRole.PARTNER}
