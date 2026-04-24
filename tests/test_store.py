"""Tests for shared store: InMemoryRepository, SQLiteModelRepository, create_resource_id."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from autoresearch.shared.store import InMemoryRepository, SQLiteModelRepository, create_resource_id


class _SampleItem(BaseModel):
    name: str
    value: int


class TestCreateResourceId:
    def test_prefix_applied(self) -> None:
        rid = create_resource_id("test")
        assert rid.startswith("test_")

    def test_unique_ids(self) -> None:
        ids = {create_resource_id("x") for _ in range(100)}
        assert len(ids) == 100

    def test_id_has_hex_suffix(self) -> None:
        rid = create_resource_id("abc")
        suffix = rid.split("_", 1)[1]
        assert len(suffix) == 12
        assert all(c in "0123456789abcdef" for c in suffix)


class TestInMemoryRepository:
    def test_save_and_get(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        item = _SampleItem(name="alpha", value=10)
        repo.save("id1", item)
        assert repo.get("id1") == item

    def test_get_missing_returns_none(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        assert repo.get("nonexistent") is None

    def test_list_returns_all(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        repo.save("a", _SampleItem(name="a", value=1))
        repo.save("b", _SampleItem(name="b", value=2))
        assert len(repo.list()) == 2

    def test_list_empty(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        assert repo.list() == []

    def test_save_overwrites(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        repo.save("id", _SampleItem(name="old", value=1))
        repo.save("id", _SampleItem(name="new", value=2))
        assert repo.get("id").name == "new"

    def test_save_returns_resource(self) -> None:
        repo = InMemoryRepository[_SampleItem]()
        item = _SampleItem(name="ret", value=5)
        result = repo.save("id", item)
        assert result is item


class TestSQLiteModelRepository:
    def test_save_and_get(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        repo = SQLiteModelRepository[_SampleItem](db, "items", _SampleItem)
        item = _SampleItem(name="hello", value=42)
        repo.save("id1", item)
        got = repo.get("id1")
        assert got is not None
        assert got.name == "hello"
        assert got.value == 42

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        repo = SQLiteModelRepository[_SampleItem](db, "items", _SampleItem)
        assert repo.get("missing") is None

    def test_list_returns_saved_items(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        repo = SQLiteModelRepository[_SampleItem](db, "items", _SampleItem)
        repo.save("a", _SampleItem(name="first", value=1))
        repo.save("b", _SampleItem(name="second", value=2))
        items = repo.list()
        assert len(items) == 2
        names = {item.name for item in items}
        assert names == {"first", "second"}

    def test_save_upserts(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        repo = SQLiteModelRepository[_SampleItem](db, "items", _SampleItem)
        repo.save("id", _SampleItem(name="v1", value=1))
        repo.save("id", _SampleItem(name="v2", value=2))
        got = repo.get("id")
        assert got.name == "v2"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        db = tmp_path / "sub" / "dir" / "test.db"
        repo = SQLiteModelRepository[_SampleItem](db, "items", _SampleItem)
        repo.save("x", _SampleItem(name="nested", value=0))
        assert db.exists()

    def test_invalid_table_name_raises(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        with pytest.raises(ValueError, match="Unsupported SQL identifier"):
            SQLiteModelRepository[_SampleItem](db, "drop table foo;--", _SampleItem)

    def test_with_pydantic_model(self, tmp_path: Path) -> None:
        from pydantic import BaseModel

        class Item(BaseModel):
            name: str
            value: int

        db = tmp_path / "test.db"
        repo = SQLiteModelRepository[Item](db, "pyd_items", Item)
        repo.save("p1", Item(name="pydantic", value=99))
        got = repo.get("p1")
        assert got is not None
        assert got.name == "pydantic"
        assert got.value == 99
