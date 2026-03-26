from __future__ import annotations

import base64
import hashlib


class AdminSecretCipher:
    """Symmetric secret encryption/decryption for admin-managed channel credentials."""

    def __init__(self, secret_key: str | None) -> None:
        self._raw_secret_key = (secret_key or "").strip()
        self._fernet = None
        self._invalid_token_exc = Exception
        if not self._raw_secret_key:
            return

        try:
            from cryptography.fernet import Fernet, InvalidToken
        except Exception as exc:  # pragma: no cover - depends on optional package availability
            raise RuntimeError(
                "cryptography package is required when AUTORESEARCH_ADMIN_SECRET_KEY is set"
            ) from exc

        derived = self._to_fernet_key(self._raw_secret_key)
        self._fernet = Fernet(derived)
        self._invalid_token_exc = InvalidToken

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if not self.enabled:
            raise RuntimeError("secret cipher is disabled")
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"fernet-v1:{token}"

    def decrypt(self, ciphertext: str) -> str:
        if not self.enabled:
            raise RuntimeError("secret cipher is disabled")
        normalized = ciphertext.strip()
        if normalized.startswith("fernet-v1:"):
            normalized = normalized[len("fernet-v1:") :]
        try:
            plaintext = self._fernet.decrypt(normalized.encode("utf-8"))
        except self._invalid_token_exc as exc:
            raise ValueError("invalid encrypted secret payload") from exc
        return plaintext.decode("utf-8")

    def _to_fernet_key(self, raw_key: str) -> bytes:
        # Accept any user-provided key shape and normalize to a fernet-compatible key.
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
