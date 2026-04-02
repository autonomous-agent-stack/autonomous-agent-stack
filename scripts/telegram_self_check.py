#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLLER_LOG = ROOT / "logs" / "telegram-poller.log"
POLLER_STATUS_SCRIPT = ROOT / "scripts" / "status_telegram_poller.sh"
ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    ROOT / "ai_lab.env",
)


@dataclass
class CheckResult:
    name: str
    ok: bool | None
    detail: str


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


def env_or_pid(env: dict[str, str], key: str) -> str:
    return env.get(key, "") or os.getenv(key, "")


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def find_api_pid(port: int) -> int | None:
    code, output = run_cmd(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"])
    if code != 0 or not output:
        return None
    lines = output.splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) > 1 and parts[1].isdigit():
            return int(parts[1])
    return None


def parse_env_from_pid(pid: int) -> dict[str, str]:
    code, output = run_cmd(["ps", "eww", "-p", str(pid)])
    if code != 0 or not output:
        return {}
    # Keep last line to skip header
    line = output.splitlines()[-1]
    env: dict[str, str] = {}
    for key in [
        "AUTORESEARCH_TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "AUTORESEARCH_TELEGRAM_SECRET_TOKEN",
        "AUTORESEARCH_TELEGRAM_ALLOWED_UIDS",
        "AUTORESEARCH_API_HOST",
        "AUTORESEARCH_API_PORT",
    ]:
        m = re.search(rf"{re.escape(key)}=([^\s]+)", line)
        if m:
            env[key] = m.group(1)
    return env


def http_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: dict[str, Any] | None = None, timeout: float = 10.0) -> tuple[int, dict[str, Any] | None, str]:
    payload = None
    req_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("content-type", "application/json")
    req = urllib.request.Request(url=url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            data = json.loads(text) if text else {}
            return int(resp.status), data, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except Exception:
            data = None
        return int(exc.code), data, text
    except Exception as exc:
        return 0, None, str(exc)


def tail_lines(path: Path, max_lines: int = 60) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return lines[-max_lines:]


def systemd_service_active(name: str) -> bool:
    code, output = run_cmd(["systemctl", "is-active", name])
    return code == 0 and output.strip() == "active"


def check_status_label(check: CheckResult) -> str:
    if check.ok is True:
        return "PASS"
    if check.ok is False:
        return "FAIL"
    return "SKIP"


def check_blocks_exit(check: CheckResult, *, ignored_names: set[str]) -> bool:
    return check.name not in ignored_names and check.ok is False


def local_webhook_payload(*, update_id: int, message_id: int, user_id: str, text: str) -> dict[str, Any]:
    numeric_user_id = int(user_id)
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "from": {"id": numeric_user_id, "username": "selfcheck"},
            "chat": {"id": numeric_user_id, "type": "private"},
            "date": int(time.time()),
            "text": text,
        },
    }


