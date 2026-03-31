"""Tests for the control-plane console router."""

from __future__ import annotations

from fastapi.testclient import TestClient

from autoresearch.api.routers.console import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestConsoleEndpoints:
    def test_list_tasks(self):
        resp = client.get("/api/v1/console/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_filter_tasks_by_status(self):
        resp = client.get("/api/v1/console/tasks", params={"status": "succeeded"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "succeeded" for t in data)

    def test_list_workers(self):
        resp = client.get("/api/v1/console/workers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all("worker_id" in w for w in data)

    def test_filter_workers_by_status(self):
        resp = client.get("/api/v1/console/workers", params={"status": "offline"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(w["status"] == "offline" for w in data)

    def test_get_run_found(self):
        resp = client.get("/api/v1/console/runs/run-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["run_id"] == "run-001"
        assert data["gate_verdict"]["outcome"] == "timeout"

    def test_get_run_not_found(self):
        resp = client.get("/api/v1/console/runs/nonexistent")
        assert resp.status_code == 404

    def test_list_approvals(self):
        resp = client.get("/api/v1/console/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(t["status"] == "approval_required" for t in data)

    def test_landing_page(self):
        resp = client.get("/api/v1/console/")
        assert resp.status_code == 200
        assert "Control Plane Console" in resp.text
