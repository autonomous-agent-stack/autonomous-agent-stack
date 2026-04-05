#!/usr/bin/env python3
"""
Media Job Store - SQLite 运行态管理

两层架构的运行层：
- SQLite 管并发、状态、恢复
- 不进 Git，仅本地 runtime

Usage:
    from lib.media_job_store import MediaJobStore

    store = MediaJobStore()
    job_id = store.enqueue("https://youtube.com/watch?v=xxx", source="reach-agent")
    job = store.claim("media-agent-01")
    store.update(job_id, status="completed", subtitle_status="downloaded")
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# 默认 runtime 目录（相对于项目根目录）
REPO_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_RUNTIME_DIR = REPO_ROOT / ".masfactory_runtime"
DEFAULT_DB_PATH = DEFAULT_RUNTIME_DIR / "media_jobs.db"


class JobStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SubtitleStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    MISSING = "missing"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_REQUESTED = "not_requested"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class MediaJob:
    """媒体处理任务"""
    id: Optional[int]
    url: str
    source: str
    status: JobStatus
    claimed_by: Optional[str]
    retry_count: int
    max_retries: int
    subtitle_status: SubtitleStatus
    download_status: DownloadStatus
    error_reason: Optional[str]
    metadata_json: Optional[str]
    archive_status: Optional[str]
    archive_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    archived_at: Optional[datetime]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["subtitle_status"] = self.subtitle_status.value
        d["download_status"] = self.download_status.value
        d["created_at"] = self.created_at.isoformat() if self.created_at else None
        d["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        d["archived_at"] = self.archived_at.isoformat() if self.archived_at else None
        return d


class MediaJobStore:
    """
    媒体任务存储 - SQLite 后端

    特点：
    - 并发安全（使用 SQLite 的 ACID 特性）
    - 支持多 agent 并发 claim
    - 归档状态追踪（幂等导出）
    - 不进 Git（在 .gitignore 中排除）
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS media_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL DEFAULT 'unknown',
        status TEXT NOT NULL DEFAULT 'queued',
        claimed_by TEXT,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        subtitle_status TEXT DEFAULT 'pending',
        download_status TEXT DEFAULT 'pending',
        error_reason TEXT,
        metadata_json TEXT,
        archive_status TEXT DEFAULT 'pending',
        archive_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        archived_at TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_status ON media_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_url ON media_jobs(url);
    CREATE INDEX IF NOT EXISTS idx_archive_status ON media_jobs(archive_status);
    CREATE INDEX IF NOT EXISTS idx_completed_at ON media_jobs(completed_at);

    -- 归档表：已完成的任务移到这里
    CREATE TABLE IF NOT EXISTS media_jobs_archive (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL,
        source TEXT,
        status TEXT,
        claimed_by TEXT,
        retry_count INTEGER,
        max_retries INTEGER,
        subtitle_status TEXT,
        download_status TEXT,
        error_reason TEXT,
        metadata_json TEXT,
        archive_status TEXT,
        archive_path TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        completed_at TIMESTAMP,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_job(self, row: sqlite3.Row) -> MediaJob:
        """将数据库行转换为 MediaJob 对象"""
        return MediaJob(
            id=row["id"],
            url=row["url"],
            source=row["source"],
            status=JobStatus(row["status"]),
            claimed_by=row["claimed_by"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            subtitle_status=SubtitleStatus(row["subtitle_status"] or "pending"),
            download_status=DownloadStatus(row["download_status"] or "pending"),
            error_reason=row["error_reason"],
            metadata_json=row["metadata_json"],
            archive_status=row["archive_status"],
            archive_path=row["archive_path"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            archived_at=datetime.fromisoformat(row["archived_at"]) if row["archived_at"] else None,
        )

    def enqueue(
        self,
        url: str,
        source: str = "unknown",
        metadata: Optional[dict] = None,
        max_retries: int = 3,
    ) -> int:
        """将 URL 加入队列"""
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        with self._get_conn() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO media_jobs (url, source, metadata_json, max_retries, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (url, source, metadata_json, max_retries, now, now),
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor = conn.execute("SELECT id FROM media_jobs WHERE url = ?", (url,))
                row = cursor.fetchone()
                return row["id"] if row else -1

    def claim(self, agent_id: str, limit: int = 1) -> list[MediaJob]:
        """声索任务（原子操作）"""
        now = datetime.now().isoformat()

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE media_jobs
                SET status = 'claimed',
                    claimed_by = ?,
                    updated_at = ?
                WHERE id IN (
                    SELECT id FROM media_jobs
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    LIMIT ?
                )
                RETURNING *
                """,
                (agent_id, now, limit),
            )
            rows = cursor.fetchall()
            conn.commit()
            return [self._row_to_job(row) for row in rows]

    def get(self, job_id: int) -> Optional[MediaJob]:
        """获取单个任务"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM media_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return self._row_to_job(row) if row else None

    def get_by_url(self, url: str) -> Optional[MediaJob]:
        """通过 URL 获取任务"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM media_jobs WHERE url = ?", (url,))
            row = cursor.fetchone()
            return self._row_to_job(row) if row else None

    def update(
        self,
        job_id: int,
        status: Optional[JobStatus] = None,
        subtitle_status: Optional[SubtitleStatus] = None,
        download_status: Optional[DownloadStatus] = None,
        error_reason: Optional[str] = None,
        metadata: Optional[dict] = None,
        increment_retry: bool = False,
    ) -> bool:
        """更新任务状态"""
        now = datetime.now().isoformat()
        updates = ["updated_at = ?"]
        params = [now]

        if status:
            updates.append("status = ?")
            params.append(status.value)
            if status == JobStatus.COMPLETED:
                updates.append("completed_at = ?")
                params.append(now)

        if subtitle_status:
            updates.append("subtitle_status = ?")
            params.append(subtitle_status.value)

        if download_status:
            updates.append("download_status = ?")
            params.append(download_status.value)

        if error_reason:
            updates.append("error_reason = ?")
            params.append(error_reason)

        if metadata:
            updates.append("metadata_json = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))

        if increment_retry:
            updates.append("retry_count = retry_count + 1")

        params.append(job_id)

        with self._get_conn() as conn:
            cursor = conn.execute(
                f"UPDATE media_jobs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_completed_for_archive(self, limit: int = 100) -> list[MediaJob]:
        """
        获取待归档的已完成任务

        只返回 archive_status != 'exported' 的任务
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM media_jobs
                WHERE status = 'completed'
                AND completed_at IS NOT NULL
                AND (archive_status IS NULL OR archive_status != 'exported')
                ORDER BY completed_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            return [self._row_to_job(row) for row in cursor.fetchall()]

    def mark_exported(self, job_id: int, archive_path: str) -> bool:
        """
        标记任务已导出

        Args:
            job_id: 任务 ID
            archive_path: 归档路径

        Returns:
            是否更新成功
        """
        now = datetime.now()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE media_jobs
                SET archive_status = 'exported',
                    archive_path = ?,
                    archived_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (archive_path, now.isoformat(), now.isoformat(), job_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def stats(self) -> dict:
        """获取队列统计"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM media_jobs
                GROUP BY status
                """
            )
            return {row["status"]: row["count"] for row in cursor.fetchall()}


if __name__ == "__main__":
    # 简单测试
    store = MediaJobStore()
    job_id = store.enqueue("https://www.youtube.com/watch?v=test", source="test")
    print(f"Enqueued: {job_id}")
    print(f"Stats: {store.stats()}")
