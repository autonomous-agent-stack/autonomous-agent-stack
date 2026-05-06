from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.daemon import _resolve_worker_api_db_path


def test_mac_worker_register_metadata_uses_configured_api_db_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "api" / "configured.sqlite3"
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(db_path))
    monkeypatch.setenv("HOUSEKEEPING_ROOT", str(tmp_path))

    config = MacWorkerConfig.from_env()
    request = config.build_register_request()

    assert request.metadata["api_db_path"] == str(db_path.resolve())
    assert _resolve_worker_api_db_path(config) == db_path.resolve()


def test_mac_worker_register_metadata_uses_repo_default_api_db_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTORESEARCH_API_DB_PATH", raising=False)
    monkeypatch.setenv("HOUSEKEEPING_ROOT", str(tmp_path))
    expected = (tmp_path / "artifacts" / "api" / "evaluations.sqlite3").resolve()

    config = MacWorkerConfig.from_env()
    request = config.build_register_request()

    assert request.metadata["api_db_path"] == str(expected)
    assert _resolve_worker_api_db_path(config) == expected


def test_mac_worker_legacy_display_name_maps_to_aas_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOUSEKEEPING_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_WORKER_DISPLAY_NAME", "初代worker")

    config = MacWorkerConfig.from_env()

    assert config.telegram_reply_brand == "AAS Worker"
