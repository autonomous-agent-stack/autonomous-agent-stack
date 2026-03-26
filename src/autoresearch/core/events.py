"""Vision Event Protocol - 多模态视觉事件协议"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(Enum):
    """事件类型枚举"""
    VISION = "vision"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CONTROL = "control"
    SHUTDOWN = "shutdown"


@dataclass
class VisionEvent:
    """视觉事件数据结构
    
    遵循 OpenSage 多模态事件协议
    """
    image_base64: str
    caption: str
    source: str = "telegram"
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: f"vision_{datetime.now().timestamp()}")
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "image_base64": self.image_base64,
            "caption": self.caption,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "metadata": self.metadata,
        }


@dataclass
class P4Event:
    """P4 演化事件
    
    P4 = Pull → Parse → Plan → Push
    """
    github_url: str
    repo_name: str
    branch: str = "main"
    status: str = "pending"  # pending, scanning, testing, auditing, hitl, completed
    scan_result: Optional[Dict[str, Any]] = None
    test_result: Optional[Dict[str, Any]] = None
    audit_result: Optional[Dict[str, Any]] = None
    hitl_approved: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: f"p4_{datetime.now().timestamp()}")
    
    def __post_init__(self):
        """初始化默认值"""
        if self.scan_result is None:
            self.scan_result = {"status": "pending"}
        if self.test_result is None:
            self.test_result = {"status": "pending", "tests_run": 0, "tests_passed": 0}
        if self.audit_result is None:
            self.audit_result = {"status": "pending"}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "github_url": self.github_url,
            "repo_name": self.repo_name,
            "branch": self.branch,
            "status": self.status,
            "scan_result": self.scan_result,
            "test_result": self.test_result,
            "audit_result": self.audit_result,
            "hitl_approved": self.hitl_approved,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
        }
