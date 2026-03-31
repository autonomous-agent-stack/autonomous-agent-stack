from __future__ import annotations

import json
from pathlib import Path
import sys

from autoresearch.core.services.linux_supervisor import LinuxSupervisorService
from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorConclusion,
    LinuxSupervisorTaskCreateRequest,
    LinuxSupervisorTaskStatus,
)


def _write_helper(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _builder(helper: Path):
    def build(task, run_dir: Path) -> list[str]:
        return [sys.executable, str(helper), str(run_dir), task.run_id]

    return build


def _read_summary(task_dir: Path) -> dict:
    return json.loads((task_dir / "summary.json").read_text(encoding="utf-8"))


def _read_status(task_dir: Path) -> dict:
    return json.loads((task_dir / "status.json").read_text(encoding="utf-8"))


def test_linux_supervisor_success_task_writes_summary_and_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    helper = _write_helper(
        tmp_path / "success_worker.py",
        """from __future__ import annotations
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "events.ndjson").write_text(json.dumps({"type": "attempt_started", "agent_id": "openhands"}) + "\\n", encoding="utf-8")
(run_dir / "progress.txt").write_text("ok\\n", encoding="utf-8")
summary = {
    "run_id": run_id,
    "final_status": "ready_for_promotion",
    "driver_result": {
        "run_id": run_id,
        "agent_id": "openhands",
        "attempt": 1,
        "status": "succeeded",
        "summary": "ok",
        "changed_paths": ["apps/demo/ok.py"],
        "output_artifacts": [],
        "metrics": {},
        "recommended_action": "promote",
        "error": None
    },
    "validation": {"run_id": run_id, "passed": True, "checks": []},
    "promotion_patch_uri": "artifacts/promotion.patch",
    "promotion_preflight": None,
    "promotion": None,
}
(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    task = service.enqueue_task(LinuxSupervisorTaskCreateRequest(prompt="demo"))

    summary = service.run_once()

    assert summary is not None
    assert summary.conclusion is LinuxSupervisorConclusion.SUCCEEDED
    assert summary.status is LinuxSupervisorTaskStatus.COMPLETED
    task_dir = service.queue_root / task.task_id
    assert (task_dir / "heartbeat.json").exists()
    assert (task_dir / "artifacts" / "aep_summary.json").exists()
    assert _read_summary(task_dir)["conclusion"] == "succeeded"
    assert _read_status(task_dir)["status"] == "completed"


def test_linux_supervisor_marks_timeout_when_total_budget_is_hit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    helper = _write_helper(
        tmp_path / "timeout_worker.py",
        """from __future__ import annotations
import time
time.sleep(10)
""",
    )
    service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    task = service.enqueue_task(
        LinuxSupervisorTaskCreateRequest(
            prompt="timeout",
            total_timeout_sec=1,
            stall_timeout_sec=5,
        )
    )

    summary = service.run_once()

    assert summary is not None
    assert summary.conclusion is LinuxSupervisorConclusion.TIMED_OUT
    assert summary.status is LinuxSupervisorTaskStatus.FAILED
    assert _read_summary(service.queue_root / task.task_id)["conclusion"] == "timed_out"


def test_linux_supervisor_marks_stalled_when_progress_stops(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    helper = _write_helper(
        tmp_path / "stalled_worker.py",
        """from __future__ import annotations
import json
from pathlib import Path
import sys
import time

run_dir = Path(sys.argv[1])
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "events.ndjson").write_text(json.dumps({"type": "attempt_started", "agent_id": "openhands"}) + "\\n", encoding="utf-8")
(run_dir / "progress.txt").write_text("once\\n", encoding="utf-8")
time.sleep(10)
""",
    )
    service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    task = service.enqueue_task(
        LinuxSupervisorTaskCreateRequest(
            prompt="stalled",
            total_timeout_sec=5,
            stall_timeout_sec=1,
        )
    )

    summary = service.run_once()

    assert summary is not None
    assert summary.conclusion is LinuxSupervisorConclusion.STALLED_NO_PROGRESS
    assert summary.status is LinuxSupervisorTaskStatus.FAILED
    assert _read_summary(service.queue_root / task.task_id)["conclusion"] == "stalled_no_progress"


def test_linux_supervisor_classifies_mock_fallback_from_events(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    helper = _write_helper(
        tmp_path / "mock_fallback_worker.py",
        """from __future__ import annotations
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
run_dir.mkdir(parents=True, exist_ok=True)
events = [
    {"type": "attempt_started", "agent_id": "openhands"},
    {"type": "attempt_completed", "agent_id": "openhands", "driver_status": "timed_out", "validation_passed": False},
    {"type": "attempt_started", "agent_id": "mock"},
]
(run_dir / "events.ndjson").write_text("\\n".join(json.dumps(item) for item in events) + "\\n", encoding="utf-8")
summary = {
    "run_id": run_id,
    "final_status": "human_review",
    "driver_result": {
        "run_id": run_id,
        "agent_id": "mock",
        "attempt": 2,
        "status": "partial",
        "summary": "mock fallback produced a patch but validation still failed",
        "changed_paths": ["apps/demo/ok.py"],
        "output_artifacts": [],
        "metrics": {},
        "recommended_action": "human_review",
        "error": "validation failed after fallback"
    },
    "validation": {"run_id": run_id, "passed": False, "checks": []},
    "promotion_patch_uri": None,
    "promotion_preflight": None,
    "promotion": None,
}
(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    task = service.enqueue_task(LinuxSupervisorTaskCreateRequest(prompt="fallback"))

    summary = service.run_once()

    assert summary is not None
    assert summary.conclusion is LinuxSupervisorConclusion.MOCK_FALLBACK
    assert summary.used_mock_fallback is True
    assert _read_summary(service.queue_root / task.task_id)["used_mock_fallback"] is True
