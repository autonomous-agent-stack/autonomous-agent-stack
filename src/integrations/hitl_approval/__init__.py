"""HITL Approval System for Cross-Ecosystem Operations.

Integrates cross-ecosystem operations (Google, Apple) with Human-in-the-Loop approval flow.
"""

from .approval_manager import ApprovalManager
from .approval_types import (
    ApprovalRequest,
    ApprovalType,
    CalendarApprovalRequest,
    TaskApprovalRequest,
    NoteApprovalRequest,
    FileUploadApprovalRequest,
)

__all__ = [
    "ApprovalManager",
    "ApprovalRequest",
    "ApprovalType",
    "CalendarApprovalRequest",
    "TaskApprovalRequest",
    "NoteApprovalRequest",
    "FileUploadApprovalRequest",
]
