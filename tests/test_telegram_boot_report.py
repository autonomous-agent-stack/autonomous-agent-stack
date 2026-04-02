from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "telegram_boot_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_boot_report", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_latest_run_summary_uses_most_recent_summary(tmp_path: Path) -> None:
    module = load_module()
    runs_root = tmp_path / "runs"
    older = runs_root / "older"
    newer = runs_root / "newer"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "summary.json").write_text(json.dumps({"run_id": "older", "final_status": "failed"}), encoding="utf-8")
    (newer / "summary.json").write_text(json.dumps({"run_id": "newer", "final_status": "ready"}), encoding="utf-8")

    older_time = 1_700_000_000
    newer_time = older_time + 60
    (older / "summary.json").touch()
    (newer / "summary.json").touch()
    import os
    os.utime(older / "summary.json", (older_time, older_time))
    os.utime(newer / "summary.json", (newer_time, newer_time))

    run_id, status = module.latest_run_summary(runs_root)

    assert run_id == "newer"
    assert status == "ready"


def test_build_message_includes_core_runtime_state() -> None:
    module = load_module()
    state = module.BootState(
        hostname="lisa-vm",
        api_host="100.68.246.67",
        api_port=8001,
        api_ok=True,
        api_checked_url="http://100.68.246.67:8001/healthz",
        poller_ok=True,
        offset="42",
        pending_runs=0,
        latest_run_id="mgrdispatch_demo",
        latest_run_status="completed",
    )

    message = module.build_message(state)

    assert "Linux 管家已上线" in message
    assert "host: lisa-vm" in message
    assert "api: ok (100.68.246.67:8001)" in message
    assert "poller: running" in message
    assert "last_run: mgrdispatch_demo / completed" in message
    assert "poller_offset: 42" in message


def test_build_message_with_custom_title() -> None:
    module = load_module()
    state = module.BootState(
        hostname="lisa-vm",
        api_host="100.68.246.67",
        api_port=8001,
        api_ok=True,
        api_checked_url="http://100.68.246.67:8001/healthz",
        poller_ok=True,
        offset="42",
        pending_runs=0,
        latest_run_id=None,
        latest_run_status=None,
    )

    message = module.build_message_with_title(state, title="Linux 管家定时报平安")

    assert message.splitlines()[0] == "Linux 管家定时报平安"
