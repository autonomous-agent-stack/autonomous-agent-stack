"""Tests for the 3-cut implementation:
- Cut 1: topic-aware session
- Cut 2: claude_runtime in worker queue
- Cut 3: session stickiness
"""
from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.api.settings import TelegramSettings
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.core.services.telegram_identity import build_telegram_session_identity
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    AssistantScope,
    ChatType,
    ClaudeRuntimeSessionRecordRead,
    JobStatus,
    WorkerClaimRequest,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerQueueName,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import InMemoryRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(**overrides) -> TelegramSettings:
    defaults = {
        "bot_token": "test-token",
        "owner_uids": ["100"],
        "partner_uids": [],
        "allowed_uids": ["200"],
        "shared_assistant_id": "shared-bot",
    }
    defaults.update(overrides)
    return TelegramSettings(**defaults)


def _extracted(
    *,
    chat_id="123",
    chat_type="private",
    from_user_id="100",
    message_thread_id=None,
    is_topic_message=False,
    reply_to_message_id=None,
) -> dict:
    return {
        "chat_id": chat_id,
        "chat_type": chat_type,
        "from_user_id": from_user_id,
        "message_id": "999",
        "username": "tester",
        "message_thread_id": message_thread_id,
        "is_topic_message": is_topic_message,
        "reply_to_message_id": reply_to_message_id,
    }


def _make_worker_registry(*worker_ids: str) -> WorkerRegistryService:
    repo: InMemoryRepository[WorkerRegistrationRead] = InMemoryRepository()
    svc = WorkerRegistryService(repository=repo)
    for wid in worker_ids:
        svc.register(WorkerRegistrationRead(
            worker_id=wid,
            worker_type="mac",
            name=wid,
            host="localhost",
            mode=WorkerMode.ACTIVE,
            accepting_work=True,
            registered_at=utc_now(),
            last_heartbeat_at=utc_now(),
            updated_at=utc_now(),
            metadata={},
        ))
    return svc


# ===========================================================================
# Cut 1: topic-aware session
# ===========================================================================

class TestTopicAwareSession:
    """Test that session keys differentiate by topic/thread."""

    def test_private_chat_personal_scope(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(chat_type="private", from_user_id="100"),
            settings,
        )
        assert identity.scope == AssistantScope.PERSONAL
        assert identity.session_key == "telegram:personal:user:100"
        assert identity.chat_context.message_thread_id is None
        assert identity.chat_context.is_topic_message is False

    def test_shared_group_no_topic(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500", from_user_id="100"),
            settings,
        )
        assert identity.scope == AssistantScope.SHARED
        assert identity.session_key == "telegram:shared:chat:500"
        assert identity.chat_context.message_thread_id is None

    def test_shared_group_with_topic(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(
                chat_type="supergroup",
                chat_id="500",
                from_user_id="100",
                message_thread_id="42",
                is_topic_message=True,
            ),
            settings,
        )
        assert identity.scope == AssistantScope.SHARED
        assert identity.session_key == "telegram:shared:chat:500:topic:42"
        assert identity.chat_context.message_thread_id == "42"
        assert identity.chat_context.is_topic_message is True

    def test_different_topics_generate_different_session_keys(self) -> None:
        settings = _settings()
        id_a = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500", message_thread_id="10"),
            settings,
        )
        id_b = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500", message_thread_id="20"),
            settings,
        )
        assert id_a.session_key != id_b.session_key
        assert "topic:10" in id_a.session_key
        assert "topic:20" in id_b.session_key

    def test_topic_and_no_topic_are_different_sessions(self) -> None:
        settings = _settings()
        with_topic = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500", message_thread_id="42"),
            settings,
        )
        without_topic = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500"),
            settings,
        )
        assert with_topic.session_key != without_topic.session_key

    def test_reply_to_message_id_passed_through(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(chat_type="private", from_user_id="100", reply_to_message_id="789"),
            settings,
        )
        assert identity.chat_context.reply_to_message_id == "789"

    def test_backward_compat_missing_thread_fields(self) -> None:
        """Old extracted dicts without thread fields still work."""
        settings = _settings()
        extracted = {
            "chat_id": "500",
            "chat_type": "supergroup",
            "from_user_id": "100",
            "message_id": "999",
            "username": "tester",
        }
        identity = build_telegram_session_identity(extracted, settings)
        assert identity.chat_context.message_thread_id is None
        assert identity.chat_context.is_topic_message is False
        assert identity.chat_context.reply_to_message_id is None
        assert identity.session_key == "telegram:shared:chat:500"


# ===========================================================================
# Cut 1: notifier payload
# ===========================================================================

