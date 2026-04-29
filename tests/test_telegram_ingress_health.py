from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "telegram_ingress_health.py"
    spec = importlib.util.spec_from_file_location("telegram_ingress_health", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_status_file_returns_empty_dict_when_missing(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing.json"
    assert module._load_status_file(missing) == {}


def test_load_status_file_returns_payload_when_valid(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "status.json"
    payload = {"mode": "polling", "active_consumer": "webhook", "state": "failover"}
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert module._load_status_file(target) == payload
