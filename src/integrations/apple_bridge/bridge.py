"""macOS Host Bridge - FastAPI Application.

A lightweight HTTP proxy running on the host machine (NOT inside Docker)
that exposes safe Apple ecosystem operations to Docker containers.

SECURITY ARCHITECTURE:
1. Bridge runs on host (outside Docker)
2. Docker containers communicate via HTTP
3. Only CREATE and READ operations allowed
4. DELETE operations are strictly forbidden

RUNNING THE BRIDGE:
    python -m integrations.apple_bridge.bridge

Or with uvicorn:
    uvicorn integrations.apple_bridge.bridge:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .reminders import RemindersService
from .notes import NotesService
from .calendar import CalendarService


# Pydantic models for request/response
class AddReminderRequest(BaseModel):
    title: str = Field(..., description="Reminder title")
    notes: str | None = Field(None, description="Reminder notes")
    due_date: str | None = Field(None, description="Due date in ISO format")
    list_name: str = Field("Reminders", description="Reminders list name")


class AppendNoteRequest(BaseModel):
    note_name: str = Field(..., description="Note name")
    content: str = Field(..., description="Content to append")
    folder_name: str = Field("Notes", description="Folder name")
    create_if_missing: bool = Field(True, description="Create note if missing")


class CreateNoteRequest(BaseModel):
    title: str = Field(..., description="Note title")
    body: str = Field(..., description="Note body")
    folder_name: str = Field("Notes", description="Folder name")


# Initialize FastAPI app
app = FastAPI(
    title="macOS Host Bridge",
    description="Secure HTTP bridge for Apple ecosystem operations",
    version="1.0.0",
)

# Initialize services
reminders_service = RemindersService()
notes_service = NotesService()
calendar_service = CalendarService()


# Health check
@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "macOS Host Bridge"}


# ============================================================================
# REMINDERS ENDPOINTS (CREATE + READ ONLY)
# ============================================================================

@app.post("/reminders/add", tags=["reminders"])
def add_reminder(request: AddReminderRequest) -> dict[str, Any]:
    """Add a new reminder to Apple Reminders.

    SECURITY: CREATE operation - Allowed
    """
    result = reminders_service.add_apple_reminder(
        title=request.title,
        notes=request.notes,
        due_date=request.due_date,
        list_name=request.list_name,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/reminders/list", tags=["reminders"])
def list_reminders(
    list_name: str = "Reminders",
    include_completed: bool = False,
) -> dict[str, Any]:
    """List reminders from Apple Reminders.

    SECURITY: READ operation - Allowed
    """
    result = reminders_service.list_apple_reminders(
        list_name=list_name,
        include_completed=include_completed,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


# ============================================================================
# NOTES ENDPOINTS (CREATE + READ ONLY)
# ============================================================================

@app.post("/notes/append", tags=["notes"])
def append_note(request: AppendNoteRequest) -> dict[str, Any]:
    """Append content to an Apple Note.

    SECURITY: CREATE operation - Allowed
    """
    result = notes_service.append_apple_note(
        note_name=request.note_name,
        content=request.content,
        folder_name=request.folder_name,
        create_if_missing=request.create_if_missing,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.post("/notes/create", tags=["notes"])
def create_note(request: CreateNoteRequest) -> dict[str, Any]:
    """Create a new Apple Note.

    SECURITY: CREATE operation - Allowed
    """
    result = notes_service.create_apple_note(
        title=request.title,
        body=request.body,
        folder_name=request.folder_name,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/notes/list", tags=["notes"])
def list_notes(
    folder_name: str = "Notes",
    limit: int = 50,
) -> dict[str, Any]:
    """List notes from Apple Notes.

    SECURITY: READ operation - Allowed
    """
    result = notes_service.list_apple_notes(
        folder_name=folder_name,
        limit=limit,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


# ============================================================================
# CALENDAR ENDPOINTS (READ ONLY)
# ============================================================================

@app.get("/calendar/today", tags=["calendar"])
def read_calendar_today(
    calendar_name: str | None = None,
) -> dict[str, Any]:
    """Read today's calendar events.

    SECURITY: READ operation - Allowed
    """
    result = calendar_service.read_calendar_today(
        calendar_name=calendar_name,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/calendar/range", tags=["calendar"])
def read_calendar_range(
    start_date: str,
    end_date: str,
    calendar_name: str | None = None,
) -> dict[str, Any]:
    """Read calendar events in a date range.

    SECURITY: READ operation - Allowed
    """
    result = calendar_service.read_calendar_range(
        start_date=start_date,
        end_date=end_date,
        calendar_name=calendar_name,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


# ============================================================================
# DELETE ENDPOINTS - STRICTLY FORBIDDEN
# ============================================================================

# No DELETE endpoints are exposed!
# This is a SECURITY requirement to prevent data loss.


def run() -> None:
    """Run the macOS Host Bridge server."""
    import uvicorn

    host = os.getenv("APPLE_BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("APPLE_BRIDGE_PORT", "8765"))

    print(f"🍎 Starting macOS Host Bridge on {host}:{port}")
    print("🔒 Security: Only CREATE and READ operations allowed")
    print("❌ DELETE operations are strictly forbidden")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
