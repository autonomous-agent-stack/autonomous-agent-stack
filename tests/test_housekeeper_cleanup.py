from __future__ import annotations

import warnings
from pathlib import Path

from autoresearch.api import dependencies
import autoresearch.housekeeper as legacy_housekeeper_package
from autoresearch.api.routers import openclaw_housekeeper
from autoresearch.core.services.personal_housekeeper import PersonalHousekeeperService
from autoresearch.housekeeper import schemas as legacy_housekeeper_schemas
from autoresearch.shared import housekeeper_contract


def test_active_housekeeper_wiring_uses_mainline_service() -> None:
    assert dependencies.PersonalHousekeeperService is PersonalHousekeeperService
    assert openclaw_housekeeper.PersonalHousekeeperService is PersonalHousekeeperService


def test_parallel_housekeeper_runtime_module_has_been_removed() -> None:
    legacy_runtime = Path(__file__).resolve().parents[1] / "src" / "autoresearch" / "housekeeper" / "service.py"
    assert legacy_runtime.exists() is False


def test_legacy_housekeeper_schema_module_is_compatibility_only() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert (
            legacy_housekeeper_schemas.HousekeeperDispatchRequest
            is legacy_housekeeper_schemas.LegacyFrontdeskDispatchRequest
        )
        assert (
            legacy_housekeeper_schemas.HousekeeperApprovalRequest
            is legacy_housekeeper_schemas.LegacyFrontdeskApprovalRequest
        )
        assert legacy_housekeeper_schemas.HousekeeperTaskRead is legacy_housekeeper_schemas.LegacyFrontdeskTaskRead
    assert len(caught) == 3
    assert all(item.category is DeprecationWarning for item in caught)

    assert dependencies.HousekeeperTaskRead is housekeeper_contract.HousekeeperTaskRead
    assert openclaw_housekeeper.HousekeeperDispatchRequest is housekeeper_contract.HousekeeperDispatchRequest


def test_legacy_housekeeper_package_aliases_warn_but_still_resolve() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert legacy_housekeeper_package.HousekeeperDispatchRequest is legacy_housekeeper_schemas.LegacyFrontdeskDispatchRequest
        assert legacy_housekeeper_package.HousekeeperApprovalRequest is legacy_housekeeper_schemas.LegacyFrontdeskApprovalRequest
        assert legacy_housekeeper_package.HousekeeperTaskRead is legacy_housekeeper_schemas.LegacyFrontdeskTaskRead
    assert len(caught) == 6
    assert all(item.category is DeprecationWarning for item in caught)
