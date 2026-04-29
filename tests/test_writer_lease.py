"""Tests for WriterLeaseService — per-key single-writer lease."""
from __future__ import annotations

import threading
import time

import pytest

from autoresearch.core.services.writer_lease import WriterLeaseService


class TestWriterLeaseService:
    def test_acquire_and_release(self) -> None:
        svc = WriterLeaseService()
        with svc.acquire("test-key"):
            pass  # Should not raise

    def test_empty_key_raises(self) -> None:
        svc = WriterLeaseService()
        with pytest.raises(ValueError, match="key is required"):
            with svc.acquire(""):
                pass

    def test_whitespace_key_raises(self) -> None:
        svc = WriterLeaseService()
        with pytest.raises(ValueError, match="key is required"):
            with svc.acquire("   "):
                pass

    def test_reentrant_same_thread(self) -> None:
        """Same thread can re-acquire same key after release."""
        svc = WriterLeaseService()
        with svc.acquire("key1"):
            pass
        with svc.acquire("key1"):
            pass  # Should succeed — previous lock released

    def test_blocking_acquire_waits(self) -> None:
        """Second acquire blocks until first releases."""
        svc = WriterLeaseService()
        acquired_after_release = threading.Event()
        release_event = threading.Event()

        def holder() -> None:
            with svc.acquire("shared"):
                release_event.wait(timeout=5)
            acquired_after_release.set()

        t = threading.Thread(target=holder)
        t.start()

        # Give the holder time to acquire
        time.sleep(0.05)

        # This should block until holder releases
        with svc.acquire("shared"):
            pass

        assert acquired_after_release.is_set()
        t.join(timeout=2)

    def test_nonblocking_raises_when_held(self) -> None:
        svc = WriterLeaseService()
        release_event = threading.Event()

        def holder() -> None:
            with svc.acquire("busy"):
                release_event.wait(timeout=5)

        t = threading.Thread(target=holder)
        t.start()
        time.sleep(0.05)

        with pytest.raises(TimeoutError, match="currently held"):
            with svc.acquire("busy", blocking=False):
                pass

        release_event.set()
        t.join(timeout=2)

    def test_different_keys_dont_block(self) -> None:
        """Different keys can be held simultaneously."""
        svc = WriterLeaseService()
        with svc.acquire("key-a"):
            with svc.acquire("key-b"):
                pass  # Should not block
