from __future__ import annotations

from autoresearch.core.services.recovery_orchestrator import (
    ButlerRecoveryOrchestrator,
    classify_recovery_failure_kind,
)


def test_recovery_failure_taxonomy_maps_unusual_failures() -> None:
    assert classify_recovery_failure_kind(error_kind="collector_missing") == "dependency_missing"
    assert classify_recovery_failure_kind(error_kind="collector_auth_failed") == "auth_required"
    assert classify_recovery_failure_kind(error_kind="payload missing field") == "contract_error"
    assert classify_recovery_failure_kind(error_kind="ambiguous route needs_user_decision") == "needs_user_decision"


def test_recovery_doctor_surfaces_missing_contracts_and_agent_governance(tmp_path) -> None:
    agent_dir = tmp_path / "agents" / "prompt_only"
    agent_dir.mkdir(parents=True)
    (agent_dir / "manifest.yaml").write_text(
        "\n".join(
            [
                'version: "1"',
                "agent:",
                '  id: "prompt_only"',
                '  role: "specialist"',
                "routing:",
                "  task_types:",
                '    - "content_kb.ingest"',
            ]
        ),
        encoding="utf-8",
    )

    checks = ButlerRecoveryOrchestrator(repo_root=tmp_path).doctor_checks()

    recovery = next(item for item in checks if item.name == "recovery contracts")
    governance = next(item for item in checks if item.name == "agent governance")
    assert recovery.status == "degraded"
    assert "content_kb" in recovery.metadata["missing"]
    assert governance.status == "degraded"
    assert governance.metadata["missing_recovery_contract"] == ["prompt_only"]
    assert governance.metadata["missing_lifecycle"] == ["prompt_only"]
