"""Panel Audit Services.

Provides two audit services:
1. PanelAuditService: Original service for manual intervention events
2. PanelAuditLogger: SQLite-based logger for group access attempts
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import logging

from autoresearch.shared.models import PanelAuditLogRead, utc_now
from autoresearch.shared.store import Repository, create_resource_id

logger = logging.getLogger(__name__)


# ============================================================================
# Original PanelAuditService (for manual intervention events)
# ============================================================================


class PanelAuditService:
    """Persist panel manual intervention events for zero-trust auditing."""

    def __init__(self, repository: Repository[PanelAuditLogRead]) -> None:
        self._repository = repository

    def log_action(
        self,
        *,
        telegram_uid: str,
        action: str,
        target_id: str,
        target_type: str = "agent_run",
        status: str = "accepted",
        reason: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PanelAuditLogRead:
        now = utc_now()
        entry = PanelAuditLogRead(
            audit_id=create_resource_id("audit"),
            telegram_uid=telegram_uid,
            action=action,
            target_type=target_type,
            target_id=target_id,
            status=status,
            reason=reason,
            request_ip=request_ip,
            user_agent=user_agent,
            metadata=metadata or {},
            created_at=now,
        )
        return self._repository.save(entry.audit_id, entry)

    def list_by_uid(self, telegram_uid: str, limit: int = 100) -> list[PanelAuditLogRead]:
        normalized_uid = telegram_uid.strip()
        if not normalized_uid:
            return []
        logs = [item for item in self._repository.list() if item.telegram_uid == normalized_uid]
        logs.sort(key=lambda item: item.created_at, reverse=True)
        return logs[: max(1, limit)]


# ============================================================================
# PanelAuditLogger (for group access attempts)
# ============================================================================


@dataclass(frozen=True)
class AuditLogEntry:
    """Audit log entry for group access."""

    timestamp: datetime
    user_id: int
    chat_id: int | None
    action: str
    status: str  # "success" or "unauthorized"
    reason: str | None
    ip_address: str | None
    user_agent: str | None


class PanelAuditLogger:
    """SQLite-based audit logger for panel access.

    Schema:
    - id: INTEGER PRIMARY KEY
    - timestamp: TEXT (ISO format)
    - user_id: INTEGER
    - chat_id: INTEGER (nullable)
    - action: TEXT
    - status: TEXT ("success" or "unauthorized")
    - reason: TEXT (nullable)
    - ip_address: TEXT (nullable)
    - user_agent: TEXT (nullable)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or self._get_default_db_path()
        self._ensure_table()

    def _get_default_db_path(self) -> str:
        """Get default database path."""
        # Check for custom audit database path from environment
        custom_path = os.getenv("AUTORESEARCH_AUDIT_DB_PATH")
        if custom_path:
            return custom_path

        # Use project directory or temp directory
        project_root = os.getenv("AUTORESEARCH_PROJECT_ROOT", "/tmp")
        db_dir = Path(project_root) / ".autoresearch" / "audit"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "panel_audit.db")

    def _ensure_table(self) -> None:
        """Create audit table if not exists."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS panel_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON panel_audit(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON panel_audit(timestamp)
        """)

        conn.commit()
        conn.close()

        logger.info(f"✅ 审计日志表已初始化: {self._db_path}")

    def log_access(
        self,
        *,
        user_id: int,
        chat_id: int | None = None,
        action: str = "panel_access",
        status: str = "success",
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log panel access attempt.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID (for group links)
            action: Action type (e.g., "panel_access", "magic_link_click")
            status: "success" or "unauthorized"
            reason: Reason for unauthorized access
            ip_address: Client IP address
            user_agent: Client user agent
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO panel_audit
            (timestamp, user_id, chat_id, action, status, reason, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, user_id, chat_id, action, status, reason, ip_address, user_agent))

        conn.commit()
        conn.close()

        logger.info(
            f"📝 审计日志: user={user_id}, chat={chat_id}, action={action}, status={status}"
        )

    def get_unauthorized_attempts(
        self,
        user_id: int | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Get unauthorized access attempts.

        Args:
            user_id: Filter by user ID (optional)
            since: Filter by timestamp (optional)
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        query = """
            SELECT timestamp, user_id, chat_id, action, status, reason, ip_address, user_agent
            FROM panel_audit
            WHERE status = 'unauthorized'
        """
        params: list[Any] = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if since is not None:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        entries = []
        for row in rows:
            entries.append(
                AuditLogEntry(
                    timestamp=datetime.fromisoformat(row[0]),
                    user_id=row[1],
                    chat_id=row[2],
                    action=row[3],
                    status=row[4],
                    reason=row[5],
                    ip_address=row[6],
                    user_agent=row[7],
                )
            )

        return entries

    def get_stats(self) -> dict[str, Any]:
        """Get audit statistics.

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Total entries
        cursor.execute("SELECT COUNT(*) FROM panel_audit")
        total = cursor.fetchone()[0]

        # Success entries
        cursor.execute("SELECT COUNT(*) FROM panel_audit WHERE status = 'success'")
        success = cursor.fetchone()[0]

        # Unauthorized entries
        cursor.execute("SELECT COUNT(*) FROM panel_audit WHERE status = 'unauthorized'")
        unauthorized = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total,
            "success": success,
            "unauthorized": unauthorized,
            "unauthorized_rate": unauthorized / total if total > 0 else 0.0,
        }