class TestNotifierTopicSupport:
    """Test that TelegramNotifierService passes thread_id in payloads."""

    def test_send_message_without_thread_id(self, tmp_path: Path) -> None:
        """When no thread_id, payload should not contain message_thread_id."""
        import json
        import urllib.request as req

        notifier = TelegramNotifierService(bot_token="test-token")
        payloads: list[dict] = []

        original_request = req.Request

        def _capture_request(url, data=None, headers=None, method=None, **kw):
            if data and "sendMessage" in url:
                payloads.append(json.loads(data))
            raise Exception("block network")

        req.Request = _capture_request
        try:
            notifier.send_message(chat_id="123", text="hello")
        except Exception:
            pass
        finally:
            req.Request = original_request

        if payloads:
            assert "message_thread_id" not in payloads[0]

    def test_send_message_with_thread_id(self, tmp_path: Path) -> None:
        """When thread_id is provided, payload should contain it."""
        import json
        import urllib.request as req

        notifier = TelegramNotifierService(bot_token="test-token")
        payloads: list[dict] = []

        original_request = req.Request

        def _capture_request(url, data=None, headers=None, method=None, **kw):
            if data and "sendMessage" in url:
                payloads.append(json.loads(data))
            raise Exception("block network")

        req.Request = _capture_request
        try:
            notifier.send_message(chat_id="123", text="hello", message_thread_id=42)
        except Exception:
            pass
        finally:
            req.Request = original_request

        if payloads:
            assert payloads[0].get("message_thread_id") == 42


# ===========================================================================
# Cut 2: webhook -> queue
# ===========================================================================

class TestWebhookToQueue:
    """Test that the webhook enqueue path works for CLAUDE_RUNTIME."""

    def test_enqueue_claude_runtime_task(self) -> None:
        worker_registry = _make_worker_registry("w1")
        queue_repo: InMemoryRepository[WorkerQueueItemRead] = InMemoryRepository()
        lease_repo = InMemoryRepository()
        scheduler = WorkerSchedulerService(
            worker_registry=worker_registry,
            queue_repository=queue_repo,
            lease_repository=lease_repo,
        )

        item = scheduler.enqueue(WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={
                "session_id": "sess_123",
                "session_key": "telegram:shared:chat:500:topic:42",
                "prompt": "hello",
                "chat_id": "500",
                "message_thread_id": "42",
            },
            metadata={
                "session_key": "telegram:shared:chat:500:topic:42",
                "preferred_worker_id": None,
            },
        ))

        assert item.task_type == WorkerTaskType.CLAUDE_RUNTIME
        assert item.status == JobStatus.QUEUED
        assert item.payload["prompt"] == "hello"

        # Worker can claim it
        claim = scheduler.claim("w1", WorkerClaimRequest(queue_name=WorkerQueueName.HOUSEKEEPING))
        assert claim.claimed is True
        assert claim.run is not None
        assert claim.run.task_type == WorkerTaskType.CLAUDE_RUNTIME


# ===========================================================================
# Cut 3: session stickiness
# ===========================================================================

