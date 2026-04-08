"""Foundation package initialization.

Provides unified task orchestration foundation layer.
"""

from __future__ import annotations
from pathlib import Path

from .contracts import *
from .manifest_loader import *
from .router import *
from .state_machine import *
from .gate import *
from .adapters import *
from .approvals import *

__all__ = [
    "JobSpec",
    "JobContext",
    "DriverRequest",
    "DriverResult",
    "DriverMetrics",
    "RunState",
    "TaskGateCheck",
    "TaskGateResult",
    "ApprovalRequirement",
    "RunRecord",
    "is_valid_transition",
    "utc_now",
]
