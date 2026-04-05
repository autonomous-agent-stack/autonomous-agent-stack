#!/usr/bin/env python3
"""
Tests for repo-agent and media archiver

Tests the complete archive flow:
    1. Create completed job in SQLite
    2. Export to archive/
    3. Verify idempotency
"""

import json
import sqlite3
import sys
import tempfile
import shutil
from pathlib import Path
from unittest import TestCase, main

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from lib.media_job_store import (
    MediaJobStore,
    JobStatus,
    SubtitleStatus,
    DownloadStatus,
)
from lib.media_archiver import (
    MediaArchiver,
    ArchivedVideo,
    slugify,
    extract_video_id,
    detect_platform,
)
from scripts.repo_agent import RepoAgent


class TestSlugify(TestCase):
    """Test slugify function"""

    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_special_chars(self):
        self.assertEqual(slugify("Hello! @World#"), "hello-world")

    def test_length_limit(self):
        long_text = "a" * 100
        self.assertEqual(len(slugify(long_text, max_length=50)), 50)


class TestVideoIdExtraction(TestCase):
    """Test video ID extraction"""

    def test_youtube_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_youtube_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_bilibili_bv(self):
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        self.assertEqual(extract_video_id(url), "BV1xx411c7mD")


class TestPlatformDetection(TestCase):
    """Test platform detection"""

    def test_youtube(self):
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=abc"), "youtube")

    def test_bilibili(self):
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV1xx"), "bilibili")

    def test_vimeo(self):
        self.assertEqual(detect_platform("https://vimeo.com/123456"), "vimeo")

    def test_unknown(self):
        self.assertEqual(detect_platform("https://example.com/video"), "other")


class TestMediaJobStore(TestCase):
    """Test SQLite job store"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.store = MediaJobStore(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enqueue(self):
        job_id = self.store.enqueue("https://youtube.com/watch?v=test", source="test")
        self.assertIsNotNone(job_id)
        job = self.store.get(job_id)
        self.assertEqual(job.url, "https://youtube.com/watch?v=test")
        self.assertEqual(job.status, JobStatus.QUEUED)

    def test_enqueue_duplicate(self):
        id1 = self.store.enqueue("https://youtube.com/watch?v=dup")
        id2 = self.store.enqueue("https://youtube.com/watch?v=dup")
        self.assertEqual(id1, id2)

    def test_mark_exported(self):
        job_id = self.store.enqueue("https://youtube.com/watch?v=exp", source="test")
        self.store.mark_exported(job_id, "archive/youtube/2026/test")

        job = self.store.get(job_id)
        self.assertEqual(job.archive_status, "exported")
        self.assertEqual(job.archive_path, "archive/youtube/2026/test")
        self.assertIsNotNone(job.archived_at)

    def test_get_completed_for_archive(self):
        # Create and complete a job
        job_id = self.store.enqueue("https://youtube.com/watch?v=done", source="test")
        self.store.update(job_id, status=JobStatus.COMPLETED)

        jobs = self.store.get_completed_for_archive()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, job_id)

        # Mark as exported
        self.store.mark_exported(job_id, "archive/youtube/2026/done")

        # Should not return anymore
        jobs = self.store.get_completed_for_archive()
        self.assertEqual(len(jobs), 0)

    def test_stats(self):
        self.store.enqueue("https://youtube.com/watch?v=1")
        self.store.enqueue("https://youtube.com/watch?v=2")
        stats = self.store.stats()
        self.assertEqual(stats.get("queued", 0), 2)


class TestMediaArchiver(TestCase):
    """Test media archiver"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.archive_dir = Path(self.temp_dir) / "archive"
        self.store = MediaJobStore(db_path=self.db_path)
        self.archiver = MediaArchiver(store=self.store, archive_dir=self.archive_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_job(self):
        job_id = self.store.enqueue(
            "https://www.youtube.com/watch?v=test123",
            source="test-agent",
            metadata={"title": "Test Video Title"},
        )
        self.store.update(job_id, status=JobStatus.COMPLETED)
        job = self.store.get(job_id)

        archive_path = self.archiver.export_job(job, files=[{"name": "test.vtt", "size": 1234}])

        self.assertTrue(archive_path.exists())
        self.assertTrue((archive_path / "metadata.json").exists())
        self.assertTrue((archive_path / "README.md").exists())
        self.assertTrue((archive_path / "assets.json").exists())

    def test_update_index(self):
        job_id = self.store.enqueue(
            "https://www.youtube.com/watch?v=idx",
            source="test",
            metadata={"title": "Index Test"},
        )
        self.store.update(job_id, status=JobStatus.COMPLETED)
        job = self.store.get(job_id)
        self.archiver.export_job(job)

        index = self.archiver.update_index()

        self.assertEqual(index["total"], 1)
        self.assertIn("youtube", index["platforms"])
        self.assertTrue((self.archive_dir / "index.json").exists())


class TestRepoAgent(TestCase):
    """Test repo-agent"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.archive_dir = Path(self.temp_dir) / "archive"
        self.store = MediaJobStore(db_path=self.db_path)
        self.archiver = MediaArchiver(store=self.store, archive_dir=self.archive_dir)
        self.agent = RepoAgent(store=self.store, archiver=self.archiver)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_empty(self):
        exported = self.agent.export()
        self.assertEqual(exported, [])

    def test_export_completed(self):
        job_id = self.store.enqueue(
            "https://www.youtube.com/watch?v=agent",
            source="test",
            metadata={"title": "Agent Test"},
        )
        self.store.update(job_id, status=JobStatus.COMPLETED)

        exported = self.agent.export()
        self.assertEqual(len(exported), 1)
        self.assertIn(job_id, exported)

        # Idempotency: second export should return empty
        exported2 = self.agent.export()
        self.assertEqual(len(exported2), 0)

    def test_export_specific_job(self):
        job_id = self.store.enqueue(
            "https://www.youtube.com/watch?v=specific",
            source="test",
            metadata={"title": "Specific Job"},
        )
        self.store.update(job_id, status=JobStatus.COMPLETED)

        exported = self.agent.export(job_id=job_id)
        self.assertEqual(len(exported), 1)


if __name__ == "__main__":
    main()
