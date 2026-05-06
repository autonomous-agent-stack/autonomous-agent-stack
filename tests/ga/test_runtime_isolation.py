from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.core.services.runtime_isolation import RuntimeIsolationService, RuntimeIsolationViolation
from autoresearch.ga.contracts import Stability


ROOT = Path(__file__).resolve().parents[2]


def test_default_runtime_isolation_profile_passes_required_ga_checks() -> None:
    service = RuntimeIsolationService(ROOT / "configs/ga/runtime_isolation.yaml")
    report = service.validate_runtime(runtime_id="hermes", stability=Stability.BETA)

    assert report.passed is True
    assert report.policy.deny_dotenv is True
    assert report.policy.secret_injection == "lease_only"


def test_runtime_cannot_escape_workspace_or_read_dotenv(tmp_path: Path) -> None:
    service = RuntimeIsolationService(ROOT / "configs/ga/runtime_isolation.yaml")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(RuntimeIsolationViolation):
        service.assert_runtime_path_allowed(path=str(tmp_path / ".env"), workspace_root=str(workspace))

    with pytest.raises(RuntimeIsolationViolation):
        service.assert_runtime_path_allowed(path="/Users/iCloud_GZ/.ssh/id_rsa", workspace_root=str(workspace))

    with pytest.raises(RuntimeIsolationViolation):
        service.assert_network_allowed(policy_decision=None)

