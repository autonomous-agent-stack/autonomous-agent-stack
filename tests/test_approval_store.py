"""Tests for ApprovalStoreService — create, list, resolve, expiration."""
from __future__ import annotations

from datetime import timedelta

import pytest

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalStatus,
    ApprovalRisk,
)
from autoresearch.shared.store import InMemoryRepository


def _make_service() -> ApprovalStoreService:
    return ApprovalStoreService(repository=InMemoryRepository())


def _make_create_request(**overrides) -> ApprovalRequestCreateRequest:
    defaults = {
        "title": "Test Approval",
        "summary": "A test approval request",
        "risk": ApprovalRisk.READ,
        "source": "test",
        "expires_in_seconds": 3600,
    }
    defaults.update(overrides)
    return ApprovalRequestCreateRequest(**defaults)


class TestApprovalStoreCreate:
    def test_create_returns_pending(self) -> None:
        svc = _make_service()
        req = _make_create_request()
        result = svc.create_request(req)
        assert result.approval_id.startswith("apr_")
        assert result.status == ApprovalStatus.PENDING
        assert result.title == "Test Approval"

    def test_create_strips_whitespace(self) -> None:
        svc = _make_service()
        req = _make_create_request(title="  hello  ", summary="  world  ")
        result = svc.create_request(req)
        assert result.title == "hello"
        assert result.summary == "world"

    def test_create_with_optional_fields(self) -> None:
        svc = _make_service()
        req = _make_create_request(
            telegram_uid="12345",
            session_id="sess_abc",
            agent_run_id="run_xyz",
        )
        result = svc.create_request(req)
        assert result.telegram_uid == "12345"
        assert result.session_id == "sess_abc"
        assert result.agent_run_id == "run_xyz"


class TestApprovalStoreGet:
    def test_get_existing(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        got = svc.get_request(created.approval_id)
        assert got is not None
        assert got.approval_id == created.approval_id

    def test_get_missing_returns_none(self) -> None:
        svc = _make_service()
        assert svc.get_request("nonexistent") is None


class TestApprovalStoreList:
    def test_list_returns_all(self) -> None:
        svc = _make_service()
        svc.create_request(_make_create_request(title="A"))
        svc.create_request(_make_create_request(title="B"))
        items = svc.list_requests()
        assert len(items) == 2

    def test_list_filter_by_status(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        svc.resolve_request(
            created.approval_id,
            ApprovalDecisionRequest(decision="approved", decided_by="admin"),
        )
        pending = svc.list_requests(status=ApprovalStatus.PENDING)
        assert len(pending) == 0
        approved = svc.list_requests(status=ApprovalStatus.APPROVED)
        assert len(approved) == 1

    def test_list_filter_by_telegram_uid(self) -> None:
        svc = _make_service()
        svc.create_request(_make_create_request(telegram_uid="u1"))
        svc.create_request(_make_create_request(telegram_uid="u2"))
        items = svc.list_requests(telegram_uid="u1")
        assert len(items) == 1
        assert items[0].telegram_uid == "u1"

    def test_list_respects_limit(self) -> None:
        svc = _make_service()
        for i in range(5):
            svc.create_request(_make_create_request(title=f"T{i}"))
        items = svc.list_requests(limit=2)
        assert len(items) == 2


class TestApprovalStoreResolve:
    def test_approve(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        result = svc.resolve_request(
            created.approval_id,
            ApprovalDecisionRequest(decision="approved", decided_by="admin", note="looks good"),
        )
        assert result.status == ApprovalStatus.APPROVED
        assert result.decided_by == "admin"
        assert result.decision_note == "looks good"
        assert result.resolved_at is not None

    def test_reject(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        result = svc.resolve_request(
            created.approval_id,
            ApprovalDecisionRequest(decision="rejected", decided_by="bob"),
        )
        assert result.status == ApprovalStatus.REJECTED

    def test_resolve_missing_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(KeyError, match="not found"):
            svc.resolve_request(
                "nonexistent",
                ApprovalDecisionRequest(decision="approved", decided_by="x"),
            )

    def test_resolve_already_resolved_raises(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        svc.resolve_request(
            created.approval_id,
            ApprovalDecisionRequest(decision="approved", decided_by="admin"),
        )
        with pytest.raises(ValueError, match="not pending"):
            svc.resolve_request(
                created.approval_id,
                ApprovalDecisionRequest(decision="rejected", decided_by="admin"),
            )


class TestApprovalStoreExpiration:
    def test_expired_approval_auto_transitions(self) -> None:
        svc = _make_service()
        # Create with minimum expiration then manually backdate expires_at
        created = svc.create_request(_make_create_request(expires_in_seconds=60))
        # Force-expire by overwriting with past expires_at
        from autoresearch.shared.models import utc_now
        from datetime import datetime, timezone, timedelta

        expired = created.model_copy(update={
            "expires_at": utc_now() - timedelta(seconds=1),
        })
        svc._repository.save(expired.approval_id, expired)

        # Getting it should auto-expire
        got = svc.get_request(created.approval_id)
        assert got.status == ApprovalStatus.EXPIRED

    def test_update_metadata(self) -> None:
        svc = _make_service()
        created = svc.create_request(_make_create_request())
        updated = svc.update_request_metadata(
            created.approval_id,
            {"github_issue_url": "https://github.com/owner/repo/issues/1"},
        )
        assert updated.metadata["github_issue_url"] == "https://github.com/owner/repo/issues/1"

    def test_update_metadata_missing_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(KeyError, match="not found"):
            svc.update_request_metadata("nonexistent", {"key": "value"})
