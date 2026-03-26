from __future__ import annotations

import json
from pathlib import Path

from autoresearch.shared.models import (
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionSkillLoadRequest,
    OpenClawSkillDetailRead,
    OpenClawSkillRead,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = REPO_ROOT / "migration" / "openclaw" / "contracts"


def _load_json(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def test_openclaw_contract_fixtures_parse_with_shared_models() -> None:
    session_create = OpenClawSessionCreateRequest.model_validate(
        _load_json("openclaw-session-create-request.v1.json")
    )
    assert session_create.channel == "telegram"

    event_append = OpenClawSessionEventAppendRequest.model_validate(
        _load_json("openclaw-session-event-append-request.v1.json")
    )
    assert event_append.role == "user"

    skill_load = OpenClawSessionSkillLoadRequest.model_validate(
        _load_json("openclaw-session-skill-load-request.v1.json")
    )
    assert skill_load.skill_names == ["weather", "voice-call"]

    skill_read = OpenClawSkillRead.model_validate(_load_json("openclaw-skill-read.v1.json"))
    assert skill_read.skill_key == "weather"

    skill_detail = OpenClawSkillDetailRead.model_validate(
        _load_json("openclaw-skill-detail-read.v1.json")
    )
    assert "Weather Skill" in skill_detail.content
