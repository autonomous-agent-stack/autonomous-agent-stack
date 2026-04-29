from __future__ import annotations

import json
from typing import Protocol
from urllib import error, request

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerClaimRead,
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
)
from autoresearch.workers.mac.config import MacWorkerConfig


class MacWorkerClientError(RuntimeError):
    pass


class MacWorkerClient(Protocol):
    def register_worker(self, payload: WorkerRegisterRequest) -> WorkerRegistrationRead: ...

    def heartbeat(self, worker_id: str, payload: WorkerHeartbeatRequest) -> WorkerRegistrationRead: ...

    def claim_run(self, worker_id: str, payload: WorkerClaimRequest) -> WorkerClaimRead: ...

    def get_run(self, run_id: str) -> WorkerQueueItemRead | None: ...

    def report_run(self, worker_id: str, run_id: str, payload: WorkerRunReportRequest) -> WorkerQueueItemRead: ...


class MacWorkerApiClient:
    def __init__(self, config: MacWorkerConfig, *, timeout_seconds: float = 10.0) -> None:
        self._base_url = config.control_plane_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def register_worker(self, payload: WorkerRegisterRequest) -> WorkerRegistrationRead:
        body = self._request_json("POST", "/api/v1/workers/register", payload.model_dump(mode="json"))
        return WorkerRegistrationRead.model_validate(body)

    def heartbeat(self, worker_id: str, payload: WorkerHeartbeatRequest) -> WorkerRegistrationRead:
        body = self._request_json(
            "POST",
            f"/api/v1/workers/{worker_id}/heartbeat",
            payload.model_dump(mode="json"),
        )
        return WorkerRegistrationRead.model_validate(body)

    def claim_run(self, worker_id: str, payload: WorkerClaimRequest) -> WorkerClaimRead:
        body = self._request_json(
            "POST",
            f"/api/v1/workers/{worker_id}/claim",
            payload.model_dump(mode="json"),
        )
        return WorkerClaimRead.model_validate(body)

    def get_run(self, run_id: str) -> WorkerQueueItemRead | None:
        try:
            body = self._request_json("GET", f"/api/v1/worker-runs/{run_id}", {})
        except MacWorkerClientError:
            return None
        return WorkerQueueItemRead.model_validate(body)

    def report_run(self, worker_id: str, run_id: str, payload: WorkerRunReportRequest) -> WorkerQueueItemRead:
        body = self._request_json(
            "POST",
            f"/api/v1/workers/{worker_id}/runs/{run_id}/report",
            payload.model_dump(mode="json"),
        )
        return WorkerQueueItemRead.model_validate(body)

    def _request_json(self, method: str, path: str, payload: dict[str, object]) -> dict[str, object]:
        raw = json.dumps(payload).encode("utf-8") if method != "GET" else None
        req = request.Request(
            url=f"{self._base_url}{path}",
            method=method,
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise MacWorkerClientError(f"{method} {path} failed with {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise MacWorkerClientError(f"{method} {path} failed: {exc.reason}") from exc


class InProcessMacWorkerClient:
    def __init__(
        self,
        *,
        worker_registry: WorkerRegistryService,
        worker_scheduler: WorkerSchedulerService,
    ) -> None:
        self._worker_registry = worker_registry
        self._worker_scheduler = worker_scheduler

    def register_worker(self, payload: WorkerRegisterRequest) -> WorkerRegistrationRead:
        return self._worker_registry.register(payload)

    def heartbeat(self, worker_id: str, payload: WorkerHeartbeatRequest) -> WorkerRegistrationRead:
        return self._worker_registry.heartbeat(worker_id, payload)

    def claim_run(self, worker_id: str, payload: WorkerClaimRequest) -> WorkerClaimRead:
        return self._worker_scheduler.claim(worker_id, payload)

    def get_run(self, run_id: str) -> WorkerQueueItemRead | None:
        return self._worker_scheduler.get_run(run_id)

    def report_run(self, worker_id: str, run_id: str, payload: WorkerRunReportRequest) -> WorkerQueueItemRead:
        return self._worker_scheduler.report(worker_id, run_id, payload)
