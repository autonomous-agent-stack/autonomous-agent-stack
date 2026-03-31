"""Tests for fake worker adapters (C7-C10).

C7: Fake Linux worker adapter
C8: Fake Windows/Yingdao worker adapter
C9: Worker heartbeat/lease/timeout simulation
C10: Failure taxonomy fixture
"""

from __future__ import annotations

from autoresearch.shared.task_contract import Task
from autoresearch.shared.task_gate_contract import GateAction, GateOutcome, make_gate_verdict
from autoresearch.shared.worker_contract import WorkerStatus, WorkerType
from autoresearch.testing.fake_workers import (
    FAILURE_TAXONOMY,
    FailureCategory,
    FakeLinuxWorker,
    FakeWinYingdaoWorker,
    HeartbeatSimulation,
    LeaseManager,
    get_failure_by_category,
    get_non_retryable_failures,
    get_retryable_failures,
)


def _make_task(task_id: str = "task-test") -> Task:
    return Task(id=task_id, type="software_change", agent_package_id="test-pkg")


# ---------------------------------------------------------------------------
# C7: Fake Linux worker adapter
# ---------------------------------------------------------------------------


class TestFakeLinuxWorker:
    def test_registration(self):
        worker = FakeLinuxWorker()
        reg = worker.registration()
        assert reg.worker_type == WorkerType.LINUX
        assert "shell" in reg.capabilities

    def test_success_execution(self):
        worker = FakeLinuxWorker(default_outcome="success")
        result = worker.execute(_make_task())
        assert result["status"] == "succeeded"
        assert result["data"]["files_changed"] == 2

    def test_timeout_execution(self):
        worker = FakeLinuxWorker(default_outcome="timeout")
        result = worker.execute(_make_task())
        assert result["status"] == "failed"
        assert result["error"]["code"] == "TIMEOUT"
        assert result["error"]["retryable"] is True

    def test_crash_execution(self):
        worker = FakeLinuxWorker(default_outcome="crash")
        result = worker.execute(_make_task())
        assert result["status"] == "failed"
        assert result["error"]["code"] == "CRASH"

    def test_needs_review_execution(self):
        worker = FakeLinuxWorker(default_outcome="needs_review")
        result = worker.execute(_make_task())
        assert result["status"] == "needs_review"

    def test_permission_denied_execution(self):
        worker = FakeLinuxWorker(default_outcome="permission_denied")
        result = worker.execute(_make_task())
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert result["error"]["retryable"] is False

    def test_override_outcome_per_task(self):
        worker = FakeLinuxWorker(default_outcome="success")
        result = worker.execute(_make_task(), outcome="timeout")
        assert result["status"] == "failed"
        assert result["error"]["code"] == "TIMEOUT"

    def test_execution_log(self):
        worker = FakeLinuxWorker()
        worker.execute(_make_task("t1"))
        worker.execute(_make_task("t2"))
        assert len(worker.execution_log) == 2
        assert worker.execution_log[0]["task_id"] == "t1"
        assert worker.execution_log[1]["task_id"] == "t2"

    def test_heartbeat_idle(self):
        worker = FakeLinuxWorker()
        hb = worker.heartbeat()
        assert hb.status == WorkerStatus.ONLINE
        assert len(hb.active_task_ids) == 0

    def test_heartbeat_during_execution(self):
        worker = FakeLinuxWorker()
        task = _make_task()
        worker._current_task = task
        hb = worker.heartbeat()
        assert hb.status == WorkerStatus.BUSY
        assert task.id in hb.active_task_ids


# ---------------------------------------------------------------------------
# C8: Fake Windows/Yingdao worker adapter
# ---------------------------------------------------------------------------


