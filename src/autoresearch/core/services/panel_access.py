from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from autoresearch.shared.models import PanelMagicLinkRead
from autoresearch.shared.store import create_resource_id


_TAILSCALE_IPV4_RANGE = ipaddress.ip_network("100.64.0.0/10")
_TAILSCALE_IPV6_RANGE = ipaddress.ip_network("fd7a:115c:a1e0::/48")


def is_private_or_tailscale_host(host: str) -> bool:
    normalized = host.strip().lower()
    if not normalized:
        return False
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if ip.version == 4 and ip in _TAILSCALE_IPV4_RANGE:
        return True
    if ip.version == 6 and ip in _TAILSCALE_IPV6_RANGE:
        return True
    return False


def assert_safe_bind_host(host: str, allow_unsafe: bool = False) -> None:
    if allow_unsafe or is_private_or_tailscale_host(host):
        return
    raise ValueError(
        "Refusing unsafe API bind host. Use localhost/127.0.0.1 or a Tailscale IP "
        "(100.64.0.0/10, fd7a:115c:a1e0::/48). "
        "Set AUTORESEARCH_API_ALLOW_UNSAFE_BIND=true only if you accept public exposure."
    )


@dataclass(frozen=True)
class MagicLinkClaims:
    telegram_uid: str
    expires_at: datetime
    issued_at: datetime
    token_id: str | None = None


@dataclass(frozen=True)
class TelegramInitDataClaims:
    telegram_uid: str
    auth_date: datetime
    expires_at: datetime
    query_id: str | None = None


