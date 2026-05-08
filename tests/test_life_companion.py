from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from autoresearch.api import dependencies as api_dependencies
from autoresearch.api.main import create_app
from autoresearch.api.settings import clear_settings_caches


def _enable_life_companion(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path, Path]:
    goodnotes = tmp_path / "GoodNotes-Inbox"
    marginnote = tmp_path / "MarginNote-Inbox"
    goodnotes_backup = tmp_path / "GoodNotes-Backup"
    marginnote_export = tmp_path / "MarginNote-Export"
    for path in [goodnotes, marginnote, goodnotes_backup, marginnote_export]:
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(
        "AUTORESEARCH_ENABLED_PERSONAL_PACKAGES",
        "personal.study_workspace,personal.entertainment_curator,personal.life_companion",
    )
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("AUTORESEARCH_STUDY_GOODNOTES_INBOX_DIR", str(goodnotes))
    monkeypatch.setenv("AUTORESEARCH_STUDY_MARGINNOTE_INBOX_DIR", str(marginnote))
    monkeypatch.setenv("AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS", str(goodnotes_backup))
    monkeypatch.setenv("AUTORESEARCH_STUDY_MARGINNOTE_EXPORT_DIRS", str(marginnote_export))
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()
    return TestClient(create_app()), goodnotes, marginnote


def test_life_companion_promotes_cards_and_exports(tmp_path, monkeypatch) -> None:
    client, goodnotes, marginnote = _enable_life_companion(tmp_path, monkeypatch)

    promoted = client.post(
        "/api/v1/personal/promote",
        json={
            "title": "Agent memory architecture",
            "summary": "Design durable memory, spaced review, and recommendation feedback.",
        },
    )
    assert promoted.status_code == 201
    assert promoted.json()["study_item"]["source_key"].startswith("life_companion:")

    cards = client.post("/api/v1/personal/cards", json={"limit": 4})
    assert cards.status_code == 201
    assert len(cards.json()) >= 1

    plan = client.post(
        "/api/v1/personal/plans/daily",
        json={"available_minutes": 120, "auto_export": True},
    )
    assert plan.status_code == 201
    payload = plan.json()
    assert payload["blocks"]
    assert payload["export_job_ids"]
    assert any(path.suffix == ".pdf" for path in goodnotes.iterdir())
    assert any(path.suffix == ".pdf" for path in marginnote.iterdir())
    sidecars = [path for path in marginnote.iterdir() if path.suffix == ".md"]
    assert sidecars
    assert "## Graph Seed" in sidecars[0].read_text(encoding="utf-8")


def test_life_companion_feedback_hides_recommendation(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)

    recs = client.post("/api/v1/personal/recommendations", json={"limit": 8})
    assert recs.status_code == 200
    first = next(
        item
        for row in recs.json()["rows"]
        for item in row["items"]
    )

    feedback = client.post(
        "/api/v1/personal/feedback",
        json={"target_id": first["recommendation_id"], "signal": "not_interested"},
    )
    assert feedback.status_code == 201

    next_recs = client.post("/api/v1/personal/recommendations", json={"limit": 20})
    returned_ids = {
        item["recommendation_id"]
        for row in next_recs.json()["rows"]
        for item in row["items"]
    }
    assert first["recommendation_id"] not in returned_ids


