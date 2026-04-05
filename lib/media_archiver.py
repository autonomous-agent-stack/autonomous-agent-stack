#!/usr/bin/env python3
"""
Media Archiver - 归档态导出器

将 SQLite 运行态中的已完成任务导出为 Git 友好的文本格式。

目录结构：
    archive/
    ├── index.json           # 总索引
    ├── README.md            # 归档说明
    └── youtube/
        └── 2026/
            └── 2026-04-03-video-slug/
                ├── metadata.json
                ├── transcript.md
                └── assets.json

幂等性保证：
    - 同一个 job 重复导出时不会创建新目录
    - 不会重复追加 index.json
"""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from lib.media_job_store import MediaJobStore, MediaJob

# 默认归档目录（相对于项目根目录）
REPO_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_ARCHIVE_DIR = REPO_ROOT / "archive"


def slugify(text: str, max_length: int = 50) -> str:
    """将文本转换为 URL 友好的 slug"""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:max_length]


def extract_video_id(url: str) -> Optional[str]:
    """从 URL 提取视频 ID"""
    if "youtube.com" in url or "youtu.be" in url:
        parsed = urlparse(url)
        if "youtu.be" in url:
            return parsed.path.lstrip("/")
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]

    if "bilibili.com" in url:
        parsed = urlparse(url)
        match = re.search(r"BV\w+", parsed.path)
        if match:
            return match.group(0)
        match = re.search(r"av(\d+)", parsed.path)
        if match:
            return f"av{match.group(1)}"

    if "vimeo.com" in url:
        parsed = urlparse(url)
        return parsed.path.lstrip("/").split("/")[0]

    return None


def detect_platform(url: str) -> str:
    """检测视频平台"""
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "bilibili.com" in url:
        return "bilibili"
    if "vimeo.com" in url:
        return "vimeo"
    if "twitter.com" in url or "x.com" in url:
        return "twitter"
    if "twitch.tv" in url:
        return "twitch"
    return "other"


@dataclass
class ArchivedVideo:
    """归档的视频元数据"""
    id: str
    url: str
    platform: str
    title: Optional[str]
    slug: str
    archived_at: datetime
    subtitle_status: str
    download_status: str
    files: list
    source: str
    processed_at: Optional[datetime]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["archived_at"] = self.archived_at.isoformat()
        d["processed_at"] = self.processed_at.isoformat() if self.processed_at else None
        return d


class MediaArchiver:
    """媒体归档器 - 导出完成的任务到 Git 友好格式"""

    def __init__(
        self,
        store: Optional[MediaJobStore] = None,
        archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    ):
        self.store = store or MediaJobStore()
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _get_archive_path(self, platform: str, year: str, slug: str) -> Path:
        """获取归档目录路径"""
        return self.archive_dir / platform / year / slug

    def export_job(self, job: MediaJob, files: Optional[list] = None) -> Path:
        """
        导出单个任务到归档目录

        Args:
            job: 已完成的任务
            files: 相关文件列表

        Returns:
            归档目录路径
        """
        now = datetime.now()
        year = str(now.year)
        platform = detect_platform(job.url)
        video_id = extract_video_id(job.url) or str(job.id)

        metadata = json.loads(job.metadata_json) if job.metadata_json else {}
        title = metadata.get("title")

        if title:
            slug = f"{now.strftime('%Y-%m-%d')}-{slugify(title)}"
        else:
            slug = f"{now.strftime('%Y-%m-%d')}-{video_id}"

        archive_path = self._get_archive_path(platform, year, slug)
        archive_path.mkdir(parents=True, exist_ok=True)

        # 构建 metadata.json
        archived_video = ArchivedVideo(
            id=video_id,
            url=job.url,
            platform=platform,
            title=title,
            slug=slug,
            archived_at=now,
            subtitle_status=job.subtitle_status.value,
            download_status=job.download_status.value,
            files=files or [],
            source=job.source,
            processed_at=job.completed_at,
            error=job.error_reason,
        )

        (archive_path / "metadata.json").write_text(
            json.dumps(archived_video.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 创建 README.md
        if title:
            (archive_path / "README.md").write_text(
                self._generate_readme(archived_video),
                encoding="utf-8",
            )

        # 创建 assets.json
        assets = {
            "video_id": video_id,
            "url": job.url,
            "files": files or [],
            "total_size": sum(f.get("size", 0) for f in (files or [])),
        }
        (archive_path / "assets.json").write_text(
            json.dumps(assets, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return archive_path

    def _generate_readme(self, video: ArchivedVideo) -> str:
        """生成 README.md 内容"""
        lines = [
            f"# {video.title or video.id}",
            "",
            f"- **Platform**: {video.platform}",
            f"- **URL**: {video.url}",
            f"- **Archived**: {video.archived_at.strftime('%Y-%m-%d %H:%M')}",
            f"- **Subtitle**: {video.subtitle_status}",
            f"- **Download**: {video.download_status}",
            "",
        ]

        if video.files:
            lines.append("## Files\n")
            for f in video.files:
                lines.append(f"- `{f.get('name', 'unknown')}` ({f.get('size_human', '?')})")
            lines.append("")

        if video.error:
            lines.extend(["## Error", "", f"```", video.error, "```", ""])

        lines.extend(["---", "*Auto-generated by media-archiver*"])
        return "\n".join(lines)

    def update_index(self) -> dict:
        """更新总索引文件"""
        index_path = self.archive_dir / "index.json"
        entries = []

        for platform_dir in self.archive_dir.iterdir():
            if not platform_dir.is_dir() or platform_dir.name.startswith("."):
                continue

            for year_dir in platform_dir.iterdir():
                if not year_dir.is_dir():
                    continue

                for video_dir in year_dir.iterdir():
                    if not video_dir.is_dir():
                        continue

                    metadata_path = video_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        entries.append({
                            "path": str(video_dir.relative_to(self.archive_dir)),
                            "url": metadata.get("url"),
                            "title": metadata.get("title"),
                            "platform": metadata.get("platform"),
                            "archived_at": metadata.get("archived_at"),
                        })
                    except (json.JSONDecodeError, KeyError):
                        continue

        entries.sort(key=lambda x: x.get("archived_at", ""), reverse=True)

        index_data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "total": len(entries),
            "platforms": list(set(e["platform"] for e in entries if e.get("platform"))),
            "entries": entries,
        }

        index_path.write_text(
            json.dumps(index_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._update_archive_readme(index_data)
        return index_data

    def _update_archive_readme(self, index_data: dict):
        """更新归档 README.md"""
        readme_path = self.archive_dir / "README.md"

        lines = [
            "# Media Archive",
            "",
            f"Total entries: **{index_data['total']}**",
            f"Last updated: {index_data['updated_at'][:10]}",
            "",
            "## Platforms",
            "",
        ]

        for platform in sorted(index_data.get("platforms", [])):
            count = sum(1 for e in index_data["entries"] if e.get("platform") == platform)
            lines.append(f"- **{platform}**: {count} entries")

        lines.extend(["", "## Recent Entries", ""])

        for entry in index_data["entries"][:20]:
            title = entry.get("title") or entry.get("url", "Unknown")
            path = entry.get("path", "")
            lines.append(f"- [{title[:60]}]({path})")

        lines.extend(["", "---", "*Auto-generated by media-archiver*"])
        readme_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    # 测试
    store = MediaJobStore()
    archiver = MediaArchiver(store=store)
    print(f"Archive dir: {archiver.archive_dir}")
