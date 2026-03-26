from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any

from autoresearch.shared.models import AdminTokenRead
from autoresearch.shared.store import create_resource_id


_DEFAULT_ROLES = {"viewer", "editor", "admin", "owner"}


@dataclass(frozen=True)
class AdminAccessClaims:
    subject: str
    roles: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    token_id: str | None = None


class AdminAuthService:
    """Issue and verify short-lived admin JWT tokens with role checks."""

    def __init__(
        self,
        *,
        secret: str | None,
        bootstrap_key: str | None,
        issuer: str = "autoresearch.admin",
        audience: str = "autoresearch.admin.api",
        default_ttl_seconds: int = 3600,
        max_ttl_seconds: int = 86400,
        allowed_roles: set[str] | None = None,
    ) -> None:
        self._secret = (secret or "").strip()
        self._bootstrap_key = (bootstrap_key or "").strip()
        self._issuer = issuer
        self._audience = audience
        self._default_ttl_seconds = max(60, default_ttl_seconds)
        self._max_ttl_seconds = max(self._default_ttl_seconds, max_ttl_seconds)
        normalized_roles = {role.strip().lower() for role in (allowed_roles or _DEFAULT_ROLES) if role.strip()}
        self._allowed_roles = normalized_roles or _DEFAULT_ROLES

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    @property
    def bootstrap_enabled(self) -> bool:
        return bool(self._bootstrap_key)

    def issue_token(
        self,
        *,
        subject: str,
        roles: list[str],
        bootstrap_key: str | None,
        ttl_seconds: int | None = None,
    ) -> AdminTokenRead:
        if not self.enabled:
            raise PermissionError("admin auth is disabled: missing AUTORESEARCH_ADMIN_JWT_SECRET")
        if not self.bootstrap_enabled:
            raise PermissionError("admin token issuing is disabled: missing bootstrap key")
        provided_key = (bootstrap_key or "").strip()
        if not provided_key or not hmac.compare_digest(provided_key, self._bootstrap_key):
            raise PermissionError("invalid bootstrap key")

        normalized_subject = subject.strip()
        if not normalized_subject:
            raise ValueError("subject is required")
        normalized_roles = self._normalize_roles(roles)
        if not normalized_roles:
            raise ValueError("at least one valid role is required")

        ttl = self._clamp_ttl(ttl_seconds)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)
        payload = {
            "sub": normalized_subject,
            "roles": list(normalized_roles),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._issuer,
            "aud": self._audience,
            "jti": create_resource_id("admintok"),
        }
        token = self._encode_jwt(payload)
        return AdminTokenRead(
            token=token,
            token_type="Bearer",
            subject=normalized_subject,
            roles=list(normalized_roles),
            issued_at=now,
            expires_at=expires_at,
        )

    def verify_token(
        self,
        token: str,
        *,
        required_roles: set[str] | None = None,
        now: datetime | None = None,
    ) -> AdminAccessClaims:
        if not self.enabled:
            raise PermissionError("admin auth is disabled: missing AUTORESEARCH_ADMIN_JWT_SECRET")
        payload = self._decode_jwt(token)
        subject = str(payload.get("sub", "")).strip()
        if not subject:
            raise PermissionError("missing admin subject")

        issued_at = self._require_datetime_claim(payload, "iat")
        expires_at = self._require_datetime_claim(payload, "exp")
        current = now or datetime.now(timezone.utc)
        if expires_at <= current:
            raise PermissionError("admin token expired")
        if issued_at > current + timedelta(seconds=60):
            raise PermissionError("admin token issued in the future")

        if payload.get("iss") != self._issuer:
            raise PermissionError("invalid admin token issuer")
        if payload.get("aud") != self._audience:
            raise PermissionError("invalid admin token audience")

        raw_roles = payload.get("roles")
        if not isinstance(raw_roles, list):
            raise PermissionError("invalid admin token roles")
        normalized_roles = tuple(self._normalize_roles([str(item) for item in raw_roles]))
        if not normalized_roles:
            raise PermissionError("admin token contains no valid role")

        required = {item.strip().lower() for item in (required_roles or set()) if item.strip()}
        if required and not required.intersection(set(normalized_roles)):
            raise PermissionError("insufficient admin role")

        return AdminAccessClaims(
            subject=subject,
            roles=normalized_roles,
            issued_at=issued_at,
            expires_at=expires_at,
            token_id=str(payload.get("jti", "")).strip() or None,
        )

    def _clamp_ttl(self, ttl_seconds: int | None) -> int:
        if ttl_seconds is None:
            return self._default_ttl_seconds
        return max(60, min(self._max_ttl_seconds, int(ttl_seconds)))

    def _normalize_roles(self, roles: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for role in roles:
            normalized = role.strip().lower()
            if not normalized:
                continue
            if normalized not in self._allowed_roles:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

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
            raise PermissionError("invalid admin token format")
        header_part, payload_part, signature_part = parts
        try:
            header = self._decode_segment(header_part)
            payload = self._decode_segment(payload_part)
            provided_sig = self._decode_bytes(signature_part)
        except (ValueError, json.JSONDecodeError) as exc:
            raise PermissionError("invalid admin token encoding") from exc
        if header.get("alg") != "HS256":
            raise PermissionError("unsupported admin token algorithm")
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(provided_sig, expected_sig):
            raise PermissionError("invalid admin token signature")
        if not isinstance(payload, dict):
            raise PermissionError("invalid admin token payload")
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