class TestFakeWinYingdaoWorker:
    def test_registration(self):
        worker = FakeWinYingdaoWorker()
        reg = worker.registration()
        assert reg.worker_type == WorkerType.WIN_YINGDAO
        assert "form_fill" in reg.capabilities
        assert "yingdao_flow" in reg.capabilities

    def test_success_execution(self):
        worker = FakeWinYingdaoWorker(default_outcome="success")
        result = worker.execute(_make_task())
        assert result["status"] == "succeeded"
        assert result["data"]["forms_filled"] == 1

    def test_form_not_found_execution(self):
        worker = FakeWinYingdaoWorker(default_outcome="form_not_found")
        result = worker.execute(_make_task())
        assert result["status"] == "failed"
        assert result["error"]["code"] == "FORM_NOT_FOUND"

    def test_network_error_execution(self):
        worker = FakeWinYingdaoWorker(default_outcome="network_error")
        result = worker.execute(_make_task())
        assert result["error"]["code"] == "NETWORK_ERROR"
        assert result["error"]["retryable"] is True

    def test_needs_review_execution(self):
        worker = FakeWinYingdaoWorker(default_outcome="needs_review")
        result = worker.execute(_make_task())
        assert result["status"] == "needs_review"

    def test_override_outcome(self):
        worker = FakeWinYingdaoWorker(default_outcome="success")
        result = worker.execute(_make_task(), outcome="network_error")
        assert result["error"]["code"] == "NETWORK_ERROR"

    def test_heartbeat_idle(self):
        worker = FakeWinYingdaoWorker()
        hb = worker.heartbeat()
        assert hb.status == WorkerStatus.ONLINE

    def test_heartbeat_during_execution(self):
        worker = FakeWinYingdaoWorker()
        task = _make_task()
        worker._current_task = task
        hb = worker.heartbeat()
        assert hb.status == WorkerStatus.BUSY


# ---------------------------------------------------------------------------
# C9: Heartbeat / lease / timeout simulation
# ---------------------------------------------------------------------------


class TestHeartbeatSimulation:
    def test_online_when_fresh(self):
        sim = HeartbeatSimulation(worker_id="test")
        status = sim.simulate_heartbeat_age(0)
        assert status == WorkerStatus.ONLINE

    def test_online_within_interval(self):
        sim = HeartbeatSimulation(worker_id="test")
        status = sim.simulate_heartbeat_age(30)
        assert status == WorkerStatus.ONLINE

    def test_degraded_when_stale(self):
        sim = HeartbeatSimulation(worker_id="test")
        status = sim.simulate_heartbeat_age(60)
        assert status == WorkerStatus.DEGRADED

    def test_degraded_before_dead(self):
        sim = HeartbeatSimulation(worker_id="test")
        status = sim.simulate_heartbeat_age(200)
        assert status == WorkerStatus.DEGRADED

    def test_offline_when_dead(self):
        sim = HeartbeatSimulation(worker_id="test")
        status = sim.simulate_heartbeat_age(400)
        assert status == WorkerStatus.OFFLINE

    def test_busy_when_task_running(self):
        sim = HeartbeatSimulation(worker_id="test")
        sim.acquire_lease("task-1")
        status = sim.simulate_heartbeat_age(0)
        assert status == WorkerStatus.BUSY

    def test_acquire_lease(self):
        sim = HeartbeatSimulation(worker_id="test")
        assert sim.acquire_lease("task-1") is True
        assert sim._current_task_id == "task-1"

    def test_cannot_double_lease(self):
        sim = HeartbeatSimulation(worker_id="test")
        sim.acquire_lease("task-1")
        assert sim.acquire_lease("task-2") is False

    def test_release_lease(self):
        sim = HeartbeatSimulation(worker_id="test")
        sim.acquire_lease("task-1")
        sim.release_lease()
        assert sim._current_task_id is None
        assert sim.acquire_lease("task-2") is True

    def test_tick_heartbeat_returns_payload(self):
        sim = HeartbeatSimulation(worker_id="test")
        hb = sim.tick_heartbeat()
        assert hb.worker_id == "test"
        assert hb.status == WorkerStatus.ONLINE


