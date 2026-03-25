from __future__ import annotations

from typing import Any

from autoresearch.shared.models import PanelAuditLogRead, utc_now
from autoresearch.shared.store import Repository, create_resource_id


class PanelAuditService:
    """Persist panel manual intervention events for zero-trust auditing."""

    def __init__(self, repository: Repository[PanelAuditLogRead]) -> None:
        self._repository = repository

    def log_action(
        self,
        *,
        telegram_uid: str,
        action: str,
        target_id: str,
        status: str = "accepted",
        reason: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PanelAuditLogRead:
        now = utc_now()
        entry = PanelAuditLogRead(
            audit_id=create_resource_id("audit"),
            telegram_uid=telegram_uid,
            action=action,
            target_type="agent_run",
            target_id=target_id,
            status=status,
            reason=reason,
            request_ip=request_ip,
            user_agent=user_agent,
            metadata=metadata or {},
            created_at=now,
        )
        return self._repository.save(entry.audit_id, entry)

    def list_by_uid(self, telegram_uid: str, limit: int = 100) -> list[PanelAuditLogRead]:
        normalized_uid = telegram_uid.strip()
        if not normalized_uid:
            return []
        logs = [item for item in self._repository.list() if item.telegram_uid == normalized_uid]
        logs.sort(key=lambda item: item.created_at, reverse=True)
        return logs[: max(1, limit)]
