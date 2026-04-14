from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry


class _DummyRuntimeAdapter(RuntimeAdapterContract):
    def __init__(self, runtime_id: str) -> None:
        self.runtime_id = runtime_id

    def create_session(self, request):  # type: ignore[override]
        raise NotImplementedError

    def run(self, request):  # type: ignore[override]
        raise NotImplementedError

    def stream(self, request):  # type: ignore[override]
        raise NotImplementedError

    def cancel(self, request):  # type: ignore[override]
        raise NotImplementedError

    def status(self, request):  # type: ignore[override]
        raise NotImplementedError


def _write_manifest(dir_path: Path, runtime_id: str) -> None:
    (dir_path / f"{runtime_id}.yaml").write_text(
        (
            "{\n"
            f'  "id": "{runtime_id}",\n'
            '  "kind": "runtime",\n'
            '  "service": "tests.dummy:DummyRuntimeAdapter",\n'
            '  "version": "0.1",\n'
            '  "capabilities": ["create_session", "run", "stream", "cancel", "status"]\n'
            "}\n"
        ),
        encoding="utf-8",
    )


def test_runtime_adapter_service_registry_resolves_and_caches_instances(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "runtime_manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(manifests_dir, "openclaw")
    _write_manifest(manifests_dir, "hermes")

    created: dict[str, int] = {"openclaw": 0, "hermes": 0}

    def _make_factory(runtime_id: str):
        def _factory() -> RuntimeAdapterContract:
            created[runtime_id] += 1
            return _DummyRuntimeAdapter(runtime_id)

        return _factory

    registry = RuntimeAdapterServiceRegistry(
        manifest_registry=RuntimeAdapterRegistry(manifests_dir),
        factories={
            "openclaw": _make_factory("openclaw"),
            "hermes": _make_factory("hermes"),
        },
    )

    openclaw_adapter = registry.get("openclaw")
    hermes_adapter = registry.get("hermes")
    openclaw_adapter_again = registry.get("openclaw")

    assert isinstance(openclaw_adapter, _DummyRuntimeAdapter)
    assert isinstance(hermes_adapter, _DummyRuntimeAdapter)
    assert openclaw_adapter.runtime_id == "openclaw"
    assert hermes_adapter.runtime_id == "hermes"
    assert openclaw_adapter_again is openclaw_adapter
    assert created["openclaw"] == 1
    assert created["hermes"] == 1


def test_runtime_adapter_service_registry_fails_on_unknown_runtime(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "runtime_manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(manifests_dir, "openclaw")

    registry = RuntimeAdapterServiceRegistry(
        manifest_registry=RuntimeAdapterRegistry(manifests_dir),
        factories={"openclaw": lambda: _DummyRuntimeAdapter("openclaw")},
    )

    try:
        registry.get("missing-runtime")
    except KeyError as exc:
        assert "manifest not found" in str(exc)
    else:
        raise AssertionError("expected KeyError for unknown runtime")
