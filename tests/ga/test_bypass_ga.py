from __future__ import annotations

from pathlib import Path

from scripts.bypass_ga import run_bypass_checks


ROOT = Path(__file__).resolve().parents[2]


def test_bypass_ga_blocks_required_bypass_paths() -> None:
    checks = run_bypass_checks(ROOT)
    statuses = {str(item["check"]): item["status"] for item in checks}

    for required in (
        "direct_env_key_access",
        "direct_model_call",
        "direct_tool_call",
        "approval_rejected_but_action_continues",
        "federation_without_lease",
        "unauthorized_package_tool_registration",
        "direct_db_mutation",
        "artifact_promotion_bypass",
    ):
        assert statuses[required] == "passed"
