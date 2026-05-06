from __future__ import annotations

from pathlib import Path

from scripts.bypass_ga import run_bypass_checks


ROOT = Path(__file__).resolve().parents[2]


def test_bypass_ga_blocks_required_bypass_paths() -> None:
    checks = run_bypass_checks(ROOT)
    statuses = {str(item["check"]): item["status"] for item in checks}

    for required in (
        "runtime direct model key access",
        "runtime direct .env access",
        "runtime direct tool call",
        "Model Gateway bypass",
        "Tool Broker bypass",
        "Secret Vault bypass",
        "approval rejected but action continues",
        "federation peer without lease",
        "UI direct DB mutation",
        "artifact promotion bypassing gate",
    ):
        assert statuses[required] == "passed"

