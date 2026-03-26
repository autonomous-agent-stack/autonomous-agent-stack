"""
Bridge API - OpenClaw 与外部系统的双向桥梁

提供：
- OpenClaw 任务接收与委派
- Codex 登录与任务对接
- 外部 Skill 动态加载与安全扫描
- 双向鉴权与凭证解耦
"""

from .api import BridgeAPI
from .skill_loader import SkillLoader
from .codex_client import CodexClient

__all__ = [
    "BridgeAPI",
    "SkillLoader",
    "CodexClient",
]

__version__ = "0.1.0"
