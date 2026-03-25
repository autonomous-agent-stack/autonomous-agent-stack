"""Communication Module - OpenSage 架构"""

from .bus import Message, MessageBus, MessageType
from .protocols import ShutdownRequest, TaskRequest, TaskResult

__all__ = [
    "MessageBus",
    "Message",
    "MessageType",
    "TaskRequest",
    "TaskResult",
    "ShutdownRequest",
]
