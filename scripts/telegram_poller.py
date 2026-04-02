#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OFFSET_FILE = ROOT / ".masfactory_runtime" / "telegram-poller" / "update_offset.txt"
ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    ROOT / "ai_lab.env",
)
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


@dataclass(frozen=True)
class PollResult:
    offset: int
    processed_updates: int


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


def mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def log(msg: str) -> None:
    print(msg, flush=True)


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
    if isinstance(token, str):
        return token
    return None


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
    if token and not os.getenv("TELEGRAM_BOT_TOKEN"):
        os.environ["TELEGRAM_BOT_TOKEN"] = token
    if token and not os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN"):
        os.environ["AUTORESEARCH_TELEGRAM_BOT_TOKEN"] = token
    return token


def resolve_webhook_url() -> str:
    explicit = os.getenv("TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL", "").strip()
    if explicit:
        return explicit
    host = os.getenv("AUTORESEARCH_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("AUTORESEARCH_API_PORT", "8000").strip() or "8000"
    return f"http://{host}:{port}/api/v1/gateway/telegram/webhook"


def resolve_offset_file() -> Path:
    configured = os.getenv("AUTORESEARCH_TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    if not configured:
        configured = os.getenv("TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_OFFSET_FILE


def read_offset(path: Path, default_offset: int) -> int:
    if not path.exists():
        return default_offset
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return default_offset


def write_offset(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value), encoding="utf-8")


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 60,
) -> tuple[int, dict[str, Any]]:
    req = request.Request(url=url, data=body, headers=headers or {}, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        status = int(resp.status)
        payload = resp.read().decode("utf-8")
        if not payload:
            return status, {}
        return status, json.loads(payload)


def telegram_call(token: str, method_name: str, params: dict[str, Any]) -> dict[str, Any]:
    api_url = f"https://api.telegram.org/bot{token}/{method_name}"
    form = parse.urlencode(params).encode("utf-8")
    status, data = http_json(
        url=api_url,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=form,
        timeout=90,
    )
    if status >= 400:
        raise RuntimeError(f"telegram {method_name} http {status}: {data}")
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method_name} api error: {data}")
    return data


def forward_update(update: dict[str, Any], webhook_url: str, secret_token: str | None) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if secret_token:
        headers["x-telegram-bot-api-secret-token"] = secret_token
    body = json.dumps(update, ensure_ascii=False).encode("utf-8")
    return http_json(
        url=webhook_url,
        method="POST",
        headers=headers,
        body=body,
        timeout=30,
    )


def parse_allowed_updates(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return ["message", "edited_message", "callback_query"]


def poll_once(
    *,
    bot_token: str,
    webhook_url: str,
    secret_token: str | None,
    offset: int,
    offset_path: Path,
    poll_timeout: int,
    allowed_updates: list[str],
) -> PollResult:
    resp = telegram_call(
        bot_token,
        "getUpdates",
        {
            "offset": offset,
            "timeout": poll_timeout,
            "allowed_updates": json.dumps(allowed_updates, ensure_ascii=False),
        },
    )
    updates = resp.get("result") or []
    if not updates:
        return PollResult(offset=offset, processed_updates=0)

    next_offset = offset
    processed = 0
    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            next_offset = max(next_offset, update_id + 1)
        try:
            status, ack = forward_update(update, webhook_url, secret_token)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(f"local webhook http {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"local webhook network error: {exc}") from exc

        if status >= 400:
            raise RuntimeError(f"local webhook failed status={status}, body={ack}")

        processed += 1
        write_offset(offset_path, next_offset)
        accepted = ack.get("accepted") if isinstance(ack, dict) else None
        log(f"[poller] update_id={update_id} forwarded status={status} accepted={accepted}")

    return PollResult(offset=next_offset, processed_updates=processed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram polling sidecar for local webhook bridge")
    parser.add_argument("--once", action="store_true", help="poll exactly once and exit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_default_env()

    bot_token = resolve_bot_token()
    if not bot_token:
        log("[poller] missing TELEGRAM_BOT_TOKEN/AUTORESEARCH_TELEGRAM_BOT_TOKEN")
        return 2

    webhook_url = resolve_webhook_url()
    secret_token = os.getenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "").strip() or None
    poll_timeout = int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "25"))
    retry_delay = float(os.getenv("TELEGRAM_POLL_RETRY_SECONDS", "3"))
    allowed_updates = parse_allowed_updates(
        os.getenv(
            "TELEGRAM_POLL_ALLOWED_UPDATES",
            '["message","edited_message","callback_query"]',
        )
    )
    initial_offset = int(os.getenv("TELEGRAM_POLL_INITIAL_OFFSET", "0"))
    offset_path = resolve_offset_file()
    offset = read_offset(offset_path, initial_offset)

    log(f"[poller] starting with token={mask_token(bot_token)}")
    log(f"[poller] target webhook={webhook_url}")
    log(f"[poller] offset={offset}")

    try:
        telegram_call(
            bot_token,
            "deleteWebhook",
            {"drop_pending_updates": "false"},
        )
        log("[poller] deleteWebhook ok")
    except Exception as exc:
        log(f"[poller] deleteWebhook warning: {exc}")

    me = telegram_call(bot_token, "getMe", {})
    username = me.get("result", {}).get("username")
    log(f"[poller] online as @{username}")

    while True:
        try:
            result = poll_once(
                bot_token=bot_token,
                webhook_url=webhook_url,
                secret_token=secret_token,
                offset=offset,
                offset_path=offset_path,
                poll_timeout=poll_timeout,
                allowed_updates=allowed_updates,
            )
            offset = result.offset
            if args.once:
                return 0
        except KeyboardInterrupt:
            log("[poller] stopped by keyboard interrupt")
            return 0
        except Exception as exc:
            log(f"[poller] error: {exc}")
            if args.once:
                return 1
            time.sleep(retry_delay)


if __name__ == "__main__":
    raise SystemExit(main())
