from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from autoresearch.core.services.study_dashboard import (
    StudyDashboardService,
    parse_rss_items,
    parse_x_bookmark_items,
    parse_youtube_playlist_items,
)
from autoresearch.core.services.study_workbench import StudyWorkbenchService
from autoresearch.shared.models import (
    StudyDashboardDailyBriefRequest,
    StudyDashboardExportRequest,
    StudyDashboardExportTarget,
    StudyDashboardItemActionRequest,
    StudyDashboardItemStatus,
    StudyDashboardRefreshRequest,
    StudyDashboardSourceKind,
)
from autoresearch.shared.store import InMemoryRepository


def _workbench_settings(tmp_path: Path) -> SimpleNamespace:
    vault = tmp_path / "vault"
    goodnotes_inbox = tmp_path / "GoodNotes-Inbox"
    goodnotes_backup = tmp_path / "GoodNotes-Backup"
    marginnote_inbox = tmp_path / "MarginNote-Inbox"
    marginnote_export = tmp_path / "MarginNote-Export"
    for path in [vault, goodnotes_inbox, goodnotes_backup, marginnote_inbox, marginnote_export]:
        path.mkdir(parents=True)
    return SimpleNamespace(
        obsidian_vault_dir=vault,
        goodnotes_inbox_dir=goodnotes_inbox,
        goodnotes_backup_dirs=[goodnotes_backup],
        marginnote_inbox_dir=marginnote_inbox,
        marginnote_export_dirs=[marginnote_export],
        git_repo_dir=vault,
        review_inbox_relative_dir="inbox_review",
        git_push_enabled=False,
        ocr_command="",
    )


def _dashboard_settings(**overrides: object) -> SimpleNamespace:
    values = {
        "x_user_id": "",
        "x_bearer_token": "",
        "youtube_api_key": "",
        "youtube_playlist_id": "",
        "rss_urls": [],
        "daily_hour": 8,
        "daily_timezone": "Asia/Taipei",
        "daily_item_limit": 4,
        "source_limit": 10,
        "request_timeout_seconds": 3.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _service(
    tmp_path: Path,
    *,
    settings: SimpleNamespace | None = None,
    fetch_json=None,
    fetch_text=None,
) -> StudyDashboardService:
    workbench = StudyWorkbenchService(
        settings=_workbench_settings(tmp_path),
        state_db_path=tmp_path / "study.sqlite3",
        artifact_root=tmp_path / "artifacts" / "study_workbench",
    )
    return StudyDashboardService(
        settings=settings or _dashboard_settings(),
        item_repository=InMemoryRepository(),
        brief_repository=InMemoryRepository(),
        study_workbench=workbench,
        artifact_root=tmp_path / "artifacts" / "study_dashboard",
        fetch_json=fetch_json,
        fetch_text=fetch_text,
    )


def test_x_bookmark_parser_extracts_source_link_and_author() -> None:
    payload = {
        "data": [
            {
                "id": "123",
                "author_id": "u1",
                "created_at": "2026-05-08T01:00:00Z",
                "text": "New AI Agent MCP workflow guide",
                "entities": {"urls": [{"expanded_url": "https://example.com/guide"}]},
            }
        ],
        "includes": {"users": [{"id": "u1", "username": "expert"}]},
    }

    items = parse_x_bookmark_items(payload)

    assert len(items) == 1
    assert items[0].source_kind == StudyDashboardSourceKind.X_BOOKMARKS
    assert items[0].source_url == "https://x.com/expert/status/123"
    assert items[0].metadata["expanded_urls"] == ["https://example.com/guide"]


def test_youtube_playlist_parser_marks_video_source() -> None:
    payload = {
        "items": [
            {
                "id": "playlist-item",
                "snippet": {
                    "title": "Distributed Systems for AI Agents",
                    "description": "A long lecture about durable state and agent routing.",
                    "videoOwnerChannelTitle": "Tech Expert",
                    "resourceId": {"videoId": "abc123"},
                    "publishedAt": "2026-05-08T02:00:00Z",
                },
                "contentDetails": {"videoId": "abc123"},
            }
        ]
    }

    items = parse_youtube_playlist_items(payload)

    assert len(items) == 1
    assert items[0].source_url == "https://www.youtube.com/watch?v=abc123"
    assert items[0].author == "Tech Expert"


def test_rss_parser_deduplicates_by_guid_digest() -> None:
    rss = """
    <rss><channel>
      <item>
        <title>FastAPI PWA study workflow</title>
        <link>https://example.com/pwa</link>
        <guid>stable-guid</guid>
        <description><![CDATA[<p>GoodNotes and MarginNote4 pipeline</p>]]></description>
      </item>
    </channel></rss>
    """

    items = parse_rss_items(rss, source_url="https://example.com/feed.xml")

    assert len(items) == 1
    assert items[0].title == "FastAPI PWA study workflow"
    assert items[0].summary == "GoodNotes and MarginNote4 pipeline"


def test_refresh_degrades_missing_external_credentials_but_keeps_local_topics(tmp_path: Path) -> None:
    service = _service(tmp_path)

    result = service.refresh(StudyDashboardRefreshRequest())
    state = service.state()

    assert result.status.value == "completed"
    assert result.added_count >= 1
    assert any(source.source_kind == StudyDashboardSourceKind.LOCAL for source in result.sources)
    assert state.status == "ok"
    assert any(item.source_kind == StudyDashboardSourceKind.LOCAL for item in state.items)
    assert any(source.status == "not_configured" for source in state.sources)


def test_daily_brief_exports_goodnotes_pdf_and_marginnote_sidecar(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.refresh(StudyDashboardRefreshRequest())

    brief = service.create_daily_brief(
        StudyDashboardDailyBriefRequest(auto_refresh=False, targets=[StudyDashboardExportTarget.BOTH])
    )
    exported = service.export_brief(
        brief.brief_id,
        StudyDashboardExportRequest(target=StudyDashboardExportTarget.BOTH),
    )

    assert brief.item_ids
    assert "MarginNote4" in brief.content_markdown
    assert exported.pdf_paths
    assert Path(exported.pdf_paths[0]).read_bytes().startswith(b"%PDF-")
    assert any(path.endswith(".md") for path in exported.markdown_paths)
    assert any(copy["target"] == "goodnotes" for copy in exported.copies)
    assert any(copy["target"] == "marginnote" for copy in exported.copies)


def test_item_actions_prepare_cards_and_archive(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.refresh(StudyDashboardRefreshRequest())
    item = service.state().items[0]

    cards = service.apply_item_action(
        item.item_id,
        request=StudyDashboardItemActionRequest(action="generate_cards"),
    )
    archived = service.apply_item_action(
        item.item_id,
        request=StudyDashboardItemActionRequest(action="archive"),
    )

    assert cards.artifacts[0]["kind"] == "flashcards"
    assert archived.item.status == StudyDashboardItemStatus.ARCHIVED
