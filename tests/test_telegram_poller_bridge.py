from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "openclaw" / "scripts" / "telegram_poller_bridge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("telegram_poller_bridge", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_should_advance_offset_on_duplicate_update_conflict() -> None:
    module = _load_module()

    assert module.should_advance_offset_on_http_error(
        409,
        '{"detail":"duplicate telegram update rejected"}',
    ) is True


def test_should_not_advance_offset_on_other_conflicts() -> None:
    module = _load_module()

    assert module.should_advance_offset_on_http_error(409, '{"detail":"Run is leased to another worker"}') is False
    assert module.should_advance_offset_on_http_error(500, '{"detail":"boom"}') is False
    assert module.should_advance_offset_on_http_error(409, 'not-json') is False


def test_should_advance_offset_when_duplicate_substring_in_body() -> None:
    """Substring match tolerates whitespace / framing around FastAPI JSON."""
    module = _load_module()

    assert (
        module.should_advance_offset_on_http_error(
            409,
            '\n{"detail":"duplicate telegram update rejected"}\n',
        )
        is True
    )


def test_should_advance_offset_when_detail_is_fastapi_list_shape() -> None:
    module = _load_module()

    body = '{"detail":[{"type":"value_error","msg":"duplicate telegram update rejected"}]}'
    assert module.should_advance_offset_on_http_error(409, body) is True
