"""Legacy housekeeper package for schemas only.

Active runtime wiring lives in ``autoresearch.core.services.personal_housekeeper``.
Do not add a second housekeeper runtime under this package.
"""

from __future__ import annotations

import warnings

from autoresearch.housekeeper import schemas as _schemas


def __getattr__(name: str):
    if name not in {
        "HousekeeperApprovalRequest",
        "HousekeeperDispatchRequest",
        "HousekeeperTaskRead",
    }:
        raise AttributeError(name)
    warnings.warn(
        (
            f"`autoresearch.housekeeper.{name}` is deprecated and kept only for compatibility. "
            f"Use `LegacyFrontdesk*` from `autoresearch.housekeeper.schemas` for legacy frontdesk "
            f"schemas, or `autoresearch.shared.housekeeper_contract` for active runtime contracts."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(_schemas, name)


__all__ = ["HousekeeperApprovalRequest", "HousekeeperDispatchRequest", "HousekeeperTaskRead"]
