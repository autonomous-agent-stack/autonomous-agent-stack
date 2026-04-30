from __future__ import annotations

import logging
from datetime import timedelta

from autoresearch.core.services.session_events import SessionEventService, resolve_session_id_from_payload
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalStatus,
    SessionEventCreateRequest,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id

logger = logging.getLogger(__name__)


class ApprovalStoreService:
    """SQLite-backed approval request store.

    This phase only needs one stable source of truth for pending approvals.
    Decision actions can be layered on top later without changing the storage contract.
    """

    def __init__(
        self,
        repository: Repository[ApprovalRequestRead],
        writer_lease: WriterLeaseService | None = None,
        session_events: SessionEventService | None = None,
    ) -> None:
        self._repository = repository
        self._writer_lease = writer_lease or WriterLeaseService()
        self._session_events = session_events

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
            saved = self._repository.save(approval.approval_id, approval)
            self._append_approval_event(
                saved,
                event_type="approval.requested",
                content=saved.title,
                idempotency_key=f"approval:{saved.approval_id}:created",
                metadata={"summary": saved.summary, "risk": saved.risk.value},
            )
            return saved

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

    def find_by_metadata(
        self,
        expected: dict[str, object],
        *,
        status: ApprovalStatus | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequestRead]:
        normalized_expected = {
            str(key): value
            for key, value in expected.items()
            if str(key).strip()
        }
        if not normalized_expected:
            return []
        matches: list[ApprovalRequestRead] = []
        for item in self._repository.list():
            normalized = self._normalize_expiration(item)
            if status is not None and normalized.status != status:
                continue
            if all(normalized.metadata.get(key) == value for key, value in normalized_expected.items()):
                matches.append(normalized)
        matches.sort(key=lambda item: item.updated_at, reverse=True)
        return matches[: max(1, limit)]

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
            saved = self._repository.save(updated.approval_id, updated)
            self._append_approval_event(
                saved,
                event_type=f"approval.{status.value}",
                content=f"approval {status.value}: {saved.title}",
                idempotency_key=f"approval:{saved.approval_id}:{status.value}",
                metadata={
                    "decided_by": saved.decided_by,
                    "decision_note": saved.decision_note,
                },
            )
            return saved

    def update_request_metadata(
        self,
        approval_id: str,
        metadata_updates: dict[str, object],
        *,
        require_status: ApprovalStatus | None = None,
    ) -> ApprovalRequestRead:
        with self._writer_lease.acquire(f"approval:{approval_id}"):
            item = self.get_request(approval_id)
            if item is None:
                raise KeyError(f"approval not found: {approval_id}")
            if require_status is not None and item.status != require_status:
                raise ValueError(f"approval is not {require_status.value}: {approval_id}")

            updated = item.model_copy(
                update={
                    "metadata": {
                        **item.metadata,
                        **metadata_updates,
                    },
                    "updated_at": utc_now(),
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
        saved = self._repository.save(expired.approval_id, expired)
        self._append_approval_event(
            saved,
            event_type="approval.expired",
            content=f"approval expired: {saved.title}",
            idempotency_key=f"approval:{saved.approval_id}:expired",
        )
        return saved

    def append_pending_side_event(
        self,
        approval: ApprovalRequestRead,
        *,
        event_type: str,
        content: str,
        metadata: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        self._append_approval_event(
            approval,
            event_type=event_type,
            content=content,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    def _append_approval_event(
        self,
        approval: ApprovalRequestRead,
        *,
        event_type: str,
        content: str,
        idempotency_key: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self._session_events is None:
            return
        session_id = approval.session_id or resolve_session_id_from_payload(approval.metadata, None)
        if not session_id:
            return
        try:
            self._session_events.append(
                SessionEventCreateRequest(
                    session_id=session_id,
                    source="approval_store",
                    event_type=event_type,
                    role="status",
                    content=content,
                    status=approval.status.value,
                    runtime_id=_optional_string(approval.metadata.get("runtime_id")),
                    run_id=approval.agent_run_id or _optional_string(approval.metadata.get("run_id")),
                    approval_id=approval.approval_id,
                    worker_id=_optional_string(approval.metadata.get("worker_id")),
                    idempotency_key=idempotency_key,
                    metadata={
                        "source": approval.source,
                        **dict(metadata or {}),
                    },
                )
            )
        except Exception:
            logger.warning("Failed to append approval session event for %s", approval.approval_id, exc_info=True)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
