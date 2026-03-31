"""Unified run state machine for the control plane.

A *run* is one execution attempt of a task on a worker.  The run has its own
lifecycle independent of (but subordinate to) the task lifecycle.

State diagram::

    queued ──► leased ──► running ──► succeeded
                        │    │    └──► failed
                        │    └──────► needs_review
                        │
                        └──► failed  (lease lost / worker died)
    queued ──► cancelled
    leased ──► cancelled
    running ──► cancelled

Terminal states: succeeded, failed, needs_review, cancelled.

The AEP layer adds its own *final_status* (ready_for_promotion / blocked /
promoted / human_review) on top of the run status.  Those are NOT part of the
run state machine proper; they are derived by the gate / promotion layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from .models import StrictModel

# ---------------------------------------------------------------------------
# Run status enum
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    """Unified run status across the control plane."""

    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------

# Legal forward transitions.  A run may only move to a state listed here
# from its current state.
_RUN_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {RunStatus.LEASED, RunStatus.CANCELLED, RunStatus.FAILED},
    RunStatus.LEASED: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.NEEDS_REVIEW,
        RunStatus.CANCELLED,
    },
    RunStatus.SUCCEEDED: set(),  # terminal
    RunStatus.FAILED: set(),  # terminal (retry creates a new run)
    RunStatus.NEEDS_REVIEW: {RunStatus.SUCCEEDED, RunStatus.FAILED},  # human resolution
    RunStatus.CANCELLED: set(),  # terminal
}


def is_valid_run_transition(current: RunStatus, target: RunStatus) -> bool:
    """Return True if *current* -> *target* is a legal state change."""
    return target in _RUN_TRANSITIONS.get(current, set())


def must_be_terminal(status: RunStatus) -> bool:
    """Return True if *status* is terminal (no further transitions)."""
    return len(_RUN_TRANSITIONS.get(status, set())) == 0


# ---------------------------------------------------------------------------
# Run record
# ---------------------------------------------------------------------------


class RunRecord(StrictModel):
    """Canonical run record in the control plane.

    One RunRecord per execution attempt.  Retries create new records.
    """

    run_id: str
    task_id: str
    worker_id: str | None = None

    status: RunStatus = RunStatus.QUEUED

    # Timing
    queued_at: Any = None  # datetime, using Any to avoid pydantic serialization issues
    leased_at: Any = None
    started_at: Any = None
    completed_at: Any = None

    # Result
    error_message: str | None = None
    result_data: dict[str, Any] | None = None

    # Attempt tracking
    attempt: int = 1

    # Metadata
    created_at: Any = None
    updated_at: Any = None
    metadata: dict[str, Any] = {}

    def transition_to(self, target: RunStatus) -> None:
        """Validate and apply a state transition in-place.

        Raises ValueError if the transition is illegal.
        """
        if not is_valid_run_transition(self.status, target):
            raise ValueError(f"Illegal run state transition: {self.status.value} -> {target.value}")
        self.status = target


# ---------------------------------------------------------------------------
# Legacy AEP status mapping
# ---------------------------------------------------------------------------

# The AEP DriverResult.status values map to unified RunStatus as follows:
_AEP_DRIVER_TO_RUN: dict[str, RunStatus] = {
    "succeeded": RunStatus.SUCCEEDED,
    "partial": RunStatus.NEEDS_REVIEW,
    "failed": RunStatus.FAILED,
    "timed_out": RunStatus.FAILED,
    "stalled_no_progress": RunStatus.FAILED,
    "policy_blocked": RunStatus.NEEDS_REVIEW,
    "contract_error": RunStatus.FAILED,
}

# The AEP RunSummary.final_status values:
_AEP_FINAL_TO_RUN: dict[str, RunStatus] = {
    "ready_for_promotion": RunStatus.SUCCEEDED,
    "promoted": RunStatus.SUCCEEDED,
    "blocked": RunStatus.NEEDS_REVIEW,
    "failed": RunStatus.FAILED,
    "human_review": RunStatus.NEEDS_REVIEW,
}


def aep_driver_status_to_run(aep_status: str) -> RunStatus:
    """Map an AEP DriverResult.status string to unified RunStatus."""
    return _AEP_DRIVER_TO_RUN[aep_status]


def aep_final_status_to_run(aep_final: str) -> RunStatus:
    """Map an AEP RunSummary.final_status string to unified RunStatus."""
    return _AEP_FINAL_TO_RUN[aep_final]
