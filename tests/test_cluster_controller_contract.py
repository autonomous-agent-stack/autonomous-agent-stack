from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.routers.cluster import router
from autoresearch.core.services.controller_lease import (
    evaluate_controller_state,
    write_controller_state,
)


def test_evaluate_controller_state_marks_fresh_linux_lease_online() -> None:
    now_ts = int(time.time())
    snapshot = evaluate_controller_state(
        {
            "active_controller": "linux",
            "controller_name": "linux",
            "execution_role": "primary",
            "runtime_host": "linux",
            "should_poll": True,
            "reason": "local_primary_online",
            "lease_ttl_seconds": 30,
            "updated_at": now_ts - 5,
        },
        now_ts=now_ts,
    )

    assert snapshot.controller_status == "online"
    assert snapshot.active_controller == "linux"
    assert snapshot.lease_age_seconds == 5
    assert snapshot.lease_expires_at == snapshot.updated_at + 30


def test_evaluate_controller_state_marks_expired_lease_stale() -> None:
    now_ts = int(time.time())
    snapshot = evaluate_controller_state(
        {
            "active_controller": "linux",
            "controller_name": "linux",
            "execution_role": "primary",
            "runtime_host": "linux",
            "should_poll": True,
            "lease_ttl_seconds": 30,
            "updated_at": now_ts - 45,
        },
        now_ts=now_ts,
    )

    assert snapshot.controller_status == "stale"
    assert snapshot.lease_age_seconds == 45


def test_cluster_health_exposes_active_controller_lease(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "active_controller.json"
    write_controller_state(
        state_path,
        {
            "active_controller": "linux",
            "controller_name": "linux",
            "execution_role": "primary",
            "runtime_host": "linux",
            "should_poll": True,
            "reason": "local_primary_online",
            "lease_ttl_seconds": 30,
            "status_signal": "recovered",
            "task_risk_profile": "full",
            "updated_at": int(time.time()) - 2,
        },
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ACTIVE_CONTROLLER_FILE", str(state_path))

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/v1/cluster/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["active_controller"] == "linux"
    assert payload["controller_name"] == "linux"
    assert payload["controller_status"] == "online"
    assert payload["execution_role"] == "primary"
    assert payload["runtime_host"] == "linux"
    assert payload["should_poll"] is True
    assert payload["reason"] == "local_primary_online"
    assert payload["status_signal"] == "recovered"
    assert payload["task_risk_profile"] == "full"
    assert payload["lease_ttl_seconds"] == 30
    assert payload["lease_expires_at"] >= payload["updated_at"]
