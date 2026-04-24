"""Cross-process Telegram update_id dedup for webhook + long-poll bridge.

In-memory sets break under multiple uvicorn workers or duplicate forwards; SQLite
is shared with the API DB file so all handlers agree on first-seen semantics.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_DEDUP_LOCK = threading.Lock()
_TTL_SECONDS = 86400 * 3  # keep keys long enough for Telegram retries / poller overlap


def claim_first_telegram_update(db_path: Path, update_id: int) -> bool:
    """Return True if this update_id is new (claimed). False if already processed."""
    path = db_path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    cutoff = now - _TTL_SECONDS
    with _DEDUP_LOCK:
        conn = sqlite3.connect(path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_inbound_update_ids (
                    update_id INTEGER PRIMARY KEY,
                    seen_at REAL NOT NULL
                )
                """
            )
            if update_id % 61 == 0:
                conn.execute(
                    "DELETE FROM telegram_inbound_update_ids WHERE seen_at < ?",
                    (cutoff,),
                )
            conn.execute(
                "INSERT OR IGNORE INTO telegram_inbound_update_ids (update_id, seen_at) VALUES (?, ?)",
                (int(update_id), now),
            )
            row = conn.execute("SELECT changes()").fetchone()
            inserted = int(row[0]) if row and row[0] is not None else 0
            conn.commit()
            return inserted > 0
        finally:
            conn.close()
