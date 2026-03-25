"""
Routers Module - 网关路由器

包含 Telegram、Discord 等平台的消息网关实现。
"""

from .gateway_telegram import TelegramGateway, TelegramMessage, TelegramCommand

__all__ = [
    "TelegramGateway",
    "TelegramMessage",
    "TelegramCommand",
]
