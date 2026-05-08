from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from packages.study_workspace.workbench import StudyWorkbenchService
from autoresearch.shared.models import (
    JobStatus,
    StudyDashboardBriefRead,
    StudyDashboardDailyBriefRequest,
    StudyDashboardExportRead,
    StudyDashboardExportRequest,
    StudyDashboardExportTarget,
    StudyDashboardItemActionRead,
    StudyDashboardItemActionRequest,
    StudyDashboardItemRead,
    StudyDashboardItemStatus,
    StudyDashboardReadingDepth,
    StudyDashboardRefreshRead,
    StudyDashboardRefreshRequest,
    StudyDashboardSourceKind,
    StudyDashboardSourceStatusRead,
    StudyDashboardStateRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


JsonFetcher = Callable[[str, dict[str, str], float], dict[str, Any]]
TextFetcher = Callable[[str, dict[str, str], float], str]


@dataclass(frozen=True, slots=True)
class CollectedStudyItem:
    source_kind: StudyDashboardSourceKind
    source_key: str
    title: str
    summary: str = ""
    source_url: str = ""
    author: str = ""
    published_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class StudyDashboardError(RuntimeError):
    pass


class StudyDashboardService:
    def __init__(
        self,
        *,
        settings: Any,
        item_repository: Repository[StudyDashboardItemRead],
        brief_repository: Repository[StudyDashboardBriefRead],
        study_workbench: StudyWorkbenchService,
        artifact_root: Path,
        fetch_json: JsonFetcher | None = None,
        fetch_text: TextFetcher | None = None,
    ) -> None:
        self._settings = settings
        self._items = item_repository
        self._briefs = brief_repository
        self._study_workbench = study_workbench
        self._artifact_root = artifact_root.expanduser().resolve()
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        self._fetch_json = fetch_json or _fetch_json
        self._fetch_text = fetch_text or _fetch_text

    def state(self) -> StudyDashboardStateRead:
        items = self._visible_items()
        briefs = self._recent_briefs()
        sources = self._source_status_from_cache(items)
        status = "ok" if any(source.item_count for source in sources) else "degraded"
        return StudyDashboardStateRead(
            status=status,
            today=self._today_string(),
            sources=sources,
            items=items[:50],
            briefs=briefs,
            quick_actions=_quick_actions(),
            daily_schedule=self._daily_schedule(),
            generated_at=utc_now(),
            metadata={
                "default_entry": "pwa",
                "targets": ["goodnotes", "marginnote"],
                "source_limit": self._source_limit(),
            },
        )

    def refresh(self, request: StudyDashboardRefreshRequest | None = None) -> StudyDashboardRefreshRead:
        request = request or StudyDashboardRefreshRequest()
        include = set(request.include_sources or list(StudyDashboardSourceKind))
        source_limit = request.limit or self._source_limit()
        now = utc_now()
        statuses: list[StudyDashboardSourceStatusRead] = []
        collected: list[CollectedStudyItem] = []

        collectors: list[tuple[StudyDashboardSourceKind, Callable[[int], tuple[StudyDashboardSourceStatusRead, list[CollectedStudyItem]]]]] = [
            (StudyDashboardSourceKind.X_BOOKMARKS, self._collect_x_bookmarks),
            (StudyDashboardSourceKind.YOUTUBE_PLAYLIST, self._collect_youtube_playlist),
            (StudyDashboardSourceKind.RSS, self._collect_rss),
            (StudyDashboardSourceKind.LOCAL, self._collect_local_topics),
        ]
        for kind, collector in collectors:
            if kind not in include:
                continue
            status, items = collector(source_limit)
            statuses.append(status)
            collected.extend(items)

        existing = {item.source_key: item for item in self._items.list()}
        added = 0
        updated = 0
        skipped = 0
        saved: list[StudyDashboardItemRead] = []
        for item in collected:
            normalized = self._normalize_collected_item(item, now=now)
            previous = existing.get(normalized.source_key)
            if previous is None:
                self._items.save(normalized.item_id, normalized)
                saved.append(normalized)
                added += 1
                continue
            if request.force or _item_content_changed(previous, normalized):
                merged = normalized.model_copy(
                    update={
                        "item_id": previous.item_id,
                        "status": previous.status,
                        "created_at": previous.created_at,
                        "metadata": {**previous.metadata, **normalized.metadata},
                    }
                )
                self._items.save(merged.item_id, merged)
                saved.append(merged)
                updated += 1
            else:
                saved.append(previous)
                skipped += 1

        saved_sorted = sorted(saved, key=lambda item: (item.score, item.updated_at), reverse=True)
        return StudyDashboardRefreshRead(
            status=JobStatus.COMPLETED,
            sources=statuses,
            items=saved_sorted[:source_limit],
            added_count=added,
            updated_count=updated,
            skipped_count=skipped,
            created_at=now,
            metadata={"included_sources": [kind.value for kind in include]},
        )

    def create_daily_brief(
        self,
        request: StudyDashboardDailyBriefRequest | None = None,
    ) -> StudyDashboardBriefRead:
        request = request or StudyDashboardDailyBriefRequest()
        if request.auto_refresh:
            self.refresh(StudyDashboardRefreshRequest(limit=request.item_limit or self._source_limit()))

        selected = self._select_daily_items(limit=request.item_limit or self._daily_item_limit())
        if not selected:
            raise StudyDashboardError("study dashboard has no items to brief")

        now = utc_now()
        brief_id = create_resource_id("study_brief")
        title = request.title.strip() or f"今日技术手帐 {self._today_string()}"
        markdown = self._render_brief_markdown(brief_id=brief_id, title=title, items=selected, created_at=now)
        markdown_path = self._write_markdown_artifact(brief_id=brief_id, title=title, markdown=markdown)
        brief = StudyDashboardBriefRead(
            brief_id=brief_id,
            title=title,
            brief_date=self._today_string(),
            status=JobStatus.COMPLETED,
            item_ids=[item.item_id for item in selected],
            content_markdown=markdown,
            artifact_markdown_path=str(markdown_path),
            created_at=now,
            updated_at=now,
            metadata={
                "requested_by": request.requested_by,
                "targets": [target.value for target in request.targets],
            },
        )
        saved = self._briefs.save(brief.brief_id, brief)
        for item in selected:
            if item.status == StudyDashboardItemStatus.NEW:
                self._items.save(
                    item.item_id,
                    item.model_copy(update={"status": StudyDashboardItemStatus.UNREAD, "updated_at": now}),
                )
        return saved

    def export_brief(
        self,
        brief_id: str,
        request: StudyDashboardExportRequest | None = None,
    ) -> StudyDashboardExportRead:
        request = request or StudyDashboardExportRequest()
        brief = self._briefs.get(brief_id)
        if brief is None:
            raise KeyError(brief_id)

        now = utc_now()
        targets = _targets_for_export(request.target)
        prepared = self._study_workbench.prepare(
            {
                "title": brief.title,
                "markdown_text": brief.content_markdown,
                "targets": targets,
            }
        )
        copies = [
            dict(copy)
            for item in prepared.get("prepared", [])
            for copy in item.get("copies", [])
            if isinstance(copy, dict)
        ]
        pdf_paths = [
            str(item.get("artifact_pdf_path"))
            for item in prepared.get("prepared", [])
            if item.get("artifact_pdf_path")
        ]
        markdown_paths = [path for path in [brief.artifact_markdown_path] if path]
        if "marginnote" in targets:
            markdown_paths.extend(self._write_marginnote_sidecars(brief=brief, pdf_paths=pdf_paths))

        export_record = {
            "target": request.target.value,
            "requested_by": request.requested_by,
            "pdf_paths": pdf_paths,
            "markdown_paths": markdown_paths,
            "copies": copies,
            "created_at": now.isoformat(),
        }
        updated_brief = brief.model_copy(
            update={
                "artifact_pdf_path": pdf_paths[0] if pdf_paths else brief.artifact_pdf_path,
                "exports": [*brief.exports, export_record],
                "updated_at": now,
            }
        )
        updated_brief = self._briefs.save(updated_brief.brief_id, updated_brief)
        return StudyDashboardExportRead(
            brief=updated_brief,
            target=request.target,
            pdf_paths=pdf_paths,
            markdown_paths=markdown_paths,
            copies=copies,
            created_at=now,
            metadata={"prepared_count": prepared.get("prepared_count", 0)},
        )

    def apply_item_action(
        self,
        item_id: str,
        request: StudyDashboardItemActionRequest,
    ) -> StudyDashboardItemActionRead:
        item = self._items.get(item_id)
        if item is None:
            raise KeyError(item_id)
        now = utc_now()
        metadata = dict(item.metadata)
        artifacts: list[dict[str, Any]] = []
        status = item.status
        message = "updated"

        if request.action == "mark_read":
            status = StudyDashboardItemStatus.READ
            message = "marked read"
        elif request.action == "mark_annotated":
            status = StudyDashboardItemStatus.ANNOTATED
            message = "marked annotated"
        elif request.action == "mark_synthesized":
            status = StudyDashboardItemStatus.SYNTHESIZED
            message = "marked synthesized"
        elif request.action == "archive":
            status = StudyDashboardItemStatus.ARCHIVED
            message = "archived"
        elif request.action == "deep_dive":
            metadata["deep_dive_requested_at"] = now.isoformat()
            metadata["deep_dive_prompt"] = _deep_dive_prompt(item)
            artifacts.append({"kind": "prompt", "content": metadata["deep_dive_prompt"]})
            message = "deep dive prompt prepared"
        elif request.action == "generate_cards":
            cards = _flashcards_for_item(item)
            metadata["flashcards"] = cards
            artifacts.append({"kind": "flashcards", "items": cards})
            message = "flashcards prepared"
        elif request.action == "add_to_weekly":
            metadata["weekly_queue"] = True
            metadata["weekly_queued_at"] = now.isoformat()
            message = "added to weekly queue"

        updated = item.model_copy(
            update={
                "status": status,
                "updated_at": now,
                "metadata": {**metadata, **request.metadata},
            }
        )
        updated = self._items.save(updated.item_id, updated)
        return StudyDashboardItemActionRead(
            item=updated,
            action=request.action,
            message=message,
            artifacts=artifacts,
            created_at=now,
            metadata=request.metadata,
        )

    def _collect_x_bookmarks(self, limit: int) -> tuple[StudyDashboardSourceStatusRead, list[CollectedStudyItem]]:
        configured = bool(self._settings.x_user_id and self._settings.x_bearer_token)
        if not configured:
            return self._source_status(
                StudyDashboardSourceKind.X_BOOKMARKS,
                status="not_configured",
                configured=False,
                detail="X bookmark OAuth is not configured.",
            ), []

        params = urlencode(
            {
                "max_results": min(max(limit, 1), 100),
                "tweet.fields": "created_at,author_id,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "username,name",
            }
        )
        url = f"https://api.x.com/2/users/{self._settings.x_user_id}/bookmarks?{params}"
        try:
            payload = self._fetch_json(
                url,
                {"Authorization": f"Bearer {self._settings.x_bearer_token}"},
                self._timeout(),
            )
        except Exception as exc:
            return self._source_status(
                StudyDashboardSourceKind.X_BOOKMARKS,
                status="error",
                configured=True,
                detail=f"X bookmark request failed: {exc}",
            ), []
        items = parse_x_bookmark_items(payload)[:limit]
        return self._source_status(
            StudyDashboardSourceKind.X_BOOKMARKS,
            status="connected",
            configured=True,
            item_count=len(items),
            detail="X bookmarks refreshed.",
        ), items

    def _collect_youtube_playlist(
        self,
        limit: int,
    ) -> tuple[StudyDashboardSourceStatusRead, list[CollectedStudyItem]]:
        configured = bool(self._settings.youtube_api_key and self._settings.youtube_playlist_id)
        if not configured:
            return self._source_status(
                StudyDashboardSourceKind.YOUTUBE_PLAYLIST,
                status="not_configured",
                configured=False,
                detail="YouTube playlist API key or playlist id is not configured.",
            ), []

        params = urlencode(
            {
                "part": "snippet,contentDetails",
                "maxResults": min(max(limit, 1), 50),
                "playlistId": self._settings.youtube_playlist_id,
                "key": self._settings.youtube_api_key,
            }
        )
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?{params}"
        try:
            payload = self._fetch_json(url, {}, self._timeout())
        except Exception as exc:
            return self._source_status(
                StudyDashboardSourceKind.YOUTUBE_PLAYLIST,
                status="error",
                configured=True,
                detail=f"YouTube playlist request failed: {exc}",
            ), []
        items = parse_youtube_playlist_items(payload)[:limit]
        return self._source_status(
            StudyDashboardSourceKind.YOUTUBE_PLAYLIST,
            status="connected",
            configured=True,
            item_count=len(items),
            detail="Dedicated YouTube playlist refreshed.",
        ), items

    def _collect_rss(self, limit: int) -> tuple[StudyDashboardSourceStatusRead, list[CollectedStudyItem]]:
        urls = list(self._settings.rss_urls or [])
        if not urls:
            return self._source_status(
                StudyDashboardSourceKind.RSS,
                status="not_configured",
                configured=False,
                detail="RSS sources are not configured.",
            ), []
        items: list[CollectedStudyItem] = []
        errors: list[str] = []
        for url in urls:
            try:
                text = self._fetch_text(url, {}, self._timeout())
                items.extend(parse_rss_items(text, source_url=url))
            except Exception as exc:
                errors.append(f"{url}: {exc}")
        status = "connected" if items else "error"
        detail = "RSS sources refreshed." if items else "; ".join(errors)[:300]
        return self._source_status(
            StudyDashboardSourceKind.RSS,
            status=status,
            configured=True,
            item_count=len(items[:limit]),
            detail=detail,
            metadata={"errors": errors[:5]},
        ), items[:limit]

    def _collect_local_topics(self, limit: int) -> tuple[StudyDashboardSourceStatusRead, list[CollectedStudyItem]]:
        items = _local_study_topics()[:limit]
        return self._source_status(
            StudyDashboardSourceKind.LOCAL,
            status="connected",
            configured=True,
            item_count=len(items),
            detail="Local project learning topics are available.",
        ), items

    def _normalize_collected_item(self, item: CollectedStudyItem, *, now: datetime) -> StudyDashboardItemRead:
        title = _clean_text(item.title)[:180] or "Untitled study item"
        summary = _clean_text(item.summary)[:800]
        technologies = _extract_technologies(f"{title}\n{summary}")
        score = _score_item(source_kind=item.source_kind, title=title, summary=summary, technologies=technologies)
        depth = _reading_depth(score=score, technologies=technologies)
        source_key = f"{item.source_kind.value}:{item.source_key or _digest(title + item.source_url)}"
        return StudyDashboardItemRead(
            item_id=create_resource_id("study_item"),
            source_kind=item.source_kind,
            source_key=source_key,
            title=title,
            summary=summary,
            why_it_matters=_why_it_matters(technologies=technologies, source_kind=item.source_kind),
            technologies=technologies,
            source_url=item.source_url,
            author=item.author,
            published_at=item.published_at,
            reading_depth=depth,
            suggested_action=_suggested_action(depth=depth, source_kind=item.source_kind),
            status=StudyDashboardItemStatus.NEW,
            score=score,
            created_at=now,
            updated_at=now,
            metadata=item.metadata or {},
        )

    def _visible_items(self) -> list[StudyDashboardItemRead]:
        items = [item for item in self._items.list() if item.status != StudyDashboardItemStatus.ARCHIVED]
        return sorted(items, key=lambda item: (item.score, item.updated_at), reverse=True)

    def _recent_briefs(self) -> list[StudyDashboardBriefRead]:
        return sorted(self._briefs.list(), key=lambda brief: brief.updated_at, reverse=True)[:10]

    def _source_status_from_cache(self, items: list[StudyDashboardItemRead]) -> list[StudyDashboardSourceStatusRead]:
        counts = {kind: 0 for kind in StudyDashboardSourceKind}
        for item in items:
            counts[item.source_kind] += 1
        return [
            self._source_status(
                StudyDashboardSourceKind.X_BOOKMARKS,
                status="connected" if counts[StudyDashboardSourceKind.X_BOOKMARKS] else "not_configured",
                configured=bool(self._settings.x_user_id and self._settings.x_bearer_token),
                item_count=counts[StudyDashboardSourceKind.X_BOOKMARKS],
                detail="X bookmarks cached." if counts[StudyDashboardSourceKind.X_BOOKMARKS] else "X bookmark OAuth is not configured.",
            ),
            self._source_status(
                StudyDashboardSourceKind.YOUTUBE_PLAYLIST,
                status="connected" if counts[StudyDashboardSourceKind.YOUTUBE_PLAYLIST] else "not_configured",
                configured=bool(self._settings.youtube_api_key and self._settings.youtube_playlist_id),
                item_count=counts[StudyDashboardSourceKind.YOUTUBE_PLAYLIST],
                detail=(
                    "Dedicated YouTube playlist cached."
                    if counts[StudyDashboardSourceKind.YOUTUBE_PLAYLIST]
                    else "YouTube playlist API key or playlist id is not configured."
                ),
            ),
            self._source_status(
                StudyDashboardSourceKind.RSS,
                status="connected" if counts[StudyDashboardSourceKind.RSS] else "not_configured",
                configured=bool(self._settings.rss_urls),
                item_count=counts[StudyDashboardSourceKind.RSS],
                detail="RSS items cached." if counts[StudyDashboardSourceKind.RSS] else "RSS sources are not configured.",
            ),
            self._source_status(
                StudyDashboardSourceKind.LOCAL,
                status="connected",
                configured=True,
                item_count=counts[StudyDashboardSourceKind.LOCAL],
                detail="Local project learning topics are available.",
            ),
        ]

    def _select_daily_items(self, *, limit: int) -> list[StudyDashboardItemRead]:
        priority = {
            StudyDashboardItemStatus.NEW: 0,
            StudyDashboardItemStatus.UNREAD: 1,
            StudyDashboardItemStatus.READ: 2,
            StudyDashboardItemStatus.ANNOTATED: 3,
            StudyDashboardItemStatus.SYNTHESIZED: 4,
            StudyDashboardItemStatus.ARCHIVED: 99,
        }
        candidates = [
            item for item in self._items.list() if item.status != StudyDashboardItemStatus.ARCHIVED
        ]
        return sorted(candidates, key=lambda item: (priority[item.status], -item.score, item.updated_at))[:limit]

    def _render_brief_markdown(
        self,
        *,
        brief_id: str,
        title: str,
        items: list[StudyDashboardItemRead],
        created_at: datetime,
    ) -> str:
        lines = [
            "---",
            f"brief_id: {brief_id}",
            f"generated_at: {created_at.isoformat()}",
            "targets:",
            "  - goodnotes",
            "  - marginnote",
            "---",
            "",
            f"# {title}",
            "",
            "## 今日手帐",
            "- [ ] 先扫一遍今日必读",
            "- [ ] 给 1 个主题做手写批注",
            "- [ ] 选 1 个主题进 MarginNote4 深读",
            "- [ ] 生成 3 张复习卡片",
            "",
            "## 今日必读",
        ]
        for index, item in enumerate(items, start=1):
            source = f" [source]({item.source_url})" if item.source_url else ""
            video_line = (
                "- MarginNote4 video mode: import the video into a Study Set, keep this item_id on the note card."
                if item.source_kind == StudyDashboardSourceKind.YOUTUBE_PLAYLIST
                else ""
            )
            lines.extend(
                [
                    "",
                    f"### {index}. {item.title}",
                    f"<a id=\"item-{item.item_id}\"></a>",
                    f"- Depth: `{item.reading_depth.value}` | Score: `{item.score:.0f}` | Status: `{item.status.value}`",
                    f"- Source: `{item.source_kind.value}`{source}",
                    f"- Why: {item.why_it_matters}",
                    f"- Tech: {', '.join(item.technologies) if item.technologies else 'general'}",
                    f"- Action: {item.suggested_action}",
                    video_line,
                    "",
                    item.summary or "No summary yet.",
                    "",
                    "Notes:",
                    "",
                    "- ",
                    "- ",
                    "- ",
                ]
            )
        lines.extend(
            [
                "",
                "## MarginNote4 深读回链种子",
                "",
                "把 PDF 导入 MarginNote4 后，可用下面的条目 ID 对齐导出的笔记与 AAS 原始来源。",
            ]
        )
        for item in items:
            lines.append(f"- `{item.item_id}` -> `{item.source_url or item.source_key}`")
        lines.extend(["", "## 空白复盘", "", "- 今天最值得复用的技术判断：", "- 明天要补的一个缺口："])
        return "\n".join(lines).strip() + "\n"

    def _write_markdown_artifact(self, *, brief_id: str, title: str, markdown: str) -> Path:
        path = self._artifact_root / "briefs" / f"{_slugify(title)}-{brief_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return path

    def _write_marginnote_sidecars(self, *, brief: StudyDashboardBriefRead, pdf_paths: list[str]) -> list[str]:
        sidecar_text = _marginnote_sidecar(brief=brief, pdf_paths=pdf_paths)
        artifact_path = self._artifact_root / "marginnote" / f"{_slugify(brief.title)}-{brief.brief_id}.md"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(sidecar_text, encoding="utf-8")
        paths = [str(artifact_path)]
        inbox = getattr(self._study_workbench.settings, "marginnote_inbox_dir", None)
        if inbox is not None:
            inbox_path = Path(inbox).expanduser().resolve()
            inbox_path.mkdir(parents=True, exist_ok=True)
            copy_path = inbox_path / artifact_path.name
            shutil.copyfile(artifact_path, copy_path)
            paths.append(str(copy_path))
        return paths

    def _source_status(
        self,
        source_kind: StudyDashboardSourceKind,
        *,
        status: str,
        configured: bool,
        item_count: int = 0,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StudyDashboardSourceStatusRead:
        return StudyDashboardSourceStatusRead(
            source_kind=source_kind,
            status=status,  # type: ignore[arg-type]
            configured=configured,
            item_count=item_count,
            detail=detail,
            updated_at=utc_now(),
            metadata=metadata or {},
        )

    def _daily_schedule(self) -> dict[str, Any]:
        tz = _zoneinfo(self._settings.daily_timezone)
        now = datetime.now(tz)
        next_run = now.replace(hour=int(self._settings.daily_hour), minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return {
            "mode": "daily",
            "enabled": True,
            "local_time": f"{int(self._settings.daily_hour):02d}:00",
            "timezone": self._settings.daily_timezone,
            "next_run_at": next_run.isoformat(),
            "worker_task_type": "study_dashboard_daily",
            "schedule_payload": {"task_type": "study_dashboard_daily", "interval_seconds": 86400},
        }

    def _today_string(self) -> str:
        return datetime.now(_zoneinfo(self._settings.daily_timezone)).date().isoformat()

    def _source_limit(self) -> int:
        return int(getattr(self._settings, "source_limit", 20) or 20)

    def _daily_item_limit(self) -> int:
        return int(getattr(self._settings, "daily_item_limit", 8) or 8)

    def _timeout(self) -> float:
        return float(getattr(self._settings, "request_timeout_seconds", 10.0) or 10.0)


def parse_x_bookmark_items(payload: dict[str, Any]) -> list[CollectedStudyItem]:
    users = {
        str(user.get("id")): user
        for user in (payload.get("includes") or {}).get("users", [])
        if isinstance(user, dict)
    }
    items: list[CollectedStudyItem] = []
    for tweet in payload.get("data") or []:
        if not isinstance(tweet, dict):
            continue
        tweet_id = str(tweet.get("id") or "").strip()
        if not tweet_id:
            continue
        user = users.get(str(tweet.get("author_id"))) or {}
        username = str(user.get("username") or tweet.get("username") or tweet.get("author_id") or "").strip()
        text = _clean_text(str(tweet.get("text") or ""))
        expanded_urls = _expanded_urls(tweet)
        source_url = f"https://x.com/{username}/status/{tweet_id}" if username else ""
        items.append(
            CollectedStudyItem(
                source_kind=StudyDashboardSourceKind.X_BOOKMARKS,
                source_key=tweet_id,
                title=text[:120] or f"X bookmark {tweet_id}",
                summary=text,
                source_url=source_url,
                author=username,
                published_at=_parse_datetime(tweet.get("created_at")),
                metadata={"expanded_urls": expanded_urls, "public_metrics": tweet.get("public_metrics") or {}},
            )
        )
    return items


def parse_youtube_playlist_items(payload: dict[str, Any]) -> list[CollectedStudyItem]:
    items: list[CollectedStudyItem] = []
    for raw in payload.get("items") or []:
        if not isinstance(raw, dict):
            continue
        snippet = raw.get("snippet") if isinstance(raw.get("snippet"), dict) else {}
        content = raw.get("contentDetails") if isinstance(raw.get("contentDetails"), dict) else {}
        resource = snippet.get("resourceId") if isinstance(snippet.get("resourceId"), dict) else {}
        video_id = str(content.get("videoId") or resource.get("videoId") or "").strip()
        item_id = str(raw.get("id") or video_id or "").strip()
        if not item_id:
            continue
        title = _clean_text(str(snippet.get("title") or "YouTube study item"))
        description = _clean_text(str(snippet.get("description") or ""))
        items.append(
            CollectedStudyItem(
                source_kind=StudyDashboardSourceKind.YOUTUBE_PLAYLIST,
                source_key=video_id or item_id,
                title=title,
                summary=description[:800],
                source_url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                author=_clean_text(str(snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle") or "")),
                published_at=_parse_datetime(snippet.get("publishedAt") or content.get("videoPublishedAt")),
                metadata={"playlist_item_id": item_id, "video_id": video_id},
            )
        )
    return items


def parse_rss_items(text: str, *, source_url: str = "") -> list[CollectedStudyItem]:
    root = ET.fromstring(text)
    items: list[CollectedStudyItem] = []
    if root.tag.lower().endswith("feed"):
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry"):
            title = _xml_text(entry, "title")
            link = _atom_link(entry) or source_url
            updated = _xml_text(entry, "updated") or _xml_text(entry, "published")
            summary = _xml_text(entry, "summary") or _xml_text(entry, "content")
            key = _xml_text(entry, "id") or link or title
            items.append(
                CollectedStudyItem(
                    source_kind=StudyDashboardSourceKind.RSS,
                    source_key=_digest(key),
                    title=title,
                    summary=_strip_html(summary),
                    source_url=link,
                    published_at=_parse_datetime(updated),
                    metadata={"feed_url": source_url},
                )
            )
        return [item for item in items if item.title]

    for item in root.findall(".//item"):
        title = _xml_text(item, "title")
        link = _xml_text(item, "link") or source_url
        summary = _xml_text(item, "description") or _xml_text(item, "summary")
        published = _xml_text(item, "pubDate") or _xml_text(item, "published")
        guid = _xml_text(item, "guid") or link or title
        items.append(
            CollectedStudyItem(
                source_kind=StudyDashboardSourceKind.RSS,
                source_key=_digest(guid),
                title=title,
                summary=_strip_html(summary),
                source_url=link,
                published_at=_parse_datetime(published),
                metadata={"feed_url": source_url},
            )
        )
    return [item for item in items if item.title]


def _fetch_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", **headers})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured user sources only
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str, headers: dict[str, str], timeout: float) -> str:
    request = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, text/xml, */*", **headers})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured user sources only
        return response.read().decode("utf-8", errors="replace")


def _item_content_changed(previous: StudyDashboardItemRead, current: StudyDashboardItemRead) -> bool:
    return (
        previous.title != current.title
        or previous.summary != current.summary
        or previous.source_url != current.source_url
        or previous.score != current.score
    )


def _quick_actions() -> list[dict[str, str]]:
    return [
        {"id": "daily_brief", "label": "生成今日手帐", "icon": "notebook"},
        {"id": "export_goodnotes", "label": "导出 GoodNotes", "icon": "pen-line"},
        {"id": "export_marginnote", "label": "导出 MarginNote4", "icon": "network"},
        {"id": "deep_dive", "label": "深挖主题", "icon": "search"},
        {"id": "flashcards", "label": "生成卡片", "icon": "layers"},
        {"id": "mark_read", "label": "标记已读", "icon": "check"},
    ]


def _targets_for_export(target: StudyDashboardExportTarget) -> list[str]:
    if target == StudyDashboardExportTarget.GOODNOTES:
        return ["goodnotes"]
    if target == StudyDashboardExportTarget.MARGINNOTE:
        return ["marginnote"]
    return ["goodnotes", "marginnote"]


def _local_study_topics() -> list[CollectedStudyItem]:
    topics = [
        (
            "AAS Study Dashboard PWA",
            "Build the iPad command surface around daily briefs, source triage, and study export states.",
            "PWA, Next.js, FastAPI, SQLite",
        ),
        (
            "GoodNotes Daily PDF Workflow",
            "Use a daily PDF as the handwriting-first review surface, then ingest marked-up exports back to the review inbox.",
            "GoodNotes, PDF, OCR, review workflow",
        ),
        (
            "MarginNote4 Deep Reading Loop",
            "Keep source links and item identifiers beside the PDF so exported notes can be reconciled with AAS items.",
            "MarginNote4, deep links, knowledge graph, flashcards",
        ),
        (
            "Governed Agent Control Plane",
            "Durable task state, worker queues, approvals, and artifacts should stay in the control plane instead of the UI.",
            "AI Agent, MCP, approval, audit",
        ),
        (
            "YouTube Dedicated Playlist Intake",
            "Use a dedicated study playlist as the stable video intake path, then summarize transcripts into the knowledge base.",
            "YouTube API, transcript, content_kb, RAG",
        ),
    ]
    return [
        CollectedStudyItem(
            source_kind=StudyDashboardSourceKind.LOCAL,
            source_key=_slugify(title),
            title=title,
            summary=f"{summary} Topics: {tags}.",
            source_url="",
            metadata={"tags": tags.split(", ")},
        )
        for title, summary, tags in topics
    ]


def _extract_technologies(text: str) -> list[str]:
    candidates = [
        "AI Agent",
        "MCP",
        "RAG",
        "LLM",
        "FastAPI",
        "Next.js",
        "PWA",
        "SQLite",
        "YouTube API",
        "X API",
        "GoodNotes",
        "MarginNote4",
        "PDF",
        "OCR",
        "TypeScript",
        "Python",
        "OAuth",
        "knowledge graph",
        "flashcards",
    ]
    lowered = text.lower()
    found = [candidate for candidate in candidates if candidate.lower() in lowered]
    return found[:8]


def _score_item(
    *,
    source_kind: StudyDashboardSourceKind,
    title: str,
    summary: str,
    technologies: list[str],
) -> float:
    base = {
        StudyDashboardSourceKind.X_BOOKMARKS: 76,
        StudyDashboardSourceKind.YOUTUBE_PLAYLIST: 78,
        StudyDashboardSourceKind.RSS: 72,
        StudyDashboardSourceKind.LOCAL: 68,
    }[source_kind]
    text = f"{title}\n{summary}".lower()
    bonus = len(technologies) * 3
    if any(token in text for token in ("agent", "pwa", "mcp", "rag", "workflow", "study")):
        bonus += 8
    if any(token in text for token in ("release", "breaking", "paper", "guide", "tutorial")):
        bonus += 4
    return float(min(100, base + bonus))


def _reading_depth(*, score: float, technologies: list[str]) -> StudyDashboardReadingDepth:
    deep_terms = {"AI Agent", "MCP", "RAG", "knowledge graph", "MarginNote4"}
    if score >= 88 or any(term in deep_terms for term in technologies):
        return StudyDashboardReadingDepth.DEEP
    if score >= 74:
        return StudyDashboardReadingDepth.READ
    return StudyDashboardReadingDepth.SKIM


def _why_it_matters(*, technologies: list[str], source_kind: StudyDashboardSourceKind) -> str:
    if "MarginNote4" in technologies or "GoodNotes" in technologies:
        return "It directly improves the iPad study capture and review loop."
    if "AI Agent" in technologies or "MCP" in technologies:
        return "It can change how the governed agent stack routes tools, memory, and approvals."
    if source_kind == StudyDashboardSourceKind.YOUTUBE_PLAYLIST:
        return "It is already in the video study queue and should be turned into notes or cards."
    return "It is a candidate for the daily technical radar and weekly knowledge base."


def _suggested_action(*, depth: StudyDashboardReadingDepth, source_kind: StudyDashboardSourceKind) -> str:
    if depth == StudyDashboardReadingDepth.DEEP:
        return "Send to MarginNote4 for deep reading, then synthesize cards."
    if source_kind == StudyDashboardSourceKind.YOUTUBE_PLAYLIST:
        return "Watch once, extract transcript notes, and decide whether to keep."
    if depth == StudyDashboardReadingDepth.SKIM:
        return "Skim and archive unless it maps to an active project."
    return "Read, annotate in GoodNotes, and capture one reusable takeaway."


def _marginnote_sidecar(*, brief: StudyDashboardBriefRead, pdf_paths: list[str]) -> str:
    frontmatter = {
        "brief_id": brief.brief_id,
        "title": brief.title,
        "pdf_paths": pdf_paths,
        "created_at": brief.created_at.isoformat(),
        "link_strategy": "source links first; reconcile exported MarginNote links by item_id",
    }
    return (
        "---\n"
        + json.dumps(frontmatter, ensure_ascii=False, indent=2)
        + "\n---\n\n"
        + brief.content_markdown
    )


def _deep_dive_prompt(item: StudyDashboardItemRead) -> str:
    return (
        f"Deeply analyze this study item: {item.title}\n"
        f"Source: {item.source_url or item.source_key}\n"
        f"Focus on: {', '.join(item.technologies) or 'technical implications'}\n"
        "Return: core idea, implementation relevance, risks, and 3 follow-up reading tasks."
    )


def _flashcards_for_item(item: StudyDashboardItemRead) -> list[dict[str, str]]:
    cards = [
        {
            "front": f"What is the main point of {item.title}?",
            "back": item.summary[:240] or item.why_it_matters,
        },
        {
            "front": "Why does this matter?",
            "back": item.why_it_matters,
        },
    ]
    if item.technologies:
        cards.append({"front": "Which technologies are involved?", "back": ", ".join(item.technologies)})
    return cards


def _expanded_urls(tweet: dict[str, Any]) -> list[str]:
    entities = tweet.get("entities") if isinstance(tweet.get("entities"), dict) else {}
    urls = entities.get("urls") if isinstance(entities.get("urls"), list) else []
    return [str(item.get("expanded_url") or item.get("url") or "") for item in urls if isinstance(item, dict)]


def _xml_text(node: ET.Element, tag: str) -> str:
    found = node.find(tag)
    if found is None:
        found = node.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    if found is None or found.text is None:
        return ""
    return _clean_text(found.text)


def _atom_link(node: ET.Element) -> str:
    for link in node.findall("{http://www.w3.org/2005/Atom}link") or node.findall("link"):
        href = str(link.attrib.get("href") or "").strip()
        if href:
            return href
    return ""


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return _clean_text(" ".join(self.parts))


def _strip_html(value: str) -> str:
    parser = _HTMLStripper()
    parser.feed(value)
    return parser.text()


def _clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value.replace("\u200b", " ")).strip()
    return text


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "study"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _zoneinfo(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")
