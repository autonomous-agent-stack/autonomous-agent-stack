#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
FALLBACK_PORT = 8011
SMOKE_WORKER_ID = "cpv2-smoke-worker"
SMOKE_CHAT_ID = "880100"
SMOKE_YOUTUBE_URL = "https://www.youtube.com/watch?v=6yjJ7Prt-RI"


class SmokeFailure(RuntimeError):
    pass


def _json_dumps(value: Any, *, compact: bool = False) -> str:
    kwargs = {"ensure_ascii": False, "sort_keys": True}
    if compact:
        kwargs["separators"] = (",", ":")
    return json.dumps(value, **kwargs)


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _select_port(host: str, preferred: int, fallback: int) -> int:
    for port in (preferred, fallback):
        if _port_available(host, port):
            return port
    raise SmokeFailure(f"no free smoke API port: {preferred}, {fallback}")


def _api_env(*, db_path: Path, host: str, port: int) -> dict[str, str]:
    env = dict(os.environ)
    pythonpath = str(SRC)
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env.update(
        {
            "PYTHONPATH": pythonpath,
            "AUTORESEARCH_MODE": "minimal",
            "AUTORESEARCH_ENV": "development",
            "ENVIRONMENT": "development",
            "AUTORESEARCH_API_HOST": host,
            "AUTORESEARCH_API_PORT": str(port),
            "AUTORESEARCH_API_DB_PATH": str(db_path),
            "AUTORESEARCH_TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_BOT_TOKEN": "",
            "AUTORESEARCH_TELEGRAM_SECRET_TOKEN": "",
            "AUTORESEARCH_TELEGRAM_ALLOWED_UIDS": "[]",
            "AUTORESEARCH_TELEGRAM_OWNER_UIDS": "[]",
            "AUTORESEARCH_TELEGRAM_PARTNER_UIDS": "[]",
            "AUTORESEARCH_INTERNAL_GROUPS": "[]",
            "AUTORESEARCH_TELEGRAM_BOT_USERNAMES": "",
            "AUTORESEARCH_BUTLER_MODEL_FILL_ENABLED": "",
        }
    )
    return env


def _request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    expected_status: set[int] | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    expected = expected_status or {200}
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = _json_dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeFailure(f"{method} {path} returned {exc.code}: {body[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"{method} {path} failed: {exc}") from exc
    if status not in expected:
        raise SmokeFailure(f"{method} {path} returned {status}: {body[:1000]}")
    if not body.strip():
        return {}
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"{method} {path} returned non-JSON: {body[:1000]}") from exc
    if not isinstance(decoded, dict):
        raise SmokeFailure(f"{method} {path} returned non-object JSON")
    return decoded


def _wait_for_health(*, base_url: str, process: subprocess.Popen, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SmokeFailure(f"API process exited before healthy: code={process.returncode}")
        try:
            _request_json(base_url=base_url, method="GET", path="/health", timeout_seconds=2.0)
            return
        except SmokeFailure:
            time.sleep(0.4)
    raise SmokeFailure(f"API did not become healthy at {base_url}/health")


def _telegram_message(*, update_id: int, text: str) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id + 100,
            "text": text,
            "chat": {"id": int(SMOKE_CHAT_ID), "type": "private"},
            "from": {"id": int(SMOKE_CHAT_ID), "username": "cpv2-smoke"},
        },
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _event_types(timeline: dict[str, Any]) -> list[str]:
    events = timeline.get("events")
    _require(isinstance(events, list), "timeline payload missing events")
    return [str(event.get("event_type")) for event in events if isinstance(event, dict)]


