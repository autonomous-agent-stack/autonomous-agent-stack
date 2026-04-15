from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverMetrics
from autoresearch.agent_protocol.runtime_models import (
    RuntimeCancelRead,
    RuntimeCancelRequest,
    RuntimeRunRead,
    RuntimeRunRequest,
    RuntimeSessionCreateRequest,
    RuntimeSessionRead,
    RuntimeStatusRead,
    RuntimeStatusRequest,
    RuntimeStreamEvent,
    RuntimeStreamRequest,
)
from autoresearch.api.dependencies import get_runtime_adapter_registry_service
from autoresearch.api.routers.runtime import router
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry
from autoresearch.shared.models import AssistantScope, JobStatus


class _FakeRuntimeAdapter(RuntimeAdapterContract):
    def create_session(self, request: RuntimeSessionCreateRequest) -> RuntimeSessionRead:
        now = datetime.now(UTC)
        return RuntimeSessionRead(
            runtime_id=request.runtime_id,
            session_id="sess-1",
            channel=request.channel,
            title=request.title,
            scope=request.scope,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=dict(request.metadata),
        )

    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead:
        now = datetime.now(UTC)
        return RuntimeRunRead(
            runtime_id=request.runtime_id,
            run_id="run-1",
            session_id=request.session_id,
            task_name=request.task_name,
            status=JobStatus.RUNNING,
            summary=f"running: {request.task_name}",
            changed_paths=[],
            output_artifacts=[],
            metrics=DriverMetrics(duration_ms=0, steps=1, commands=1),
            command=["fake-runtime"],
            timeout_seconds=request.timeout_seconds,
            work_dir=request.work_dir,
            returncode=None,
            created_at=now,
            updated_at=now,
            metadata=dict(request.metadata),
            error=None,
        )

    def stream(self, request: RuntimeStreamRequest) -> list[RuntimeStreamEvent]:
        return [
            RuntimeStreamEvent(
                runtime_id=request.runtime_id,
                session_id=request.session_id,
                run_id="run-1",
                event_id="evt-1",
                role="status",
                content="streaming",
                created_at=datetime.now(UTC).isoformat(),
                metadata={},
            )
        ]

    def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelRead:
        return RuntimeCancelRead(
            runtime_id=request.runtime_id,
            run_id=request.run_id,
            session_id="sess-1",
            status=JobStatus.INTERRUPTED,
            error=request.reason,
            metadata={},
        )

    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusRead:
        now = datetime.now(UTC)
        session = RuntimeSessionRead(
            runtime_id=request.runtime_id,
            session_id=request.session_id or "sess-1",
            channel="runtime",
            title="runtime",
            scope=AssistantScope.PERSONAL,
            status=JobStatus.RUNNING,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        run = RuntimeRunRead(
            runtime_id=request.runtime_id,
            run_id=request.run_id or "run-1",
            session_id=session.session_id,
            task_name="runtime-task",
            status=JobStatus.RUNNING,
            summary="ok",
            changed_paths=[],
            output_artifacts=[],
            metrics=DriverMetrics(duration_ms=1, steps=1, commands=1),
            command=["fake-runtime"],
            timeout_seconds=10,
            work_dir=None,
            returncode=None,
            created_at=now,
            updated_at=now,
            metadata={},
            error=None,
        )
        return RuntimeStatusRead(
            runtime_id=request.runtime_id,
            session=session,
            run=run,
            latest_events=[],
            error=None,
            metadata={},
        )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    registry = RuntimeAdapterServiceRegistry(
        manifest_registry=type(
            "_ManifestRegistry",
            (),
            {"load": staticmethod(lambda runtime_id: type("_M", (), {"id": runtime_id})())},
        )(),
        factories={"hermes": _FakeRuntimeAdapter, "openclaw": _FakeRuntimeAdapter},
    )
    app.dependency_overrides[get_runtime_adapter_registry_service] = lambda: registry
    return TestClient(app)


def test_runtime_router_provides_unified_endpoints() -> None:
    client = _client()

    session_resp = client.post(
        "/api/v1/runtime/hermes/sessions",
        json={"runtime_id": "ignored", "channel": "runtime", "title": "demo", "metadata": {"x": "1"}},
    )
    assert session_resp.status_code == 201
    assert session_resp.json()["runtime_id"] == "hermes"

    run_resp = client.post(
        "/api/v1/runtime/hermes/runs",
        json={"runtime_id": "ignored", "session_id": "sess-1", "task_name": "do", "prompt": "run"},
    )
    assert run_resp.status_code == 201
    assert run_resp.json()["runtime_id"] == "hermes"

    stream_resp = client.get("/api/v1/runtime/hermes/sessions/sess-1/events")
    assert stream_resp.status_code == 200
    assert stream_resp.json()[0]["runtime_id"] == "hermes"

    status_resp = client.get("/api/v1/runtime/hermes/status", params={"run_id": "run-1"})
    assert status_resp.status_code == 200
    assert status_resp.json()["runtime_id"] == "hermes"

    cancel_resp = client.post(
        "/api/v1/runtime/hermes/runs/run-1/cancel",
        json={"runtime_id": "ignored", "run_id": "ignored", "reason": "stop"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["run_id"] == "run-1"
