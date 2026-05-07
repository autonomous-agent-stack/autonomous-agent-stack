from importlib import import_module
from typing import Any

__all__ = [
    "InProcessMacWorkerClient",
    "MacWorkerApiClient",
    "MacWorkerConfig",
    "MacWorkerDaemon",
    "MacWorkerExecutionResult",
    "MacWorkerExecutor",
]

_EXPORTS = {
    "InProcessMacWorkerClient": ("autoresearch.workers.mac.client", "InProcessMacWorkerClient"),
    "MacWorkerApiClient": ("autoresearch.workers.mac.client", "MacWorkerApiClient"),
    "MacWorkerConfig": ("autoresearch.workers.mac.config", "MacWorkerConfig"),
    "MacWorkerDaemon": ("autoresearch.workers.mac.daemon", "MacWorkerDaemon"),
    "MacWorkerExecutionResult": ("autoresearch.workers.mac.executor", "MacWorkerExecutionResult"),
    "MacWorkerExecutor": ("autoresearch.workers.mac.executor", "MacWorkerExecutor"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
