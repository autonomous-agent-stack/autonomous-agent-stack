"""Group Access Manager for Malu Internal Groups.

Manages group whitelist and magic link generation with group scope.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroupMagicLink:
    """Magic link with group scope."""

    url: str
    chat_id: int
    user_id: int
    scope: str
    expires_at: datetime


class GroupAccessManager:
    """Manages access control for internal groups.

    Features:
    - Load internal group whitelist from environment
    - Generate magic links with group scope
    - Validate group membership
    """

    def __init__(
        self,
        *,
        internal_groups: list[int] | None = None,
        jwt_secret: str | None = None,
        base_url: str = "http://127.0.0.1:8000/api/v1/panel/view",
        default_ttl_seconds: int = 86400,  # 24 hours
    ) -> None:
        self._internal_groups = internal_groups or self._load_internal_groups()
        self._jwt_secret = jwt_secret or os.getenv("JWT_SECRET", "")
        self._base_url = base_url
        self._default_ttl_seconds = default_ttl_seconds

    def _load_internal_groups(self) -> list[int]:
        """Load internal group whitelist from environment."""
        groups_str = os.getenv("AUTORESEARCH_INTERNAL_GROUPS", "").strip()
        if not groups_str:
            return []

        try:
            # Parse JSON array format: "[-10012345678, -10098765432]"
            import json
            groups = json.loads(groups_str)

            # Validate format
            if not isinstance(groups, list):
                raise ValueError("必须是列表")
            if not all(isinstance(g, int) and g < 0 for g in groups):
                raise ValueError("群组ID必须是负数")

            logger.info(f"✅ 已加载 {len(groups)} 个内部群组白名单")
            return groups

        except Exception as e:
            logger.warning(f"⚠️ 加载内部群组失败: {e}")
            return []

    @property
    def enabled(self) -> bool:
        """Check if group access is enabled."""
        return bool(self._jwt_secret) and bool(self._internal_groups)

    def is_internal_group(self, chat_id: int) -> bool:
        """Check if chat_id is in internal group whitelist."""
        return chat_id in self._internal_groups

    def create_group_magic_link(
        self,
        chat_id: int,
        user_id: int,
        ttl_seconds: int | None = None,
    ) -> GroupMagicLink | None:
        """Create magic link with group scope for internal groups.

        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            ttl_seconds: Token TTL (default: 24 hours)

        Returns:
            GroupMagicLink if successful, None if not in whitelist
        """
        if not self.enabled:
            logger.warning("Group access is not enabled (missing JWT_SECRET or whitelist)")
            return None

        if not self.is_internal_group(chat_id):
            logger.info(f"Chat {chat_id} is not in internal group whitelist")
            return None

        ttl = ttl_seconds or self._default_ttl_seconds
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        # Build JWT payload with group scope
        # Note: Include both telegram_uid and user_id for compatibility
        # Use same issuer as PanelAccessService for compatibility
        payload = {
            "sub": str(user_id),  # Standard JWT subject claim
            "telegram_uid": str(user_id),  # Required by PanelAccessService
            "user_id": user_id,
            "chat_id": chat_id,
            "scope": "group",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": "autoresearch.telegram",  # Same as PanelAccessService
            "aud": "autoresearch.panel",
            "jti": self._generate_token_id(),
        }

        # Encode JWT
        token = self._encode_jwt(payload)

        # Build magic link URL
        from urllib.parse import urlencode, urlparse, urlunparse
        parsed = urlparse(self._base_url)
        query_items = {"token": token}
        url = urlunparse(parsed._replace(query=urlencode(query_items)))

        logger.info(f"✅ 为群组 {chat_id} 用户 {user_id} 生成魔法链接")

        return GroupMagicLink(
            url=url,
            chat_id=chat_id,
            user_id=user_id,
            scope="group",
            expires_at=expires_at,
        )

    def _generate_token_id(self) -> str:
        """Generate unique token ID."""
        import uuid
        return f"ml_{uuid.uuid4().hex[:16]}"

    def _encode_jwt(self, payload: dict[str, Any]) -> str:
        """Encode JWT with HS256 algorithm."""
        import base64
        import hashlib
        import hmac
        import json

        header = {"alg": "HS256", "typ": "JWT"}
        header_part = self._encode_segment(header)
        payload_part = self._encode_segment(payload)
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        signature = hmac.new(
            self._jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        signature_part = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
        return f"{header_part}.{payload_part}.{signature_part}"

    def _encode_segment(self, value: dict[str, Any]) -> str:
        """Encode JSON segment for JWT."""
        import base64
        import json

        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
