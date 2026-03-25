"""Integrations Package.

Provides cross-ecosystem integration modules:
- Google Workspace (Calendar, Tasks, Drive)
- Apple Ecosystem (Reminders, Notes, Calendar)
- HITL Approval System
"""

from . import google_workspace
from . import apple_bridge
from . import hitl_approval

__all__ = [
    "google_workspace",
    "apple_bridge",
    "hitl_approval",
]
