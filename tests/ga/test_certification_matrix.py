from __future__ import annotations

from pathlib import Path

from autoresearch.ga.certification import AdapterCertificationRegistry
from autoresearch.ga.contracts import Stability


ROOT = Path(__file__).resolve().parents[2]


def test_adapter_certification_matrix_has_no_uncertified_stable_adapters() -> None:
    registry = AdapterCertificationRegistry(ROOT / "configs/certification/adapters.yaml")

    assert registry.required_checks
    assert registry.stable_violations() == {}


def test_demo_only_adapters_are_not_stable() -> None:
    registry = AdapterCertificationRegistry(ROOT / "configs/certification/adapters.yaml")
    statuses = {item.object_id: item for item in registry.list_statuses()}

    assert statuses["crewai"].stability == Stability.EXPERIMENTAL
    assert statuses["haystack"].stability == Stability.EXPERIMENTAL
    assert statuses["langgraph"].stability == Stability.EXPERIMENTAL
    assert statuses["mcp_tool_broker"].stability == Stability.BETA
    assert "live_integration_test" in statuses["mcp_tool_broker"].missing_checks

