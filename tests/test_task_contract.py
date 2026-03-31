"""Tests for the unified task contract."""

from __future__ import annotations

import pytest

from autoresearch.shared.models import JobStatus
from autoresearch.shared.housekeeper_contract import HousekeeperTaskStatus
from autoresearch.shared.task_contract import (
    ApprovalStatus,
    CreateTaskRequest,
    Task,
    TaskError,
    TaskPriority,
    TaskResult,
    TaskStatus,
    housekeeper_status_to_task_status,
    task_status_to_housekeeper_status,
    is_valid_transition,
    job_status_to_task_status,
    task_status_to_job_status,
)

# ---------------------------------------------------------------------------
# TaskStatus enum
# ---------------------------------------------------------------------------


class TestTaskStatus:
    def test_all_values_are_lowercase_strings(self):
        for s in TaskStatus:
            assert s.value == s.value.lower()

    def test_core_lifecycle_present(self):
        assert TaskStatus.PENDING
        assert TaskStatus.QUEUED
        assert TaskStatus.RUNNING
        assert TaskStatus.SUCCEEDED
        assert TaskStatus.FAILED

    def test_approval_states_present(self):
        assert TaskStatus.APPROVAL_REQUIRED
        assert TaskStatus.NEEDS_REVIEW
        assert TaskStatus.REJECTED

    def test_cancelled_present(self):
        assert TaskStatus.CANCELLED


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------


class TestTask:
    def test_minimal_task(self):
        t = Task(id="t1", type="software_change", agent_package_id="pkg-1")
        assert t.status == TaskStatus.PENDING
        assert t.priority == TaskPriority.MEDIUM
        assert t.result is None
        assert t.requires_approval is False

    def test_full_task(self):
        t = Task(
            id="t2",
            type="linux_housekeeping",
            agent_package_id="linux-hk",
            input={"goal": "clean /tmp"},
            status=TaskStatus.RUNNING,
            requires_approval=True,
            approval_status=ApprovalStatus.APPROVED,
            worker_id="worker-1",
            priority=TaskPriority.HIGH,
            tags=["infra"],
            metadata={"source": "housekeeper"},
        )
        assert t.status == TaskStatus.RUNNING
        assert t.priority == TaskPriority.HIGH
        assert t.tags == ["infra"]

    def test_task_with_result(self):
        r = TaskResult(success=True, data={"files_changed": 3})
        t = Task(id="t3", type="test", agent_package_id="pkg", result=r)
        assert t.result.success is True
        assert t.result.data["files_changed"] == 3

    def test_task_with_error(self):
        e = TaskError(code="TIMEOUT", message="worker timed out", retryable=True)
        t = Task(id="t4", type="test", agent_package_id="pkg", error=e)
        assert t.error.code == "TIMEOUT"
        assert t.error.retryable is True

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            Task(id="t5", type="test", agent_package_id="pkg", unknown_field="x")


# ---------------------------------------------------------------------------
# CreateTaskRequest
# ---------------------------------------------------------------------------


class TestCreateTaskRequest:
    def test_minimal(self):
        r = CreateTaskRequest(type="software_change", agent_package_id="pkg")
        assert r.priority == TaskPriority.MEDIUM
        assert r.requires_approval is False

    def test_with_all_fields(self):
        r = CreateTaskRequest(
            type="linux_housekeeping",
            agent_package_id="linux-hk",
            input={"goal": "clean"},
            created_by="housekeeper",
            priority=TaskPriority.CRITICAL,
            tags=["urgent"],
            requires_approval=True,
            max_retries=5,
            timeout_seconds=600,
        )
        assert r.max_retries == 5
        assert r.timeout_seconds == 600


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_happy_path(self):
        assert is_valid_transition(TaskStatus.PENDING, TaskStatus.QUEUED)
        assert is_valid_transition(TaskStatus.QUEUED, TaskStatus.RUNNING)
        assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.SUCCEEDED)

    def test_failure_path(self):
        assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.FAILED)

    def test_approval_path(self):
        assert is_valid_transition(TaskStatus.PENDING, TaskStatus.APPROVAL_REQUIRED)
        assert is_valid_transition(TaskStatus.APPROVAL_REQUIRED, TaskStatus.QUEUED)
        assert is_valid_transition(TaskStatus.APPROVAL_REQUIRED, TaskStatus.REJECTED)

    def test_retry_from_failed(self):
        assert is_valid_transition(TaskStatus.FAILED, TaskStatus.QUEUED)

    def test_needs_review_path(self):
        assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.NEEDS_REVIEW)
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.SUCCEEDED)
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.FAILED)

    def test_invalid_terminal_transitions(self):
        assert not is_valid_transition(TaskStatus.SUCCEEDED, TaskStatus.RUNNING)
        assert not is_valid_transition(TaskStatus.REJECTED, TaskStatus.QUEUED)
        assert not is_valid_transition(TaskStatus.CANCELLED, TaskStatus.RUNNING)

    def test_invalid_backwards(self):
        assert not is_valid_transition(TaskStatus.RUNNING, TaskStatus.PENDING)
        assert not is_valid_transition(TaskStatus.SUCCEEDED, TaskStatus.PENDING)


