"""
Services Module - 核心服务层

包含 Telegram 媒体服务等业务逻辑。
"""

from .telegram_media import (
    MediaType,
    ParseMode,
    KeyboardType,
    MediaAttachment,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Markup,
    RichMessage,
    MessageBuilder,
    InlineKeyboardBuilder,
    ReplyKeyboardBuilder,
    text_message,
    photo_message,
    document_message,
    with_inline_keyboard,
    with_reply_keyboard,
    remove_keyboard,
    TelegramMediaService,
)

__all__ = [
    # 枚举
    "MediaType",
    "ParseMode",
    "KeyboardType",

    # 数据模型
    "MediaAttachment",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "ReplyKeyboardButton",
    "ReplyKeyboardMarkup",
    "ReplyKeyboardRemove",
    "Markup",
    "RichMessage",

    # 构建器
    "MessageBuilder",
    "InlineKeyboardBuilder",
    "ReplyKeyboardBuilder",

    # 便捷函数
    "text_message",
    "photo_message",
    "document_message",
    "with_inline_keyboard",
    "with_reply_keyboard",
    "remove_keyboard",

    # 服务类
    "TelegramMediaService",
]
