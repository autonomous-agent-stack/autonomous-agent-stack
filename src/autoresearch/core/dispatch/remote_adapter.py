from __future__ import annotations

from abc import ABC, abstractmethod

from autoresearch.shared.remote_run_contract import (
    RemoteHeartbeat,
    RemoteRunRecord,
    RemoteRunSummary,
    RemoteTaskSpec,
    RemoteWorkerHealthRead,
)


class RemoteDispatchAdapter(ABC):
    @abstractmethod
    def healthcheck(self) -> RemoteWorkerHealthRead:
        raise NotImplementedError

    @abstractmethod
    def dispatch(self, spec: RemoteTaskSpec) -> RemoteRunRecord:
        raise NotImplementedError

    @abstractmethod
    def poll(self, run_id: str) -> RemoteRunRecord:
        raise NotImplementedError

    @abstractmethod
    def heartbeat(self, run_id: str) -> RemoteHeartbeat | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_summary(self, run_id: str) -> RemoteRunSummary:
        raise NotImplementedError
