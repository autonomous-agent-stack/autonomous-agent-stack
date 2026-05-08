from __future__ import annotations

from pathlib import Path

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
