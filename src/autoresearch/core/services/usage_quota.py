from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionEventCreateRequest, StrictModel, utc_now
from autoresearch.shared.store import Repository, create_resource_id


UsageSubjectType = Literal["user", "peer"]
UsageLedgerStatus = Literal["reserved", "committed", "released", "rejected"]


class UsageQuotaCheckRequest(StrictModel):
    subject_id: str = Field(..., min_length=1)
    subject_type: UsageSubjectType = "user"
    actor_role: str = "member"
    agent_name: str | None = None
    tool_id: str | None = None
    task_id: str | None = None
    quota_units: int = Field(default=1, ge=0)
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("subject_id", "actor_role", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("agent_name", "tool_id", "task_id", "session_id", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class UsageLedgerEntryRead(StrictModel):
    entry_id: str
    subject_id: str
    subject_type: UsageSubjectType = "user"
    actor_role: str = "member"
    agent_name: str | None = None
    tool_id: str | None = None
    task_id: str | None = None
    quota_units: int = 0
    status: UsageLedgerStatus
    reason: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageQuotaRead(StrictModel):
    subject_id: str
    subject_type: UsageSubjectType = "user"
    actor_role: str = "member"
    period_seconds: int
    limit_units: int
    used_units: int
    reserved_units: int
    remaining_units: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageReserveRead(StrictModel):
    allowed: bool
    reason: str
    quota: UsageQuotaRead
    entry: UsageLedgerEntryRead | None = None


class UsageQuotaService:
    """Credit-unit quota ledger for users and federation peers."""

    def __init__(
        self,
        *,
        repository: Repository[UsageLedgerEntryRead],
        policy_path: Path,
        session_events: SessionEventService | None = None,
    ) -> None:
        self._repository = repository
        self._policy_path = policy_path
        self._session_events = session_events
        self._policy = self._load_policy()

    @property
    def policy_path(self) -> Path:
        return self._policy_path

    def list_entries(
        self,
        *,
        subject_id: str | None = None,
        status: UsageLedgerStatus | None = None,
        limit: int = 200,
    ) -> list[UsageLedgerEntryRead]:
        items = self._repository.list()
        if subject_id:
            items = [item for item in items if item.subject_id == subject_id]
        if status:
            items = [item for item in items if item.status == status]
        return items[: max(1, min(limit, 1000))]

    def quota_for(
        self,
        *,
        subject_id: str,
        subject_type: UsageSubjectType = "user",
        actor_role: str = "member",
    ) -> UsageQuotaRead:
        role = (actor_role or "member").strip().lower() or "member"
        period_seconds = self._period_seconds()
        limit_units = self._limit_units_for(role=role, subject_id=subject_id, subject_type=subject_type)
        used, reserved = self._current_usage(
            subject_id=subject_id,
            subject_type=subject_type,
            period_seconds=period_seconds,
        )
        return UsageQuotaRead(
            subject_id=subject_id,
            subject_type=subject_type,
            actor_role=role,
            period_seconds=period_seconds,
            limit_units=limit_units,
            used_units=used,
            reserved_units=reserved,
            remaining_units=max(0, limit_units - used - reserved),
            metadata={"policy_path": str(self._policy_path), "policy_loaded": self._policy_path.exists()},
        )

    def reserve(self, request: UsageQuotaCheckRequest) -> UsageReserveRead:
        quota = self.quota_for(
            subject_id=request.subject_id,
            subject_type=request.subject_type,
            actor_role=request.actor_role,
        )
        if request.quota_units <= 0:
            return UsageReserveRead(allowed=True, reason="zero-cost request", quota=quota, entry=None)
        if request.quota_units > quota.remaining_units:
            entry = self._save_entry(request, status="rejected", reason="quota exceeded")
            return UsageReserveRead(
                allowed=False,
                reason="quota exceeded",
                quota=quota,
                entry=entry,
            )
        entry = self._save_entry(request, status="reserved", reason="quota reserved")
        refreshed = self.quota_for(
            subject_id=request.subject_id,
            subject_type=request.subject_type,
            actor_role=request.actor_role,
        )
        return UsageReserveRead(allowed=True, reason="quota reserved", quota=refreshed, entry=entry)

    def commit(self, entry_id: str, *, metadata: dict[str, Any] | None = None) -> UsageLedgerEntryRead:
        return self._transition(entry_id, status="committed", reason="quota committed", metadata=metadata)

    def release(self, entry_id: str, *, metadata: dict[str, Any] | None = None) -> UsageLedgerEntryRead:
        return self._transition(entry_id, status="released", reason="quota released", metadata=metadata)

    def doctor(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "policy_path": str(self._policy_path),
            "policy_loaded": self._policy_path.exists(),
            "entries": len(self._repository.list()),
            "period_seconds": self._period_seconds(),
        }

    def _save_entry(
        self,
        request: UsageQuotaCheckRequest,
        *,
        status: UsageLedgerStatus,
        reason: str,
    ) -> UsageLedgerEntryRead:
        current = utc_now()
        entry = UsageLedgerEntryRead(
            entry_id=create_resource_id("usage"),
            subject_id=request.subject_id,
            subject_type=request.subject_type,
            actor_role=request.actor_role.strip().lower() or "member",
            agent_name=request.agent_name,
            tool_id=request.tool_id,
            task_id=request.task_id,
            quota_units=request.quota_units,
            status=status,
            reason=reason,
            created_at=current,
            updated_at=current,
            metadata=dict(request.metadata),
        )
        saved = self._repository.save(entry.entry_id, entry)
        self._record_usage_event(saved, session_id=request.session_id)
        return saved

    def _transition(
        self,
        entry_id: str,
        *,
        status: UsageLedgerStatus,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> UsageLedgerEntryRead:
        entry = self._repository.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        updated = entry.model_copy(
            update={
                "status": status,
                "reason": reason,
                "updated_at": utc_now(),
                "metadata": {**entry.metadata, **dict(metadata or {})},
            }
        )
        saved = self._repository.save(updated.entry_id, updated)
        self._record_usage_event(saved, session_id=_optional_string(saved.metadata.get("session_id")))
        return saved

    def _record_usage_event(self, entry: UsageLedgerEntryRead, *, session_id: str | None) -> None:
        if self._session_events is None or not session_id:
            return
        self._session_events.append(
            SessionEventCreateRequest(
                session_id=session_id,
                source="usage_quota",
                event_type=f"usage.{entry.status}",
                role="status",
                content=f"usage {entry.status}: {entry.quota_units} CU",
                status=entry.status,
                idempotency_key=f"usage:{entry.entry_id}:{entry.status}",
                metadata=entry.model_dump(mode="json"),
            )
        )

    def _current_usage(
        self,
        *,
        subject_id: str,
        subject_type: UsageSubjectType,
        period_seconds: int,
    ) -> tuple[int, int]:
        cutoff = utc_now() - timedelta(seconds=period_seconds)
        committed = 0
        reserved = 0
        for entry in self._repository.list():
            if entry.subject_id != subject_id or entry.subject_type != subject_type:
                continue
            if entry.created_at < cutoff:
                continue
            if entry.status == "committed":
                committed += entry.quota_units
            elif entry.status == "reserved":
                reserved += entry.quota_units
        return committed, reserved

    def _load_policy(self) -> dict[str, Any]:
        if not self._policy_path.exists():
            return {}
        return load_yaml_object(self._policy_path)

    def _period_seconds(self) -> int:
        raw = (self._policy.get("defaults") or {}).get("period_seconds", 86400)
        try:
            return max(60, int(raw))
        except (TypeError, ValueError):
            return 86400

    def _limit_units_for(self, *, role: str, subject_id: str, subject_type: UsageSubjectType) -> int:
        subjects = self._policy.get("subjects") if isinstance(self._policy.get("subjects"), dict) else {}
        subject_policy = subjects.get(subject_id) if isinstance(subjects, dict) else None
        if isinstance(subject_policy, dict) and subject_policy.get("max_units_per_period") is not None:
            return _positive_int(subject_policy.get("max_units_per_period"), default=100)

        peers = self._policy.get("peers") if isinstance(self._policy.get("peers"), dict) else {}
        if subject_type == "peer" and isinstance(peers, dict):
            peer_policy = peers.get(subject_id)
            if isinstance(peer_policy, dict) and peer_policy.get("max_units_per_period") is not None:
                return _positive_int(peer_policy.get("max_units_per_period"), default=100)

        roles = self._policy.get("roles") if isinstance(self._policy.get("roles"), dict) else {}
        role_policy = roles.get(role) if isinstance(roles, dict) else None
        if isinstance(role_policy, dict) and role_policy.get("max_units_per_period") is not None:
            return _positive_int(role_policy.get("max_units_per_period"), default=100)

        return _positive_int((self._policy.get("defaults") or {}).get("max_units_per_period"), default=100)


def _positive_int(value: Any, *, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
