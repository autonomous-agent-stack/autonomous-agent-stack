"""C7-C10: Fake worker adapters and simulation fixtures for offline testing.

These adapters simulate worker behavior without any real connections.
Used by the offline demo runner, gate tests, and fault drills.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from autoresearch.shared.task_contract import Task
from autoresearch.shared.task_gate_contract import GateAction, GateOutcome
from autoresearch.shared.worker_contract import (
    AllowedAction,
    WorkerHeartbeat,
    WorkerMetrics,
    WorkerRegistration,
    WorkerStatus,
    WorkerType,
)

# ---------------------------------------------------------------------------
# C7: Fake Linux worker adapter
# ---------------------------------------------------------------------------


class FakeLinuxWorker:
    """Simulates a Linux housekeeper worker for offline testing.

    Configurable outcomes: success, failure, timeout, needs_review.
    """

    def __init__(
        self,
        worker_id: str = "linux-housekeeper-fake",
        *,
        default_outcome: str = "success",
        task_timeout_sec: int = 900,
        heartbeat_interval_sec: int = 30,
    ) -> None:
        self.worker_id = worker_id
        self.default_outcome = default_outcome
        self.task_timeout_sec = task_timeout_sec
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self._execution_log: list[dict[str, Any]] = []
        self._current_task: Task | None = None
        self._run_count = 0

    def registration(self, status: WorkerStatus = WorkerStatus.ONLINE) -> WorkerRegistration:
        return WorkerRegistration(
            worker_id=self.worker_id,
            name=f"Fake {self.worker_id}",
            worker_type=WorkerType.LINUX,
            capabilities=["shell", "script_runner", "log_collection", "ops_inspection"],
            allowed_actions=[
                AllowedAction.EXECUTE_TASK,
                AllowedAction.RUN_SCRIPT,
                AllowedAction.COLLECT_LOGS,
            ],
            status=status,
            backend_kind="linux_supervisor",
            max_concurrent_tasks=1,
        )

    def heartbeat(self, status: WorkerStatus | None = None) -> WorkerHeartbeat:
        active_tasks = [self._current_task.id] if self._current_task else []
        return WorkerHeartbeat(
            worker_id=self.worker_id,
            status=status or (WorkerStatus.BUSY if self._current_task else WorkerStatus.ONLINE),
            metrics=WorkerMetrics(
                cpu_usage_percent=35.0 if self._current_task else 5.0,
                memory_usage_mb=512.0,
                active_tasks=len(active_tasks),
            ),
            active_task_ids=active_tasks,
        )

    def execute(self, task: Task, *, outcome: str | None = None) -> dict[str, Any]:
        """Simulate executing a task. Returns result dict with status and data."""
        self._current_task = task
        self._run_count += 1
        effective_outcome = outcome or self.default_outcome
        result = self._build_result(task, effective_outcome)
        self._execution_log.append(
            {
                "task_id": task.id,
                "run_count": self._run_count,
                "outcome": effective_outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._current_task = None
        return result

    def _build_result(self, task: Task, outcome: str) -> dict[str, Any]:
        if outcome == "success":
            return {
                "status": "succeeded",
                "data": {"files_changed": 2, "commands_run": 5},
                "error": None,
            }
        elif outcome == "timeout":
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Worker timed out after {self.task_timeout_sec}s",
                    "retryable": True,
                    "suggested_action": "retry",
                },
            }
        elif outcome == "needs_review":
            return {
                "status": "needs_review",
                "data": {"partial_changes": True},
                "error": None,
            }
        elif outcome == "crash":
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "CRASH",
                    "message": "Worker process crashed with exit code 137",
                    "retryable": True,
                    "suggested_action": "retry",
                },
            }
        elif outcome == "permission_denied":
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Insufficient permissions to modify target files",
                    "retryable": False,
                    "suggested_action": "manual",
                },
            }
        else:
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "UNKNOWN",
                    "message": f"Unknown outcome: {outcome}",
                    "retryable": False,
                    "suggested_action": "manual",
                },
            }

    @property
    def execution_log(self) -> list[dict[str, Any]]:
        return list(self._execution_log)


# ---------------------------------------------------------------------------
# C8: Fake Windows/Yingdao worker adapter
# ---------------------------------------------------------------------------


class FakeWinYingdaoWorker:
    """Simulates a Windows Yingdao worker for offline testing.

    Supports form_fill and yingdao_flow capabilities.
    """

    def __init__(
        self,
        worker_id: str = "win-yingdao-fake",
        *,
        default_outcome: str = "success",
    ) -> None:
        self.worker_id = worker_id
        self.default_outcome = default_outcome
        self._execution_log: list[dict[str, Any]] = []
        self._current_task: Task | None = None

    def registration(self, status: WorkerStatus = WorkerStatus.OFFLINE) -> WorkerRegistration:
        return WorkerRegistration(
            worker_id=self.worker_id,
            name=f"Fake {self.worker_id}",
            worker_type=WorkerType.WIN_YINGDAO,
            capabilities=["yingdao_flow", "form_fill", "structured_data_entry", "erp_form_fill"],
            allowed_actions=[
                AllowedAction.EXECUTE_TASK,
                AllowedAction.FILL_FORM,
                AllowedAction.RUN_FLOW,
            ],
            status=status,
            backend_kind="win_yingdao",
            max_concurrent_tasks=1,
        )

    def heartbeat(self, status: WorkerStatus | None = None) -> WorkerHeartbeat:
        active_tasks = [self._current_task.id] if self._current_task else []
        return WorkerHeartbeat(
            worker_id=self.worker_id,
            status=status or (WorkerStatus.BUSY if self._current_task else WorkerStatus.ONLINE),
            metrics=WorkerMetrics(
                cpu_usage_percent=25.0 if self._current_task else 2.0,
                memory_usage_mb=1024.0,
                active_tasks=len(active_tasks),
            ),
            active_task_ids=active_tasks,
        )

    def execute(self, task: Task, *, outcome: str | None = None) -> dict[str, Any]:
        effective_outcome = outcome or self.default_outcome
        self._current_task = task
        self._execution_log.append(
            {
                "task_id": task.id,
                "outcome": effective_outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._current_task = None

        if effective_outcome == "success":
            return {
                "status": "succeeded",
                "data": {"forms_filled": 1, "flow_completed": True},
                "error": None,
            }
        elif effective_outcome == "form_not_found":
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "FORM_NOT_FOUND",
                    "message": "Target form element not found on page",
                    "retryable": True,
                    "suggested_action": "retry",
                },
            }
        elif effective_outcome == "network_error":
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "NETWORK_ERROR",
                    "message": "Connection to Yingdao server lost",
                    "retryable": True,
                    "suggested_action": "retry",
                },
            }
        elif effective_outcome == "needs_review":
            return {
                "status": "needs_review",
                "data": {"partial_form": True, "screenshot_path": "/tmp/partial.png"},
                "error": None,
            }
        else:
            return {
                "status": "failed",
                "data": None,
                "error": {
                    "code": "UNKNOWN",
                    "message": f"Unknown outcome: {effective_outcome}",
                    "retryable": False,
                    "suggested_action": "manual",
                },
            }

    @property
    def execution_log(self) -> list[dict[str, Any]]:
        return list(self._execution_log)


# ---------------------------------------------------------------------------
# C9: Worker heartbeat / lease / timeout simulation
# ---------------------------------------------------------------------------


@dataclass
class HeartbeatSimulation:
    """Simulates heartbeat progression over time for a worker.

    Tracks heartbeat age and derives worker status from it:
      - age <= 30s: ONLINE (or BUSY if executing)
      - 30s < age <= 120s: DEGRADED
      - 120s < age <= 300s: stale (still trying)
      - age > 300s: OFFLINE (dead)
    """

    worker_id: str
    heartbeat_interval_sec: int = 30
    stale_threshold_sec: int = 120
    dead_threshold_sec: int = 300

    _last_heartbeat_time: float = field(default_factory=time.monotonic)
    _current_task_id: str | None = None
    _lease_acquired: bool = False

    def tick_heartbeat(self) -> WorkerHeartbeat:
        """Record a heartbeat tick and return the heartbeat payload."""
        self._last_heartbeat_time = time.monotonic()
        status = self._derive_status()
        return WorkerHeartbeat(
            worker_id=self.worker_id,
            status=status,
            metrics=WorkerMetrics(active_tasks=1 if self._current_task_id else 0),
            active_task_ids=[self._current_task_id] if self._current_task_id else [],
        )

    def acquire_lease(self, task_id: str) -> bool:
        """Attempt to acquire a lease for a task."""
        if self._current_task_id is not None:
            return False  # already leased
        self._current_task_id = task_id
        self._lease_acquired = True
        return True

    def release_lease(self) -> None:
        """Release the current lease."""
        self._current_task_id = None
        self._lease_acquired = False

    def simulate_heartbeat_age(self, age_seconds: float) -> WorkerStatus:
        """Simulate what the worker status would be given a heartbeat age."""
        if age_seconds <= self.heartbeat_interval_sec:
            return WorkerStatus.BUSY if self._current_task_id else WorkerStatus.ONLINE
        elif age_seconds <= self.stale_threshold_sec:
            return WorkerStatus.DEGRADED
        elif age_seconds <= self.dead_threshold_sec:
            return WorkerStatus.DEGRADED
        else:
            return WorkerStatus.OFFLINE

    def _derive_status(self) -> WorkerStatus:
        age = time.monotonic() - self._last_heartbeat_time
        return self.simulate_heartbeat_age(age)


@dataclass
class LeaseManager:
    """Manages lease acquisition and timeout for tasks on workers."""

    _leases: dict[str, str] = field(default_factory=dict)  # task_id -> worker_id
    _lease_times: dict[str, float] = field(default_factory=dict)  # task_id -> timestamp
    lease_timeout_sec: int = 900

    def acquire(self, task_id: str, worker_id: str) -> bool:
        if task_id in self._leases:
            return False
        self._leases[task_id] = worker_id
        self._lease_times[task_id] = time.monotonic()
        return True

    def release(self, task_id: str) -> None:
        self._leases.pop(task_id, None)
        self._lease_times.pop(task_id, None)

    def is_leased(self, task_id: str) -> bool:
        return task_id in self._leases

    def check_timeouts(self) -> list[str]:
        """Return list of task IDs whose leases have timed out."""
        now = time.monotonic()
        timed_out = []
        for task_id, lease_time in self._lease_times.items():
            if now - lease_time > self.lease_timeout_sec:
                timed_out.append(task_id)
        return timed_out

    def simulate_timeout_check(self, task_id: str, elapsed_seconds: float) -> bool:
        """Check if a task would be timed out given elapsed time."""
        return elapsed_seconds > self.lease_timeout_sec


# ---------------------------------------------------------------------------
# C10: Failure taxonomy fixture
# ---------------------------------------------------------------------------


class FailureCategory(str, Enum):
    """Taxonomy of failure categories."""

    TIMEOUT = "timeout"
    CRASH = "crash"
    OVERREACH = "overreach"
    MISSING_ARTIFACTS = "missing_artifacts"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    CONTRACT_ERROR = "contract_error"
    STALL = "stall"
    OOM = "oom"
    DISK_FULL = "disk_full"


@dataclass(frozen=True)
class FailureScenario:
    """A single failure scenario with all details needed for fault drill."""

    name: str
    category: FailureCategory
    error_code: str
    error_message: str
    retryable: bool
    suggested_action: str
    gate_outcome: GateOutcome
    expected_gate_action: GateAction
    description: str = ""


FAILURE_TAXONOMY: list[FailureScenario] = [
    FailureScenario(
        name="worker_timeout",
        category=FailureCategory.TIMEOUT,
        error_code="TIMEOUT",
        error_message="Worker exceeded 900s timeout",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        description="Worker process exceeds configured task timeout",
    ),
    FailureScenario(
        name="worker_crash",
        category=FailureCategory.CRASH,
        error_code="CRASH",
        error_message="Worker process crashed with exit code 137 (OOM killed)",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        description="Worker process killed by OS (OOM, signal, etc.)",
    ),
    FailureScenario(
        name="scope_overreach",
        category=FailureCategory.OVERREACH,
        error_code="OVERREACH",
        error_message="Agent modified files outside allowed scope",
        retryable=False,
        suggested_action="reject",
        gate_outcome=GateOutcome.OVERREACH,
        expected_gate_action=GateAction.REJECT,
        description="Agent attempted to modify files not in the allowed list",
    ),
    FailureScenario(
        name="missing_screenshot",
        category=FailureCategory.MISSING_ARTIFACTS,
        error_code="MISSING_ARTIFACT",
        error_message="Expected screenshot artifact not found",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.MISSING_ARTIFACTS,
        expected_gate_action=GateAction.RETRY,
        description="Required output artifact was not produced",
    ),
    FailureScenario(
        name="permission_denied",
        category=FailureCategory.PERMISSION_DENIED,
        error_code="PERMISSION_DENIED",
        error_message="Insufficient permissions to modify target files",
        retryable=False,
        suggested_action="manual",
        gate_outcome=GateOutcome.NEEDS_HUMAN_CONFIRM,
        expected_gate_action=GateAction.NEEDS_REVIEW,
        description="Worker lacks file system permissions for the operation",
    ),
    FailureScenario(
        name="network_partition",
        category=FailureCategory.NETWORK_ERROR,
        error_code="NETWORK_ERROR",
        error_message="Connection to external service lost",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        description="Network connectivity lost during execution",
    ),
    FailureScenario(
        name="contract_violation",
        category=FailureCategory.CONTRACT_ERROR,
        error_code="CONTRACT_ERROR",
        error_message="Worker returned invalid response format",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.NEEDS_HUMAN_CONFIRM,
        expected_gate_action=GateAction.NEEDS_REVIEW,
        description="Worker response doesn't conform to the expected contract",
    ),
    FailureScenario(
        name="progress_stall",
        category=FailureCategory.STALL,
        error_code="STALL",
        error_message="No progress detected for 600s",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        description="Worker is alive but making no forward progress",
    ),
    FailureScenario(
        name="out_of_memory",
        category=FailureCategory.OOM,
        error_code="OOM",
        error_message="Worker process killed: out of memory",
        retryable=True,
        suggested_action="retry",
        gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        description="Worker consumed too much memory and was killed",
    ),
    FailureScenario(
        name="disk_full",
        category=FailureCategory.DISK_FULL,
        error_code="DISK_FULL",
        error_message="No space left on device",
        retryable=False,
        suggested_action="manual",
        gate_outcome=GateOutcome.NEEDS_HUMAN_CONFIRM,
        expected_gate_action=GateAction.NEEDS_REVIEW,
        description="Worker ran out of disk space during execution",
    ),
]


def get_failure_by_category(category: FailureCategory) -> list[FailureScenario]:
    """Get all failure scenarios in a given category."""
    return [f for f in FAILURE_TAXONOMY if f.category == category]


def get_retryable_failures() -> list[FailureScenario]:
    """Get all retryable failure scenarios."""
    return [f for f in FAILURE_TAXONOMY if f.retryable]


def get_non_retryable_failures() -> list[FailureScenario]:
    """Get all non-retryable failure scenarios."""
    return [f for f in FAILURE_TAXONOMY if not f.retryable]
