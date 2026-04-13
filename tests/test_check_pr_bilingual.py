"""Tests for scripts/ci/check_pr_bilingual.py coarse validation."""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_pr_bilingual",
    _ROOT / "scripts" / "ci" / "check_pr_bilingual.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_mod)


def test_check_pr_body_accepts_bilingual() -> None:
    body = """
## Summary
**中文：** 这是中文说明，长度足够覆盖检查。
**English:** This is English prose with enough Latin letters for the coarse gate.
"""
    ok, msg = _mod.check_pr_body(body)
    assert ok, msg


def test_check_pr_body_rejects_too_short() -> None:
    ok, msg = _mod.check_pr_body("short")
    assert not ok


def test_check_pr_body_rejects_english_only() -> None:
    body = "x" * 200 + " " + "English only " * 20
    ok, msg = _mod.check_pr_body(body)
    assert not ok


def test_should_skip_title() -> None:
    skip, _ = _mod.should_skip(title="fix: foo [skip i18n]", body="")
    assert skip


def test_main_skips_when_env_skip() -> None:
    import os

    old = os.environ.get("SKIP_CHECK")
    try:
        os.environ["SKIP_CHECK"] = "1"
        assert _mod.main() == 0
    finally:
        if old is None:
            os.environ.pop("SKIP_CHECK", None)
        else:
            os.environ["SKIP_CHECK"] = old
