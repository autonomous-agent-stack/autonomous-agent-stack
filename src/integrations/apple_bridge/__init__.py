"""macOS Host Bridge for Apple Ecosystem Integration.

A lightweight FastAPI proxy running on the host machine (not inside Docker)
that exposes safe Apple ecosystem operations via HTTP endpoints.

SECURITY: Only Create and Read operations are allowed. Delete is strictly forbidden.
"""

from .bridge import macOSHostBridge
from .reminders import RemindersService
from .notes import NotesService
from .calendar import CalendarService

__all__ = [
    "macOSHostBridge",
    "RemindersService",
    "NotesService",
    "CalendarService",
]
