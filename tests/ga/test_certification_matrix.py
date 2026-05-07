from __future__ import annotations

from pathlib import Path

from autoresearch.ga.certification import AdapterCertificationRegistry
from autoresearch.ga.contracts import CertificationStatus, Stability


ROOT = Path(__file__).resolve().parents[2]


def test_adapter_certification_matrix_has_no_uncertified_stable_adapters() -> None:
    registry = AdapterCertificationRegistry(ROOT / "configs/certification/adapters.yaml")

    assert registry.required_checks
    assert registry.stable_violations() == {}


def test_scoped_adapters_are_stable_only_from_live_evidence() -> None:
    registry = AdapterCertificationRegistry(ROOT / "configs/certification/adapters.yaml")
    statuses = {item.object_id: item for item in registry.list_statuses()}

    assert statuses
    for status in statuses.values():
        assert status.intent_stability in {Stability.EXPERIMENTAL, Stability.BETA, Stability.STABLE}
        assert status.stability == Stability.STABLE
        assert status.certification_status == CertificationStatus.CERTIFIED
        assert status.missing_checks == []
        assert status.evidence_path