def test_life_companion_backfills_export_notes(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)
    backup = tmp_path / "GoodNotes-Backup"
    (backup / "annotated-note.md").write_text(
        "# Annotated Agent Notes\n\nitem_id: study_item_123\n\nSpaced repetition feedback.",
        encoding="utf-8",
    )

    response = client.post("/api/v1/personal/ingest", json={"scan_exports": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 1
    assert payload["items"][0]["source_app"] == "goodnotes"


def test_life_companion_remote_magic_link_guards_personal_routes(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTORESEARCH_PERSONAL_REMOTE_ENABLED", "true")
    monkeypatch.setenv("AUTORESEARCH_PANEL_JWT_SECRET", "life-panel-secret")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "9527")
    monkeypatch.setenv("AUTORESEARCH_PERSONAL_REMOTE_BASE_URL", "https://life.example/study")
    clear_settings_caches()
    api_dependencies.get_panel_access_service.cache_clear()

    blocked = client.get("/api/v1/personal/state")
    assert blocked.status_code == 401

    magic = client.post("/api/v1/personal/access/magic-link", json={"telegram_uid": "9527"})
    assert magic.status_code == 201
    payload = magic.json()
    assert payload["status"] == "created"
    assert payload["url"].startswith("https://life.example/study?")
    token = parse_qs(urlparse(payload["url"]).query)["token"][0]

    verified = client.get(f"/api/v1/personal/state?token={token}")
    assert verified.status_code == 200
    assert verified.json()["enabled"] is True

    tampered = client.get("/api/v1/personal/state?token=broken")
    assert tampered.status_code == 401


def test_life_companion_graph_promotes_unlinked_mentions(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)

    promoted = client.post(
        "/api/v1/personal/promote",
        json={
            "title": "双链学习系统",
            "summary": "深读 [[Agent Memory]] with @ProjectAtlas and #learning signals.",
        },
    )
    assert promoted.status_code == 201

    graph = client.get("/api/v1/personal/graph")
    assert graph.status_code == 200
    payload = graph.json()
    node_titles = {node["title"] for node in payload["nodes"]}
    assert "Agent Memory" in node_titles
    assert "learning" in node_titles
    assert any(link["relation"] == "references" for link in payload["links"])
    assert any(link["relation"] == "tagged_as" for link in payload["links"])

    mentions = client.get("/api/v1/personal/mentions").json()
    mention = next(item for item in mentions if item["target_text"] == "ProjectAtlas")
    promoted_mention = client.post(
        f"/api/v1/personal/mentions/{mention['mention_id']}/promote",
        json={"mention_id": mention["mention_id"]},
    )
    assert promoted_mention.status_code == 200
    assert promoted_mention.json()["status"] == "promoted"

    links = client.get("/api/v1/personal/links").json()
    mention_link = next(link for link in links if link["relation"] == "mentions")
    backlinks = client.get(f"/api/v1/personal/nodes/{mention_link['target_node_id']}/backlinks")
    assert backlinks.status_code == 200
    assert any(link["link_id"] == mention_link["link_id"] for link in backlinks.json())

    deleted = client.delete(f"/api/v1/personal/links/{mention_link['link_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_life_companion_layout_surfaces_blind_spots_hot_feed_and_tracking(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)

    promoted = client.post(
        "/api/v1/personal/promote",
        json={
            "title": "Agent Memory Project",
            "summary": "Agent Memory needs retrieval practice, source coverage, and anti bubble discovery.",
        },
    )
    assert promoted.status_code == 201
    study_item_id = promoted.json()["study_item"]["item_id"]
    client.post(
        "/api/v1/personal/feedback",
        json={
            "target_id": study_item_id,
            "signal": "more_like_this",
            "note": "Agent Memory",
            "metadata": {"topics": ["Agent", "Memory"]},
        },
    )

    layout = client.post(
        "/api/v1/personal/layout",
        json={"intent": "看热点和盲区，但不要打扰我", "focus": "low"},
    )
    assert layout.status_code == 200
    payload = layout.json()
    kinds = {panel["view_kind"] for panel in payload["panels"]}
    assert {"blind_spots", "hot_feed", "tracking", "boredom_feed"} <= kinds
    assert payload["metadata"]["filter_bubble_policy"]
    assert any("blind spots" in item for item in payload["overlooked"])


def test_seen_items_are_downranked_unless_followed(tmp_path, monkeypatch) -> None:
    client, _, _ = _enable_life_companion(tmp_path, monkeypatch)

    client.post(
        "/api/v1/personal/promote",
        json={"title": "Rust agent orchestration", "summary": "A focused learning item."},
    )
    first_recs = client.post("/api/v1/personal/recommendations", json={"limit": 8}).json()
    first = next(item for row in first_recs["rows"] for item in row["items"] if item["related_item_ids"])
    target_id = first["related_item_ids"][0]
    client.post(
        "/api/v1/personal/feedback",
        json={"target_id": target_id, "signal": "done"},
    )

    second_recs = client.post("/api/v1/personal/recommendations", json={"limit": 20}).json()
    seen_items = [
        item
        for row in second_recs["rows"]
        for item in row["items"]
        if target_id in item["related_item_ids"]
    ]
    assert seen_items
    assert seen_items[0]["metadata"]["seen_before"] is True
    assert seen_items[0]["metadata"]["attention"] == "boredom_feed"
