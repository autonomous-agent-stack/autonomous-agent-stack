#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OFFSET_FILE = ROOT / ".masfactory_runtime" / "telegram-poller" / "update_offset.txt"
RUNS_ROOT = ROOT / ".masfactory_runtime" / "runs"
PID_FILE = ROOT / "logs" / "telegram-poller.pid"
ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    ROOT / "ai_lab.env",
)
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


@dataclass(frozen=True)
class BootState:
    hostname: str
    api_host: str
    api_port: int
    api_ok: bool
    api_checked_url: str
    poller_ok: bool
    offset: str
    pending_runs: int
    latest_run_id: str | None
    latest_run_status: str | None


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_default_env() -> None:
    for env_file in ENV_FILES:
        load_env_file(env_file)


def read_openclaw_bot_token() -> str | None:
    if not OPENCLAW_CONFIG.exists():
        return None
    try:
        data = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return None
    channels = data.get("channels", {})
    telegram = channels.get("telegram", {})
    token = telegram.get("botToken")
    return token if isinstance(token, str) else None


def normalize_token(raw: str | None) -> str | None:
    token = str(raw or "").strip()
    if not token:
        return None
    lowered = token.lower()
    if "replace_with" in lowered or "your_new_bot_token" in lowered or "your-telegram-bot-token" in lowered:
        return None
    return token


def resolve_bot_token() -> str | None:
    token = normalize_token(
        os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
    )
    if token is None:
        token = normalize_token(read_openclaw_bot_token())
    return token


def parse_uid_list(raw: str | None) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def resolve_chat_id() -> str | None:
    for key in (
        "AUTORESEARCH_TELEGRAM_BOOT_NOTIFY_CHAT_ID",
        "TELEGRAM_CHAT_ID",
    ):
        value = str(os.getenv(key, "")).strip()
        if value:
            return value

    for key in (
        "AUTORESEARCH_TELEGRAM_ALLOWED_UIDS",
        "AUTORESEARCH_TELEGRAM_OWNER_UIDS",
        "AUTORESEARCH_TELEGRAM_PARTNER_UIDS",
    ):
        values = parse_uid_list(os.getenv(key))
        if values:
            return values[0]
    return None


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any]]:
    req = request.Request(url=url, data=body, headers=headers or {}, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
        if not payload:
            return int(resp.status), {}
        return int(resp.status), json.loads(payload)


def telegram_call(token: str, method_name: str, params: dict[str, Any]) -> dict[str, Any]:
    endpoint = f"https://api.telegram.org/bot{token}/{method_name}"
    body = parse.urlencode(params).encode("utf-8")
    status, data = http_json(
        endpoint,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
        timeout=60,
    )
    if status >= 400:
        raise RuntimeError(f"telegram {method_name} http {status}: {data}")
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method_name} api error: {data}")
    return data


def send_message(token: str, chat_id: str, text: str) -> None:
    telegram_call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


def resolve_offset_file() -> Path:
    configured = os.getenv("AUTORESEARCH_TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    if not configured:
        configured = os.getenv("TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_OFFSET_FILE


def read_offset_value(path: Path) -> str:
    if not path.exists():
        return "none"
    try:
        return path.read_text(encoding="utf-8").strip() or "none"
    except Exception:
        return "unreadable"


def poller_running(pid_file: Path) -> bool:
    if not pid_file.exists():
        code, output = run_systemctl(["is-active", "autonomous-agent-stack-telegram-poller.service"])
        return code == 0 and output.strip() == "active"
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
    except Exception:
        code, output = run_systemctl(["is-active", "autonomous-agent-stack-telegram-poller.service"])
        return code == 0 and output.strip() == "active"
    return True


def run_systemctl(args: list[str]) -> tuple[int, str]:
    try:
        import subprocess

        proc = subprocess.run(
            ["systemctl", *args],
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output.strip()
    except Exception:
        return 1, ""


def count_pending_runs(runs_root: Path) -> int:
    if not runs_root.exists():
        return 0
    total = 0
    for child in runs_root.iterdir():
        if child.is_dir() and not (child / "summary.json").exists():
            total += 1
    return total


def latest_run_summary(runs_root: Path) -> tuple[str | None, str | None]:
    if not runs_root.exists():
        return None, None
    summaries = sorted(runs_root.glob("*/summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in summaries:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        run_id = data.get("run_id") or path.parent.name
        final_status = data.get("final_status")
        return str(run_id), str(final_status) if final_status is not None else None
    return None, None


def check_api_health(api_host: str, api_port: int) -> tuple[bool, str]:
    urls = [
        f"http://{api_host}:{api_port}/healthz",
        f"http://{api_host}:{api_port}/health",
    ]
    for url in urls:
        try:
            status, data = http_json(url, timeout=10)
            if status == 200 and data.get("status") == "ok":
                return True, url
        except error.URLError:
            continue
        except Exception:
            continue
    return False, urls[0]


def collect_state() -> BootState:
    hostname = socket.gethostname()
    api_host = (os.getenv("AUTORESEARCH_API_HOST", "127.0.0.1").strip() or "127.0.0.1")
    api_port = int(os.getenv("AUTORESEARCH_API_PORT", "8001").strip() or "8001")
    api_ok, api_checked_url = check_api_health(api_host, api_port)
    poller_ok = poller_running(PID_FILE)
    offset = read_offset_value(resolve_offset_file())
    pending_runs = count_pending_runs(RUNS_ROOT)
    latest_run_id, latest_run_status = latest_run_summary(RUNS_ROOT)
    return BootState(
        hostname=hostname,
        api_host=api_host,
        api_port=api_port,
        api_ok=api_ok,
        api_checked_url=api_checked_url,
        poller_ok=poller_ok,
        offset=offset,
        pending_runs=pending_runs,
        latest_run_id=latest_run_id,
        latest_run_status=latest_run_status,
    )


def build_message(state: BootState) -> str:
    return build_message_with_title(state, title="Linux 管家已上线")


def build_message_with_title(state: BootState, *, title: str) -> str:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    api_status = "ok" if state.api_ok else "fail"
    poller_status = "running" if state.poller_ok else "down"
    latest_run = "none"
    if state.latest_run_id:
        latest_run = f"{state.latest_run_id} / {state.latest_run_status or 'unknown'}"
    return "\n".join(
        [
            title,
            f"time: {timestamp}",
            f"host: {state.hostname}",
            f"api: {api_status} ({state.api_host}:{state.api_port})",
            f"poller: {poller_status}",
            f"pending_runs: {state.pending_runs}",
            f"last_run: {latest_run}",
            f"poller_offset: {state.offset}",
            f"health_probe: {state.api_checked_url}",
        ]
    )


def main() -> int:
    load_default_env()

    parser = argparse.ArgumentParser(description="Send a Linux boot status notification to Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print the message instead of sending it")
    parser.add_argument("--title", default="Linux 管家已上线", help="First line of the Telegram status message")
    args = parser.parse_args()

    state = collect_state()
    message = build_message_with_title(state, title=args.title)

    if args.dry_run:
        print(message)
        return 0

    token = resolve_bot_token()
    chat_id = resolve_chat_id()
    if not token:
        print("missing TELEGRAM_BOT_TOKEN/AUTORESEARCH_TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 2
    if not chat_id:
        print("missing boot notification chat id; set AUTORESEARCH_TELEGRAM_BOOT_NOTIFY_CHAT_ID or AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", file=sys.stderr)
        return 2

    send_message(token, chat_id, message)
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
