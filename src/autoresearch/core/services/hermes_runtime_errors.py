from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HermesRuntimeErrorKind(str, Enum):
    INVALID_REQUEST = "invalid_request"
    BINARY_MISSING = "binary_missing"
    COMMAND_BUILD_FAILED = "command_build_failed"
    LAUNCH_FAILED = "launch_failed"
    TIMEOUT = "timeout"
    NONZERO_EXIT = "nonzero_exit"
    CANCELLED = "cancelled"
    INTERNAL_ERROR = "internal_error"


@dataclass(slots=True)
class HermesRuntimeFailure(Exception):
    kind: HermesRuntimeErrorKind
    message: str
    failed_stage: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message
