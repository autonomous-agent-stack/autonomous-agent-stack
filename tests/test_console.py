"""Tests for the enhanced control-plane console router (D11-D14).

Covers:
- D11: Task list filtering by status and priority
- D12: Worker list with status/capability/heartbeat data
- D13: Run detail with logs, artifacts, and gate verdict
- D14: Approval actions (approve, reject, retry, fallback)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.routers.console import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


# ---------------------------------------------------------------------------
# D11: Task list filtering and status badges
# ---------------------------------------------------------------------------


class TestTaskList:
    def test_list_all_tasks(self):
        resp = client.get("/api/v1/console/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    def test_filter_tasks_by_status_succeeded(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "succeeded"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "succeeded" for t in data)

    def test_filter_tasks_by_status_failed(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "failed"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "failed" for t in data)

    def test_filter_tasks_by_status_approval_required(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "approval_required"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "approval_required" for t in data)

    def test_filter_tasks_by_priority(self):
        resp = client.get("/api/v1/console/tasks", params={"priority": "high"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["priority"] == "high" for t in data)

    def test_filter_tasks_by_status_and_priority(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "running", "priority": "high"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "running" and t["priority"] == "high" for t in data)

    def test_filter_tasks_nonexistent_status(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "nonexistent"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_task_has_priority_field(self):
        resp = client.get("/api/v1/console/tasks")
        data = resp.json()
        for task in data:
            assert "priority" in task

    def test_task_has_tags_field(self):
        resp = client.get("/api/v1/console/tasks")
        data = resp.json()
        for task in data:
            assert "tags" in task

    def test_task_limit_parameter(self):
        resp = client.get("/api/v1/console/tasks", params={"limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 1


# ---------------------------------------------------------------------------
# D12: Worker list with status/capability/last_seen/heartbeat
# ---------------------------------------------------------------------------


class TestWorkerList:
    def test_list_all_workers(self):
        resp = client.get("/api/v1/console/workers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_worker_has_capabilities(self):
        resp = client.get("/api/v1/console/workers")
        data = resp.json()
        for w in data:
            assert "capabilities" in w
            assert isinstance(w["capabilities"], list)
            assert len(w["capabilities"]) > 0

    def test_worker_has_heartbeat_data(self):
        resp = client.get("/api/v1/console/workers")
        data = resp.json()
        for w in data:
            assert "last_heartbeat" in w
            assert "heartbeat_age_seconds" in w

    def test_worker_has_metrics(self):
        resp = client.get("/api/v1/console/workers")
        data = resp.json()
        online_workers = [w for w in data if w["status"] == "online"]
        for w in online_workers:
            assert w["metrics"] is not None
            assert "cpu_usage_percent" in w["metrics"]

    def test_worker_status_values(self):
        resp = client.get("/api/v1/console/workers")
        data = resp.json()
        statuses = {w["status"] for w in data}
        assert "online" in statuses or "offline" in statuses or "degraded" in statuses

    def test_filter_workers_online(self):
        resp = client.get("/api/v1/console/workers", params={"status": "online"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(w["status"] == "online" for w in data)

    def test_filter_workers_offline(self):
        resp = client.get("/api/v1/console/workers", params={"status": "offline"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(w["status"] == "offline" for w in data)


# ---------------------------------------------------------------------------
# D13: Run detail with logs/artifacts/decision trace
# ---------------------------------------------------------------------------


class TestRunDetail:
    def test_run_detail_found(self):
        resp = client.get("/api/v1/console/runs/run-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["run_id"] == "run-001"

    def test_run_has_logs(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        assert "logs" in data["run"]
        assert len(data["run"]["logs"]) > 0

    def test_run_log_entries_have_fields(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        for log in data["run"]["logs"]:
            assert "timestamp" in log
            assert "level" in log
            assert "message" in log

    def test_run_has_artifacts(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        assert "artifacts" in data["run"]
        assert len(data["run"]["artifacts"]) > 0

    def test_run_artifact_entries_have_fields(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        for art in data["run"]["artifacts"]:
            assert "type" in art
            assert "path" in art
            assert "size_bytes" in art

    def test_run_has_gate_verdict(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        assert data["gate_verdict"] is not None
        assert "outcome" in data["gate_verdict"]
        assert "action" in data["gate_verdict"]

    def test_gate_verdict_has_checks(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        assert "checks" in data["gate_verdict"]
        assert len(data["gate_verdict"]["checks"]) > 0

    def test_failed_run_detail(self):
        resp = client.get("/api/v1/console/runs/run-002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["status"] == "failed"
        assert data["run"]["error_message"] is not None

    def test_run_not_found(self):
        resp = client.get("/api/v1/console/runs/nonexistent")
        assert resp.status_code == 404

    def test_run_has_timing_fields(self):
        resp = client.get("/api/v1/console/runs/run-001")
        data = resp.json()
        run = data["run"]
        assert "queued_at" in run
        assert "started_at" in run
        assert "completed_at" in run


# ---------------------------------------------------------------------------
# D14: Approval actions (approve/reject/retry/fallback)
# ---------------------------------------------------------------------------


class TestApprovalActions:
    def test_list_pending_approvals(self):
        resp = client.get("/api/v1/console/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(t["status"] == "approval_required" for t in data)

    def test_approve_task(self):
        # Find an approval_required task
        resp = client.get("/api/v1/console/approvals")
        task_id = resp.json()[0]["id"]
        # Approve it
        resp = client.post(f"/api/v1/console/approvals/{task_id}/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "approved"
        assert data["new_status"] == "queued"

    def test_approve_nonexistent_task(self):
        resp = client.post("/api/v1/console/approvals/nonexistent/approve")
        assert resp.status_code == 404

    def test_approve_non_approval_task(self):
        resp = client.post("/api/v1/console/approvals/task-001/approve")
        assert resp.status_code == 404  # task-001 is succeeded, not approval_required

    def test_reject_task(self):
        # Reset: we need a fresh approval task
        # Since we approved the previous one, check if any remain
        resp = client.get("/api/v1/console/approvals")
        remaining = resp.json()
        if remaining:
            task_id = remaining[0]["id"]
            resp = client.post(f"/api/v1/console/approvals/{task_id}/reject")
            assert resp.status_code == 200
            data = resp.json()
            assert data["action"] == "rejected"
            assert data["new_status"] == "rejected"

    def test_retry_failed_task(self):
        resp = client.post("/api/v1/console/approvals/task-002/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "retried"
        assert data["new_status"] == "queued"

    def test_retry_non_failed_task(self):
        resp = client.post("/api/v1/console/approvals/task-001/retry")
        assert resp.status_code == 404  # task-001 is succeeded, not failed

    def test_fallback_failed_task(self):
        # Reset task-002 back to failed for this test
        from autoresearch.api.routers.console import _MOCK_TASKS
        for t in _MOCK_TASKS:
            if t["id"] == "task-004":
                t["status"] = "failed"
        resp = client.post("/api/v1/console/approvals/task-004/fallback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "fallback"
        assert "fallback_agent" in data

    def test_approval_log_records_actions(self):
        resp = client.get("/api/v1/console/approval-log")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        for entry in data:
            assert "task_id" in entry
            assert "action" in entry
            assert "at" in entry


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


class TestLandingPage:
    def test_landing_page(self):
        resp = client.get("/api/v1/console/")
        assert resp.status_code == 200
        assert "Control Plane Console" in resp.text

    def test_landing_has_task_table(self):
        resp = client.get("/api/v1/console/")
        assert "task-table" in resp.text

    def test_landing_has_worker_table(self):
        resp = client.get("/api/v1/console/")
        assert "worker-table" in resp.text

    def test_landing_has_approval_section(self):
        resp = client.get("/api/v1/console/")
        assert "approval-section" in resp.text

    def test_landing_has_run_detail(self):
        resp = client.get("/api/v1/console/")
        assert "run-detail" in resp.text
