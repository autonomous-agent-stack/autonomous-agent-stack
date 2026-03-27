from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autoresearch.api.dependencies import clear_dependency_caches
from autoresearch.api.settings import clear_settings_caches

_TEST_BOOTSTRAP_DIR = Path(tempfile.mkdtemp(prefix="autoresearch-tests-")).resolve()
os.environ.setdefault("AUTORESEARCH_API_DB_PATH", str(_TEST_BOOTSTRAP_DIR / "bootstrap.sqlite3"))


@pytest.fixture(autouse=True)
def isolate_api_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str((tmp_path / "api-test.sqlite3").resolve()))
    monkeypatch.setenv("AUTORESEARCH_API_HOST", "127.0.0.1")
    clear_dependency_caches()
    clear_settings_caches()
    yield
    clear_dependency_caches()
    clear_settings_caches()