class TestLeaseManager:
    def test_acquire_lease(self):
        lm = LeaseManager()
        assert lm.acquire("task-1", "worker-1") is True
        assert lm.is_leased("task-1")

    def test_cannot_reacquire(self):
        lm = LeaseManager()
        lm.acquire("task-1", "worker-1")
        assert lm.acquire("task-1", "worker-2") is False

    def test_release_lease(self):
        lm = LeaseManager()
        lm.acquire("task-1", "worker-1")
        lm.release("task-1")
        assert not lm.is_leased("task-1")

    def test_simulate_timeout_not_expired(self):
        lm = LeaseManager(lease_timeout_sec=900)
        assert lm.simulate_timeout_check("task-1", 100) is False

    def test_simulate_timeout_expired(self):
        lm = LeaseManager(lease_timeout_sec=900)
        assert lm.simulate_timeout_check("task-1", 1000) is True

    def test_simulate_timeout_exactly_at_boundary(self):
        lm = LeaseManager(lease_timeout_sec=900)
        assert lm.simulate_timeout_check("task-1", 900) is False

    def test_simulate_timeout_just_past(self):
        lm = LeaseManager(lease_timeout_sec=900)
        assert lm.simulate_timeout_check("task-1", 901) is True

    def test_multiple_leases(self):
        lm = LeaseManager()
        lm.acquire("task-1", "worker-1")
        lm.acquire("task-2", "worker-2")
        assert lm.is_leased("task-1")
        assert lm.is_leased("task-2")
        lm.release("task-1")
        assert not lm.is_leased("task-1")
        assert lm.is_leased("task-2")


# ---------------------------------------------------------------------------
# C10: Failure taxonomy fixture
# ---------------------------------------------------------------------------


class TestFailureTaxonomy:
    def test_taxonomy_has_entries(self):
        assert len(FAILURE_TAXONOMY) == 10

    def test_all_categories_covered(self):
        categories = {f.category for f in FAILURE_TAXONOMY}
        for cat in FailureCategory:
            assert cat in categories, f"Missing category: {cat}"

    def test_each_scenario_has_required_fields(self):
        for f in FAILURE_TAXONOMY:
            assert f.name
            assert f.error_code
            assert f.error_message
            assert isinstance(f.retryable, bool)
            assert f.gate_outcome in GateOutcome
            assert f.expected_gate_action in GateAction

    def test_get_by_category(self):
        timeouts = get_failure_by_category(FailureCategory.TIMEOUT)
        assert len(timeouts) >= 1
        assert all(f.category == FailureCategory.TIMEOUT for f in timeouts)

    def test_get_retryable(self):
        retryable = get_retryable_failures()
        assert len(retryable) >= 1
        assert all(f.retryable for f in retryable)

    def test_get_non_retryable(self):
        non_retryable = get_non_retryable_failures()
        assert len(non_retryable) >= 1
        assert all(not f.retryable for f in non_retryable)

    def test_retryable_plus_non_retryable_equals_total(self):
        retryable = get_retryable_failures()
        non_retryable = get_non_retryable_failures()
        assert len(retryable) + len(non_retryable) == len(FAILURE_TAXONOMY)

    def test_gate_outcome_matches_expected_action(self):
        """Verify the expected gate action is consistent with the outcome."""
        for f in FAILURE_TAXONOMY:
            v = make_gate_verdict(
                f.gate_outcome,
                retry_attempt=0,
                max_retries=3,
            )
            # The expected action should match the default action for that outcome
            # (at retry_attempt=0, no exhaustion upgrade)
            assert f.expected_gate_action == v.action or f.gate_outcome in {
                GateOutcome.NEEDS_HUMAN_CONFIRM,
                GateOutcome.MISSING_ARTIFACTS,
            }

    def test_overreach_is_not_retryable(self):
        overreach = [f for f in FAILURE_TAXONOMY if f.category == FailureCategory.OVERREACH]
        assert len(overreach) == 1
        assert overreach[0].retryable is False
        assert overreach[0].expected_gate_action == GateAction.REJECT

    def test_permission_denied_is_not_retryable(self):
        perm = [f for f in FAILURE_TAXONOMY if f.category == FailureCategory.PERMISSION_DENIED]
        assert len(perm) == 1
        assert perm[0].retryable is False

    def test_disk_full_is_not_retryable(self):
        disk = [f for f in FAILURE_TAXONOMY if f.category == FailureCategory.DISK_FULL]
        assert len(disk) == 1
        assert disk[0].retryable is False
