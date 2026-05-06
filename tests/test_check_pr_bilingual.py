"""Tests for the documentation i18n gate."""

from pathlib import Path
import importlib.util
import sys

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_pr_bilingual",
    _ROOT / "scripts" / "ci" / "check_pr_bilingual.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = _mod
_SPEC.loader.exec_module(_mod)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_check_required_pairs_rejects_missing_mirror(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# Demo\n")

    issues = _mod.check_required_pairs(tmp_path)

    assert any(issue.code == "missing-zh-cn-doc" for issue in issues)


def test_check_file_rejects_machine_path(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "guide.md"
    _write(doc, "cd /Volumes/AI_LAB/Github/autonomous-agent-stack\n")

    issues = _mod.check_file(doc, tmp_path)

    assert issues
    assert issues[0].code == "machine-path"


def test_check_file_rejects_inline_bilingual_marker(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "guide.md"
    _write(doc, "**中文：** 示例\n")

    issues = _mod.check_file(doc, tmp_path)

    assert issues
    assert issues[0].code == "inline-bilingual-marker"


def test_check_file_rejects_translation_placeholder(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "guide.md"
    _write(doc, "TODO translate this later\n")

    issues = _mod.check_file(doc, tmp_path)

    assert issues
    assert issues[0].code == "translation-placeholder"


def test_repository_docs_i18n_gate_passes_current_checkout() -> None:
    issues = _mod.check_repository(_ROOT)

    assert not issues, "\n".join(issue.render() for issue in issues)


def test_main_skips_when_env_skip(monkeypatch) -> None:
    monkeypatch.setenv("SKIP_CHECK", "1")

    assert _mod.main() == 0