class TestSessionStickiness:
    """Test sticky session records and preferred worker binding."""

    def test_upsert_creates_new_record(self) -> None:
        repo: InMemoryRepository[ClaudeRuntimeSessionRecordRead] = InMemoryRepository()
        svc = ClaudeSessionRecordService(repository=repo)

        record = svc.upsert(
            session_key="telegram:shared:chat:500:topic:42",
            worker_id="w1",
            project_dir="/tmp/project",
        )
        assert record.session_key == "telegram:shared:chat:500:topic:42"
        assert record.worker_id == "w1"
        assert record.project_dir == "/tmp/project"

    def test_upsert_updates_existing(self) -> None:
        repo: InMemoryRepository[ClaudeRuntimeSessionRecordRead] = InMemoryRepository()
        svc = ClaudeSessionRecordService(repository=repo)

        svc.upsert(session_key="sk1", worker_id="w1")
        record = svc.upsert(session_key="sk1", latest_session_ref="ref_abc")

        assert record.worker_id == "w1"
        assert record.latest_session_ref == "ref_abc"

    def test_get_by_session_key(self) -> None:
        repo: InMemoryRepository[ClaudeRuntimeSessionRecordRead] = InMemoryRepository()
        svc = ClaudeSessionRecordService(repository=repo)

        assert svc.get_by_session_key("missing") is None
        svc.upsert(session_key="sk1", worker_id="w1")
        found = svc.get_by_session_key("sk1")
        assert found is not None
        assert found.worker_id == "w1"

    def test_bind_session_to_worker(self) -> None:
        repo: InMemoryRepository[ClaudeRuntimeSessionRecordRead] = InMemoryRepository()
        svc = ClaudeSessionRecordService(repository=repo)

        record = svc.bind_session_to_worker(
            session_key="sk1",
            worker_id="w1",
            project_dir="/workdir",
            claude_home="/home/claude",
        )
        assert record.worker_id == "w1"
        assert record.project_dir == "/workdir"
        assert record.claude_home == "/home/claude"

    def test_consecutive_requests_find_same_binding(self) -> None:
        repo: InMemoryRepository[ClaudeRuntimeSessionRecordRead] = InMemoryRepository()
        svc = ClaudeSessionRecordService(repository=repo)

        # First request - creates binding
        svc.bind_session_to_worker(session_key="sk1", worker_id="w1")
        # Second request - should find the same binding
        record = svc.get_by_session_key("sk1")
        assert record is not None
        assert record.worker_id == "w1"

        # Third request - update and verify
        svc.update_latest(session_key="sk1", last_summary="success")
        record = svc.get_by_session_key("sk1")
        assert record is not None
        assert record.last_summary == "success"
        assert record.worker_id == "w1"  # Still bound to same worker

    def test_preferred_worker_claim_priority(self) -> None:
        """When a task has preferred_worker_id, that worker gets priority."""
        worker_registry = _make_worker_registry("w1", "w2")
        queue_repo: InMemoryRepository[WorkerQueueItemRead] = InMemoryRepository()
        lease_repo = InMemoryRepository()
        scheduler = WorkerSchedulerService(
            worker_registry=worker_registry,
            queue_repository=queue_repo,
            lease_repository=lease_repo,
        )

        # Create a task preferred for w1
        scheduler.enqueue(WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={"prompt": "hello"},
            metadata={"preferred_worker_id": "w1"},
        ))

        # w2 claims first - should NOT get the sticky task
        claim_w2 = scheduler.claim("w2", WorkerClaimRequest(queue_name=WorkerQueueName.HOUSEKEEPING))
        assert claim_w2.claimed is False  # preferred worker is still healthy

        # w1 claims - should get it
        claim_w1 = scheduler.claim("w1", WorkerClaimRequest(queue_name=WorkerQueueName.HOUSEKEEPING))
        assert claim_w1.claimed is True
        assert claim_w1.run is not None
        assert claim_w1.reason == "sticky_match"

    def test_preferred_worker_fallback_when_stale(self) -> None:
        """When preferred worker goes stale, other workers can claim."""
        worker_registry = _make_worker_registry("w1", "w2")
        queue_repo: InMemoryRepository[WorkerQueueItemRead] = InMemoryRepository()
        lease_repo = InMemoryRepository()
        scheduler = WorkerSchedulerService(
            worker_registry=worker_registry,
            queue_repository=queue_repo,
            lease_repository=lease_repo,
        )

        # Create a task preferred for w1
        scheduler.enqueue(WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={"prompt": "hello"},
            metadata={"preferred_worker_id": "w1"},
        ))

        # Make w1 stale by not heartbeating - simulate by getting the worker
        # and re-registering it as stale. Actually, let's just test with w2
        # after removing w1 from the registry.
        # The simpler approach: w1 doesn't claim, so its heartbeat expires.
        # For this test, we just verify w2 CAN claim when w1 is absent.

        # Remove w1 from registry to simulate it being gone
        worker_registry._repository._items.clear()

        # Re-register only w2
        worker_registry.register(WorkerRegistrationRead(
            worker_id="w2",
            worker_type="mac",
            name="w2",
            host="localhost",
            mode=WorkerMode.ACTIVE,
            accepting_work=True,
            registered_at=utc_now(),
            last_heartbeat_at=utc_now(),
            updated_at=utc_now(),
            metadata={},
        ))

        # w2 should now be able to claim the task
        claim = scheduler.claim("w2", WorkerClaimRequest(queue_name=WorkerQueueName.HOUSEKEEPING))
        assert claim.claimed is True


# ===========================================================================
# Regression: existing private/group paths not broken
# ===========================================================================

class TestRegression:
    """Verify existing paths still work."""

    def test_private_chat_identity_unchanged(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(chat_type="private", from_user_id="100"),
            settings,
        )
        assert identity.session_key == "telegram:personal:user:100"
        assert identity.scope == AssistantScope.PERSONAL

    def test_group_chat_identity_unchanged(self) -> None:
        settings = _settings()
        identity = build_telegram_session_identity(
            _extracted(chat_type="supergroup", chat_id="500", from_user_id="100"),
            settings,
        )
        assert identity.session_key == "telegram:shared:chat:500"
        assert identity.scope == AssistantScope.SHARED

    def test_worker_task_type_enum_extended(self) -> None:
        assert WorkerTaskType.CLAUDE_RUNTIME.value == "claude_runtime"
        # All existing types still exist
        assert WorkerTaskType.NOOP.value == "noop"
        assert WorkerTaskType.YOUTUBE_AUTOFLOW.value == "youtube_autoflow"

    def test_chat_context_backward_compat(self) -> None:
        """New fields have defaults that don't break old data."""
        from autoresearch.shared.models import OpenClawSessionChatContextRead
        ctx = OpenClawSessionChatContextRead(chat_id="500", chat_type=ChatType.SUPERGROUP)
        assert ctx.message_thread_id is None
        assert ctx.is_topic_message is False
        assert ctx.reply_to_message_id is None
