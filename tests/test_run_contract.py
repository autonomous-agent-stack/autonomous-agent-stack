"""Tests for the unified run state machine."""

from __future__ import annotations

import pytest

from autoresearch.shared.run_contract import (
    RunRecord,
    RunStatus,
    aep_driver_status_to_run,
    aep_final_status_to_run,
    is_valid_run_transition,
    must_be_terminal,
)

# ---------------------------------------------------------------------------
# RunStatus enum
# ---------------------------------------------------------------------------


class TestRunStatus:
    def test_all_states_present(self):
        assert RunStatus.QUEUED
        assert RunStatus.LEASED
        assert RunStatus.RUNNING
        assert RunStatus.SUCCEEDED
        assert RunStatus.FAILED
        assert RunStatus.NEEDS_REVIEW
        assert RunStatus.CANCELLED

    def test_values_are_lowercase(self):
        for s in RunStatus:
            assert s.value == s.value.lower()


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


class TestValidTransitions:
    """Happy path transitions."""

    def test_queued_to_leased(self):
        assert is_valid_run_transition(RunStatus.QUEUED, RunStatus.LEASED)

    def test_leased_to_running(self):
        assert is_valid_run_transition(RunStatus.LEASED, RunStatus.RUNNING)

    def test_running_to_succeeded(self):
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.SUCCEEDED)

    def test_running_to_failed(self):
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.FAILED)

    def test_running_to_needs_review(self):
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.NEEDS_REVIEW)

    def test_queued_to_cancelled(self):
        assert is_valid_run_transition(RunStatus.QUEUED, RunStatus.CANCELLED)

    def test_leased_to_cancelled(self):
        assert is_valid_run_transition(RunStatus.LEASED, RunStatus.CANCELLED)

    def test_running_to_cancelled(self):
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.CANCELLED)

    def test_queued_direct_fail(self):
        assert is_valid_run_transition(RunStatus.QUEUED, RunStatus.FAILED)

    def test_leased_direct_fail(self):
        assert is_valid_run_transition(RunStatus.LEASED, RunStatus.FAILED)

    def test_needs_review_to_succeeded(self):
        assert is_valid_run_transition(RunStatus.NEEDS_REVIEW, RunStatus.SUCCEEDED)

    def test_needs_review_to_failed(self):
        assert is_valid_run_transition(RunStatus.NEEDS_REVIEW, RunStatus.FAILED)


class TestInvalidTransitions:
    """Illegal transitions must return False."""

    @pytest.mark.parametrize(
        "src, dst",
        [
            # backwards
            (RunStatus.LEASED, RunStatus.QUEUED),
            (RunStatus.RUNNING, RunStatus.LEASED),
            (RunStatus.SUCCEEDED, RunStatus.RUNNING),
            (RunStatus.FAILED, RunStatus.RUNNING),
            # terminals
            (RunStatus.SUCCEEDED, RunStatus.FAILED),
            (RunStatus.FAILED, RunStatus.SUCCEEDED),
            (RunStatus.CANCELLED, RunStatus.RUNNING),
            (RunStatus.CANCELLED, RunStatus.SUCCEEDED),
            # skip states
            (RunStatus.QUEUED, RunStatus.RUNNING),
            (RunStatus.QUEUED, RunStatus.SUCCEEDED),
            (RunStatus.LEASED, RunStatus.SUCCEEDED),
            # needs_review cannot go back to queued/leased/running
            (RunStatus.NEEDS_REVIEW, RunStatus.QUEUED),
            (RunStatus.NEEDS_REVIEW, RunStatus.RUNNING),
            (RunStatus.NEEDS_REVIEW, RunStatus.CANCELLED),
        ],
    )
    def test_invalid(self, src, dst):
        assert not is_valid_run_transition(src, dst)


# ---------------------------------------------------------------------------
# Terminal detection
# ---------------------------------------------------------------------------


class TestTerminal:
    @pytest.mark.parametrize("status", [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED])
    def test_terminal_states(self, status):
        assert must_be_terminal(status)

    @pytest.mark.parametrize(
        "status", [RunStatus.QUEUED, RunStatus.LEASED, RunStatus.RUNNING, RunStatus.NEEDS_REVIEW]
    )
    def test_non_terminal_states(self, status):
        assert not must_be_terminal(status)


# ---------------------------------------------------------------------------
# RunRecord transition method
# ---------------------------------------------------------------------------


class TestRunRecordTransition:
    def test_happy_path(self):
        r = RunRecord(run_id="r1", task_id="t1")
        assert r.status == RunStatus.QUEUED
        r.transition_to(RunStatus.LEASED)
        assert r.status == RunStatus.LEASED
        r.transition_to(RunStatus.RUNNING)
        assert r.status == RunStatus.RUNNING
        r.transition_to(RunStatus.SUCCEEDED)
        assert r.status == RunStatus.SUCCEEDED

    def test_invalid_raises(self):
        r = RunRecord(run_id="r1", task_id="t1")
        with pytest.raises(ValueError, match="Illegal run state transition"):
            r.transition_to(RunStatus.RUNNING)  # skip LEASED

    def test_terminal_cannot_transition(self):
        r = RunRecord(run_id="r1", task_id="t1")
        r.transition_to(RunStatus.LEASED)
        r.transition_to(RunStatus.RUNNING)
        r.transition_to(RunStatus.SUCCEEDED)
        with pytest.raises(ValueError, match="Illegal run state transition"):
            r.transition_to(RunStatus.FAILED)


# ---------------------------------------------------------------------------
# AEP legacy mapping
# ---------------------------------------------------------------------------


class TestAepMapping:
    @pytest.mark.parametrize(
        "aep, expected",
        [
            ("succeeded", RunStatus.SUCCEEDED),
            ("failed", RunStatus.FAILED),
            ("timed_out", RunStatus.FAILED),
            ("stalled_no_progress", RunStatus.FAILED),
            ("contract_error", RunStatus.FAILED),
            ("partial", RunStatus.NEEDS_REVIEW),
            ("policy_blocked", RunStatus.NEEDS_REVIEW),
        ],
    )
    def test_driver_status_mapping(self, aep, expected):
        assert aep_driver_status_to_run(aep) == expected

    @pytest.mark.parametrize(
        "aep, expected",
        [
            ("ready_for_promotion", RunStatus.SUCCEEDED),
            ("promoted", RunStatus.SUCCEEDED),
            ("blocked", RunStatus.NEEDS_REVIEW),
            ("failed", RunStatus.FAILED),
            ("human_review", RunStatus.NEEDS_REVIEW),
        ],
    )
    def test_final_status_mapping(self, aep, expected):
        assert aep_final_status_to_run(aep) == expected

    def test_unknown_driver_status_raises(self):
        with pytest.raises(KeyError):
            aep_driver_status_to_run("unknown_status")

    def test_unknown_final_status_raises(self):
        with pytest.raises(KeyError):
            aep_final_status_to_run("unknown_status")
