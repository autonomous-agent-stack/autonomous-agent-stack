#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
POLLER_LOG = ROOT / "migration" / "openclaw" / "logs" / "telegram-poller.log"
POLLER_STATUS_SCRIPT = ROOT / "migration" / "openclaw" / "scripts" / "status-telegram-poller.sh"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Telegram reply path for local poller mode.")
    parser.add_argument("--port", type=int, default=8000)
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
    bot_token = env.get("AUTORESEARCH_TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or ""
    secret = env.get("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "")
    allowed_uids = [x.strip() for x in env.get("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "").split(",") if x.strip()]
    primary_uid = allowed_uids[0] if allowed_uids else ""

    checks.append(CheckResult("bot_token_env", bool(bot_token), "present" if bot_token else "missing"))
    checks.append(CheckResult("secret_env", bool(secret), "present" if secret else "missing (allowed only if webhook skips validation)"))
    checks.append(CheckResult("allowed_uid_env", bool(primary_uid), primary_uid or "missing"))

    status_url = f"http://127.0.0.1:{args.port}/api/v1/gateway/telegram/health"
    status_code, status_data, status_raw = http_json(status_url)
    checks.append(CheckResult("gateway_health", status_code == 200, f"status={status_code} body={status_data or status_raw}"))

    poller_ok = False
    poller_detail = "status script missing"
    if POLLER_STATUS_SCRIPT.exists():
        code, out = run_cmd(["bash", str(POLLER_STATUS_SCRIPT)])
        poller_ok = ("running" in out.lower()) and ("not running" not in out.lower())
        poller_detail = out.splitlines()[0] if out else f"exit={code}"
    checks.append(CheckResult("poller_process", poller_ok, poller_detail))

    recent_log = tail_lines(POLLER_LOG, max_lines=120)
    recent_errors = [ln for ln in recent_log if "error:" in ln.lower()]
    recent_404 = [ln for ln in recent_log if "404" in ln]
    recent_accept_false = [ln for ln in recent_log if "accepted=False" in ln]
    log_ok = not recent_errors[-10:] and not recent_404[-10:]
    log_detail = f"errors={len(recent_errors)} 404={len(recent_404)} accepted_false={len(recent_accept_false)}"
    checks.append(CheckResult("poller_log", log_ok, log_detail))

    if bot_token:
        tg_me_url = f"https://api.telegram.org/bot{bot_token}/getMe"
        code, data, raw = http_json(tg_me_url)
        checks.append(CheckResult("telegram_getMe", code == 200 and bool(data and data.get("ok")), f"status={code} body={data or raw}"))

    if bot_token and primary_uid and args.send_test:
        msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        code, data, raw = http_json(
            msg_url,
            method="POST",
            body={"chat_id": primary_uid, "text": f"[self-check] {time.strftime('%Y-%m-%d %H:%M:%S')}"},
        )
        checks.append(CheckResult("telegram_send_test", code == 200 and bool(data and data.get("ok")), f"status={code} body={data or raw}"))

    # Local webhook synthetic tests to expose "accepted/reason"
    if primary_uid:
        hdrs = {"x-telegram-bot-api-secret-token": secret} if secret else {}
        payload_ping = {
            "update_id": int(time.time()),
            "message": {
                "message_id": 1,
                "from": {"id": int(primary_uid), "username": "selfcheck"},
                "chat": {"id": int(primary_uid), "type": "private"},
                "date": int(time.time()),
                "text": "self-check ping",
            },
        }
        c1, d1, r1 = http_json(
            f"http://127.0.0.1:{args.port}/api/v1/gateway/telegram/webhook",
            method="POST",
            headers=hdrs,
            body=payload_ping,
        )
        ok1 = c1 == 200 and isinstance(d1, dict) and bool(d1.get("accepted"))
        checks.append(CheckResult("local_webhook_ping", ok1, f"status={c1} body={d1 or r1}"))

        payload_status = {
            "update_id": int(time.time()) + 1,
            "message": {
                "message_id": 2,
                "from": {"id": int(primary_uid), "username": "selfcheck"},
                "chat": {"id": int(primary_uid), "type": "private"},
                "date": int(time.time()),
                "text": "/status",
            },
        }
        c2, d2, r2 = http_json(
            f"http://127.0.0.1:{args.port}/api/v1/gateway/telegram/webhook",
            method="POST",
            headers=hdrs,
            body=payload_status,
        )
        ok2 = c2 == 200 and isinstance(d2, dict) and bool(d2.get("accepted"))
        checks.append(CheckResult("local_webhook_status", ok2, f"status={c2} body={d2 or r2}"))

    suggestions = build_suggestions(checks, recent_errors, recent_accept_false)
    print_report(checks, suggestions)
    return 0 if all(c.ok for c in checks if c.name not in {"poller_log"}) else 2


def build_suggestions(checks: list[CheckResult], errors: list[str], accepted_false: list[str]) -> list[str]:
    by_name = {c.name: c for c in checks}
    out: list[str] = []
    if not by_name.get("bot_token_env", CheckResult("", True, "")).ok:
        out.append("Set TELEGRAM_BOT_TOKEN and AUTORESEARCH_TELEGRAM_BOT_TOKEN in runtime env.")
    if not by_name.get("allowed_uid_env", CheckResult("", True, "")).ok:
        out.append("Set AUTORESEARCH_TELEGRAM_ALLOWED_UIDS to your Telegram user id.")
    if not by_name.get("poller_process", CheckResult("", True, "")).ok:
        out.append("Restart poller: bash migration/openclaw/scripts/stop-telegram-poller.sh && bash migration/openclaw/scripts/start-telegram-poller.sh")
    if by_name.get("gateway_health", CheckResult("", True, "")).detail.startswith("status=404"):
        out.append("Gateway route missing in current app. Ensure /api/v1/gateway/telegram/webhook is mounted.")
    if errors:
        if any("404" in x for x in errors):
            out.append("Poller target path mismatch. Check TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL.")
        if any("SSL" in x for x in errors):
            out.append("Network TLS instability to Telegram API. Retry later or check outbound network.")
    if accepted_false:
        out.append("Webhook accepted=False seen. Usually unsupported update type or empty message text.")
    if not out:
        out.append("Core path looks healthy. If bot still silent, open chat with bot and press Start, then send /status.")
    return out


def print_report(checks: list[CheckResult], suggestions: list[str]) -> None:
    print("== Telegram Self-Check ==")
    for c in checks:
        mark = "PASS" if c.ok else "FAIL"
        print(f"[{mark}] {c.name}: {c.detail}")
    print("\nSuggestions:")
    for item in suggestions:
        print(f"- {item}")


if __name__ == "__main__":
    raise SystemExit(main())
