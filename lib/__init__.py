# lib module - Media processing utilities
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_LIB_DIR = Path(__file__).parent
_REPO_ROOT = _LIB_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.media_job_store import (
    MediaJobStore,
    JobStatus,
    SubtitleStatus,
    DownloadStatus,
    MediaJob,
)
from lib.media_archiver import MediaArchiver, ArchivedVideo

__all__ = [
    "MediaJobStore",
    "JobStatus",
    "SubtitleStatus",
    "DownloadStatus",
    "MediaJob",
    "MediaArchiver",
    "ArchivedVideo",
]
