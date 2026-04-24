"""Butler intent router — classify free-text messages to task types.

Keyword-based classification (no LLM). Fast, deterministic, zero cost.
Routes to specialist agents based on detected intent.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ButlerTaskType:
    EXCEL_AUDIT = "excel_audit"
    GITHUB_ADMIN = "github_admin"
    CONTENT_KB = "content_kb"
    BOOKMARK = "bookmark"
    YOUTUBE = "youtube"
    UNKNOWN = "unknown"


class ButlerClassification(StrictModel):
    """Result of classifying a user message."""
    task_type: str = ButlerTaskType.UNKNOWN
    confidence: float = 0.0
    extracted_params: dict[str, Any] = {}


# Keyword maps for each task type — sourced from agents/butler_orchestrator/prompts/classify.md
_KEYWORD_MAP: dict[str, list[str]] = {
    ButlerTaskType.EXCEL_AUDIT: [
        "核对", "提成", "对账", "excel", "xlsx", "核算", "计算检查",
        "差异报告", "审计", "核查", "报表核对",
    ],
    ButlerTaskType.GITHUB_ADMIN: [
        "仓库迁移", "盘点", "transfer", "collaborator", "仓库管理",
        "repo transfer", "协作者同步", "邀请接受",
    ],
    ButlerTaskType.CONTENT_KB: [
        "字幕入库", "知识库", "字幕分类", "索引", "subtitle",
        "知识整理", "内容分类",
    ],
    ButlerTaskType.BOOKMARK: [
        "书签", "收藏", "bookmark", "稍后读", "read later",
        "链接整理", "书签整理", "收藏夹", "收藏整理",
    ],
    ButlerTaskType.YOUTUBE: [
        "youtube", "视频", "字幕下载", "字幕提取", "yt-dlp",
        "视频下载", "transcript", "视频转文字",
    ],
}

# Regex to detect file paths (xlsx, xls, csv)
_FILE_PATH_RE = re.compile(r'[\w/\-\\\.]+\.(?:xlsx?|csv)', re.IGNORECASE)

# Regex to detect URLs (bookmark links)
_URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)


class ButlerIntentRouter:
    """Classify free-text messages to task types using keyword matching."""

    def __init__(self) -> None:
        self._keyword_map = _KEYWORD_MAP

    def classify(self, text: str) -> ButlerClassification:
        """Classify a user message.

        Returns the best-matching task type with confidence score.
        If no keywords match, returns UNKNOWN.
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for task_type, keywords in self._keyword_map.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[task_type] = score

        if not scores:
            urls = _URL_RE.findall(text)
            extracted: dict[str, Any] = {}
            if urls:
                extracted["urls"] = urls
            return ButlerClassification(extracted_params=extracted)

        best_type = max(scores, key=lambda t: scores[t])
        total = sum(scores.values())
        confidence = round(scores[best_type] / total, 2) if total > 0 else 0.0

        # Extract file paths
        file_paths = _FILE_PATH_RE.findall(text)

        # Extract URLs
        urls = _URL_RE.findall(text)

        extracted_params: dict[str, Any] = {}
        if file_paths:
            extracted_params["attachments"] = file_paths
        if urls:
            extracted_params["urls"] = urls

        return ButlerClassification(
            task_type=best_type,
            confidence=confidence,
            extracted_params=extracted_params,
        )
