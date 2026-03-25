"""Communication Protocols - OpenSage 消息协议"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ShutdownRequest:
    """关闭请求协议"""
    reason: str
    graceful: bool = True
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason,
            "graceful": self.graceful,
            "timeout": self.timeout,
        }


@dataclass
class TaskRequest:
    """任务请求协议"""
    task_id: str
    task_type: str
    parameters: Dict[str, Any]
    priority: int = 0
    deadline: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "parameters": self.parameters,
            "priority": self.priority,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        }


@dataclass
class TaskResult:
    """任务结果协议"""
    task_id: str
    status: str  # success, failure, timeout
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
        }
