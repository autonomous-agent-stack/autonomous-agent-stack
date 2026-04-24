from __future__ import annotations

import pytest

from autoresearch import __version__
from autoresearch.build_label import get_build_label


def test_get_build_label_respects_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_BUILD_LABEL", "ci-999-test")
    get_build_label.cache_clear()
    try:
        assert get_build_label() == "ci-999-test"
    finally:
        get_build_label.cache_clear()


def test_get_build_label_contains_package_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTORESEARCH_BUILD_LABEL", raising=False)
    get_build_label.cache_clear()
    try:
        label = get_build_label()
        assert __version__ in label
    finally:
        get_build_label.cache_clear()
