"""Google Workspace MCP Integration.

Provides secure access to Google Calendar, Tasks, and Drive via OAuth 2.0.
"""

from .calendar import GoogleCalendarClient
from .tasks import GoogleTasksClient
from .drive import GoogleDriveClient
from .oauth import OAuthManager

__all__ = [
    "GoogleCalendarClient",
    "GoogleTasksClient",
    "GoogleDriveClient",
    "OAuthManager",
]
