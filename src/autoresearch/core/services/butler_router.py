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
    CONTEXT_STATUS = "context_status"
    UNKNOWN = "unknown"


class ButlerCanonicalTaskType:
    SOURCE_COLLECT = "source_collect.collect"
    YOUTUBE_AUTOFLOW = "youtube.autoflow"
    GITHUB_ISSUE_OPS = "github.issue_ops"
    GITHUB_PR_OPS = "github.pr_ops"
    EXCEL_COMMISSION = "excel.commission"
    SALES_FOLLOWUP = "sales.followup"
    DESIGN_ORDER_REVIEW = "design.order_review"
    PURCHASE_TASK = "purchase.task"
    HERMES_GENERAL = "hermes.general"
    CONTENT_KB_INGEST = "content_kb.ingest"
    BOOKMARK_ORGANIZE = "bookmark.organize"
    BUTLER_CONTEXT_STATUS = "butler.context_status"


class ButlerClassification(StrictModel):
    """Result of classifying a user message."""
    task_type: str = ButlerTaskType.UNKNOWN
    confidence: float = 0.0
    extracted_params: dict[str, Any] = {}


# Keyword maps for each task type — sourced from agents/butler_orchestrator/prompts/classify.md
_KEYWORD_MAP: dict[str, list[str]] = {
    ButlerTaskType.EXCEL_AUDIT: [
        "核对", "提成", "对账", "excel", "xlsx", "核算", "计算检查",
        "差异报告", "审计", "核查", "报表核对", "佣金", "commission",
    ],
    ButlerTaskType.GITHUB_ADMIN: [
        "仓库迁移", "盘点", "transfer", "collaborator", "仓库管理",
        "repo transfer", "协作者同步", "邀请接受", "github", "pull request", "pr",
        "issue", "checks", "review", "帮我看这个 pr", "看这个 pr",
    ],
    ButlerTaskType.CONTENT_KB: [
        "字幕入库", "知识库", "字幕分类", "索引", "subtitle",
        "知识整理", "内容分类",
    ],
    ButlerTaskType.BOOKMARK: [
        "书签", "收藏", "bookmark", "稍后读", "read later",
        "链接整理", "书签整理", "收藏夹", "收藏整理",
        # X / Twitter bookmarks curation (管家口语：「整理X书签」)
        "推特书签", "twitter bookmark", "twitter bookmarks",
        "x 书签", "x书签", "x bookmark", "x bookmarks",
    ],
    ButlerTaskType.YOUTUBE: [
        "youtube", "视频", "字幕下载", "字幕提取", "yt-dlp",
        "视频下载", "transcript", "视频转文字", "总结这个 youtube", "总结这个YouTube",
    ],
}

# Regex to detect file paths (xlsx, xls, csv)
_FILE_PATH_RE = re.compile(r'[\w/\-\\\.]+\.(?:xlsx?|csv)', re.IGNORECASE)

# Regex to detect URLs (bookmark links)
_URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)
_CONTEXT_PREVIOUS_MARKER = "上文 / Previous result:"
_CONTEXT_FOLLOWUP_MARKER = "追问 / Follow-up:"
_KB_LINE_RE = re.compile(
    r"(?:知识库\s*/\s*KB|KB|知识库)\s*[：:]\s*(?P<value>[^\n]+)",
    re.IGNORECASE,
)
_FILES_LINE_RE = re.compile(
    r"(?:文件\s*/\s*Files|Files|文件)\s*[：:]\s*(?P<value>[^\n]+)",
    re.IGNORECASE,
)


def _keyword_matches(text_lower: str, keyword_lower: str) -> bool:
    if keyword_lower.isascii() and keyword_lower.isalnum() and len(keyword_lower) <= 2:
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(keyword_lower)}(?![a-z0-9])",
                text_lower,
            )
        )
    return keyword_lower in text_lower


class ButlerIntentRouter:
    """Classify free-text messages to task types using keyword matching."""

    def __init__(self) -> None:
        self._keyword_map = _KEYWORD_MAP

    def classify(self, text: str) -> ButlerClassification:
        """Classify a user message.

        Returns the best-matching task type with confidence score.
        If no keywords match, returns UNKNOWN.
        """
        classification_text = _classification_text(text)
        previous_context = _previous_context_text(text)
        if _looks_like_context_status_question(classification_text):
            extracted = _context_status_params(previous_context, classification_text)
            return ButlerClassification(
                task_type=ButlerTaskType.CONTEXT_STATUS,
                confidence=1.0 if extracted.get("context_status_confirmed") else 0.72,
                extracted_params=extracted,
            )

        text_lower = classification_text.lower()
        scores: dict[str, int] = {}

        for task_type, keywords in self._keyword_map.items():
            score = sum(1 for kw in keywords if _keyword_matches(text_lower, kw.lower()))
            if score > 0:
                scores[task_type] = score

        if _looks_like_github_status_question(classification_text):
            scores.pop(ButlerTaskType.GITHUB_ADMIN, None)

        if not scores:
            urls = _URL_RE.findall(classification_text)
            extracted: dict[str, Any] = {}
            if urls:
                extracted["urls"] = urls
            return ButlerClassification(extracted_params=extracted)

        if ButlerTaskType.BOOKMARK in scores:
            best_type = ButlerTaskType.BOOKMARK
        else:
            best_type = max(scores, key=lambda t: scores[t])
        total = sum(scores.values())
        confidence = round(scores[best_type] / total, 2) if total > 0 else 0.0

        # Extract file paths
        file_paths = _FILE_PATH_RE.findall(classification_text)

        # Extract URLs
        urls = _URL_RE.findall(classification_text)

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


