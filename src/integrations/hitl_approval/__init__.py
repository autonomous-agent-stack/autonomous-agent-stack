"""HITL Approval System for Cross-Ecosystem Operations.

Integrates cross-ecosystem operations (Google, Apple) with Human-in-the-Loop approval flow.
"""

from .approval_manager import ApprovalManager
from .approval_types import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    CalendarApprovalRequest,
    TaskApprovalRequest,
    NoteApprovalRequest,
    FileUploadApprovalRequest,
    ReminderApprovalRequest,
)

__all__ = [
    "ApprovalManager",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalType",
    "CalendarApprovalRequest",
    "TaskApprovalRequest",
    "NoteApprovalRequest",
    "FileUploadApprovalRequest",
    "ReminderApprovalRequest",
]