def main() -> int:
    load_default_env()
    parser = argparse.ArgumentParser(description="Diagnose Telegram reply path for local poller mode.")
    parser.add_argument("--host", default=os.getenv("AUTORESEARCH_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AUTORESEARCH_API_PORT", "8000")))
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only verify the local API and local webhook path. Skip token, poller, and outbound Telegram checks.",
    )
    parser.add_argument(
        "--synthetic-uid",
        type=int,
        default=999999,
        help="Synthetic Telegram uid/chat_id to use for offline local webhook tests when allowlist env is absent.",
    )
    parser.add_argument("--send-test", action="store_true", help="Send one debug message to allowed UID")
    args = parser.parse_args()

    checks: list[CheckResult] = []
    api_pid = find_api_pid(args.port)
    if api_pid is None:
        checks.append(CheckResult("api_listen", False, f"no process listening on :{args.port}"))
        print_report(checks, [])
        return 1
    checks.append(CheckResult("api_listen", True, f"pid={api_pid} on :{args.port}"))

    env = parse_env_from_pid(api_pid)
    api_host = (args.host or env_or_pid(env, "AUTORESEARCH_API_HOST") or "127.0.0.1").strip()
    bot_token = env_or_pid(env, "AUTORESEARCH_TELEGRAM_BOT_TOKEN") or env_or_pid(env, "TELEGRAM_BOT_TOKEN")
    secret = env_or_pid(env, "AUTORESEARCH_TELEGRAM_SECRET_TOKEN")
    allowed_uids = [x.strip() for x in env_or_pid(env, "AUTORESEARCH_TELEGRAM_ALLOWED_UIDS").split(",") if x.strip()]
    primary_uid = allowed_uids[0] if allowed_uids else ""
    local_test_uid = primary_uid or str(args.synthetic_uid)

    if args.offline:
        checks.append(CheckResult("bot_token_env", None, "not required in offline mode"))
        checks.append(
            CheckResult(
                "secret_env",
                True if secret else None,
                "present" if secret else "not configured (offline mode sends no secret header unless server expects one)",
            )
        )
        checks.append(
            CheckResult(
                "allowed_uid_env",
                True if primary_uid else None,
                primary_uid or f"not required in offline mode; using synthetic uid {local_test_uid}",
            )
        )
    else:
        checks.append(CheckResult("bot_token_env", bool(bot_token), "present" if bot_token else "missing"))
        checks.append(CheckResult("secret_env", bool(secret), "present" if secret else "missing (allowed only if webhook skips validation)"))
        checks.append(CheckResult("allowed_uid_env", bool(primary_uid), primary_uid or "missing"))

    status_url = f"http://{api_host}:{args.port}/api/v1/gateway/telegram/health"
    status_code, status_data, status_raw = http_json(status_url)
    checks.append(CheckResult("gateway_health", status_code == 200, f"status={status_code} body={status_data or status_raw}"))

    recent_log = tail_lines(POLLER_LOG, max_lines=120)
    recent_errors = [ln for ln in recent_log if "error:" in ln.lower()]
    recent_404 = [ln for ln in recent_log if "404" in ln]
    recent_accept_false = [ln for ln in recent_log if "accepted=False" in ln]

    if args.offline:
        checks.append(CheckResult("poller_process", None, "skipped in offline mode"))
        checks.append(CheckResult("poller_log", None, "skipped in offline mode"))
    else:
        poller_ok = False
        poller_detail = "status script missing"
        if POLLER_STATUS_SCRIPT.exists():
            code, out = run_cmd(["bash", str(POLLER_STATUS_SCRIPT)])
            poller_ok = ("running" in out.lower()) and ("not running" not in out.lower())
            poller_detail = out.splitlines()[0] if out else f"exit={code}"
        if not poller_ok and systemd_service_active("autonomous-agent-stack-telegram-poller.service"):
            poller_ok = True
            poller_detail = "systemd service active"
        checks.append(CheckResult("poller_process", poller_ok, poller_detail))

        log_ok = not recent_errors[-10:] and not recent_404[-10:]
        log_detail = f"errors={len(recent_errors)} 404={len(recent_404)} accepted_false={len(recent_accept_false)}"
        checks.append(CheckResult("poller_log", log_ok, log_detail))

    if args.offline:
        checks.append(CheckResult("telegram_getMe", None, "skipped in offline mode"))
    elif bot_token:
        tg_me_url = f"https://api.telegram.org/bot{bot_token}/getMe"
        code, data, raw = http_json(tg_me_url)
        checks.append(CheckResult("telegram_getMe", code == 200 and bool(data and data.get("ok")), f"status={code} body={data or raw}"))
    else:
        checks.append(CheckResult("telegram_getMe", None, "skipped because bot token is missing"))

    if args.offline:
        checks.append(CheckResult("telegram_send_test", None, "skipped in offline mode"))
    elif bot_token and primary_uid and args.send_test:
        msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        code, data, raw = http_json(
            msg_url,
            method="POST",
            body={"chat_id": primary_uid, "text": f"[self-check] {time.strftime('%Y-%m-%d %H:%M:%S')}"},
        )
        checks.append(CheckResult("telegram_send_test", code == 200 and bool(data and data.get("ok")), f"status={code} body={data or raw}"))
    elif args.send_test:
        checks.append(CheckResult("telegram_send_test", None, "skipped because bot token or allowed uid is missing"))

    # Local webhook synthetic tests to expose "accepted/reason"
    if args.offline or primary_uid:
        hdrs = {"x-telegram-bot-api-secret-token": secret} if secret else {}
        payload_help = local_webhook_payload(
            update_id=int(time.time()),
            message_id=1,
            user_id=local_test_uid,
            text="/help",
        )
        c1, d1, r1 = http_json(
            f"http://{api_host}:{args.port}/api/v1/gateway/telegram/webhook",
            method="POST",
            headers=hdrs,
            body=payload_help,
        )
        ok1 = c1 == 200 and isinstance(d1, dict) and bool(d1.get("accepted"))
        checks.append(CheckResult("local_webhook_help", ok1, f"status={c1} body={d1 or r1}"))

        payload_status = local_webhook_payload(
            update_id=int(time.time()) + 1,
            message_id=2,
            user_id=local_test_uid,
            text="/status",
        )
        c2, d2, r2 = http_json(
            f"http://{api_host}:{args.port}/api/v1/gateway/telegram/webhook",
            method="POST",
            headers=hdrs,
            body=payload_status,
        )
        ok2 = c2 == 200 and isinstance(d2, dict) and bool(d2.get("accepted"))
        checks.append(CheckResult("local_webhook_status", ok2, f"status={c2} body={d2 or r2}"))
    else:
        checks.append(CheckResult("local_webhook_help", None, "skipped because allowed uid is missing; use --offline to force synthetic local checks"))
        checks.append(CheckResult("local_webhook_status", None, "skipped because allowed uid is missing; use --offline to force synthetic local checks"))

    suggestions = build_suggestions(
        checks,
        recent_errors,
        recent_accept_false,
        offline=args.offline,
    )
    print_report(checks, suggestions)
    return 0 if not any(check_blocks_exit(c, ignored_names={"poller_log"}) for c in checks) else 2


