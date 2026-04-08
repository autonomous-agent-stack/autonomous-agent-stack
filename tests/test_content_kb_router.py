"""Tests for content_kb API router."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.main import app


class FakeContentKBDependencies:
    """Fake dependencies for content_kb router testing."""

    @staticmethod
    def create_test_srt(tmp_path: Path) -> Path:
        """Create a test SRT file."""
        srt_path = tmp_path / "test_subtitle.srt"
        srt_path.write_text(
            """1
00:00:01,000 --> 00:00:03,000
This is a test subtitle about AI and large language models.

2
00:00:04,000 --> 00:00:06,000
Let's discuss vibe coding and modern development workflows.
""",
            encoding="utf-8",
        )
        return srt_path


@pytest.fixture
def content_kb_client(tmp_path: Path) -> TestClient:
    """Create a test client for content_kb router."""
    with TestClient(app) as client:
        yield client


def test_content_kb_health_check(content_kb_client: TestClient) -> None:
    """Test health check endpoint."""
    response = content_kb_client.get("/api/v1/content-kb/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "content_kb"
    assert "capabilities" in data
    assert isinstance(data["capabilities"], list)


def test_content_kb_classify_ai_topic(content_kb_client: TestClient) -> None:
    """Test topic classification with AI-related text."""
    response = content_kb_client.post(
        "/api/v1/content-kb/classify",
        json={"text": "讨论AI和大模型的最新发展趋势，以及Claude和GPT的能力对比"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "primary_topic" in data
    assert "confidence" in data
    assert "alternatives" in data
    assert "valid_topics" in data
    # AI keywords should match AI_STATUS_AND_OUTLOOK
    assert data["primary_topic"] == "ai-status-and-outlook"
    assert data["confidence"] > 0


def test_content_kb_classify_coding_topic(content_kb_client: TestClient) -> None:
    """Test topic classification with coding-related text."""
    response = content_kb_client.post(
        "/api/v1/content-kb/classify",
        json={"text": "分享vibe coding工作流，使用Cursor和VSCode进行开发"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["primary_topic"] == "vibe-coding"
    assert data["confidence"] > 0


def test_content_kb_classify_empty_text_returns_error(content_kb_client: TestClient) -> None:
    """Test that empty text returns 400 error."""
    response = content_kb_client.post("/api/v1/content-kb/classify", json={"text": ""})
    assert response.status_code == 400
    error = response.json()["detail"]
    assert isinstance(error, dict)
    assert "message" in error


def test_content_kb_classify_without_text_returns_error(content_kb_client: TestClient) -> None:
    """Test that missing text field returns validation error."""
    response = content_kb_client.post("/api/v1/content-kb/classify", json={})
    assert response.status_code == 422  # FastAPI validation error for missing required field


def test_content_kb_choose_repo_with_topic(content_kb_client: TestClient) -> None:
    """Test repo selection with topic guess."""
    response = content_kb_client.post(
        "/api/v1/content-kb/choose-repo",
        json={
            "owner_profile": "default",
            "source_title": "AI Development Trends 2024",
            "topic_guess": "ai-status-and-outlook",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "profile_name" in data
    assert "repo_full_name" in data
    assert "directory" in data
    assert "reason" in data
    assert "needs_new_repo" in data
    # Should default to knowledge-base/knowledge-base
    assert "knowledge-base" in data["repo_full_name"]
    assert "ai-status-and-outlook" in data["directory"]


def test_content_kb_choose_repo_minimal(content_kb_client: TestClient) -> None:
    """Test repo selection with minimal parameters."""
    response = content_kb_client.post(
        "/api/v1/content-kb/choose-repo",
        json={"source_title": "Test Content"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile_name"] == "default"
    assert "knowledge-base" in data["repo_full_name"]


def test_content_kb_ingest_subtitle(content_kb_client: TestClient, tmp_path: Path) -> None:
    """Test subtitle ingestion with a real file."""
    # Create test SRT file
    srt_path = FakeContentKBDependencies.create_test_srt(tmp_path)

    response = content_kb_client.post(
        "/api/v1/content-kb/ingest",
        json={
            "subtitle_text_path": str(srt_path),
            "title": "AI and Vibe Coding Discussion",
            "topic": "ai-status-and-outlook",
            "source_url": "https://example.com/video",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert "metadata" in data
    assert "files_written" in data
    assert data["status"] == "ingesting"
    assert data["metadata"]["title"] == "AI and Vibe Coding Discussion"
    assert data["metadata"]["topic"] == "ai-status-and-outlook"


def test_content_kb_ingest_missing_file_returns_error(content_kb_client: TestClient) -> None:
    """Test that missing subtitle file returns 404 error."""
    response = content_kb_client.post(
        "/api/v1/content-kb/ingest",
        json={
            "subtitle_text_path": "/nonexistent/path/to/subtitle.srt",
            "title": "Test",
        },
    )
    assert response.status_code == 404
    error = response.json()["detail"]
    assert isinstance(error, dict)
    assert "not found" in error["message"].lower()


def test_content_kb_ingest_without_path_returns_error(content_kb_client: TestClient) -> None:
    """Test that missing subtitle_text_path returns validation error."""
    response = content_kb_client.post(
        "/api/v1/content-kb/ingest",
        json={"title": "Test"},
    )
    assert response.status_code == 422  # FastAPI validation error for missing required field


def test_content_kb_build_topic_index(content_kb_client: TestClient) -> None:
    """Test building a topic index."""
    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={
            "index_type": "topic",
            "entries": [
                {"topic": "ai-status-and-outlook", "title": "AI Trends", "slug": "ai-trends"},
                {"topic": "vibe-coding", "title": "Coding Workflow", "slug": "coding-workflow"},
                {"topic": "ai-status-and-outlook", "title": "LLM Update", "slug": "llm-update"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["index_type"] == "topic"
    assert data["entries_count"] == 3
    assert "index" in data
    # Check topic counts
    topics = data["index"]["topics"]
    assert topics["ai-status-and-outlook"]["count"] == 2
    assert topics["vibe-coding"]["count"] == 1
    assert topics["ai-status-and-outlook"]["latest_title"] == "LLM Update"


def test_content_kb_build_speaker_index(content_kb_client: TestClient) -> None:
    """Test building a speaker index."""
    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={
            "index_type": "speaker",
            "entries": [
                {"speaker": ["Alice", "Bob"], "topic": "ai-status-and-outlook", "title": "AI Chat"},
                {"speaker": ["Alice"], "topic": "vibe-coding", "title": "Coding Tips"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["index_type"] == "speaker"
    speakers = data["index"]["speakers"]
    assert speakers["Alice"]["appearances"] == 2
    assert speakers["Bob"]["appearances"] == 1
    assert "ai-status-and-outlook" in speakers["Alice"]["topics"]


def test_content_kb_build_timeline_index(content_kb_client: TestClient) -> None:
    """Test building a timeline index."""
    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={
            "index_type": "timeline",
            "entries": [
                {"created_at": "2024-01-15", "topic": "ai-status-and-outlook", "title": "AI Jan", "slug": "ai-jan"},
                {"created_at": "2024-02-20", "topic": "vibe-coding", "title": "Coding Feb", "slug": "coding-feb"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["index_type"] == "timeline"
    entries = data["index"]["entries"]
    # Should be sorted by date descending
    assert entries[0]["date"] == "2024-02-20"
    assert entries[1]["date"] == "2024-01-15"


def test_content_kb_build_index_with_existing(content_kb_client: TestClient) -> None:
    """Test building index with existing index data."""
    existing = {
        "version": "topics/v1",
        "updated_at": "2024-01-01",
        "topics": {"ai-status-and-outlook": {"count": 5, "latest_title": "Old AI", "latest_slug": "old-ai"}},
    }

    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={
            "index_type": "topic",
            "existing_index": existing,
            "entries": [{"topic": "ai-status-and-outlook", "title": "New AI", "slug": "new-ai"}],
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Should have incremented count
    assert data["index"]["topics"]["ai-status-and-outlook"]["count"] == 6
    assert data["index"]["topics"]["ai-status-and-outlook"]["latest_title"] == "New AI"


def test_content_kb_build_index_unknown_type_returns_error(content_kb_client: TestClient) -> None:
    """Test that unknown index_type returns 400 error."""
    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={"index_type": "unknown", "entries": [{"topic": "test"}]},
    )
    assert response.status_code == 400


def test_content_kb_build_index_empty_entries_returns_error(content_kb_client: TestClient) -> None:
    """Test that empty entries returns 400 error."""
    response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={"index_type": "topic", "entries": []},
    )
    assert response.status_code == 400
    error = response.json()["detail"]
    assert isinstance(error, dict)
    assert "entries" in error["message"].lower()


def test_content_kb_end_to_end_workflow(content_kb_client: TestClient, tmp_path: Path) -> None:
    """Test full workflow: classify -> choose-repo -> ingest -> build-index."""
    # Step 1: Classify topic
    classify_response = content_kb_client.post(
        "/api/v1/content-kb/classify",
        json={"text": "分享AI编程工作流，使用Claude辅助开发"},
    )
    assert classify_response.status_code == 200
    classify_data = classify_response.json()
    topic = classify_data["primary_topic"]

    # Step 2: Choose repo
    repo_response = content_kb_client.post(
        "/api/v1/content-kb/choose-repo",
        json={
            "source_title": "AI Programming Workflow",
            "topic_guess": topic,
        },
    )
    assert repo_response.status_code == 200
    repo_data = repo_response.json()
    repo_name = repo_data["repo_full_name"]
    directory = repo_data["directory"]

    # Step 3: Ingest subtitle
    srt_path = FakeContentKBDependencies.create_test_srt(tmp_path)
    ingest_response = content_kb_client.post(
        "/api/v1/content-kb/ingest",
        json={
            "subtitle_text_path": str(srt_path),
            "title": "AI Programming Workflow",
            "topic": topic,
        },
    )
    assert ingest_response.status_code == 200
    ingest_data = ingest_response.json()
    job_id = ingest_data["job_id"]

    # Step 4: Build index with ingested content
    index_response = content_kb_client.post(
        "/api/v1/content-kb/build-index",
        json={
            "index_type": "topic",
            "entries": [
                {
                    "topic": topic,
                    "title": "AI Programming Workflow",
                    "slug": f"{job_id}",
                }
            ],
        },
    )
    assert index_response.status_code == 200
    index_data = index_response.json()
    assert index_data["entries_count"] == 1
    assert index_data["index"]["topics"][topic]["count"] == 1
