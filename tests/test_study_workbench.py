from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from autoresearch.api.settings import StudyWorkbenchSettings, clear_settings_caches
from autoresearch.core.services.study_workbench import StudyWorkbenchError, StudyWorkbenchService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerTaskType,
)
from autoresearch.shared.store import SQLiteModelRepository


def _settings(tmp_path: Path) -> SimpleNamespace:
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


def _service(tmp_path: Path, settings: SimpleNamespace | None = None) -> StudyWorkbenchService:
    return StudyWorkbenchService(
        settings=settings or _settings(tmp_path),
        state_db_path=tmp_path / "state.sqlite3",
        artifact_root=tmp_path / "artifacts" / "study_workbench",
    )


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)


def test_study_workbench_settings_parse_env_lists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_STUDY_OBSIDIAN_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setenv(
        "AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS",
        f"{tmp_path / 'a'},{tmp_path / 'b'}",
    )
    monkeypatch.setenv("AUTORESEARCH_STUDY_GIT_PUSH_ENABLED", "false")
    clear_settings_caches()

    settings = StudyWorkbenchSettings()

    assert settings.obsidian_vault_dir == (tmp_path / "vault").resolve()
    assert settings.goodnotes_backup_dirs == [(tmp_path / "a").resolve(), (tmp_path / "b").resolve()]
    assert settings.git_push_enabled is False


def test_health_reports_degraded_when_unconfigured(tmp_path: Path) -> None:
    settings = SimpleNamespace(
        obsidian_vault_dir=None,
        goodnotes_inbox_dir=None,
        goodnotes_backup_dirs=[],
        marginnote_inbox_dir=None,
        marginnote_export_dirs=[],
        git_repo_dir=None,
        review_inbox_relative_dir="inbox_review",
        git_push_enabled=False,
        ocr_command="",
    )
    health = _service(tmp_path, settings).health()

    assert health["status"] == "degraded"
    assert health["checks"]["ocr"]["available"] is False


def test_prepare_generates_pdf_and_copies_to_inboxes(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = _service(tmp_path, settings)

    result = service.prepare(
        {
            "title": "Self Attention",
            "markdown_text": "# Self Attention\nQ K V notes",
            "targets": ["goodnotes", "marginnote"],
        }
    )

    assert result["prepared_count"] == 1
    pdf_path = Path(result["prepared"][0]["artifact_pdf_path"])
    assert pdf_path.read_bytes().startswith(b"%PDF-")
    copy_paths = [Path(item["path"]) for item in result["prepared"][0]["copies"]]
    assert settings.goodnotes_inbox_dir / "self-attention.pdf" in copy_paths
    assert settings.marginnote_inbox_dir / "self-attention.pdf" in copy_paths


def test_ingest_imports_goodnotes_sidecar_and_marginnote_html_once(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = _service(tmp_path, settings)
    pdf = settings.goodnotes_backup_dirs[0] / "derivation.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    pdf.with_suffix(".md").write_text("handwritten sidecar text", encoding="utf-8")
    html = settings.marginnote_export_dirs[0] / "paper.html"
    html.write_text("<html><body><h1>Paper</h1><p>highlight one</p></body></html>", encoding="utf-8")

    first = service.ingest()
    second = service.ingest()

    assert first["imported_count"] == 2
    assert len(first["files_written"]) == 2
    assert all(Path(path).is_relative_to(settings.obsidian_vault_dir) for path in first["files_written"])
    assert second["imported_count"] == 0
    assert second["skipped_count"] == 2


def test_ingest_marks_plain_pdf_degraded_without_ocr(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = _service(tmp_path, settings)
    pdf = settings.goodnotes_backup_dirs[0] / "handwriting.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    result = service.ingest()

    assert result["imported_count"] == 0
    assert result["degraded_count"] == 1
    assert result["degraded"][0]["reason"] == "ocr_unavailable"


def test_git_sync_commits_only_review_inbox_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _git_init(settings.git_repo_dir)
    service = _service(tmp_path, settings)
    note = settings.obsidian_vault_dir / "inbox_review" / "2026-05-07" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("study note", encoding="utf-8")

    result = service.git_sync({"paths": [str(note)], "message": "test: sync study note"})

    assert result["status"] == "completed"
    assert result["commit_sha"]
    assert result["pushed"] is False


def test_ingest_rejects_review_inbox_path_traversal(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.review_inbox_relative_dir = "../escape"
    service = _service(tmp_path, settings)
    note = settings.goodnotes_backup_dirs[0] / "unsafe.md"
    note.write_text("escaped review inbox", encoding="utf-8")

    with pytest.raises(StudyWorkbenchError, match="safe relative path"):
        service.ingest()


def test_git_sync_degraded_for_non_git_repo(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = _service(tmp_path, settings)
    note = settings.obsidian_vault_dir / "inbox_review" / "2026-05-07" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("study note", encoding="utf-8")

    result = service.git_sync({"paths": [str(note)]})

    assert result["status"] == "degraded"
    assert result["reason"].startswith("not a git repository")


def test_git_sync_rejects_paths_outside_review_inbox(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _git_init(settings.git_repo_dir)
    service = _service(tmp_path, settings)
    outside = settings.obsidian_vault_dir / "daily.md"
    outside.write_text("not review inbox", encoding="utf-8")

    with pytest.raises(StudyWorkbenchError, match="outside review inbox"):
        service.git_sync({"paths": [str(outside)]})


def test_study_workbench_api_enqueues_three_tasks(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from autoresearch.api.dependencies import get_study_workbench_service, get_worker_scheduler_service
    from autoresearch.api.main import app

    db_path = tmp_path / "api.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_study_api_test",
            model_cls=WorkerRegistrationRead,
        )
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_study_api_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_study_api_test",
            model_cls=WorkerLeaseRead,
        ),
    )
    app.dependency_overrides[get_worker_scheduler_service] = lambda: scheduler
    app.dependency_overrides[get_study_workbench_service] = lambda: _service(tmp_path)
    try:
        with TestClient(app) as client:
            prepare = client.post(
                "/api/v1/study-workbench/prepare",
                json={"title": "T", "markdown_text": "body"},
            )
            ingest = client.post("/api/v1/study-workbench/ingest", json={})
            sync = client.post("/api/v1/study-workbench/git-sync", json={"paths": []})
    finally:
        app.dependency_overrides.clear()

    assert prepare.status_code == 201
    assert ingest.status_code == 201
    assert sync.status_code == 201
    assert prepare.json()["task_type"] == WorkerTaskType.STUDY_PREPARE.value
    assert ingest.json()["task_type"] == WorkerTaskType.STUDY_INGEST.value
    assert sync.json()["task_type"] == WorkerTaskType.STUDY_GIT_SYNC.value
