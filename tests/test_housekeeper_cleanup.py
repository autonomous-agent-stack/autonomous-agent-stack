from __future__ import annotations

from pathlib import Path

from autoresearch.api import dependencies
from autoresearch.api.routers import openclaw_housekeeper
from autoresearch.core.services.personal_housekeeper import PersonalHousekeeperService


def test_active_housekeeper_wiring_uses_mainline_service() -> None:
    assert dependencies.PersonalHousekeeperService is PersonalHousekeeperService
    assert openclaw_housekeeper.PersonalHousekeeperService is PersonalHousekeeperService


def test_parallel_housekeeper_runtime_module_has_been_removed() -> None:
    legacy_runtime = Path(__file__).resolve().parents[1] / "src" / "autoresearch" / "housekeeper" / "service.py"
    assert legacy_runtime.exists() is False
