"""Run state machine for task execution.

Manages valid state transitions and run record state.
"""

from __future__ import annotations

from .contracts import RunState, RunRecord, is_valid_transition, utc_now


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: RunState, to_state: RunState, reason: str = "") -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(
            f"Cannot transition from {from_state.value} to {to_state.value}: {reason}"
        )


class StateMachine:
    """State machine for managing task run states."""

    @staticmethod
    def transition(record: RunRecord, to_state: RunState, reason: str = "") -> RunRecord:
        """Transition a run record to a new state.

        Args:
            record: The run record to transition
            to_state: The target state
            reason: Optional reason for the transition

        Returns:
            The updated run record

        Raises:
            InvalidStateTransition: If the transition is not valid
        """
        from_state = record.state

        if not is_valid_transition(from_state, to_state):
            raise InvalidStateTransition(from_state, to_state, reason)

        record.record_transition(from_state, to_state, reason)
        record.state = to_state

        return record

    @staticmethod
    def can_transition(record: RunRecord, to_state: RunState) -> bool:
        """Check if a transition to a target state is possible."""
        return is_valid_transition(record.state, to_state)
