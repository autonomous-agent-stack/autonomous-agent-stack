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
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autoresearch.core.services.controller_lease import (
    evaluate_controller_state,
    read_controller_state,
    resolve_controller_lease_seconds,
    resolve_controller_state_path,
    write_controller_state,
)


DEFAULT_OFFSET_FILE = ROOT / ".masfactory_runtime" / "telegram-poller" / "update_offset.txt"
ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    ROOT / ".env.linux",
    ROOT / "ai_lab.env",
)
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_LOCAL_HEALTH_PATHS = (
    "/healthz",
    "/health",
    "/api/v1/gateway/telegram/health",
)
DEFAULT_PRIMARY_CONTROLLER_PROBE_PATHS = (
    "/api/v1/cluster/health",
    "/api/v1/gateway/telegram/health",
    "/healthz",
    "/health",
)


@dataclass(frozen=True)
class PollResult:
    offset: int
    processed_updates: int


@dataclass(frozen=True)
class ControllerIdentity:
    runtime_host: str
    execution_role: str
    controller_name: str


@dataclass(frozen=True)
class ControllerDecision:
    active_controller: str
    should_poll: bool
    reason: str
    notification_text: str | None = None


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
    host = resolve_local_api_host()
    port = os.getenv("AUTORESEARCH_API_PORT", "8001").strip() or "8001"
    return f"http://{host}:{port}/api/v1/gateway/telegram/webhook"