class PanelAccessService:
    """Issue and verify short-lived HS256 JWT tokens for panel access."""

    def __init__(
        self,
        *,
        secret: str | None,
        base_url: str = "http://127.0.0.1:8000/api/v1/panel/view",
        issuer: str = "autoresearch.telegram",
        audience: str = "autoresearch.panel",
        default_ttl_seconds: int = 300,
        max_ttl_seconds: int = 3600,
        telegram_bot_token: str | None = None,
        telegram_init_data_max_age_seconds: int = 900,
        allowed_uids: set[str] | None = None,
    ) -> None:
        self._secret = (secret or "").strip()
        self._base_url = base_url.strip() or "http://127.0.0.1:8000/api/v1/panel/view"
        self._issuer = issuer
        self._audience = audience
        self._default_ttl_seconds = max(30, default_ttl_seconds)
        self._max_ttl_seconds = max(self._default_ttl_seconds, max_ttl_seconds)
        self._telegram_bot_token = (telegram_bot_token or "").strip()
        self._telegram_init_data_max_age_seconds = max(60, telegram_init_data_max_age_seconds)
        self._allowed_uids = {item.strip() for item in (allowed_uids or set()) if item.strip()}

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    def create_magic_link(self, telegram_uid: str, ttl_seconds: int | None = None) -> PanelMagicLinkRead:
        if not self.enabled:
            raise RuntimeError("panel magic-link signing secret is not configured")

        uid = telegram_uid.strip()
        if not uid:
            raise ValueError("telegram uid is required")
        self._enforce_allowed_uid(uid)

        ttl = self._clamp_ttl(ttl_seconds)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)
        payload = {
            "sub": uid,
            "telegram_uid": uid,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._issuer,
            "aud": self._audience,
            "jti": create_resource_id("ml"),
        }
        token = self._encode_jwt(payload)
        return PanelMagicLinkRead(
            url=self._build_magic_link_url(token),
            telegram_uid=uid,
            expires_at=expires_at,
        )

    def verify_token(self, token: str, now: datetime | None = None) -> MagicLinkClaims:
        if not self.enabled:
            raise PermissionError("panel access is disabled")

        payload = self._decode_jwt(token)
        uid_raw = payload.get("telegram_uid") or payload.get("sub")
        uid = str(uid_raw).strip() if uid_raw is not None else ""
        if not uid:
            raise PermissionError("missing telegram uid claim")
        self._enforce_allowed_uid(uid)

        issued_at = self._require_datetime_claim(payload, "iat")
        expires_at = self._require_datetime_claim(payload, "exp")
        current = now or datetime.now(timezone.utc)
        if expires_at <= current:
            raise PermissionError("token expired")
        if issued_at > current + timedelta(seconds=60):
            raise PermissionError("token issued in the future")

        if payload.get("iss") != self._issuer:
            raise PermissionError("invalid token issuer")
        if payload.get("aud") != self._audience:
            raise PermissionError("invalid token audience")

        return MagicLinkClaims(
            telegram_uid=uid,
            expires_at=expires_at,
            issued_at=issued_at,
            token_id=str(payload.get("jti", "")).strip() or None,
        )

    def verify_telegram_init_data(
        self,
        init_data: str,
        *,
        now: datetime | None = None,
    ) -> TelegramInitDataClaims:
        if not self._telegram_bot_token:
            raise PermissionError("telegram initData verification is disabled")

        raw = init_data.strip()
        if not raw:
            raise PermissionError("missing telegram initData")
        try:
            parsed_pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise PermissionError("invalid telegram initData format") from exc

        fields: dict[str, str] = {}
        for key, value in parsed_pairs:
            if key in fields:
                raise PermissionError(f"duplicate telegram initData field: {key}")
            fields[key] = value

        provided_hash = (fields.pop("hash", "") or "").strip().lower()
        if not provided_hash:
            raise PermissionError("missing telegram initData hash")
        # "signature" is used by third-party Ed25519 verification and should not
        # participate in the default HMAC data-check string.
        fields.pop("signature", None)

        data_check_items = [f"{key}={value}" for key, value in sorted(fields.items(), key=lambda pair: pair[0])]
        data_check_string = "\n".join(data_check_items)
        secret_key = hmac.new(b"WebAppData", self._telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(provided_hash, calculated_hash):
            raise PermissionError("invalid telegram initData signature")

        auth_date_raw = fields.get("auth_date")
        if auth_date_raw is None:
            raise PermissionError("missing telegram initData auth_date")
        try:
            auth_date_unix = int(auth_date_raw)
        except (TypeError, ValueError) as exc:
            raise PermissionError("invalid telegram initData auth_date") from exc
        auth_date = datetime.fromtimestamp(auth_date_unix, tz=timezone.utc)
        current = now or datetime.now(timezone.utc)
        if auth_date > current + timedelta(seconds=60):
            raise PermissionError("telegram initData is from the future")
        age_seconds = (current - auth_date).total_seconds()
        if age_seconds > self._telegram_init_data_max_age_seconds:
            raise PermissionError("telegram initData expired")

        telegram_uid = self._extract_uid_from_init_data(fields)
        if not telegram_uid:
            raise PermissionError("missing telegram uid in initData")
        self._enforce_allowed_uid(telegram_uid)
        expires_at = auth_date + timedelta(seconds=self._telegram_init_data_max_age_seconds)
        query_id = str(fields.get("query_id", "")).strip() or None
        return TelegramInitDataClaims(
            telegram_uid=telegram_uid,
            auth_date=auth_date,
            expires_at=expires_at,
            query_id=query_id,
        )

    def _clamp_ttl(self, ttl_seconds: int | None) -> int:
        if ttl_seconds is None:
            return self._default_ttl_seconds
        return max(30, min(self._max_ttl_seconds, int(ttl_seconds)))

    def _enforce_allowed_uid(self, telegram_uid: str) -> None:
        if not self._allowed_uids:
            return
        if telegram_uid not in self._allowed_uids:
            raise PermissionError(f"telegram uid {telegram_uid} is not allowed")

    def _build_magic_link_url(self, token: str) -> str:
        parsed = urlparse(self._base_url)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_items["token"] = token
        return urlunparse(parsed._replace(query=urlencode(query_items)))

    def _encode_jwt(self, payload: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_part = self._encode_segment(header)
        payload_part = self._encode_segment(payload)
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        signature = self._sign(signing_input)
        signature_part = self._encode_bytes(signature)
        return f"{header_part}.{payload_part}.{signature_part}"

    def _decode_jwt(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise PermissionError("invalid token format")
        header_part, payload_part, signature_part = parts
        try:
            header = self._decode_segment(header_part)
            payload = self._decode_segment(payload_part)
            provided_sig = self._decode_bytes(signature_part)
        except (ValueError, json.JSONDecodeError) as exc:
            raise PermissionError("invalid token encoding") from exc

        if header.get("alg") != "HS256":
            raise PermissionError("unsupported token algorithm")
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(provided_sig, expected_sig):
            raise PermissionError("invalid token signature")
        if not isinstance(payload, dict):
            raise PermissionError("invalid token payload")
        return payload

    def _require_datetime_claim(self, payload: dict[str, Any], name: str) -> datetime:
        raw = payload.get(name)
        if raw is None:
            raise PermissionError(f"missing claim: {name}")
        try:
            as_int = int(raw)
        except (TypeError, ValueError) as exc:
            raise PermissionError(f"invalid claim: {name}") from exc
        return datetime.fromtimestamp(as_int, tz=timezone.utc)

    def _extract_uid_from_init_data(self, fields: dict[str, str]) -> str | None:
        user_blob = fields.get("user", "").strip()
        if user_blob:
            try:
                user = json.loads(user_blob)
            except json.JSONDecodeError as exc:
                raise PermissionError("invalid telegram initData user payload") from exc
            if isinstance(user, dict) and user.get("id") is not None:
                return str(user["id"]).strip()
        receiver_blob = fields.get("receiver", "").strip()
        if receiver_blob:
            try:
                receiver = json.loads(receiver_blob)
            except json.JSONDecodeError as exc:
                raise PermissionError("invalid telegram initData receiver payload") from exc
            if isinstance(receiver, dict) and receiver.get("id") is not None:
                return str(receiver["id"]).strip()
        return None

    def _sign(self, signing_input: bytes) -> bytes:
        return hmac.new(self._secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    def _encode_segment(self, value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self._encode_bytes(raw)

    def _decode_segment(self, segment: str) -> Any:
        raw = self._decode_bytes(segment)
        return json.loads(raw.decode("utf-8"))

    def _encode_bytes(self, raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    def _decode_bytes(self, encoded: str) -> bytes:
        padding = "=" * ((4 - len(encoded) % 4) % 4)
        return base64.urlsafe_b64decode(f"{encoded}{padding}")
