from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import Field

from autoresearch.ga.contracts import PrincipalRead, SecretLeaseRead
from autoresearch.shared.models import StrictModel, utc_now
from autoresearch.shared.store import create_resource_id


class SecretAccessDenied(PermissionError):
    pass


class SecretAccessRequest(StrictModel):
    secret_ref: str
    principal: PrincipalRead = PrincipalRead(principal_id="local-user")
    scope: str
    purpose: str
    ttl_seconds: int = 900
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
        if path.startswith("~") or "/Users/" in path and "/Documents/evan/github/autonomous-agent-stack" not in path:
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
