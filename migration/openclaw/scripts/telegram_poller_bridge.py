#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT_DIR / "logs"
OFFSET_FILE = LOG_DIR / "telegram-poller.offset"
ENV_FILE = ROOT_DIR / ".env.local"
OPENCLAW_CONFIG = Path("/Users/iCloud_GZ/.openclaw/openclaw.json")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


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
    return (
        data.get("channels", {})
        .get("telegram", {})
        .get("botToken")
    )


def normalize_token(raw: str | None) -> str | None:
    token = str(raw or "").strip()
    if not token:
        return None
    # Guard common placeholder values from env templates.
    lowered = token.lower()
    if "replace_with" in lowered or "your_new_bot_token" in lowered:
        return None
    return token


def read_offset(default_offset: int) -> int:
    if not OFFSET_FILE.exists():
        return default_offset
    try:
        return int(OFFSET_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return default_offset


def write_offset(value: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(value), encoding="utf-8")


def http_json(
    url: str,
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


def main() -> int:
    load_env_file(ENV_FILE)

    bot_token = normalize_token(os.getenv("TELEGRAM_BOT_TOKEN"))
    if bot_token is None:
        bot_token = normalize_token(read_openclaw_bot_token())
    if not bot_token:
        log("[poller] missing TELEGRAM_BOT_TOKEN and cannot read ~/.openclaw/openclaw.json")
        return 2

    webhook_url = os.getenv(
        "TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL",
        "http://127.0.0.1:8000/api/v1/gateway/telegram/webhook",
    )
    secret_token = os.getenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "").strip() or None

    poll_timeout = int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "25"))
    retry_delay = float(os.getenv("TELEGRAM_POLL_RETRY_SECONDS", "3"))
    allowed_updates = os.getenv(
        "TELEGRAM_POLL_ALLOWED_UPDATES",
        '["message","edited_message","callback_query"]',
    )

    try:
        allowed_updates_value = json.loads(allowed_updates)
        if not isinstance(allowed_updates_value, list):
            raise ValueError("allowed updates must be list")
    except Exception:
        allowed_updates_value = ["message", "edited_message", "callback_query"]

    initial_offset = int(os.getenv("TELEGRAM_POLL_INITIAL_OFFSET", "0"))
    offset = read_offset(initial_offset)

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
            resp = telegram_call(
                bot_token,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": poll_timeout,
                    "allowed_updates": json.dumps(allowed_updates_value, ensure_ascii=False),
                },
            )
            updates = resp.get("result") or []
            if not updates:
                continue

            for update in updates:
                update_id = update.get("update_id")
                next_offset = offset
                if isinstance(update_id, int):
                    next_offset = max(offset, update_id + 1)
                try:
                    status, ack = forward_update(update, webhook_url, secret_token)
                except error.HTTPError as exc:
                    body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                    raise RuntimeError(f"local webhook http {exc.code}: {body}") from exc
                except error.URLError as exc:
                    raise RuntimeError(f"local webhook network error: {exc}") from exc

                if status >= 400:
                    raise RuntimeError(f"local webhook failed status={status}, body={ack}")

                offset = next_offset
                write_offset(offset)
                accepted = ack.get("accepted") if isinstance(ack, dict) else None
                log(f"[poller] update_id={update_id} forwarded status={status} accepted={accepted}")

        except KeyboardInterrupt:
            log("[poller] stopped by keyboard interrupt")
            return 0
        except Exception as exc:
            log(f"[poller] error: {exc}")
            time.sleep(retry_delay)


if __name__ == "__main__":
    sys.exit(main())
