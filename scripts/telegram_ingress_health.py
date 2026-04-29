#!/usr/bin/env python3
"""Telegram ingress health: 409 / conflict signals and Hermes runtime_id hit rate.

中文：扫描 OpenClaw 日志尾部与 worker 队列表，快速判断是否存在多消费者冲突，
并统计近期入队任务里 `runtime_id=hermes` 的占比。
English: Tail-scan OpenClaw logs and the worker queue table for multi-consumer conflicts
and recent `runtime_id=hermes` share.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "artifacts" / "api" / "evaluations.sqlite3"
LOG_DIR = ROOT / "migration" / "openclaw" / "logs"
STATUS_FILE = ROOT / "artifacts" / "api" / "telegram_ingress_status.json"
DEFAULT_LOGS = (
    LOG_DIR / "telegram-poller.log",
    LOG_DIR / "api.log",
)


def _tail_text(path: Path, max_bytes: int) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if len(data) <= max_bytes:
        return data.decode("utf-8", errors="replace")
    return data[-max_bytes:].decode("utf-8", errors="replace")


def _count_log_signals(text: str) -> dict[str, int]:
    lines = text.splitlines()
    out = {
        "lines_total": len(lines),
        "http_409": 0,
        "conflict_token": 0,
        "getupdates_hint": 0,
    }
    for line in lines:
        lower = line.lower()
        if "409" in line and ("conflict" in lower or "http error 409" in lower):
            out["http_409"] += 1
        if "conflict" in lower and ("telegram" in lower or "webhook" in lower or "poller" in lower):
            out["conflict_token"] += 1
        if "getupdates" in lower and ("409" in line or "conflict" in lower):
            out["getupdates_hint"] += 1
    return out


def _parse_updated_at(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _runtime_from_payload(payload_json: str) -> tuple[str | None, str | None]:
    try:
        outer: dict[str, Any] = json.loads(payload_json)
    except Exception:
        return None, None
    inner = outer.get("payload")
    if not isinstance(inner, dict):
        return None, None
    rid = inner.get("runtime_id")
    if isinstance(rid, str):
        return rid.strip().lower() or None, None
    return None, None


def _load_status_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram ingress conflict + Hermes routing audit")
    parser.add_argument(
        "--minutes",
        type=int,
        default=1440,
        help="Look-back window for queue rows (default 24h)",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite path (worker_run_queue)")
    parser.add_argument(
        "--log-tail-bytes",
        type=int,
        default=2_000_000,
        help="Bytes to read from the end of each log file",
    )
    parser.add_argument("--no-logs", action="store_true", help="Skip log tail scan")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, args.minutes))
    cutoff_iso = cutoff.isoformat()

    status = _load_status_file(STATUS_FILE)
    mode = str(status.get("mode") or "webhook")
    active_consumer = str(status.get("active_consumer") or "webhook")
    poller_state = str(status.get("state") or "unknown")
    poller_reason = str(status.get("reason") or "")

    log_stats_by_file: dict[str, dict[str, int]] = {}
    if not args.no_logs:
        for log_path in DEFAULT_LOGS:
            tail = _tail_text(log_path, args.log_tail_bytes)
            stats = _count_log_signals(tail)
            rel = log_path.relative_to(ROOT) if log_path.is_relative_to(ROOT) else log_path
            log_stats_by_file[str(rel)] = stats

    if not args.db.exists():
        summary = {
            "mode": mode,
            "active_consumer": active_consumer,
            "state": poller_state,
            "reason": "db_missing",
            "healthy": False,
            "conflict_signals": 0,
            "window_minutes": args.minutes,
            "queue_rows": 0,
            "runtime_counts": {},
            "runtime_unknown": 0,
            "hermes_share_pct": 0.0,
            "logs": log_stats_by_file,
            "status_source": str(STATUS_FILE.relative_to(ROOT) if STATUS_FILE.is_relative_to(ROOT) else STATUS_FILE),
            "db_path": str(args.db),
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        else:
            print(f"数据库缺失 | DB missing: {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    try:
        rows = conn.execute(
            """
            SELECT resource_id, payload_json, updated_at
            FROM worker_run_queue
            WHERE updated_at >= ?
            ORDER BY updated_at DESC
            """,
            (cutoff_iso,),
        ).fetchall()
    finally:
        conn.close()

    runtimes: Counter[str] = Counter()
    unknown = 0
    for _rid, payload_json, updated_at in rows:
        rt, _ = _runtime_from_payload(payload_json)
        if rt:
            runtimes[rt] += 1
        else:
            unknown += 1

    total_rt = sum(runtimes.values()) + unknown
    hermes_n = runtimes.get("hermes", 0)
    claude_n = runtimes.get("claude", 0)
    hermes_pct = round(100.0 * hermes_n / total_rt, 1) if total_rt else 0.0

    conflict_signals = sum(v.get("http_409", 0) + v.get("conflict_token", 0) for v in log_stats_by_file.values())
    healthy = poller_state not in {"error", "failover"} and conflict_signals == 0
    summary: dict[str, Any] = {
        "mode": mode,
        "active_consumer": active_consumer,
        "state": poller_state,
        "reason": poller_reason,
        "healthy": healthy,
        "conflict_signals": conflict_signals,
        "window_minutes": args.minutes,
        "queue_rows": len(rows),
        "runtime_counts": dict(runtimes),
        "runtime_unknown": unknown,
        "hermes_share_pct": hermes_pct,
        "logs": log_stats_by_file,
        "status_source": str(STATUS_FILE.relative_to(ROOT) if STATUS_FILE.is_relative_to(ROOT) else STATUS_FILE),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0 if healthy else 2

    print("Telegram 入口健康观测 | Telegram ingress health")
    print(f"时间窗口 | Window: last {args.minutes} minutes (cutoff UTC {cutoff_iso})")
    print(f"mode={mode} active_consumer={active_consumer} state={poller_state} healthy={healthy}")
    if poller_reason:
        print(f"reason={poller_reason}")
    if not args.no_logs:
        print("日志尾部信号（非零通常表示仍有抢更新风险）| Log tail signals")
        for file_name, stats in log_stats_by_file.items():
            print(f"  file: {file_name}")
            print(f"    lines_scanned: {stats['lines_total']}")
            print(f"    http_409_or_conflict_lines: {stats['http_409']}")
            print(f"    telegram_conflict_mentions: {stats['conflict_token']}")
            print(f"    getupdates_conflict_hints: {stats['getupdates_hint']}")
        print()
    print("worker_run_queue（时间窗口内行数）| worker_run_queue rows in window")
    print(f"  rows: {len(rows)}")
    print(f"  runtime_id=hermes: {hermes_n}")
    print(f"  runtime_id=claude: {claude_n}")
    print(f"  runtime_id unknown/missing: {unknown}")
    print(f"  Hermes 占比 | Hermes share: {hermes_pct}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