def _classification_text(text: str) -> str:
    """Use the actual follow-up for routing when Telegram prepended context."""
    normalized = str(text or "").strip()
    index = normalized.rfind(_CONTEXT_FOLLOWUP_MARKER)
    if index >= 0:
        followup = normalized[index + len(_CONTEXT_FOLLOWUP_MARKER) :].strip()
        if followup:
            return followup
    return normalized


def _previous_context_text(text: str) -> str:
    normalized = str(text or "").strip()
    previous_index = normalized.find(_CONTEXT_PREVIOUS_MARKER)
    followup_index = normalized.rfind(_CONTEXT_FOLLOWUP_MARKER)
    if previous_index < 0 or followup_index <= previous_index:
        return ""
    previous = normalized[previous_index + len(_CONTEXT_PREVIOUS_MARKER) : followup_index].strip()
    return previous


def _looks_like_github_status_question(text: str) -> bool:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    if "github" not in lowered:
        return False
    if "github.com/" in lowered or "git@github.com:" in lowered:
        return False
    question_tokens = ("?", "？", "么", "吗", "是否", "有没有", "done", "did it")
    status_tokens = (
        "了",
        "done",
        "整理到",
        "提交到",
        "推送到",
        "同步到",
        "pushed",
        "committed",
        "synced",
    )
    return any(token in normalized or token in lowered for token in question_tokens) and any(
        token in normalized or token in lowered for token in status_tokens
    )


def _looks_like_context_status_question(text: str) -> bool:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    if not normalized:
        return False
    if "github.com/" in lowered or "git@github.com:" in lowered:
        return False
    target_tokens = ("github", "知识库", "kb", "repo", "仓库")
    question_tokens = ("?", "？", "么", "吗", "是否", "有没有", "done", "did it")
    status_tokens = (
        "了",
        "done",
        "整理到",
        "提交到",
        "推送到",
        "同步到",
        "入库",
        "pushed",
        "committed",
        "synced",
        "saved",
    )
    return (
        any(token in normalized or token in lowered for token in target_tokens)
        and any(token in normalized or token in lowered for token in question_tokens)
        and any(token in normalized or token in lowered for token in status_tokens)
    )


def _context_status_params(previous_context: str, followup: str) -> dict[str, Any]:
    previous = str(previous_context or "").strip()
    kb_value = _extract_regex_value(_KB_LINE_RE, previous)
    files_value = _extract_regex_value(_FILES_LINE_RE, previous)
    kb_repo, kb_topic = _split_kb_value(kb_value)
    confirmed = bool(kb_repo or _previous_context_confirms_kb_sync(previous))
    if kb_repo and kb_topic:
        answer = (
            f"已从上一轮结果确认：整理结果已同步到 GitHub 知识库 {kb_repo}，主题 {kb_topic}。\n"
            f"Confirmed from the previous result: the organized output was synced to the GitHub knowledge base "
            f"{kb_repo} under topic {kb_topic}."
        )
    elif kb_repo:
        answer = (
            f"已从上一轮结果确认：整理结果已同步到 GitHub 知识库 {kb_repo}。\n"
            f"Confirmed from the previous result: the organized output was synced to the GitHub knowledge base "
            f"{kb_repo}."
        )
    elif confirmed:
        answer = (
            "已从上一轮结果确认：整理结果已同步到知识库。\n"
            "Confirmed from the previous result: the organized output was synced to the knowledge base."
        )
    else:
        answer = (
            "本地无法确认是否已经整理到 GitHub：上一轮结果里没有可解析的知识库/仓库同步记录。\n"
            "Unable to confirm locally whether it was organized to GitHub: the previous result has no parseable "
            "knowledge-base or repository sync record."
        )

    return {
        "context_status_kind": "knowledge_base_sync",
        "context_status_confirmed": confirmed,
        "context_status_answer": answer,
        "kb_repo": kb_repo,
        "kb_topic": kb_topic,
        "kb_files": _split_files_value(files_value),
        "previous_result_excerpt": previous[:1200],
        "followup_text": str(followup or "").strip(),
    }


