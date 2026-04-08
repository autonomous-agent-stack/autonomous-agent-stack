from __future__ import annotations

from fastapi.routing import APIRoute

from autoresearch.api.main import app


def _methods_for_path(path: str) -> set[str]:
    methods: set[str] = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path:
            methods.update(route.methods or set())
    return methods


def test_core_control_plane_routes_are_mounted() -> None:
    expected_routes = {
        "/health": {"GET"},
        "/api/v1/gateway/telegram/health": {"GET"},
        "/api/v1/gateway/telegram/webhook": {"POST"},
        "/api/v1/workers/register": {"POST"},
        "/api/v1/workers/{worker_id}/heartbeat": {"POST"},
        "/api/v1/workers/{worker_id}/claim": {"POST"},
        "/api/v1/workers/{worker_id}/runs/{run_id}/report": {"POST"},
        "/api/v1/worker-runs": {"POST"},
        "/api/v1/worker-runs/youtube-autoflow": {"POST"},
    }

    missing: list[str] = []
    for path, required_methods in expected_routes.items():
        actual_methods = _methods_for_path(path)
        if not required_methods.issubset(actual_methods):
            missing.append(f"{path} -> expected {sorted(required_methods)}, got {sorted(actual_methods)}")

    assert missing == [], f"Core control-plane routes are missing or mis-mounted: {missing}"