def _tail(path: Path, *, lines: int = 80) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def _terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=8)


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    host = args.host
    port = args.port or _select_port(host, DEFAULT_PORT, FALLBACK_PORT)
    base_url = f"http://{host}:{port}"
    started_at = time.time()
    process: subprocess.Popen | None = None

    with tempfile.TemporaryDirectory(prefix="cpv2-smoke-") as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cpv2-smoke.sqlite3"
        api_log = tmp_path / "api.log"
        env = _api_env(db_path=db_path, host=host, port=port)
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "autoresearch.api.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        with api_log.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        try:
            _wait_for_health(
                base_url=base_url,
                process=process,
                timeout_seconds=args.startup_timeout_seconds,
            )
            _request_json(
                base_url=base_url,
                method="POST",
                path="/api/v1/workers/register",
                payload={
                    "worker_id": SMOKE_WORKER_ID,
                    "worker_type": "mac",
                    "host": host,
                    "mode": "active",
                    "role": "smoke",
                    "capabilities": ["youtube_autoflow", "noop"],
                    "metadata": {"source": "control_plane_v2_e2e_smoke"},
                },
            )
            approval_response = _request_json(
                base_url=base_url,
                method="POST",
                path="/api/v1/gateway/telegram/webhook",
                payload=_telegram_message(
                    update_id=710001,
                    text=f"Please process this video {SMOKE_YOUTUBE_URL}",
                ),
            )
            approval_meta = approval_response.get("metadata") or {}
            approval_id = str(approval_meta.get("approval_id") or "")
            task_id = str(approval_meta.get("control_plane_task_id") or "")
            session_id = str(approval_response.get("session_id") or "")
            _require(approval_response.get("accepted") is True, "Telegram approval webhook was not accepted")
            _require(approval_meta.get("status") == "awaiting_approval", "task did not await approval")
            _require(bool(approval_id), "approval_id missing")
            _require(bool(task_id), "control_plane_task_id missing")
            _require(bool(session_id), "session_id missing")

            approve_response = _request_json(
                base_url=base_url,
                method="POST",
                path="/api/v1/gateway/telegram/webhook",
                payload=_telegram_message(
                    update_id=710002,
                    text=f"/approve {approval_id} approve",
                ),
            )
            approve_meta = approve_response.get("metadata") or {}
            run_id = str(approve_meta.get("run_id") or "")
            _require(approve_response.get("accepted") is True, "Telegram approve command was not accepted")
            _require(approve_meta.get("status") == "queued", "approved task was not queued")
            _require(bool(run_id), "run_id missing after approval")

            claim = _request_json(
                base_url=base_url,
                method="POST",
                path=f"/api/v1/workers/{SMOKE_WORKER_ID}/claim",
                payload={},
            )
            claimed_run = claim.get("run") or {}
            _require(claim.get("claimed") is True, "smoke worker did not claim work")
            _require(claimed_run.get("run_id") == run_id, "claimed run does not match approved v2 run")

            report = _request_json(
                base_url=base_url,
                method="POST",
                path=f"/api/v1/workers/{SMOKE_WORKER_ID}/runs/{run_id}/report",
                payload={
                    "status": "completed",
                    "message": "cpv2 smoke completed",
                    "result": {"summary": "cpv2 smoke completed", "smoke": True},
                    "metrics": {"smoke_steps": 5},
                },
            )
            _require(report.get("status") == "completed", "worker report did not complete")

            task = _request_json(base_url=base_url, method="GET", path=f"/api/v2/tasks/{task_id}")
            run = _request_json(base_url=base_url, method="GET", path=f"/api/v2/runs/{run_id}")
            worker_run = _request_json(base_url=base_url, method="GET", path=f"/api/v1/worker-runs/{run_id}")
            timeline = _request_json(
                base_url=base_url,
                method="GET",
                path=f"/api/v2/sessions/{session_id}/timeline",
            )

            _require(task.get("status") == "succeeded", "v2 task did not project succeeded")
            _require(run.get("status") == "succeeded", "v2 run did not project succeeded")
            events = _event_types(timeline)
            expected_events = {
                "approval.requested",
                "approval.approved",
                "run.queued",
                "worker.run.completed",
                "run.succeeded",
            }
            missing = sorted(expected_events.difference(events))
            _require(not missing, f"timeline missing events: {missing}")

            metadata = worker_run.get("metadata") or {}
            for key, expected in {
                "telegram_completion_via_api": True,
                "chat_id": SMOKE_CHAT_ID,
                "control_plane_task_id": task_id,
                "capability_id": "youtube_autoflow",
            }.items():
                _require(metadata.get(key) == expected, f"worker metadata mismatch: {key}")

            return {
                "status": "ok",
                "base_url": base_url,
                "port": port,
                "db_path": str(db_path),
                "session_id": session_id,
                "task_id": task_id,
                "approval_id": approval_id,
                "run_id": run_id,
                "task_status": task.get("status"),
                "run_status": run.get("status"),
                "timeline_events": events,
                "metadata_keys": sorted(metadata.keys()),
                "duration_seconds": round(time.time() - started_at, 3),
            }
        except Exception:
            log_tail = _tail(api_log)
            if log_tail:
                print("api_log_tail:", file=sys.stderr)
                print(log_tail, file=sys.stderr)
            raise
        finally:
            _terminate(process)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "运行 Control Plane v2 Telegram approval 到 worker terminal 的端到端 smoke。 "
            "Run a Control Plane v2 Telegram approval to worker terminal end-to-end smoke."
        )
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--startup-timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    try:
        summary = run_smoke(args)
    except SmokeFailure as exc:
        print(f"control-plane-v2-smoke failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"control-plane-v2-smoke raised: {exc}", file=sys.stderr)
        return 1
    print(_json_dumps(summary, compact=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
