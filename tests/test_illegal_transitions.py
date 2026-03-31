"""B4: Illegal state transition test matrix.

Exhaustive test of every invalid state transition for both TaskStatus and RunStatus.
Every (current, target) pair NOT in the legal transition table must be rejected.
"""

from __future__ import annotations

import pytest

from autoresearch.shared.run_contract import RunStatus, is_valid_run_transition
from autoresearch.shared.task_contract import TaskStatus, is_valid_transition

# ---------------------------------------------------------------------------
# TaskStatus illegal transitions
# ---------------------------------------------------------------------------

_ALL_TASK_STATUSES = list(TaskStatus)

# Legal transitions from task_contract.py
_LEGAL_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.APPROVAL_REQUIRED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.APPROVAL_REQUIRED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.NEEDS_REVIEW,
        TaskStatus.CANCELLED,
    },
    TaskStatus.APPROVAL_REQUIRED: {TaskStatus.QUEUED, TaskStatus.REJECTED, TaskStatus.CANCELLED},
    TaskStatus.NEEDS_REVIEW: {
        TaskStatus.QUEUED,
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.REJECTED,
    },
    TaskStatus.REJECTED: set(),
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.FAILED: {TaskStatus.QUEUED},
    TaskStatus.CANCELLED: set(),
}


class TestTaskStatusIllegalTransitions:
    """Test every invalid (current, target) pair for TaskStatus."""

    @pytest.mark.parametrize(
        "current, target",
        [
            (c, t)
            for c in _ALL_TASK_STATUSES
            for t in _ALL_TASK_STATUSES
            if t not in _LEGAL_TASK_TRANSITIONS.get(c, set())
        ],
        ids=lambda x: x.value if isinstance(x, TaskStatus) else str(x),
    )
    def test_invalid_task_transition(self, current: TaskStatus, target: TaskStatus):
        assert not is_valid_transition(current, target)

    def test_terminal_states_allow_nothing(self):
        """Terminal states (SUCCEEDED, REJECTED, CANCELLED) must have zero outgoing transitions."""
        for status in [TaskStatus.SUCCEEDED, TaskStatus.REJECTED, TaskStatus.CANCELLED]:
            assert _LEGAL_TASK_TRANSITIONS[status] == set()
            for target in _ALL_TASK_STATUSES:
                assert not is_valid_transition(status, target)

    def test_failed_only_allows_retry_to_queued(self):
        """FAILED may only transition back to QUEUED (retry)."""
        for target in _ALL_TASK_STATUSES:
            if target == TaskStatus.QUEUED:
                assert is_valid_transition(TaskStatus.FAILED, target)
            else:
                assert not is_valid_transition(TaskStatus.FAILED, target)

    def test_no_self_transitions(self):
        """No status may transition to itself."""
        for status in _ALL_TASK_STATUSES:
            assert not is_valid_transition(status, status)

    def test_count_of_legal_transitions(self):
        """Sanity check: verify total number of legal transitions."""
        total = sum(len(targets) for targets in _LEGAL_TASK_TRANSITIONS.values())
        # PENDING:3, QUEUED:3, RUNNING:4, APPROVAL_REQUIRED:3, NEEDS_REVIEW:4,
        # REJECTED:0, SUCCEEDED:0, FAILED:1, CANCELLED:0 = 18
        assert total == 18


# ---------------------------------------------------------------------------
# RunStatus illegal transitions
# ---------------------------------------------------------------------------

_ALL_RUN_STATUSES = list(RunStatus)

_LEGAL_RUN_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {RunStatus.LEASED, RunStatus.CANCELLED, RunStatus.FAILED},
    RunStatus.LEASED: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.NEEDS_REVIEW,
        RunStatus.CANCELLED,
    },
    RunStatus.SUCCEEDED: set(),
    RunStatus.FAILED: set(),
    RunStatus.NEEDS_REVIEW: {RunStatus.SUCCEEDED, RunStatus.FAILED},
    RunStatus.CANCELLED: set(),
}