def _extract_regex_value(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return match.group("value").strip()


def _split_kb_value(value: str) -> tuple[str | None, str | None]:
    normalized = " ".join(str(value or "").split()).strip()
    if not normalized:
        return None, None
    parts = [part.strip(" -") for part in re.split(r"\s*[·•]\s*", normalized, maxsplit=1)]
    if len(parts) >= 2:
        return parts[0] or None, parts[1] or None
    return normalized, None


def _split_files_value(value: str) -> list[str]:
    normalized = str(value or "").strip()
    if not normalized:
        return []
    return [
        item.strip()
        for item in re.split(r"[,，]\s*", normalized)
        if item.strip()
    ]


def _previous_context_confirms_kb_sync(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return any(
        token in normalized
        for token in (
            "已同步到知识库",
            "同步到知识库",
            "采集结果已同步",
            "知识库 / kb",
            "synced to the knowledge base",
            "synced into the knowledge base",
        )
    )


_CANONICAL_TO_LEGACY_TASK_TYPE: dict[str, str] = {
    ButlerCanonicalTaskType.SOURCE_COLLECT: ButlerTaskType.BOOKMARK,
    ButlerCanonicalTaskType.YOUTUBE_AUTOFLOW: ButlerTaskType.YOUTUBE,
    ButlerCanonicalTaskType.GITHUB_ISSUE_OPS: ButlerTaskType.GITHUB_ADMIN,
    ButlerCanonicalTaskType.GITHUB_PR_OPS: ButlerTaskType.GITHUB_ADMIN,
    ButlerCanonicalTaskType.EXCEL_COMMISSION: ButlerTaskType.EXCEL_AUDIT,
    ButlerCanonicalTaskType.SALES_FOLLOWUP: ButlerTaskType.UNKNOWN,
    ButlerCanonicalTaskType.DESIGN_ORDER_REVIEW: ButlerTaskType.UNKNOWN,
    ButlerCanonicalTaskType.PURCHASE_TASK: ButlerTaskType.UNKNOWN,
    ButlerCanonicalTaskType.HERMES_GENERAL: ButlerTaskType.UNKNOWN,
    ButlerCanonicalTaskType.CONTENT_KB_INGEST: ButlerTaskType.CONTENT_KB,
    ButlerCanonicalTaskType.BOOKMARK_ORGANIZE: ButlerTaskType.BOOKMARK,
    ButlerCanonicalTaskType.BUTLER_CONTEXT_STATUS: ButlerTaskType.CONTEXT_STATUS,
}


def normalize_butler_task_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _CANONICAL_TO_LEGACY_TASK_TYPE:
        return _CANONICAL_TO_LEGACY_TASK_TYPE[normalized]
    allowed = {
        ButlerTaskType.EXCEL_AUDIT,
        ButlerTaskType.GITHUB_ADMIN,
        ButlerTaskType.CONTENT_KB,
        ButlerTaskType.BOOKMARK,
        ButlerTaskType.YOUTUBE,
        ButlerTaskType.CONTEXT_STATUS,
        ButlerTaskType.UNKNOWN,
    }
    if normalized in allowed:
        return normalized
    raise ValueError(f"unsupported task_type: {value}")


def canonical_task_type_for(task_type: str, *, action: str | None = None) -> str:
    normalized_task_type = str(task_type or "").strip().lower()
    if normalized_task_type in _CANONICAL_TO_LEGACY_TASK_TYPE:
        return normalized_task_type
    legacy = normalize_butler_task_type(normalized_task_type)
    normalized_action = str(action or "").strip().lower()
    if legacy == ButlerTaskType.YOUTUBE:
        return ButlerCanonicalTaskType.YOUTUBE_AUTOFLOW
    if legacy == ButlerTaskType.GITHUB_ADMIN:
        if "pr" in normalized_action or "pull" in normalized_action:
            return ButlerCanonicalTaskType.GITHUB_PR_OPS
        return ButlerCanonicalTaskType.GITHUB_ISSUE_OPS
    if legacy == ButlerTaskType.EXCEL_AUDIT:
        return ButlerCanonicalTaskType.EXCEL_COMMISSION
    if legacy == ButlerTaskType.CONTENT_KB:
        return ButlerCanonicalTaskType.CONTENT_KB_INGEST
    if legacy == ButlerTaskType.BOOKMARK:
        return ButlerCanonicalTaskType.SOURCE_COLLECT
    if legacy == ButlerTaskType.CONTEXT_STATUS:
        return ButlerCanonicalTaskType.BUTLER_CONTEXT_STATUS
    return ButlerCanonicalTaskType.HERMES_GENERAL


def worker_task_type_for_canonical(canonical_task_type: str) -> str:
    normalized = str(canonical_task_type or "").strip().lower()
    if normalized == ButlerCanonicalTaskType.YOUTUBE_AUTOFLOW:
        return "youtube_autoflow"
    if normalized in {ButlerCanonicalTaskType.GITHUB_ISSUE_OPS, ButlerCanonicalTaskType.GITHUB_PR_OPS}:
        return "github_ops"
    if normalized == ButlerCanonicalTaskType.EXCEL_COMMISSION:
        return "excel_audit"
    if normalized == ButlerCanonicalTaskType.CONTENT_KB_INGEST:
        return "content_kb_ingest"
    if normalized == ButlerCanonicalTaskType.SOURCE_COLLECT:
        return "source_collect"
    if normalized == ButlerCanonicalTaskType.BUTLER_CONTEXT_STATUS:
        return "noop"
    return "claude_runtime"
