"""Unified task gate contract for the control plane.

A *gate* is the quality / compliance checkpoint at the end of a run.  It
inspects the run outcome, checks artifacts, and decides what happens next:
accept, retry, fallback, or escalate to a human.

Gate evaluation flow::

    run completes
        |
        v
    gate evaluates run + artifacts
        |
        |---> outcome = success            -> action = accept
        |---> outcome = overreach          -> action = reject
        |---> outcome = timeout            -> action = retry or fallback
        |---> outcome = missing_artifacts  -> action = retry or fallback
        +---> outcome = needs_human_confirm -> action = needs_review
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from .models import StrictModel

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GateOutcome(str, Enum):
    """What the gate discovered about the run."""

    SUCCESS = "success"
    OVERREACH = "overreach"
    TIMEOUT = "timeout"
    MISSING_ARTIFACTS = "missing_artifacts"
    NEEDS_HUMAN_CONFIRM = "needs_human_confirm"


class GateAction(str, Enum):
    """What the gate recommends doing next."""

    ACCEPT = "accept"
    RETRY = "retry"
    FALLBACK = "fallback"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Gate check (individual check within a gate evaluation)
# ---------------------------------------------------------------------------


class GateCheck(StrictModel):
    """A single check within a gate evaluation."""

    check_id: str
    passed: bool
    detail: str = ""
    severity: Literal["info", "warning", "critical"] = "info"


# ---------------------------------------------------------------------------
# Gate evaluation result
# ---------------------------------------------------------------------------


class GateVerdict(StrictModel):
    """The result of evaluating a gate for a completed run."""

    outcome: GateOutcome
    action: GateAction
    checks: list[GateCheck] = []
    reason: str = ""
    retry_attempt: int = 0
    max_retries: int = 3
    fallback_agent_id: str | None = None
    evaluated_at: datetime | None = None
    metadata: dict[str, Any] = {}

    @property
    def can_retry(self) -> bool:
        return self.retry_attempt < self.max_retries

    @property
    def all_checks_passed(self) -> bool:
        return all(c.passed for c in self.checks)


# ---------------------------------------------------------------------------
# Default outcome-to-action mapping
# ---------------------------------------------------------------------------

_DEFAULT_OUTCOME_ACTION: dict[GateOutcome, GateAction] = {
    GateOutcome.SUCCESS: GateAction.ACCEPT,
    GateOutcome.OVERREACH: GateAction.REJECT,
    GateOutcome.TIMEOUT: GateAction.RETRY,
    GateOutcome.MISSING_ARTIFACTS: GateAction.RETRY,
    GateOutcome.NEEDS_HUMAN_CONFIRM: GateAction.NEEDS_REVIEW,
}


def default_action_for_outcome(outcome: GateOutcome) -> GateAction:
    """Return the default action for a given gate outcome."""
    return _DEFAULT_OUTCOME_ACTION[outcome]


def make_gate_verdict(
    outcome: GateOutcome,
    *,
    reason: str = "",
    checks: list[GateCheck] | None = None,
    retry_attempt: int = 0,
    max_retries: int = 3,
    fallback_agent_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GateVerdict:
    """Convenience factory: auto-selects the default action for *outcome*."""
    action = default_action_for_outcome(outcome)
    if action == GateAction.RETRY and retry_attempt >= max_retries:
        action = GateAction.FALLBACK if fallback_agent_id else GateAction.NEEDS_REVIEW
    return GateVerdict(
        outcome=outcome,
        action=action,
        checks=checks or [],
        reason=reason,
        retry_attempt=retry_attempt,
        max_retries=max_retries,
        fallback_agent_id=fallback_agent_id,
        metadata=metadata or {},
    )
