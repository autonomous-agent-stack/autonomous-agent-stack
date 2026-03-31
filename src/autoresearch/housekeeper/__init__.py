"""Legacy housekeeper package for schemas only.

Active runtime wiring lives in ``autoresearch.core.services.personal_housekeeper``.
Do not add a second housekeeper runtime under this package.
"""

from autoresearch.housekeeper.schemas import (
    HousekeeperApprovalRequest,
    HousekeeperDispatchRequest,
    HousekeeperTaskRead,
)

__all__ = [
    "HousekeeperApprovalRequest",
    "HousekeeperDispatchRequest",
    "HousekeeperTaskRead",
]
