from __future__ import annotations

import json
from pathlib import Path

from scripts.furniture_e2e import FurnitureE2ERunner, REQUIRED_ARTIFACTS


ROOT = Path(__file__).resolve().parents[2]


def test_furniture_e2e_generates_required_artifacts() -> None:
    manifest = FurnitureE2ERunner(ROOT).run()

    assert set(manifest) == REQUIRED_ARTIFACTS
    root = ROOT / "artifacts/ga/furniture_e2e"
    approval = json.loads((root / "approval_record.json").read_text(encoding="utf-8"))
    design = json.loads((root / "design_prompt_audit.json").read_text(encoding="utf-8"))
    replay = json.loads((root / "session_facts_replay.json").read_text(encoding="utf-8"))

    assert approval["denied_path"]["blocked"] is True
    assert approval["approved_path"]["dry_run"] is True
    assert design["pii_redaction_verified"] is True
    assert replay["content_hash_verified"] is True
