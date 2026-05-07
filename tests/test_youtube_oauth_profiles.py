from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from packages.entertainment_curator.youtube_oauth import (
    YOUTUBE_READONLY_SCOPE,
    YouTubeOAuthProfileRegistry,
    select_profile_for_curator_payload,
)


def test_youtube_oauth_profiles_start_auth_with_readonly_scope(tmp_path) -> None:
    registry = YouTubeOAuthProfileRegistry(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://127.0.0.1:8001/api/v1/auth/youtube/oauth/callback",
        token_dir=tmp_path,
    )

    result = registry.start_authorization("youtube_music", requested_by="telegram-user")

    assert result["status"] == "auth_url"
    parsed = urlparse(result["authorization_url"])
    query = parse_qs(parsed.query)
    assert query["scope"] == [YOUTUBE_READONLY_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent select_account"]
    assert (tmp_path / "states" / f"{result['state']}.json").exists()


def test_youtube_oauth_callback_saves_profiles_separately(tmp_path) -> None:
    def exchange(payload: dict[str, str]) -> dict[str, str]:
        return {
            "access_token": f"access-{payload['code']}",
            "refresh_token": f"refresh-{payload['code']}",
            "scope": YOUTUBE_READONLY_SCOPE,
            "token_type": "Bearer",
            "expires_in": "3600",
        }

    registry = YouTubeOAuthProfileRegistry(
        client_id="client-id",
        client_secret="client-secret",
        token_dir=tmp_path,
        token_exchange=exchange,
    )

    music = registry.start_authorization("youtube_music")
    learning = registry.start_authorization("youtube_learning")
    completed = registry.complete_authorization(code="music-code", state=music["state"])

    assert completed["status"] == "authorized"
    assert registry.profile_status("youtube_music")["auth_status"] == "authorized"
    assert registry.profile_status("youtube_learning")["auth_status"] == "auth_required"
    assert (tmp_path / "youtube_music.json").exists()
    assert not (tmp_path / "youtube_learning.json").exists()

    mismatch = registry.complete_authorization(
        code="learning-code",
        state=learning["state"],
        expected_profile_id="youtube_music",
    )
    assert mismatch["status"] == "rejected"
    assert mismatch["reason"] == "oauth state profile mismatch"


def test_youtube_oauth_profiles_list_and_revoke_without_leaking_tokens(tmp_path) -> None:
    registry = YouTubeOAuthProfileRegistry(
        client_id="client-id",
        client_secret="client-secret",
        token_dir=tmp_path,
        token_exchange=lambda _: {
            "access_token": "secret-access-token",
            "refresh_token": "secret-refresh-token",
            "scope": YOUTUBE_READONLY_SCOPE,
        },
    )
    auth = registry.start_authorization("youtube_music")
    registry.complete_authorization(code="code", state=auth["state"])

    profiles = registry.list_profiles()
    music = next(item for item in profiles if item["profile_id"] == "youtube_music")
    assert music["auth_status"] == "authorized"
    assert "secret-access-token" not in str(profiles)
    assert "secret-refresh-token" not in str(profiles)

    revoked = registry.revoke_profile("youtube_music")
    assert revoked["status"] == "revoked"
    assert registry.profile_status("youtube_music")["auth_status"] == "auth_required"


def test_youtube_oauth_profiles_reject_write_scopes(tmp_path) -> None:
    with pytest.raises(ValueError, match="youtube.readonly only"):
        YouTubeOAuthProfileRegistry(
            client_id="client-id",
            client_secret="client-secret",
            token_dir=tmp_path,
            scopes=("https://www.googleapis.com/auth/youtube.upload",),
        )


def test_youtube_oauth_profiles_missing_config_is_auth_required(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    registry = YouTubeOAuthProfileRegistry(client_id="", client_secret="", token_dir=tmp_path)

    result = registry.start_authorization("youtube_learning")

    assert result["status"] == "missing_client_config"
    assert result["auth_status"] == "auth_required"
    assert result["scopes"] == [YOUTUBE_READONLY_SCOPE]


def test_youtube_oauth_profile_selection_understands_chinese_learning_context() -> None:
    assert select_profile_for_curator_payload({"mood": "学习", "interest": "AI"}) == "youtube_learning"
    assert select_profile_for_curator_payload({"raw_text": "今晚想听音乐放松"}) == "youtube_music"