def resolve_offset_file() -> Path:
    configured = os.getenv("AUTORESEARCH_TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    if not configured:
        configured = os.getenv("TELEGRAM_POLLING_OFFSET_FILE", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_OFFSET_FILE


def resolve_controller_state_file() -> Path:
    configured = os.getenv("AUTORESEARCH_TELEGRAM_ACTIVE_CONTROLLER_FILE", "").strip()
    if not configured:
        configured = os.getenv("TELEGRAM_ACTIVE_CONTROLLER_FILE", "").strip()
    return resolve_controller_state_path(configured or None)


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


def normalize_runtime_host(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value in {"mac", "macos", "darwin"}:
        return "macos"
    if value in {"linux", "lin"}:
        return "linux"
    return value


def resolve_local_api_host() -> str:
    host = str(
        os.getenv("AUTORESEARCH_LOCAL_API_HOST")
        or os.getenv("AUTORESEARCH_API_HOST")
        or "127.0.0.1"
    ).strip() or "127.0.0.1"
    if host == "0.0.0.0":
        return "127.0.0.1"
    return host


def resolve_controller_identity() -> ControllerIdentity:
    runtime_host = normalize_runtime_host(os.getenv("AUTORESEARCH_RUNTIME_HOST"))
    if not runtime_host:
        runtime_host = "linux" if sys.platform.startswith("linux") else "macos" if sys.platform == "darwin" else "unknown"

    execution_role = str(os.getenv("AUTORESEARCH_EXECUTION_ROLE", "")).strip().lower()
    if execution_role not in {"primary", "backup"}:
        execution_role = "primary" if runtime_host == "linux" else "backup" if runtime_host == "macos" else "primary"

    controller_name = runtime_host or ("primary" if execution_role == "primary" else "backup")
    return ControllerIdentity(
        runtime_host=runtime_host,
        execution_role=execution_role,
        controller_name=controller_name,
    )


def resolve_local_health_urls() -> list[str]:
    host = resolve_local_api_host()
    port = os.getenv("AUTORESEARCH_API_PORT", "8001").strip() or "8001"
    base_url = f"http://{host}:{port}"
    return [f"{base_url}{suffix}" for suffix in DEFAULT_LOCAL_HEALTH_PATHS]


def _parse_url_list(raw: str) -> list[str]:
    normalized = str(raw or "").strip()
    if not normalized:
        return []
    try:
        parsed = json.loads(normalized)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [item.strip() for item in normalized.split(",") if item.strip()]


def resolve_primary_probe_urls() -> list[str]:
    explicit_urls = _parse_url_list(os.getenv("AUTORESEARCH_PRIMARY_CONTROLLER_PROBE_URLS"))
    if explicit_urls:
        return explicit_urls

    explicit_health_url = str(os.getenv("AUTORESEARCH_PRIMARY_CONTROLLER_HEALTH_URL", "")).strip()
    if explicit_health_url:
        return [explicit_health_url]

    base_url = str(os.getenv("AUTORESEARCH_PRIMARY_CONTROLLER_BASE_URL", "")).strip().rstrip("/")
    if not base_url:
        return []
    return [f"{base_url}{suffix}" for suffix in DEFAULT_PRIMARY_CONTROLLER_PROBE_PATHS]


def controller_target_online(urls: list[str], *, timeout_seconds: float = 5.0) -> bool:
    fallback_online = False
    for url in urls:
        try:
            status, data = http_json(url=url, method="GET", timeout=timeout_seconds)
        except Exception:
            continue
        if status != 200:
            continue
        controller_status = str((data or {}).get("controller_status") or "").strip().lower()
        if controller_status:
            return controller_status == "online"
        state = str((data or {}).get("status") or "").strip().lower()
        if not state or state in {"ok", "healthy"}:
            fallback_online = True
    return fallback_online


def is_poll_conflict_error(exc: Exception) -> bool:
    normalized = str(exc).strip().lower()
    return (
        "http 409" in normalized
        or "409: conflict" in normalized
        or "other getupdates request" in normalized
        or ("conflict" in normalized and "getupdates" in normalized)
        or ("conflict" in normalized and "webhook is active" in normalized)
    )


def decide_active_controller(
    *,
    identity: ControllerIdentity,
    previous_active_controller: str | None,
    local_controller_online: bool,
    primary_controller_online: bool | None,
    primary_probe_configured: bool,
) -> ControllerDecision:
    previous = str(previous_active_controller or "").strip().lower() or None
    if identity.execution_role == "backup":
        if not primary_probe_configured:
            return ControllerDecision(
                active_controller="linux",
                should_poll=False,
                reason="primary_probe_unconfigured",
            )
        if primary_controller_online:
            notification_text = None
            if previous == identity.controller_name:
                notification_text = "Bot A: Linux 已恢复在线，Mac 结束接管并释放主处理权。"
            return ControllerDecision(
                active_controller="linux",
                should_poll=False,
                reason="linux_primary_online",
                notification_text=notification_text,
            )
        notification_text = None
        if previous != identity.controller_name:
            notification_text = "Bot A: Linux 主处理不可用，Mac 备用控制台开始接管。"
        return ControllerDecision(
            active_controller=identity.controller_name,
            should_poll=True,
            reason="linux_primary_unreachable",
            notification_text=notification_text,
        )

    if local_controller_online:
        return ControllerDecision(
            active_controller=identity.controller_name,
            should_poll=True,
            reason="local_primary_online",
        )
    return ControllerDecision(
        active_controller=identity.controller_name,
        should_poll=False,
        reason="local_primary_unhealthy",
    )


def build_controller_state_payload(
    *,
    identity: ControllerIdentity,
    decision: ControllerDecision,
    primary_probe_urls: list[str],
    lease_ttl_seconds: int,
    status_signal: str | None,
) -> dict[str, Any]:
    updated_at = int(time.time())
    payload = {
        "active_controller": decision.active_controller,
        "controller_name": identity.controller_name,
        "execution_role": identity.execution_role,
        "runtime_host": identity.runtime_host,
        "should_poll": decision.should_poll,
        "reason": decision.reason,
        "primary_probe_urls": primary_probe_urls,
        "lease_ttl_seconds": lease_ttl_seconds,
        "lease_expires_at": updated_at + lease_ttl_seconds,
        "status_signal": status_signal,
        "task_risk_profile": str(os.getenv("AUTORESEARCH_TASK_RISK_PROFILE", "")).strip() or None,
        "updated_at": updated_at,
    }
    payload["controller_status"] = evaluate_controller_state(payload).controller_status
    return payload


def parse_uid_list(raw: str | None) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def resolve_controller_notify_chat_id() -> str | None:
    for key in (
        "AUTORESEARCH_TELEGRAM_CONTROLLER_NOTIFY_CHAT_ID",
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


def send_controller_notification(*, bot_token: str, chat_id: str | None, text: str | None) -> bool:
    if not text or not chat_id:
        return False
    try:
        telegram_call(bot_token, "sendMessage", {"chat_id": chat_id, "text": text})
    except Exception as exc:
        log(f"[poller] controller notify warning: {exc}")
        return False
    return True


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
    controller_check_interval = max(float(os.getenv("AUTORESEARCH_CONTROLLER_CHECK_INTERVAL_SECONDS", "5")), 1.0)
    controller_lease_seconds = resolve_controller_lease_seconds()
    allowed_updates = parse_allowed_updates(
        os.getenv(
            "TELEGRAM_POLL_ALLOWED_UPDATES",
            '["message","edited_message","callback_query"]',
        )
    )
    initial_offset = int(os.getenv("TELEGRAM_POLL_INITIAL_OFFSET", "0"))
    offset_path = resolve_offset_file()
    controller_state_path = resolve_controller_state_file()
    offset = read_offset(offset_path, initial_offset)
    controller_identity = resolve_controller_identity()
    primary_probe_urls = resolve_primary_probe_urls()
    notify_chat_id = resolve_controller_notify_chat_id()

    log(f"[poller] starting with token={mask_token(bot_token)}")
    log(f"[poller] target webhook={webhook_url}")
    log(f"[poller] offset={offset}")
    log(
        "[poller] controller identity "
        f"name={controller_identity.controller_name} role={controller_identity.execution_role}"
    )

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

    conflict_active = False
    while True:
        try:
            previous_state = read_controller_state(controller_state_path)
            previous_snapshot = evaluate_controller_state(previous_state)
            local_controller_online = controller_target_online(resolve_local_health_urls())
            primary_controller_online = None
            if controller_identity.execution_role == "backup":
                if primary_probe_urls:
                    primary_controller_online = controller_target_online(primary_probe_urls)
                else:
                    log("[poller] backup controller missing AUTORESEARCH_PRIMARY_CONTROLLER_BASE_URL/HEALTH_URL")
            decision = decide_active_controller(
                identity=controller_identity,
                previous_active_controller=previous_state.get("active_controller"),
                local_controller_online=local_controller_online,
                primary_controller_online=primary_controller_online,
                primary_probe_configured=bool(primary_probe_urls),
            )
            status_signal = None
            if controller_identity.execution_role == "primary":
                if decision.should_poll and previous_snapshot.controller_status != "online":
                    status_signal = "recovered"
            elif decision.should_poll and previous_snapshot.active_controller != controller_identity.controller_name:
                status_signal = "takeover_started"
            elif (
                previous_snapshot.active_controller == controller_identity.controller_name
                and decision.active_controller == "linux"
                and not decision.should_poll
            ):
                status_signal = "released"
            write_controller_state(
                controller_state_path,
                build_controller_state_payload(
                    identity=controller_identity,
                    decision=decision,
                    primary_probe_urls=primary_probe_urls,
                    lease_ttl_seconds=controller_lease_seconds,
                    status_signal=status_signal,
                ),
            )
            if decision.notification_text:
                notified = send_controller_notification(
                    bot_token=bot_token,
                    chat_id=notify_chat_id,
                    text=decision.notification_text,
                )
                log(
                    f"[poller] controller transition active={decision.active_controller} "
                    f"reason={decision.reason} notified={notified}"
                )
            if not decision.should_poll:
                log(f"[poller] standby active={decision.active_controller} reason={decision.reason}")
                if args.once:
                    return 0 if controller_identity.execution_role == "backup" else 1
                time.sleep(controller_check_interval)
                continue

            effective_poll_timeout = poll_timeout
            if controller_identity.execution_role == "backup":
                effective_poll_timeout = max(1, min(poll_timeout, int(controller_check_interval)))
            result = poll_once(
                bot_token=bot_token,
                webhook_url=webhook_url,
                secret_token=secret_token,
                offset=offset,
                offset_path=offset_path,
                poll_timeout=effective_poll_timeout,
                allowed_updates=allowed_updates,
            )
            offset = result.offset
            if conflict_active:
                log("[poller] getUpdates conflict cleared; polling resumed")
                conflict_active = False
            if args.once:
                return 0
        except KeyboardInterrupt:
            log("[poller] stopped by keyboard interrupt")
            return 0
        except Exception as exc:
            if is_poll_conflict_error(exc):
                if not conflict_active:
                    log("[poller] getUpdates conflict detected; waiting for the other polling instance to release the bot token")
                    conflict_active = True
                if args.once:
                    return 1
                time.sleep(max(retry_delay, controller_check_interval))
                continue
            conflict_active = False
            log(f"[poller] error: {exc}")
            if args.once:
                return 1
            time.sleep(retry_delay)


if __name__ == "__main__":
    raise SystemExit(main())
