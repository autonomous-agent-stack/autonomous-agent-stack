from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import Field

from autoresearch.ga.contracts import PrincipalRead, SecretLeaseRead
from autoresearch.shared.models import StrictModel, utc_now
from autoresearch.shared.store import create_resource_id

_REPO_ROOT = Path(__file__).resolve().parents[4]


class SecretAccessDenied(PermissionError):
    pass


class SecretAccessRequest(StrictModel):
    secret_ref: str
    principal: PrincipalRead = PrincipalRead(principal_id="local-user")
    scope: str
    purpose: str
    ttl_seconds: int = 900
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeEnvironmentLease(StrictModel):
    env: dict[str, str] = Field(default_factory=dict)
    lease_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecretVaultService:
    """Lease-only secret boundary for runtimes, tools, connectors, and peers."""

    def __init__(self, *, allowed_scopes: set[str] | None = None) -> None:
        self._allowed_scopes = allowed_scopes or {"connector:*", "runtime:*", "model:*", "tool:*"}
        self._leases: dict[str, SecretLeaseRead] = {}

    def issue_lease(self, request: SecretAccessRequest) -> SecretLeaseRead:
        if not self._scope_allowed(request.scope):
            raise SecretAccessDenied(f"secret scope is not allowed: {request.scope}")
        current = utc_now()
        lease = SecretLeaseRead(
            lease_id=create_resource_id("secret_lease"),
            secret_ref=request.secret_ref,
            principal_id=request.principal.principal_id,
            scope=request.scope,
            purpose=request.purpose,
            expires_at=current + timedelta(seconds=max(1, min(request.ttl_seconds, 3600))),
            created_at=current,
            metadata={"tenant_id": request.principal.tenant_id, **dict(request.metadata)},
        )
        self._leases[lease.lease_id] = lease
        return lease

    def validate_lease(self, lease_id: str, *, scope: str) -> SecretLeaseRead:
        lease = self._leases.get(lease_id)
        if lease is None:
            raise SecretAccessDenied("secret lease not found")
        if lease.expires_at <= utc_now():
            raise SecretAccessDenied("secret lease expired")
        if lease.scope != scope:
            raise SecretAccessDenied("secret lease scope mismatch")
        return lease

    def assert_no_direct_secret_access(self, *, attempted_path: str | None = None) -> None:
        path = str(attempted_path or "").strip()
        if path.endswith(".env") or "/.env" in path or path == ".env":
            raise SecretAccessDenied("direct .env access is forbidden")
        resolved = Path(path).expanduser().resolve() if path else None
        in_repo = bool(resolved and resolved.is_relative_to(_REPO_ROOT))
        if path.startswith("~") or ("/Users/" in path and not in_repo):
            raise SecretAccessDenied("direct host home access is forbidden")

    def list_leases(self) -> list[SecretLeaseRead]:
        return sorted(self._leases.values(), key=lambda item: item.created_at, reverse=True)

    def _scope_allowed(self, scope: str) -> bool:
        normalized = scope.strip()
        for allowed in self._allowed_scopes:
            if allowed.endswith("*") and normalized.startswith(allowed[:-1]):
                return True
            if normalized == allowed:
                return True
        return False


DEFAULT_RUNTIME_ENV_ALLOWLIST = {
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "PYTHONPATH",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "TEMP",
    "TMPDIR",
    "VIRTUAL_ENV",
}

SENSITIVE_ENV_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "PASSWORD")


def build_lease_scoped_runtime_env(
    *,
    overrides: dict[str, Any] | None = None,
    scope: str,
    purpose: str,
    principal: PrincipalRead | None = None,
    vault: SecretVaultService | None = None,
    include_base_keys: set[str] | None = None,
) -> RuntimeEnvironmentLease:
    """Build a runtime env without copying the host environment wholesale."""

    selected = include_base_keys or DEFAULT_RUNTIME_ENV_ALLOWLIST
    env = {key: os.environ[key] for key in sorted(selected) if key in os.environ}
    service = vault or SecretVaultService()
    lease_ids: list[str] = []

    for raw_key, raw_value in dict(overrides or {}).items():
        key = str(raw_key).strip()
        if not key:
            continue
        value = "" if raw_value is None else str(raw_value)
        if _is_sensitive_env_key(key):
            lease = service.issue_lease(
                SecretAccessRequest(
                    secret_ref=f"env:{key}",
                    principal=principal or PrincipalRead(principal_id="runtime-env-builder"),
                    scope=scope,
                    purpose=purpose,
                    metadata={"env_key": key},
                )
            )
            env[f"{key}_LEASE_ID"] = lease.lease_id
            lease_ids.append(lease.lease_id)
            continue
        env[key] = value

    return RuntimeEnvironmentLease(
        env=env,
        lease_ids=lease_ids,
        metadata={
            "scope": scope,
            "purpose": purpose,
            "allowlisted_base_keys": sorted(selected),
            "lease_count": len(lease_ids),
        },
    )


def _is_sensitive_env_key(key: str) -> bool:
    normalized = key.strip().upper()
    return any(normalized.endswith(suffix) for suffix in SENSITIVE_ENV_SUFFIXES)
