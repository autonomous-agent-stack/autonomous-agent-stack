from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_repo_hygiene",
    _ROOT / "scripts" / "ci" / "check_repo_hygiene.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = _mod
_SPEC.loader.exec_module(_mod)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_tracked_runtime_database_files_are_rejected(tmp_path: Path) -> None:
    issues = _mod.check_tracked_runtime_databases(
        tmp_path,
        tracked_files=["src/app.py", "data/event_bus.sqlite", "artifacts/api/runtime.sqlite3"],
    )

    assert [issue.path for issue in issues] == [
        "data/event_bus.sqlite",
        "artifacts/api/runtime.sqlite3",
    ]


def test_machine_paths_are_rejected_in_source_files(tmp_path: Path) -> None:
    machine_path = "/Volumes/" "AI_LAB/Github/demo"
    _write(tmp_path / "src" / "service.py", f'ROOT = "{machine_path}"\n')

    issues = _mod.check_machine_paths(tmp_path)

    assert issues
    assert issues[0].code == "developer-machine-path"


def test_machine_path_allowlist_keeps_policy_fixture_tests(tmp_path: Path) -> None:
    _write(
        tmp_path / "tests" / "test_check_pr_bilingual.py",
        'fixture = "/Volumes/" "AI_LAB/Github/demo"\n',
    )

    assert _mod.check_machine_paths(tmp_path) == []


def test_active_doc_inline_language_markers_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "project-health.md", "English: keep this split\n")

    issues = _mod.check_active_doc_markers(tmp_path)

    assert issues
    assert issues[0].code == "inline-bilingual-marker"


def test_repository_hygiene_gate_passes_current_checkout() -> None:
    issues = _mod.check_repository(_ROOT)

    assert not issues, "\n".join(issue.render() for issue in issues)
