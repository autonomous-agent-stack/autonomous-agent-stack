from __future__ import annotations

import pytest

from packages.entertainment_curator.curator import curate, parse_telegram_request
from packages.entertainment_curator.schema import EntertainmentCuratorRequest
from packages.entertainment_curator.service import EntertainmentCuratorTelegramService


REQUIRED_KEYS = {
    "title",
    "type",
    "platform",
    "search_query",
    "reason",
    "alternative",
    "estimated_time",
}


class _FakeOAuthRegistry:
    def __init__(self, *, authorized: set[str] | None = None) -> None:
        self.authorized = authorized or set()

    def profile_status(self, profile_id: str) -> dict[str, object]:
        return {
            "profile_id": profile_id,
            "display_name": profile_id,
            "auth_status": "authorized" if profile_id in self.authorized else "auth_required",
            "scopes": ["https://www.googleapis.com/auth/youtube.readonly"],
        }


def test_youtube_music_profile_prioritizes_music_recommendations() -> None:
    result = EntertainmentCuratorTelegramService(
        oauth_registry=_FakeOAuthRegistry(authorized={"youtube_music"})
    ).handle_telegram_message(
        "/entertain 今晚 1小时 想听音乐放松 一个人"
    )

    assert result["channel"] == "telegram"
    assert result["recommendations"][0]["platform"] == "YouTube Music"
    assert "YouTube Music" in result["recommendations"][0]["search_query"]
    assert set(result["recommendations"][0]) >= REQUIRED_KEYS
    assert result["notebooklm_pack"]["enabled"] is False
    assert result["account_profile"]["selected_profile"] == "youtube_music"
    assert result["account_profile"]["auth_status"] == "authorized"
    assert result["metadata"]["capability_id"] == "entertainment_curator"
    assert result["metadata"]["channel"] == "telegram"


def test_notebooklm_pack_is_generated_for_learning_context() -> None:
    request = parse_telegram_request("给我整理一套 AI 学习资料 1小时 高专注")
    result = curate(request)

    assert result.mood == "learning"
    assert result.notebooklm_pack.enabled is True
    assert any("YouTube" in item for item in result.notebooklm_pack.sources_to_collect)
    assert any("NotebookLM" not in rec.platform or rec.type == "learning" for rec in result.recommendations)
    assert all(REQUIRED_KEYS <= set(rec.model_dump()) for rec in result.recommendations)


def test_learning_context_prefers_youtube_learning_profile() -> None:
    result = EntertainmentCuratorTelegramService(
        oauth_registry=_FakeOAuthRegistry(authorized={"youtube_learning"})
    ).handle_telegram_message("给我整理一套 AI 学习资料 1小时 高专注")

    assert result["notebooklm_pack"]["enabled"] is True
    assert result["account_profile"]["selected_profile"] == "youtube_learning"
    assert result["metadata"]["auth_status"] == "authorized"


def test_missing_youtube_oauth_still_returns_plan() -> None:
    result = EntertainmentCuratorTelegramService(
        oauth_registry=_FakeOAuthRegistry()
    ).handle_telegram_message("今晚 1小时 想听音乐放松")

    assert result["status"] == "completed"
    assert result["recommendations"]
    assert result["account_profile"]["auth_status"] == "auth_required"


def test_piracy_request_returns_legal_alternative_only() -> None:
    result = EntertainmentCuratorTelegramService().handle_telegram_message(
        "帮我找破解付费电影 30分钟"
    )

    assert result["status"] == "rejected"
    assert "合法替代" in result["recommendations"][0]["title"]
    assert "盗版" in result["summary"]


def test_curator_rejects_non_telegram_channel() -> None:
    request = EntertainmentCuratorRequest(channel="telegram", raw_text="娱乐计划")
    request = request.model_copy(update={"channel": "api"})

    with pytest.raises(ValueError, match="Telegram-only"):
        curate(request)