# ---------------------------------------------------------------------------
# Legacy JobStatus mapping
# ---------------------------------------------------------------------------


class TestLegacyMapping:
    def test_all_job_statuses_mapped(self):
        for js in JobStatus:
            ts = job_status_to_task_status(js)
            assert isinstance(ts, TaskStatus)

    def test_all_task_statuses_mapped_back(self):
        for ts in TaskStatus:
            js = task_status_to_job_status(ts)
            assert isinstance(js, JobStatus)

    def test_roundtrip_core_states(self):
        for js in [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]:
            ts = job_status_to_task_status(js)
            js_back = task_status_to_job_status(ts)
            assert js_back == js, f"{js} -> {ts} -> {js_back}"

    def test_created_maps_to_pending(self):
        assert job_status_to_task_status(JobStatus.CREATED) == TaskStatus.PENDING

    def test_interrupted_maps_to_failed(self):
        assert job_status_to_task_status(JobStatus.INTERRUPTED) == TaskStatus.FAILED

    def test_completed_maps_to_succeeded(self):
        assert job_status_to_task_status(JobStatus.COMPLETED) == TaskStatus.SUCCEEDED


class TestHousekeeperTaskStatusMapping:
    """Bidirectional mapping between unified TaskStatus and HousekeeperTaskStatus."""

    @pytest.mark.parametrize(
        "hs, expected",
        [
            (HousekeeperTaskStatus.CREATED, TaskStatus.PENDING),
            (HousekeeperTaskStatus.QUEUED, TaskStatus.QUEUED),
            (HousekeeperTaskStatus.RUNNING, TaskStatus.RUNNING),
            (HousekeeperTaskStatus.COMPLETED, TaskStatus.SUCCEEDED),
            (HousekeeperTaskStatus.FAILED, TaskStatus.FAILED),
            (HousekeeperTaskStatus.REJECTED, TaskStatus.REJECTED),
            (HousekeeperTaskStatus.APPROVAL_REQUIRED, TaskStatus.APPROVAL_REQUIRED),
            (HousekeeperTaskStatus.CLARIFICATION_REQUIRED, TaskStatus.NEEDS_REVIEW),
        ],
    )
    def test_housekeeper_to_unified(self, hs, expected):
        assert housekeeper_status_to_task_status(hs) == expected

    def test_roundtrip_core_states(self):
        for hs in [
            HousekeeperTaskStatus.QUEUED,
            HousekeeperTaskStatus.RUNNING,
            HousekeeperTaskStatus.COMPLETED,
            HousekeeperTaskStatus.FAILED,
        ]:
            ts = housekeeper_status_to_task_status(hs)
            hs_back = task_status_to_housekeeper_status(ts)
            assert hs_back == hs

    def test_all_housekeeper_statuses_mapped(self):
        for hs in HousekeeperTaskStatus:
            ts = housekeeper_status_to_task_status(hs)
            assert isinstance(ts, TaskStatus)

    def test_all_task_statuses_mapped_back(self):
        for ts in TaskStatus:
            hs = task_status_to_housekeeper_status(ts)
            assert isinstance(hs, HousekeeperTaskStatus)
