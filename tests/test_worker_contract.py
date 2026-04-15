"""Tests for the unified worker registration contract."""

from __future__ import annotations

import pytest

from autoresearch.shared.housekeeper_contract import WorkerAvailabilityStatus
from autoresearch.shared.worker_contract import (
    AllowedAction,
    WorkerHeartbeat,
    WorkerMetrics,
    WorkerQuery,
    WorkerRegistration,
    WorkerStatus,
    WorkerTimeoutDefaults,
    WorkerType,
    legacy_worker_status_to_unified,
    worker_status_rank,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestWorkerType:
    def test_all_types_present(self):
        assert WorkerType.LINUX
        assert WorkerType.MAC
        assert WorkerType.WIN_YINGDAO
        assert WorkerType.OPENCLAW

    def test_values_match_ts_spec(self):
        assert WorkerType.LINUX.value == "linux"
        assert WorkerType.MAC.value == "mac"
        assert WorkerType.WIN_YINGDAO.value == "win_yingdao"
        assert WorkerType.OPENCLAW.value == "openclaw"


class TestWorkerStatus:
    def test_all_states_present(self):
        assert WorkerStatus.ONLINE
        assert WorkerStatus.OFFLINE
        assert WorkerStatus.BUSY
        assert WorkerStatus.DEGRADED

    def test_values_match_ts_spec(self):
        assert WorkerStatus.ONLINE.value == "online"
        assert WorkerStatus.OFFLINE.value == "offline"
        assert WorkerStatus.BUSY.value == "busy"
        assert WorkerStatus.DEGRADED.value == "degraded"


# ---------------------------------------------------------------------------
# WorkerRegistration
# ---------------------------------------------------------------------------


class TestWorkerRegistration:
    def test_minimal_registration(self):
        w = WorkerRegistration(worker_id="w1", name="linux-01", worker_type=WorkerType.LINUX)
        assert w.status == WorkerStatus.OFFLINE
        assert w.capabilities == []
        assert w.allowed_actions == []
        assert w.registered_at is not None
        assert w.last_heartbeat is None
        assert w.max_concurrent_tasks == 1

    def test_full_registration(self):
        w = WorkerRegistration(
            worker_id="w2",
            name="yingdao-win01",
            worker_type=WorkerType.WIN_YINGDAO,
            capabilities=["yingdao_flow", "form_fill"],
            allowed_actions=[AllowedAction.EXECUTE_TASK, AllowedAction.CAPTURE_SCREENSHOT],
            status=WorkerStatus.ONLINE,
            max_concurrent_tasks=2,
            backend_kind="win_yingdao",
            timeout_defaults=WorkerTimeoutDefaults(task_timeout_sec=1800),
            metadata={"host": "win-server-01"},
        )
        assert w.worker_type == WorkerType.WIN_YINGDAO
        assert AllowedAction.CAPTURE_SCREENSHOT in w.allowed_actions
        assert w.timeout_defaults.task_timeout_sec == 1800

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            WorkerRegistration(worker_id="w3", name="x", worker_type=WorkerType.LINUX, unknown="x")


# ---------------------------------------------------------------------------
# WorkerHeartbeat
# ---------------------------------------------------------------------------


class TestWorkerHeartbeat:
    def test_minimal_heartbeat(self):
        h = WorkerHeartbeat(worker_id="w1")
        assert h.status == WorkerStatus.ONLINE
        assert h.metrics.active_tasks == 0

    def test_heartbeat_with_metrics(self):
        m = WorkerMetrics(cpu_usage_percent=45.2, memory_usage_mb=512, active_tasks=2)
        h = WorkerHeartbeat(worker_id="w1", status=WorkerStatus.BUSY, metrics=m)
        assert h.metrics.cpu_usage_percent == 45.2
        assert h.active_task_ids == []

    def test_heartbeat_with_active_tasks(self):
        h = WorkerHeartbeat(
            worker_id="w1",
            status=WorkerStatus.BUSY,
            active_task_ids=["t1", "t2"],
        )
        assert len(h.active_task_ids) == 2


# ---------------------------------------------------------------------------
# Timeout defaults
# ---------------------------------------------------------------------------


class TestTimeoutDefaults:
    def test_defaults(self):
        t = WorkerTimeoutDefaults()
        assert t.task_timeout_sec == 900
        assert t.heartbeat_interval_sec == 30
        assert t.heartbeat_stale_sec == 120
        assert t.heartbeat_dead_sec == 300

    def test_custom(self):
        t = WorkerTimeoutDefaults(task_timeout_sec=3600)
        assert t.task_timeout_sec == 3600


# ---------------------------------------------------------------------------
# Status ranking
# ---------------------------------------------------------------------------


class TestStatusRanking:
    def test_ordering(self):
        assert worker_status_rank(WorkerStatus.ONLINE) < worker_status_rank(WorkerStatus.BUSY)
        assert worker_status_rank(WorkerStatus.BUSY) < worker_status_rank(WorkerStatus.DEGRADED)
        assert worker_status_rank(WorkerStatus.DEGRADED) < worker_status_rank(WorkerStatus.OFFLINE)


# ---------------------------------------------------------------------------
# Legacy mapping
# ---------------------------------------------------------------------------


class TestLegacyMapping:
    def test_all_legacy_mapped(self):
        for ls in WorkerAvailabilityStatus:
            us = legacy_worker_status_to_unified(ls)
            assert isinstance(us, WorkerStatus)

    def test_values_match(self):
        assert (
            legacy_worker_status_to_unified(WorkerAvailabilityStatus.ONLINE) == WorkerStatus.ONLINE
        )
        assert (
            legacy_worker_status_to_unified(WorkerAvailabilityStatus.OFFLINE)
            == WorkerStatus.OFFLINE
        )
        assert legacy_worker_status_to_unified(WorkerAvailabilityStatus.BUSY) == WorkerStatus.BUSY
        assert (
            legacy_worker_status_to_unified(WorkerAvailabilityStatus.DEGRADED)
            == WorkerStatus.DEGRADED
        )


# ---------------------------------------------------------------------------
# WorkerQuery
# ---------------------------------------------------------------------------


class TestWorkerQuery:
    def test_defaults(self):
        q = WorkerQuery()
        assert q.limit == 100
        assert q.offset == 0

    def test_filters(self):
        q = WorkerQuery(worker_type=WorkerType.LINUX, status=WorkerStatus.ONLINE)
        assert q.worker_type == WorkerType.LINUX
        assert q.status == WorkerStatus.ONLINE
