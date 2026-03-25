"""Approval Request Types for HITL System.

Defines types of approval requests for cross-ecosystem operations.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ApprovalType(str, Enum):
    """Types of approval requests."""

    CALENDAR_EVENT = "calendar_event"
    TASK_CREATION = "task_creation"
    NOTE_APPEND = "note_append"
    FILE_UPLOAD = "file_upload"
    REMINDER_ADD = "reminder_add"


class ApprovalStatus(str, Enum):
    """Status of approval requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest(BaseModel):
    """Base class for approval requests."""

    request_id: str = Field(..., description="Unique request ID")
    approval_type: ApprovalType = Field(..., description="Type of approval")
    created_at: datetime = Field(default_factory=datetime.now, description="Request timestamp")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Current status")
    summary: str = Field(..., description="Human-readable summary")
    details: dict[str, Any] = Field(default_factory=dict, description="Operation details")
    timeout_seconds: int = Field(300, description="Approval timeout in seconds")


class CalendarApprovalRequest(ApprovalRequest):
    """Approval request for calendar event creation."""

    approval_type: ApprovalType = ApprovalType.CALENDAR_EVENT

    event_summary: str = Field(..., description="Event title/summary")
    start_time: str = Field(..., description="Event start time (ISO format)")
    end_time: str = Field(..., description="Event end time (ISO format)")
    location: str | None = Field(None, description="Event location")
    description: str | None = Field(None, description="Event description")
    attendees: list[str] | None = Field(None, description="Attendee emails")
    calendar_provider: str = Field(..., description="google or apple")


class TaskApprovalRequest(ApprovalRequest):
    """Approval request for task creation."""

    approval_type: ApprovalType = ApprovalType.TASK_CREATION

    task_title: str = Field(..., description="Task title")
    task_notes: str | None = Field(None, description="Task notes")
    due_date: str | None = Field(None, description="Due date (ISO format)")
    task_provider: str = Field(..., description="google or apple")


class NoteApprovalRequest(ApprovalRequest):
    """Approval request for note append operation."""

    approval_type: ApprovalType = ApprovalType.NOTE_APPEND

    note_name: str = Field(..., description="Note name")
    content_to_append: str = Field(..., description="Content to append")
    folder_name: str = Field(default="Notes", description="Folder name")


class FileUploadApprovalRequest(ApprovalRequest):
    """Approval request for file upload to Google Drive."""

    approval_type: ApprovalType = ApprovalType.FILE_UPLOAD

    filename: str = Field(..., description="Filename")
    file_size: int | None = Field(None, description="File size in bytes")
    mime_type: str | None = Field(None, description="File MIME type")
    destination_folder: str | None = Field(None, description="Destination folder ID")
    description: str | None = Field(None, description="File description")


class ReminderApprovalRequest(ApprovalRequest):
    """Approval request for reminder creation."""

    approval_type: ApprovalType = ApprovalType.REMINDER_ADD

    reminder_title: str = Field(..., description="Reminder title")
    reminder_notes: str | None = Field(None, description="Reminder notes")
    due_date: str | None = Field(None, description="Due date (ISO format)")
    list_name: str = Field(default="Reminders", description="Reminders list name")