def build_suggestions(
    checks: list[CheckResult],
    errors: list[str],
    accepted_false: list[str],
    *,
    offline: bool,
) -> list[str]:
    by_name = {c.name: c for c in checks}
    out: list[str] = []
    if not offline and by_name.get("bot_token_env", CheckResult("", True, "")).ok is False:
        out.append("Set TELEGRAM_BOT_TOKEN and AUTORESEARCH_TELEGRAM_BOT_TOKEN in runtime env.")
    if not offline and by_name.get("allowed_uid_env", CheckResult("", True, "")).ok is False:
        out.append("Set AUTORESEARCH_TELEGRAM_ALLOWED_UIDS to your Telegram user id.")
    if not offline and by_name.get("poller_process", CheckResult("", True, "")).ok is False:
        out.append("Restart poller: bash scripts/stop_telegram_poller.sh && bash scripts/start_telegram_poller.sh")
    if by_name.get("gateway_health", CheckResult("", True, "")).detail.startswith("status=404"):
        out.append("Gateway route missing in current app. Ensure /api/v1/gateway/telegram/webhook is mounted.")
    if not offline and errors:
        if any("404" in x for x in errors):
            out.append("Poller target path mismatch. Check TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL.")
        if any("SSL" in x for x in errors):
            out.append("Network TLS instability to Telegram API. Retry later or check outbound network.")
    if accepted_false:
        out.append("Webhook accepted=False seen. Usually unsupported update type or empty message text.")
    if not out:
        if offline:
            out.append("Offline core path looks healthy. You can start a short local trial now; no week-long soak is required for this smoke test.")
        else:
            out.append("Core path looks healthy. If bot still silent, open chat with bot and press Start, then send /status.")
    return out


def print_report(checks: list[CheckResult], suggestions: list[str]) -> None:
    print("== Telegram Self-Check ==")
    for c in checks:
        mark = check_status_label(c)
        print(f"[{mark}] {c.name}: {c.detail}")
    print("\nSuggestions:")
    for item in suggestions:
        print(f"- {item}")


if __name__ == "__main__":
    raise SystemExit(main())
