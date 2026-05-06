from __future__ import annotations

from pathlib import Path

from autoresearch.ga.contracts import GAStatusRead, Stability


ROOT = Path(__file__).resolve().parents[2]


def test_ga_definition_and_prohibitions_are_blocking_docs() -> None:
    definition = (ROOT / "docs/ga-definition.md").read_text(encoding="utf-8")
    prohibitions = (ROOT / "docs/ga-prohibitions.md").read_text(encoding="utf-8")

    for required in (
        "stable contract",
        "production implementation",
        "migration path",
        "rollback path",
        "bypass tests",
        "compatibility matrix",
    ):
        assert required in definition

    for forbidden in (
        "mock-only",
        "demo-only",
        "fake stream",
        "no-op cancel",
        "adapter 直接调用模型",
        "UI、CLI、SDK 直接修改数据库",
    ):
        assert forbidden in prohibitions


def test_stable_status_cannot_have_missing_checks() -> None:
    status = GAStatusRead(
        object_id="fake-adapter",
        object_type="adapter",
        stability=Stability.STABLE,
        missing_checks=["real_cancel"],
    )

    assert status.stability == Stability.STABLE
    assert status.missing_checks == ["real_cancel"]

