from __future__ import annotations

from datetime import timedelta

from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalStatus,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class ApprovalStoreService:
    """SQLite-backed approval request store.

    This phase only needs one stable source of truth for pending approvals.
    Decision actions can be layered on top later without changing the storage contract.
    """

    def __init__(
        self,
        repository: Repository[ApprovalRequestRead],
        writer_lease: WriterLeaseService | None = None,
    ) -> None:
        self._repository = repository
        self._writer_lease = writer_lease or WriterLeaseService()

    def create_request(self, request: ApprovalRequestCreateRequest) -> ApprovalRequestRead:
        with self._writer_lease.acquire("approval:create"):
            now = utc_now()
            approval = ApprovalRequestRead(
                approval_id=create_resource_id("apr"),
                title=request.title.strip(),
                summary=request.summary.strip(),
                status=ApprovalStatus.PENDING,
                risk=request.risk,
                source=request.source.strip() or "manual",
                telegram_uid=(request.telegram_uid or "").strip() or None,
                session_id=(request.session_id or "").strip() or None,
                agent_run_id=(request.agent_run_id or "").strip() or None,
                assistant_scope=request.assistant_scope,
                metadata=dict(request.metadata),
                created_at=now,
                updated_at=now,
                expires_at=now + timedelta(seconds=request.expires_in_seconds),
                resolved_at=None,
                decided_by=None,
                decision_note=None,
            )
            return self._repository.save(approval.approval_id, approval)

    def get_request(self, approval_id: str) -> ApprovalRequestRead | None:
        item = self._repository.get(approval_id)
        if item is None:
            return None
        return self._normalize_expiration(item)

    def list_requests(
        self,
        *,
        status: ApprovalStatus | None = None,
        telegram_uid: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequestRead]:
        normalized_uid = (telegram_uid or "").strip() or None
        normalized_session_id = (session_id or "").strip() or None
        items: list[ApprovalRequestRead] = []
        for item in self._repository.list():
            normalized = self._normalize_expiration(item)
            if status is not None and normalized.status != status:
                continue
            if normalized_uid is not None and normalized.telegram_uid != normalized_uid:
                continue
            if normalized_session_id is not None and normalized.session_id != normalized_session_id:
                continue
            items.append(normalized)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[: max(1, limit)]

    def resolve_request(
        self,
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> ApprovalRequestRead:
        with self._writer_lease.acquire(f"approval:{approval_id}"):
            item = self.get_request(approval_id)
            if item is None:
                raise KeyError(f"approval not found: {approval_id}")
            if item.status != ApprovalStatus.PENDING:
                raise ValueError(f"approval is not pending: {approval_id}")

            status = ApprovalStatus.APPROVED if request.decision == "approved" else ApprovalStatus.REJECTED
            now = utc_now()
            updated = item.model_copy(
                update={
                    "status": status,
                    "updated_at": now,
                    "resolved_at": now,
                    "decided_by": request.decided_by.strip(),
                    "decision_note": (request.note or "").strip() or None,
                    "metadata": {
                        **item.metadata,
                        **request.metadata,
                    },
                }
            )
            return self._repository.save(updated.approval_id, updated)

    def _normalize_expiration(self, item: ApprovalRequestRead) -> ApprovalRequestRead:
        if item.status != ApprovalStatus.PENDING:
            return item
        if item.expires_at is None or item.expires_at > utc_now():
            return item
        expired = item.model_copy(
            update={
                "status": ApprovalStatus.EXPIRED,
                "updated_at": utc_now(),
                "resolved_at": utc_now(),
                "decision_note": item.decision_note or "approval expired",
            }
        )
        return self._repository.save(expired.approval_id, expired)
