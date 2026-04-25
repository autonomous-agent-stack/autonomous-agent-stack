"""Tests for gateway.route_table — RouteTable CRUD, validation, backup routing."""
from __future__ import annotations

import pytest

from gateway.route_table import RouteTable


def _make_route(**overrides) -> dict:
    defaults = {"chat_id": -100123, "thread_id": 10, "description": "test", "enabled": True}
    defaults.update(overrides)
    return defaults


class TestRouteTableInit:
    def test_default_routes_structure(self) -> None:
        """Verify DEFAULT_ROUTES has expected keys (no instantiation needed)."""
        assert len(RouteTable.DEFAULT_ROUTES) > 0
        for key in ("intelligence", "content", "security", "user_input"):
            assert key in RouteTable.DEFAULT_ROUTES

    def test_custom_routes(self) -> None:
        custom = {"custom_a": _make_route()}
        rt = RouteTable(routes=custom)
        assert "custom_a" in rt.routes
        assert "intelligence" not in rt.routes

    def test_invalid_routes_missing_chat_id_raises(self) -> None:
        with pytest.raises(ValueError, match="missing chat_id"):
            RouteTable(routes={"bad": {"thread_id": 1, "enabled": True}})

    def test_invalid_routes_non_int_chat_id_raises(self) -> None:
        with pytest.raises(ValueError, match="chat_id must be integer"):
            RouteTable(routes={"bad": {"chat_id": "not-int", "thread_id": 1}})

    def test_invalid_routes_non_int_thread_id_raises(self) -> None:
        with pytest.raises(ValueError, match="thread_id must be integer"):
            RouteTable(routes={"bad": {"chat_id": -100, "thread_id": "x"}})


class TestRouteTableGet:
    def test_get_existing_route(self) -> None:
        rt = RouteTable(routes={"test": _make_route()})
        route = rt.get_route("test")
        assert route is not None
        assert route["chat_id"] == -100123

    def test_get_nonexistent_returns_none(self) -> None:
        rt = RouteTable(routes={"test": _make_route()})
        assert rt.get_route("nonexistent") is None

    def test_get_disabled_route_returns_none(self) -> None:
        rt = RouteTable(routes={"test": _make_route(enabled=False)})
        assert rt.get_route("test") is None


class TestRouteTableAdd:
    def test_add_new_route(self) -> None:
        rt = RouteTable(routes={"a": _make_route()})
        result = rt.add_route("b", chat_id=-200, thread_id=20, description="new")
        assert result is True
        assert rt.get_route("b") is not None
        assert rt.get_route("b")["chat_id"] == -200

    def test_add_duplicate_returns_false(self) -> None:
        rt = RouteTable(routes={"a": _make_route()})
        result = rt.add_route("a", chat_id=-200, thread_id=20)
        assert result is False

    def test_add_with_none_thread_id(self) -> None:
        rt = RouteTable(routes={})
        result = rt.add_route("group_only", chat_id=-300, thread_id=None)
        assert result is True
        route = rt.get_route("group_only")
        assert route["thread_id"] is None


class TestRouteTableUpdate:
    def test_update_existing(self) -> None:
        rt = RouteTable(routes={"a": _make_route()})
        result = rt.update_route("a", description="updated")
        assert result is True
        assert rt.get_route("a")["description"] == "updated"

    def test_update_nonexistent_returns_false(self) -> None:
        rt = RouteTable(routes={"a": _make_route()})
        assert rt.update_route("missing", description="x") is False

    def test_update_multiple_fields(self) -> None:
        rt = RouteTable(routes={"a": _make_route()})
        rt.update_route("a", chat_id=-999, thread_id=99)
        route = rt.get_route("a")
        assert route["chat_id"] == -999
        assert route["thread_id"] == 99


class TestRouteTableToggle:
    def test_disable_route(self) -> None:
        rt = RouteTable(routes={"a": _make_route(enabled=True)})
        assert rt.disable_route("a") is True
        assert rt.get_route("a") is None  # disabled routes return None

    def test_enable_route(self) -> None:
        rt = RouteTable(routes={"a": _make_route(enabled=False)})
        assert rt.enable_route("a") is True
        assert rt.get_route("a") is not None

    def test_disable_nonexistent_returns_false(self) -> None:
        rt = RouteTable(routes={})
        assert rt.disable_route("missing") is False

    def test_enable_nonexistent_returns_false(self) -> None:
        rt = RouteTable(routes={})
        assert rt.enable_route("missing") is False


class TestRouteTableList:
    def test_list_returns_all(self) -> None:
        rt = RouteTable(routes={"a": _make_route(), "b": _make_route(chat_id=-200)})
        routes = rt.list_routes()
        assert len(routes) == 2
        types = {r["type"] for r in routes}
        assert types == {"a", "b"}


class TestRouteTableBackup:
    def test_backup_route_computes_offset(self) -> None:
        rt = RouteTable(routes={"a": _make_route(thread_id=10)})
        backup = rt.get_backup_route("a")
        assert backup is not None
        assert backup["thread_id"] == 110  # 10 + 100
        assert "备份" in backup["description"]

    def test_backup_route_none_thread_returns_none(self) -> None:
        rt = RouteTable(routes={"a": _make_route(thread_id=None)})
        assert rt.get_backup_route("a") is None

    def test_backup_route_nonexistent_returns_none(self) -> None:
        rt = RouteTable(routes={})
        assert rt.get_backup_route("missing") is None

    def test_backup_route_disabled_returns_none(self) -> None:
        rt = RouteTable(routes={"a": _make_route(enabled=False)})
        assert rt.get_backup_route("a") is None
