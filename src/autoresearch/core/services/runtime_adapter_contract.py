from __future__ import annotations

from abc import ABC, abstractmethod

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


class RuntimeAdapterContract(ABC):
    """Stable runtime contract for pluggable agent backends."""

    @abstractmethod
    def create_session(self, request: RuntimeSessionCreateRequest) -> RuntimeSessionRead: ...

    @abstractmethod
    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead: ...

    @abstractmethod
    def stream(self, request: RuntimeStreamRequest) -> list[RuntimeStreamEvent]: ...

    @abstractmethod
    def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelRead: ...

    @abstractmethod
    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusRead: ...
