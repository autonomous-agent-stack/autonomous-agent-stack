"""Local Markdown and SQLite archive for content knowledge items."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any

from content_kb.repo_selector import slugify


_URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
_COMMAND_RE = re.compile(
    r"^\s*(?:\$|>|\b(?:git|gh|python3?|pipx?|uv|npm|pnpm|yarn|make|docker|curl)\b)\s+",
    re.IGNORECASE,
)
_STEP_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\d+[.)]|step\s+\d+|first\b|then\b|next\b|finally\b|"
    r"首先|然后|接着|最后|步骤)",
    re.IGNORECASE,
)
_RISK_RE = re.compile(
    r"\b(risk|warning|caution|danger|break|failure|fail|blocked|unsafe)\b|风险|注意|警告|失败|阻断|危险",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class BookmarkEntry:
    url: str
    title: str = ""
    note: str = ""
    tags: tuple[str, ...] = ()
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "note": self.note,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeArchiveResult:
    item_id: str
    source_type: str
    title: str
    markdown_path: str
    relative_markdown_path: str
    sqlite_index_path: str
    transcript_path: str | None = None
    obsidian_path: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_type": self.source_type,
            "title": self.title,
            "markdown_path": self.markdown_path,
            "relative_markdown_path": self.relative_markdown_path,
            "sqlite_index_path": self.sqlite_index_path,
            "transcript_path": self.transcript_path,
            "obsidian_path": self.obsidian_path,
            "tags": list(self.tags),
            "metadata": self.metadata,
        }


class LocalKnowledgeArchive:
    """Write content summaries into a local Markdown vault plus a SQLite index."""

    def __init__(
        self,
        *,
        root: Path | str | None = None,
        sqlite_path: Path | str | None = None,
        obsidian_vault_path: Path | str | None = None,
        obsidian_subdir: str = "AAS Knowledge",
    ) -> None:
        self.root = Path(root).expanduser().resolve() if root else default_knowledge_root()
        self.sqlite_path = (
            Path(sqlite_path).expanduser().resolve()
            if sqlite_path
            else self.root / "knowledge.sqlite3"
        )
        self.obsidian_vault_path = (
            Path(obsidian_vault_path).expanduser().resolve()
            if obsidian_vault_path
            else _optional_path_from_env("OBSIDIAN_VAULT_PATH")
        )
        self.obsidian_subdir = obsidian_subdir.strip().strip("/") or "AAS Knowledge"

    def write_youtube(
        self,
        *,
        video_id: str,
        source_url: str,
        title: str | None,
        channel_title: str | None = None,
        description: str | None = None,
        published_at: datetime | None = None,
        digest_content: str,
        transcript_content: str | None = None,
        transcript_language: str | None = None,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        sync_obsidian: bool = False,
    ) -> KnowledgeArchiveResult:
        clean_title = (title or "").strip() or f"YouTube {video_id}"
        safe_video_id = _safe_token(video_id)
        published_date = published_at.date().isoformat() if published_at else date.today().isoformat()
        slug = slugify(clean_title) or safe_video_id
        relative = Path("youtube") / f"{published_date}-{safe_video_id}-{slug}.md"
        markdown_path = self._write_relative(relative, self._render_youtube_markdown(
            video_id=video_id,
            source_url=source_url,
            title=clean_title,
            channel_title=channel_title,
            description=description,
            published_at=published_at,
            digest_content=digest_content,
            transcript_language=transcript_language,
            requested_by=requested_by,
            metadata=metadata or {},
        ))

        transcript_path: Path | None = None
        if transcript_content and transcript_content.strip():
            transcript_relative = Path("youtube") / f"{published_date}-{safe_video_id}-{slug}.transcript.md"
            transcript_path = self._write_relative(
                transcript_relative,
                self._render_transcript_markdown(
                    title=clean_title,
                    source_url=source_url,
                    transcript_language=transcript_language,
                    transcript_content=transcript_content,
                ),
            )

        tags = tuple(_dedupe([*(_suggest_youtube_tags(clean_title, digest_content)), "YouTube"]))
        item_id = f"youtube:{video_id}"
        summary = _first_summary(digest_content)
        item_metadata = {
            **(metadata or {}),
            "video_id": video_id,
            "channel_title": channel_title,
            "published_at": published_at.isoformat() if published_at else None,
            "transcript_language": transcript_language,
            "transcript_path": str(transcript_path) if transcript_path else None,
        }
        self._index_item(
            item_id=item_id,
            source_type="youtube",
            source_url=source_url,
            title=clean_title,
            slug=slug,
            topic="youtube",
            path=markdown_path,
            summary=summary,
            tags=tags,
            metadata=item_metadata,
        )
        obsidian_path = self._sync_obsidian(relative, markdown_path) if sync_obsidian else None
        return KnowledgeArchiveResult(
            item_id=item_id,
            source_type="youtube",
            title=clean_title,
            markdown_path=str(markdown_path),
            relative_markdown_path=relative.as_posix(),
            sqlite_index_path=str(self.sqlite_path),
            transcript_path=str(transcript_path) if transcript_path else None,
            obsidian_path=str(obsidian_path) if obsidian_path else None,
            tags=tags,
            metadata=item_metadata,
        )

    def write_bookmarks(
        self,
        *,
        bookmarks: list[BookmarkEntry],
        title: str = "X bookmarks",
        source_type: str = "x_bookmarks",
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        sync_obsidian: bool = False,
    ) -> KnowledgeArchiveResult:
        if not bookmarks:
            raise ValueError("at least one bookmark is required")
        today = date.today().isoformat()
        digest_key = hashlib.sha1(
            "\n".join(item.url for item in bookmarks).encode("utf-8")
        ).hexdigest()[:12]
        clean_title = title.strip() or "X bookmarks"
        slug = slugify(clean_title) or "x-bookmarks"
        relative = Path("x-bookmarks") / f"{today}-{slug}-{digest_key}.md"
        markdown_path = self._write_relative(
            relative,
            self._render_bookmarks_markdown(
                title=clean_title,
                bookmarks=bookmarks,
                requested_by=requested_by,
                metadata=metadata or {},
            ),
        )

        tags = tuple(_dedupe(["X", "bookmarks", *[tag for item in bookmarks for tag in item.tags]]))
        item_id = f"{source_type}:{digest_key}"
        summary = f"{len(bookmarks)} bookmarks archived."
        collection_metadata = {
            **(metadata or {}),
            "bookmark_count": len(bookmarks),
            "requested_by": requested_by,
            "bookmarks": [item.as_dict() for item in bookmarks],
        }
        self._index_item(
            item_id=item_id,
            source_type=source_type,
            source_url=bookmarks[0].url,
            title=clean_title,
            slug=slug,
            topic="x-bookmarks",
            path=markdown_path,
            summary=summary,
            tags=tags,
            metadata=collection_metadata,
        )
        for item in bookmarks:
            self._index_item(
                item_id=f"{source_type}:url:{hashlib.sha1(item.url.encode('utf-8')).hexdigest()[:16]}",
                source_type=source_type,
                source_url=item.url,
                title=item.title or item.url,
                slug=slugify(item.title or item.url) or "bookmark",
                topic="x-bookmarks",
                path=markdown_path,
                summary=item.note,
                tags=tuple(_dedupe(["X", "bookmark", *item.tags])),
                metadata={**(metadata or {}), **item.as_dict(), "collection_item_id": item_id},
            )
        obsidian_path = self._sync_obsidian(relative, markdown_path) if sync_obsidian else None
        return KnowledgeArchiveResult(
            item_id=item_id,
            source_type=source_type,
            title=clean_title,
            markdown_path=str(markdown_path),
            relative_markdown_path=relative.as_posix(),
            sqlite_index_path=str(self.sqlite_path),
            obsidian_path=str(obsidian_path) if obsidian_path else None,
            tags=tags,
            metadata=collection_metadata,
        )

    def _render_youtube_markdown(
        self,
        *,
        video_id: str,
        source_url: str,
        title: str,
        channel_title: str | None,
        description: str | None,
        published_at: datetime | None,
        digest_content: str,
        transcript_language: str | None,
        requested_by: str | None,
        metadata: dict[str, Any],
    ) -> str:
        steps = _extract_matching_lines(digest_content, _STEP_RE, fallback_bullets=True)
        commands = _extract_commands(digest_content)
        risks = _extract_matching_lines(digest_content, _RISK_RE, fallback_bullets=False)
        frontmatter = {
            "title": title,
            "source_type": "youtube",
            "source_url": source_url,
            "video_id": video_id,
            "channel_title": channel_title,
            "published_at": published_at.isoformat() if published_at else None,
            "transcript_language": transcript_language,
            "requested_by": requested_by,
            "archived_at": datetime.now(timezone.utc).isoformat(),
        }
        lines = [_yaml_frontmatter(frontmatter), f"# {title}", ""]
        lines.extend(
            [
                "## 来源 / Source",
                "",
                f"- URL: {source_url}",
                f"- Video ID: `{video_id}`",
                f"- Channel: {channel_title or '(unknown)'}",
                f"- Published: {published_at.isoformat() if published_at else '(unknown)'}",
                "",
            ]
        )
        if description and description.strip():
            lines.extend(["## 描述 / Description", "", description.strip()[:2000], ""])
        lines.extend(["## 步骤 / Steps", "", *_list_or_empty(steps), ""])
        lines.extend(["## 命令 / Commands", "", *_list_or_empty(commands), ""])
        lines.extend(["## 风险 / Risks", "", *_list_or_empty(risks), ""])
        lines.extend(["## 摘要 / Digest", "", digest_content.strip(), ""])
        if metadata:
            lines.extend(
                [
                    "## 元数据 / Metadata",
                    "",
                    "```json",
                    json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
                    "```",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_transcript_markdown(
        *,
        title: str,
        source_url: str,
        transcript_language: str | None,
        transcript_content: str,
    ) -> str:
        return "\n".join(
            [
                _yaml_frontmatter(
                    {
                        "title": f"{title} transcript",
                        "source_type": "youtube_transcript",
                        "source_url": source_url,
                        "transcript_language": transcript_language,
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                f"# {title} Transcript",
                "",
                f"- URL: {source_url}",
                f"- Language: {transcript_language or '(unknown)'}",
                "",
                "## Transcript",
                "",
                transcript_content.strip(),
                "",
            ]
        )

    @staticmethod
    def _render_bookmarks_markdown(
        *,
        title: str,
        bookmarks: list[BookmarkEntry],
        requested_by: str | None,
        metadata: dict[str, Any],
    ) -> str:
        frontmatter = {
            "title": title,
            "source_type": "x_bookmarks",
            "bookmark_count": len(bookmarks),
            "requested_by": requested_by,
            "archived_at": datetime.now(timezone.utc).isoformat(),
        }
        lines = [_yaml_frontmatter(frontmatter), f"# {title}", ""]
        lines.extend(["## 概览 / Overview", "", f"- Count: {len(bookmarks)}", ""])
        lines.extend(["## 书签 / Bookmarks", ""])
        for idx, item in enumerate(bookmarks, start=1):
            display = item.title or item.url
            lines.extend([f"### {idx}. {display}", "", f"- URL: {item.url}"])
            if item.created_at:
                lines.append(f"- Created: {item.created_at}")
            if item.tags:
                lines.append(f"- Tags: {', '.join(item.tags)}")
            if item.note:
                lines.extend(["", item.note.strip()])
            lines.append("")
        if metadata:
            lines.extend(
                [
                    "## 元数据 / Metadata",
                    "",
                    "```json",
                    json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
                    "```",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def _write_relative(self, relative_path: Path, content: str) -> Path:
        target = (self.root / relative_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root not in target.parents and target != self.root:
            raise ValueError(f"refusing to write outside knowledge root: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def _sync_obsidian(self, relative_path: Path, source: Path) -> Path | None:
        if self.obsidian_vault_path is None:
            return None
        target = (self.obsidian_vault_path / self.obsidian_subdir / relative_path).resolve()
        if self.obsidian_vault_path.resolve() not in target.parents:
            raise ValueError(f"refusing to copy outside Obsidian vault: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def _index_item(
        self,
        *,
        item_id: str,
        source_type: str,
        source_url: str,
        title: str,
        slug: str,
        topic: str,
        path: Path,
        summary: str,
        tags: tuple[str, ...],
        metadata: dict[str, Any],
    ) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    item_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO knowledge_items (
                    item_id, source_type, source_url, title, slug, topic, path, summary,
                    tags_json, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    source_type=excluded.source_type,
                    source_url=excluded.source_url,
                    title=excluded.title,
                    slug=excluded.slug,
                    topic=excluded.topic,
                    path=excluded.path,
                    summary=excluded.summary,
                    tags_json=excluded.tags_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    item_id,
                    source_type,
                    source_url,
                    title,
                    slug,
                    topic,
                    str(path),
                    summary,
                    json.dumps(list(tags), ensure_ascii=False),
                    json.dumps(metadata, ensure_ascii=False, default=str),
                    now,
                    now,
                ),
            )


def default_knowledge_root() -> Path:
    raw = os.getenv("AUTORESEARCH_KNOWLEDGE_ROOT") or os.getenv("AAS_KNOWLEDGE_ROOT")
    if raw and raw.strip():
        return Path(raw).expanduser().resolve()
    return (Path.home() / "aas" / "data" / "knowledge").resolve()


def parse_bookmark_entries(
    *,
    text: str = "",
    items: list[dict[str, Any]] | None = None,
    bookmarks_path: str | Path | None = None,
) -> list[BookmarkEntry]:
    parsed: list[BookmarkEntry] = []
    if items:
        parsed.extend(_bookmark_entries_from_objects(items))
    if bookmarks_path:
        parsed.extend(_bookmark_entries_from_file(Path(bookmarks_path).expanduser()))
    if text and text.strip():
        parsed.extend(_bookmark_entries_from_text(text))
    return _dedupe_bookmarks(parsed)


def _bookmark_entries_from_file(path: Path) -> list[BookmarkEntry]:
    if not path.exists():
        raise FileNotFoundError(f"bookmark file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            raw_items = payload.get("bookmarks") or payload.get("items") or payload.get("data") or []
        else:
            raw_items = payload
        if not isinstance(raw_items, list):
            raise ValueError("bookmark JSON must contain a list of bookmark objects")
        return _bookmark_entries_from_objects([item for item in raw_items if isinstance(item, dict)])
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            return _bookmark_entries_from_objects(list(csv.DictReader(handle, delimiter=delimiter)))
    return _bookmark_entries_from_text(path.read_text(encoding="utf-8"))


def _bookmark_entries_from_objects(items: list[dict[str, Any]]) -> list[BookmarkEntry]:
    entries: list[BookmarkEntry] = []
    for item in items:
        url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or item.get("text") or item.get("label") or "").strip()
        note = str(item.get("note") or item.get("description") or item.get("summary") or "").strip()
        tags = _normalize_tags(item.get("tags"))
        created_at = str(item.get("created_at") or item.get("created") or item.get("date") or "").strip()
        entries.append(BookmarkEntry(url=url, title=title, note=note, tags=tuple(tags), created_at=created_at))
    return entries


def _bookmark_entries_from_text(text: str) -> list[BookmarkEntry]:
    entries: list[BookmarkEntry] = []
    for line in text.splitlines():
        urls = _URL_RE.findall(line)
        for url in urls:
            title = line.replace(url, "").strip(" -:\t")
            entries.append(BookmarkEntry(url=url.rstrip(".,)"), title=title))
    if not entries:
        for url in _URL_RE.findall(text):
            entries.append(BookmarkEntry(url=url.rstrip(".,)")))
    return entries


def _dedupe_bookmarks(items: list[BookmarkEntry]) -> list[BookmarkEntry]:
    seen: set[str] = set()
    out: list[BookmarkEntry] = []
    for item in items:
        normalized_url = item.url.strip()
        if not normalized_url or normalized_url in seen:
            continue
        seen.add(normalized_url)
        out.append(item)
    return out


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re.split(r"[,#]", value)
    elif isinstance(value, (list, tuple, set)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]
    return _dedupe([item.strip() for item in raw_items if item.strip()])


def _extract_matching_lines(text: str, pattern: re.Pattern[str], *, fallback_bullets: bool) -> list[str]:
    matches: list[str] = []
    bullet_fallback: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if pattern.search(line):
            matches.append(_clean_list_line(line))
        elif fallback_bullets and line.startswith(("-", "*")):
            bullet_fallback.append(_clean_list_line(line))
    return _dedupe(matches or bullet_fallback[:8])


def _extract_commands(text: str) -> list[str]:
    commands: list[str] = []
    in_fence = False
    fence_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_fence and fence_lines:
                commands.extend(_dedupe(fence_lines))
                fence_lines = []
            in_fence = not in_fence
            continue
        if in_fence:
            if line.strip():
                fence_lines.append(line.strip())
            continue
        if _COMMAND_RE.search(line):
            commands.append(line.strip())
    return _dedupe(commands[:20])


def _first_summary(text: str) -> str:
    for raw_line in text.splitlines():
        line = _clean_list_line(raw_line.strip())
        if line and not line.startswith("#"):
            return line[:800]
    return text.strip()[:800]


def _suggest_youtube_tags(title: str, digest: str) -> list[str]:
    joined = f"{title}\n{digest}".lower()
    candidates = []
    for token, tag in (
        ("ai", "AI"),
        ("agent", "agent"),
        ("github", "GitHub"),
        ("workflow", "workflow"),
        ("python", "python"),
        ("coding", "coding"),
        ("字幕", "字幕"),
        ("摘要", "摘要"),
    ):
        if token in joined:
            candidates.append(tag)
    return candidates


def _yaml_frontmatter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if value is None:
            continue
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False, default=str)}")
    lines.append("---")
    return "\n".join(lines)


def _list_or_empty(items: list[str]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]


def _clean_list_line(line: str) -> str:
    return re.sub(r"^\s*[-*]\s+", "", line).strip()


def _safe_token(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return safe[:80] or hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _optional_path_from_env(name: str) -> Path | None:
    raw = os.getenv(name)
    if not raw or not raw.strip():
        return None
    return Path(raw).expanduser().resolve()
