"""Approval Manager for HITL System.

Manages approval requests and integrates with existing HITL framework.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from .approval_types import (
    ApprovalRequest,
    ApprovalStatus,
    CalendarApprovalRequest,
    TaskApprovalRequest,
    NoteApprovalRequest,
    FileUploadApprovalRequest,
    ReminderApprovalRequest,
)


class ApprovalManager:
    """Manages approval requests for cross-ecosystem operations.

    Integrates with:
    - Existing HITL framework (src/orchestrator/hitl.py)
    - Telegram TWA Dashboard
    - Event Bus for notifications
    """

    def __init__(self) -> None:
        self.pending_requests: dict[str, ApprovalRequest] = {}
        self.approval_callbacks: dict[str, Callable[[ApprovalRequest], None]] = {}

    def create_calendar_approval(
        self,
        event_summary: str,
        start_time: str,
        end_time: str,
        location: str | None = None,
        description: str | None = None,
        attendees: list[str] | None = None,
        calendar_provider: str = "google",
        timeout_seconds: int = 300,
    ) -> CalendarApprovalRequest:
        """Create a calendar event approval request.

        Args:
            event_summary: Event title
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            location: Event location (optional)
            description: Event description (optional)
            attendees: Attendee emails (optional)
            calendar_provider: "google" or "apple"
            timeout_seconds: Approval timeout

        Returns:
            CalendarApprovalRequest
        """
        request_id = str(uuid.uuid4())

        request = CalendarApprovalRequest(
            request_id=request_id,
            event_summary=event_summary,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            attendees=attendees,
            calendar_provider=calendar_provider,
            summary=f"📅 日程添加请求: {event_summary}",
            details={
                "provider": calendar_provider,
                "time_range": f"{start_time} - {end_time}",
            },
            timeout_seconds=timeout_seconds,
        )

        self.pending_requests[request_id] = request
        return request

    def create_task_approval(
        self,
        task_title: str,
        task_notes: str | None = None,
        due_date: str | None = None,
        task_provider: str = "google",
        timeout_seconds: int = 300,
    ) -> TaskApprovalRequest:
        """Create a task creation approval request."""
        request_id = str(uuid.uuid4())

        request = TaskApprovalRequest(
            request_id=request_id,
            task_title=task_title,
            task_notes=task_notes,
            due_date=due_date,
            task_provider=task_provider,
            summary=f"✅ 任务创建请求: {task_title}",
            details={
                "provider": task_provider,
                "due_date": due_date,
            },
            timeout_seconds=timeout_seconds,
        )

        self.pending_requests[request_id] = request
        return request

    def create_note_approval(
        self,
        note_name: str,
        content_to_append: str,
        folder_name: str = "Notes",
        timeout_seconds: int = 300,
    ) -> NoteApprovalRequest:
        """Create a note append approval request."""
        request_id = str(uuid.uuid4())

        request = NoteApprovalRequest(
            request_id=request_id,
            note_name=note_name,
            content_to_append=content_to_append,
            folder_name=folder_name,
            summary=f"📝 备忘录追加请求: {note_name}",
            details={
                "folder": folder_name,
                "content_length": len(content_to_append),
            },
            timeout_seconds=timeout_seconds,
        )

        self.pending_requests[request_id] = request
        return request

    def create_file_upload_approval(
        self,
        filename: str,
        file_size: int | None = None,
        mime_type: str | None = None,
        destination_folder: str | None = None,
        description: str | None = None,
        timeout_seconds: int = 300,
    ) -> FileUploadApprovalRequest:
        """Create a file upload approval request."""
        request_id = str(uuid.uuid4())

        request = FileUploadApprovalRequest(
            request_id=request_id,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            destination_folder=destination_folder,
            description=description,
            summary=f"📤 文件上传请求: {filename}",
            details={
                "size": file_size,
                "mime_type": mime_type,
                "folder": destination_folder,
            },
            timeout_seconds=timeout_seconds,
        )

        self.pending_requests[request_id] = request
        return request

    def create_reminder_approval(
        self,
        reminder_title: str,
        reminder_notes: str | None = None,
        due_date: str | None = None,
        list_name: str = "Reminders",
        timeout_seconds: int = 300,
    ) -> ReminderApprovalRequest:
        """Create a reminder creation approval request."""
        request_id = str(uuid.uuid4())

        request = ReminderApprovalRequest(
            request_id=request_id,
            reminder_title=reminder_title,
            reminder_notes=reminder_notes,
            due_date=due_date,
            list_name=list_name,
            summary=f"⏰ 提醒创建请求: {reminder_title}",
            details={
                "list": list_name,
                "due_date": due_date,
            },
            timeout_seconds=timeout_seconds,
        )

        self.pending_requests[request_id] = request
        return request

    async def wait_for_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalStatus:
        """Wait for user approval with timeout.

        Args:
            request: Approval request to wait for

        Returns:
            ApprovalStatus (APPROVED, REJECTED, or TIMEOUT)
        """
        start_time = datetime.now()
        timeout = timedelta(seconds=request.timeout_seconds)

        while datetime.now() - start_time < timeout:
            # Check if request status has been updated
            if request.status != ApprovalStatus.PENDING:
                return request.status

            # Poll every second
            await asyncio.sleep(1)

        # Timeout reached
        request.status = ApprovalStatus.TIMEOUT
        return ApprovalStatus.TIMEOUT

    def approve_request(self, request_id: str) -> bool:
        """Approve a pending request.

        Args:
            request_id: Request ID to approve

        Returns:
            True if approved, False if not found
        """
        if request_id not in self.pending_requests:
            return False

        request = self.pending_requests[request_id]
        request.status = ApprovalStatus.APPROVED

        # Trigger callback if registered
        if request_id in self.approval_callbacks:
            self.approval_callbacks[request_id](request)

        return True

    def reject_request(self, request_id: str) -> bool:
        """Reject a pending request.

        Args:
            request_id: Request ID to reject

        Returns:
            True if rejected, False if not found
        """
        if request_id not in self.pending_requests:
            return False

        request = self.pending_requests[request_id]
        request.status = ApprovalStatus.REJECTED

        return True

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        return [
            req
            for req in self.pending_requests.values()
            if req.status == ApprovalStatus.PENDING
        ]

    def register_callback(
        self,
        request_id: str,
        callback: Callable[[ApprovalRequest], None],
    ) -> None:
        """Register a callback to be called when request is approved."""
        self.approval_callbacks[request_id] = callback
