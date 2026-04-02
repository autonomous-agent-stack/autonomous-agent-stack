from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_dev_start_reuses_linux_env_and_standard_runners() -> None:
    content = _read("scripts/dev-start.sh")

    assert ".env.linux" in content
    assert "resolve_bind_host()" in content
    assert 'export AUTORESEARCH_LOCAL_API_HOST="${HOST}"' in content
    assert 'bash "${POLLER_STARTER}"' in content
    assert 'exec "${API_RUNNER}"' in content
    assert 'if api_is_healthy;' in content
    assert "--reload" not in content


def test_linux_startup_helpers_load_env_linux_and_use_loopback_for_local_probe() -> None:
    api_runner = _read("scripts/run_api_service.sh")
    poller_runner = _read("scripts/run_telegram_poller.sh")
    poller_starter = _read("scripts/start_telegram_poller.sh")

    assert ".env.linux" in api_runner
    assert ".env.linux" in poller_runner
    assert "resolve_bind_host()" in api_runner
    assert "resolve_local_api_host()" in poller_runner
    assert 'export AUTORESEARCH_LOCAL_API_HOST="${HOST}"' in api_runner
    assert 'export AUTORESEARCH_LOCAL_API_HOST="${PROBE_HOST}"' in poller_runner
    assert "stopping existing local telegram poller(s)" in poller_starter
    assert 'pgrep -u "$(id -u)" -f "${SCRIPT_PATH}|${RUNNER}"' in poller_starter
    assert 'telegram poller already managed by systemd' in poller_starter