class TestRunStatusIllegalTransitions:
    """Test every invalid (current, target) pair for RunStatus."""

    @pytest.mark.parametrize(
        "current, target",
        [
            (c, t)
            for c in _ALL_RUN_STATUSES
            for t in _ALL_RUN_STATUSES
            if t not in _LEGAL_RUN_TRANSITIONS.get(c, set())
        ],
        ids=lambda x: x.value if isinstance(x, RunStatus) else str(x),
    )
    def test_invalid_run_transition(self, current: RunStatus, target: RunStatus):
        assert not is_valid_run_transition(current, target)

    def test_terminal_run_states_allow_nothing(self):
        """Terminal states (SUCCEEDED, FAILED, CANCELLED) must have zero outgoing transitions."""
        for status in [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED]:
            assert _LEGAL_RUN_TRANSITIONS[status] == set()
            for target in _ALL_RUN_STATUSES:
                assert not is_valid_run_transition(status, target)

    def test_no_self_transitions_run(self):
        """No status may transition to itself."""
        for status in _ALL_RUN_STATUSES:
            assert not is_valid_run_transition(status, status)

    def test_needs_review_only_allows_succeeded_or_failed(self):
        """NEEDS_REVIEW may only go to SUCCEEDED or FAILED."""
        for target in _ALL_RUN_STATUSES:
            if target in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
                assert is_valid_run_transition(RunStatus.NEEDS_REVIEW, target)
            else:
                assert not is_valid_run_transition(RunStatus.NEEDS_REVIEW, target)

    def test_count_of_legal_run_transitions(self):
        """Sanity check: verify total number of legal transitions."""
        total = sum(len(targets) for targets in _LEGAL_RUN_TRANSITIONS.values())
        # QUEUED:3, LEASED:3, RUNNING:4, SUCCEEDED:0, FAILED:0, NEEDS_REVIEW:2, CANCELLED:0 = 12
        assert total == 12


# ---------------------------------------------------------------------------
# RunRecord.transition_to() raises ValueError on illegal transitions
# ---------------------------------------------------------------------------


class TestRunRecordTransitionErrors:
    """Verify RunRecord.transition_to() raises ValueError for illegal moves."""

    @pytest.mark.parametrize(
        "current, target",
        [
            (RunStatus.SUCCEEDED, RunStatus.RUNNING),
            (RunStatus.FAILED, RunStatus.RUNNING),
            (RunStatus.CANCELLED, RunStatus.QUEUED),
            (RunStatus.QUEUED, RunStatus.SUCCEEDED),
            (RunStatus.QUEUED, RunStatus.RUNNING),
            (RunStatus.LEASED, RunStatus.SUCCEEDED),
            (RunStatus.LEASED, RunStatus.NEEDS_REVIEW),
            (RunStatus.RUNNING, RunStatus.QUEUED),
            (RunStatus.RUNNING, RunStatus.LEASED),
            (RunStatus.NEEDS_REVIEW, RunStatus.RUNNING),
            (RunStatus.NEEDS_REVIEW, RunStatus.QUEUED),
            (RunStatus.NEEDS_REVIEW, RunStatus.CANCELLED),
        ],
        ids=lambda x: x.value if isinstance(x, RunStatus) else str(x),
    )
    def test_transition_raises_value_error(self, current: RunStatus, target: RunStatus):
        from autoresearch.shared.run_contract import RunRecord

        run = RunRecord(run_id="test", task_id="t1", status=current)
        with pytest.raises(ValueError, match="Illegal run state transition"):
            run.transition_to(target)

    def test_error_message_contains_both_statuses(self):
        from autoresearch.shared.run_contract import RunRecord

        run = RunRecord(run_id="test", task_id="t1", status=RunStatus.SUCCEEDED)
        with pytest.raises(ValueError, match="succeeded") as exc_info:
            run.transition_to(RunStatus.RUNNING)
        assert "running" in str(exc_info.value).lower()
