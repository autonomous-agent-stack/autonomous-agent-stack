from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8001/api/v1/auth/youtube/oauth/callback"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True)
class YouTubeOAuthProfile:
    profile_id: str
    display_name: str
    purpose: str
    preferred_for: tuple[str, ...]


YOUTUBE_OAUTH_PROFILES: dict[str, YouTubeOAuthProfile] = {
    "youtube_music": YouTubeOAuthProfile(
        profile_id="youtube_music",
        display_name="YouTube Premium / Music",
        purpose="music, relaxation, and companion recommendations",
        preferred_for=("music", "relax", "companion"),
    ),
    "youtube_learning": YouTubeOAuthProfile(
        profile_id="youtube_learning",
        display_name="YouTube + NotebookLM learning",
        purpose="learning, AI, business, documentary, and source organization",
        preferred_for=("learning", "ai", "business", "documentary", "notebooklm"),
    ),
}


TokenExchange = Callable[[dict[str, str]], dict[str, Any]]


class YouTubeOAuthProfileRegistry:
    """Local read-only OAuth profile registry for two Google/YouTube accounts."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        token_dir: Path | str | None = None,
        scopes: tuple[str, ...] | None = None,
        token_exchange: TokenExchange | None = None,
    ) -> None:
        self.client_id = (
            client_id
            or os.getenv("AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID")
            or os.getenv("GOOGLE_CLIENT_ID")
            or ""
        ).strip()
        self.client_secret = (
            client_secret
            or os.getenv("AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET")
            or os.getenv("GOOGLE_CLIENT_SECRET")
            or ""
        ).strip()
        self.redirect_uri = (
            redirect_uri
            or os.getenv("AUTORESEARCH_YOUTUBE_OAUTH_REDIRECT_URI")
            or os.getenv("GOOGLE_REDIRECT_URI")
            or DEFAULT_REDIRECT_URI
        ).strip()
        default_dir = Path.home() / ".config" / "autoresearch" / "google" / "youtube_profiles"
        self.token_dir = Path(
            token_dir or os.getenv("AUTORESEARCH_YOUTUBE_OAUTH_TOKEN_DIR") or default_dir
        ).expanduser()
        self.scopes = scopes or (YOUTUBE_READONLY_SCOPE,)
        self._validate_scopes(self.scopes)
        self._token_exchange = token_exchange or self._exchange_code_for_token

    def list_profiles(self) -> list[dict[str, Any]]:
        return [self.profile_status(profile_id) for profile_id in sorted(YOUTUBE_OAUTH_PROFILES)]

    def profile_status(self, profile_id: str) -> dict[str, Any]:
        profile = self._profile(profile_id)
        token = self._read_token(profile.profile_id)
        authorized = bool(token.get("refresh_token") or token.get("access_token"))
        return {
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "purpose": profile.purpose,
            "preferred_for": list(profile.preferred_for),
            "auth_status": "authorized" if authorized else "auth_required",
            "scopes": list(self.scopes),
            "last_authorized_at": str(token.get("obtained_at") or token.get("updated_at") or ""),
            "token_present": authorized,
        }

    def start_authorization(
        self,
        profile_id: str,
        *,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self._profile(profile_id)
        if not self.client_id or not self.client_secret:
            return {
                "status": "missing_client_config",
                "profile_id": profile.profile_id,
                "auth_status": "auth_required",
                "reason": "missing Google OAuth client id or client secret",
                "required_env": [
                    "AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID",
                    "AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET",
                ],
                "scopes": list(self.scopes),
            }

        state = secrets.token_urlsafe(32)
        self._write_state(
            state,
            {
                "state": state,
                "profile_id": profile.profile_id,
                "requested_by": requested_by or "",
                "created_at": _utc_now(),
                "scopes": list(self.scopes),
                "metadata": dict(metadata or {}),
            },
        )
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.scopes),
                "state": state,
                "access_type": "offline",
                "prompt": "consent select_account",
                "include_granted_scopes": "false",
            }
        )
        return {
            "status": "auth_url",
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "authorization_url": f"{GOOGLE_OAUTH_AUTH_URL}?{query}",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scopes": list(self.scopes),
            "auth_status": self.profile_status(profile.profile_id)["auth_status"],
        }

    def complete_authorization(
        self,
        *,
        code: str | None,
        state: str | None,
        error: str | None = None,
        expected_profile_id: str | None = None,
    ) -> dict[str, Any]:
        if error:
            return {"status": "rejected", "reason": error, "auth_status": "auth_required"}
        normalized_state = str(state or "").strip()
        if not normalized_state:
            return {"status": "rejected", "reason": "missing oauth state", "auth_status": "auth_required"}
        state_record = self._read_state(normalized_state)
        if not state_record:
            return {"status": "rejected", "reason": "oauth state not found", "auth_status": "auth_required"}

        profile_id = str(state_record.get("profile_id") or "").strip()
        profile = self._profile(profile_id)
        if expected_profile_id and expected_profile_id != profile.profile_id:
            return {
                "status": "rejected",
                "profile_id": profile.profile_id,
                "reason": "oauth state profile mismatch",
                "auth_status": "auth_required",
            }
        if not self.client_id or not self.client_secret:
            return {
                "status": "missing_client_config",
                "profile_id": profile.profile_id,
                "reason": "missing Google OAuth client id or client secret",
                "auth_status": "auth_required",
                "required_env": [
                    "AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID",
                    "AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET",
                ],
            }
        normalized_code = str(code or "").strip()
        if not normalized_code:
            return {
                "status": "rejected",
                "profile_id": profile.profile_id,
                "reason": "missing authorization code",
                "auth_status": "auth_required",
            }

        token = self._token_exchange(
            {
                "code": normalized_code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        returned_scopes = _normalize_scope_string(str(token.get("scope") or " ".join(self.scopes)))
        self._validate_scopes(tuple(returned_scopes))
        existing = self._read_token(profile.profile_id)
        if "refresh_token" not in token and existing.get("refresh_token"):
            token["refresh_token"] = existing["refresh_token"]
        self._write_token(
            profile.profile_id,
            {
                **token,
                "profile_id": profile.profile_id,
                "scopes": list(self.scopes),
                "obtained_at": _utc_now(),
            },
        )
        self._delete_state(normalized_state)
        status = self.profile_status(profile.profile_id)
        return {
            "status": "authorized",
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "auth_status": status["auth_status"],
            "scopes": list(self.scopes),
        }

    def revoke_profile(self, profile_id: str) -> dict[str, Any]:
        profile = self._profile(profile_id)
        token_path = self._token_path(profile.profile_id)
        existed = token_path.exists()
        if existed:
            token_path.unlink()
        for state_path in self._state_dir().glob("*.json"):
            state = _read_json_file(state_path)
            if state.get("profile_id") == profile.profile_id:
                state_path.unlink(missing_ok=True)
        return {
            "status": "revoked" if existed else "auth_required",
            "profile_id": profile.profile_id,
            "auth_status": "auth_required",
            "scopes": list(self.scopes),
        }

    def _exchange_code_for_token(self, payload: dict[str, str]) -> dict[str, Any]:
        body = urlencode(payload).encode("utf-8")
        request = Request(
            GOOGLE_OAUTH_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
        token = json.loads(raw)
        if not isinstance(token, dict):
            raise ValueError("Google OAuth token response must be a JSON object")
        return token

    def _profile(self, profile_id: str) -> YouTubeOAuthProfile:
        normalized = str(profile_id or "").strip()
        if normalized not in YOUTUBE_OAUTH_PROFILES:
            raise ValueError(f"unknown YouTube OAuth profile: {profile_id}")
        return YOUTUBE_OAUTH_PROFILES[normalized]

    def _validate_scopes(self, scopes: tuple[str, ...]) -> None:
        normalized = tuple(_normalize_scope_string(" ".join(scopes)))
        if normalized != (YOUTUBE_READONLY_SCOPE,):
            raise ValueError("YouTube OAuth profiles must use youtube.readonly only")

    def _token_path(self, profile_id: str) -> Path:
        return self.token_dir / f"{profile_id}.json"

    def _state_dir(self) -> Path:
        return self.token_dir / "states"

    def _read_token(self, profile_id: str) -> dict[str, Any]:
        return _read_json_file(self._token_path(profile_id))

    def _write_token(self, profile_id: str, payload: dict[str, Any]) -> None:
        self.token_dir.mkdir(parents=True, exist_ok=True)
        path = self._token_path(profile_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        path.chmod(0o600)

    def _read_state(self, state: str) -> dict[str, Any]:
        return _read_json_file(self._state_dir() / f"{state}.json")

    def _write_state(self, state: str, payload: dict[str, Any]) -> None:
        self._state_dir().mkdir(parents=True, exist_ok=True)
        path = self._state_dir() / f"{state}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        path.chmod(0o600)

    def _delete_state(self, state: str) -> None:
        (self._state_dir() / f"{state}.json").unlink(missing_ok=True)


def select_profile_for_curator_payload(payload: dict[str, Any]) -> str:
    notebooklm_pack = payload.get("notebooklm_pack") if isinstance(payload, dict) else {}
    if isinstance(notebooklm_pack, dict) and bool(notebooklm_pack.get("enabled")):
        return "youtube_learning"
    text = " ".join(
        str(payload.get(key) or "")
        for key in ("mood", "interest", "focus_level", "raw_text", "title")
        if isinstance(payload, dict)
    ).strip().lower()
    learning_markers = (
        "learning",
        "learn",
        "study",
        "ai",
        "business",
        "documentary",
        "notebooklm",
        "学习",
        "资料",
        "人工智能",
        "商业",
        "纪录片",
    )
    if any(marker in text for marker in learning_markers):
        return "youtube_learning"
    recommendations = payload.get("recommendations") if isinstance(payload, dict) else []
    if isinstance(recommendations, list):
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            rec_type = str(item.get("type") or "").strip().lower()
            platform = str(item.get("platform") or "").strip().lower()
            if rec_type in {"learning", "reading"}:
                return "youtube_learning"
            if platform == "youtube music" or rec_type == "music":
                return "youtube_music"
    return "youtube_music"


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _normalize_scope_string(scope: str) -> list[str]:
    return sorted({item.strip() for item in str(scope or "").split() if item.strip()})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
