from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .schema import (
    Company,
    EntertainmentCuratorRequest,
    EntertainmentCuratorResult,
    EntertainmentRecommendation,
    FocusLevel,
    Mood,
    NotebookLMPack,
)


_MOOD_ALIASES: tuple[tuple[tuple[str, ...], Mood], ...] = (
    (("学习", "资料", "研究", "notebooklm", "notebook lm", "ai", "商业", "纪录片"), "learning"),
    (("音乐", "听歌", "歌单", "陪伴", "睡前", "背景音"), "companion"),
    (("搞笑", "好笑", "脱口秀", "喜剧", "放松笑"), "funny"),
    (("刺激", "紧张", "悬疑", "动作", "惊悚"), "exciting"),
    (("周末", "混合", "安排", "计划"), "mixed"),
    (("放松", "休息", "轻松", "解压"), "relax"),
)
_COMPANY_ALIASES: tuple[tuple[tuple[str, ...], Company], ...] = (
    (("朋友", "同事", "聚会"), "friends"),
    (("老板", "客户", "商务"), "boss"),
    (("家人", "家庭", "父母", "孩子"), "family"),
    (("一个人", "自己", "solo", "alone"), "solo"),
)
_FOCUS_ALIASES: tuple[tuple[tuple[str, ...], FocusLevel], ...] = (
    (("高专注", "深度", "认真", "系统"), "high"),
    (("低专注", "轻松", "随便", "背景"), "low"),
)
_INTEREST_HINTS = (
    "电影",
    "音乐",
    "AI",
    "商业",
    "家具设计",
    "纪录片",
    "播客",
    "游戏",
    "学习",
    "设计",
    "创业",
)
_PIRACY_HINTS = (
    "盗版",
    "破解",
    "白嫖付费",
    "绕过付费",
    "绕过会员",
    "免费下载付费",
    "piracy",
    "crack",
    "bypass paywall",
    "paid bypass",
)
_TIME_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>分钟|分|小时|h|hr|hour|hours|min|mins)")


def parse_telegram_request(
    text: str,
    *,
    requested_by: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> EntertainmentCuratorRequest:
    normalized = _strip_entertain_command(text)
    lowered = normalized.lower()
    return EntertainmentCuratorRequest(
        mood=_detect_mood(normalized),
        time_available=_detect_time(normalized),
        interest=_detect_interests(normalized),
        focus_level=_detect_focus(lowered),
        company=_detect_company(normalized),
        channel="telegram",
        raw_text=normalized,
        requested_by=requested_by,
        metadata=dict(metadata or {}),
    )


def curate(request: EntertainmentCuratorRequest) -> EntertainmentCuratorResult:
    if request.channel != "telegram":
        raise ValueError("entertainment_curator is Telegram-only")

    sources = load_sources()
    boundary = str(sources.get("copyright_boundary") or _DEFAULT_COPYRIGHT_BOUNDARY)
    if _contains_piracy_intent(request.raw_text):
        return _rejected_result(request, boundary=boundary)

    recommendations = _build_recommendations(request)
    notebooklm_pack = _build_notebooklm_pack(request)
    title = _result_title(request)
    summary = _summary_for(request, recommendations)
    return EntertainmentCuratorResult(
        title=title,
        mood=request.mood,
        time_available=request.time_available,
        company=request.company,
        recommendations=recommendations,
        notebooklm_pack=notebooklm_pack,
        copyright_boundary=boundary,
        channel="telegram",
        account_profile={
            "youtube_music": "music recommendations prefer the read-only YouTube Premium/Music profile when authorized",
            "youtube_learning": "learning plans prefer the read-only YouTube/NotebookLM profile when authorized",
            "notebooklm": "learning plans provide manual source organization only",
        },
        status="completed",
        summary=summary,
    )


def load_sources() -> dict[str, Any]:
    path = Path(__file__).with_name("sources.yaml")
    text = path.read_text(encoding="utf-8")
    return {
        "copyright_boundary": _read_top_level_yaml_string(text, "copyright_boundary")
        or _DEFAULT_COPYRIGHT_BOUNDARY,
        "source_path": str(path),
    }


def _read_top_level_yaml_string(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(?P<value>.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    value = match.group("value").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _build_recommendations(request: EntertainmentCuratorRequest) -> list[EntertainmentRecommendation]:
    interests = _interest_text(request)
    total = _time_label(request.time_available)
    recs: list[EntertainmentRecommendation] = []

    if _music_first(request):
        recs.append(
            EntertainmentRecommendation(
                title="YouTube Music 情绪歌单",
                type="music",
                platform="YouTube Music",
                search_query=f"{interests} {request.mood} playlist YouTube Music",
                reason="你有 YouTube Premium/Music，音乐和陪伴场景优先用正常会员权益里的歌单、radio 和 mix。",
                alternative=f"{interests} acoustic live session YouTube",
                estimated_time=_slot(total, 0),
            )
        )

    if request.mood == "learning" or request.focus_level == "high":
        recs.append(
            EntertainmentRecommendation(
                title="学习视频主线",
                type="learning",
                platform="YouTube",
                search_query=f"{interests} lecture documentary explainer official",
                reason="先找公开课程、官方演讲或纪录片片段，再把优质来源手动整理进 NotebookLM。",
                alternative=f"{interests} podcast interview deep dive",
                estimated_time=_slot(total, len(recs)),
            )
        )
        recs.append(
            EntertainmentRecommendation(
                title="Podcast 补充视角",
                type="podcast",
                platform="Podcast RSS",
                search_query=f"{interests} podcast interview 2026",
                reason="播客适合补足案例、人物观点和行业语境，后续可作为 NotebookLM 的资料源。",
                alternative=f"{interests} panel discussion YouTube",
                estimated_time=_slot(total, len(recs)),
            )
        )
    elif request.mood == "funny":
        recs.append(
            EntertainmentRecommendation(
                title="轻松喜剧片段",
                type="video",
                platform="YouTube",
                search_query=f"{interests} stand up comedy clean clips official",
                reason=_company_reason(request.company, "搞笑内容适合快速放松，也适合多人场景破冰。"),
                alternative=f"{interests} funny podcast highlights",
                estimated_time=_slot(total, len(recs)),
            )
        )
    elif request.mood == "exciting":
        recs.append(
            EntertainmentRecommendation(
                title="高张力观看清单",
                type="video",
                platform="YouTube",
                search_query=f"{interests} thriller documentary official trailer analysis",
                reason="刺激场景优先选择官方预告、幕后解析和纪录片，不碰未授权完整片源。",
                alternative=f"{interests} action game free itch.io",
                estimated_time=_slot(total, len(recs)),
            )
        )
    else:
        recs.append(
            EntertainmentRecommendation(
                title="轻量观看计划",
                type="video",
                platform="YouTube",
                search_query=f"{interests} relaxing documentary official",
                reason=_company_reason(request.company, "低负担视频适合休息时快速进入状态。"),
                alternative=f"{interests} public domain film Internet Archive",
                estimated_time=_slot(total, len(recs)),
            )
        )

    if _wants_reading_or_archive(request):
        recs.append(
            EntertainmentRecommendation(
                title="合法长内容替代",
                type="reading",
                platform="Project Gutenberg / Internet Archive",
                search_query=f"{interests} public domain collection",
                reason="需要电影或长内容时，优先选择公版或权利清晰的来源。",
                alternative=f"{interests} official YouTube channel documentary",
                estimated_time=_slot(total, len(recs)),
            )
        )

    if _wants_games(request):
        recs.append(
            EntertainmentRecommendation(
                title="独立小游戏候选",
                type="game",
                platform="itch.io",
                search_query=f"{interests} free indie game itch.io",
                reason="短时间娱乐可以用创作者发布的免费或自定价小游戏补充。",
                alternative=f"{interests} game design documentary YouTube",
                estimated_time=_slot(total, len(recs)),
            )
        )

    if len(recs) < 3:
        recs.append(
            EntertainmentRecommendation(
                title="备用播客/访谈",
                type="podcast",
                platform="Podcast RSS",
                search_query=f"{interests} conversation interview podcast",
                reason="当视频不合适时，播客能保持陪伴感，也适合后台听。",
                alternative=f"{interests} YouTube Music focus mix",
                estimated_time=_slot(total, len(recs)),
            )
        )

    return recs[:4]


def _build_notebooklm_pack(request: EntertainmentCuratorRequest) -> NotebookLMPack:
    interests = _interest_text(request)
    enabled = request.mood == "learning" or request.focus_level == "high" or _contains_any(
        " ".join(request.interest).lower(),
        ("ai", "商业", "纪录片", "学习", "资料", "研究"),
    )
    if not enabled:
        return NotebookLMPack(
            enabled=False,
            title="NotebookLM 暂不需要",
            workflow=["本次以娱乐/音乐计划为主；如果发现好资料，再手动加入 NotebookLM。"],
        )
    return NotebookLMPack(
        enabled=True,
        title=f"{interests} 学习资料包",
        sources_to_collect=[
            f"YouTube: {interests} lecture documentary official",
            f"Podcast: {interests} interview deep dive",
            f"Article/PDF: {interests} beginner guide case study",
        ],
        suggested_questions=[
            f"{interests} 这个主题的核心概念是什么？",
            "这些来源之间有哪些共识和分歧？",
            "给我整理一个 30 分钟复习提纲。",
        ],
        workflow=[
            "先人工筛 3-5 个官方、公开或自有资料源。",
            "把链接、PDF 或笔记手动加入 NotebookLM。",
            "用 suggested_questions 做摘要、对比和复习卡片。",
        ],
    )


def _rejected_result(request: EntertainmentCuratorRequest, *, boundary: str) -> EntertainmentCuratorResult:
    alternative = EntertainmentRecommendation(
        title="合法替代路线",
        type="legal_alternative",
        platform="YouTube / Internet Archive / Project Gutenberg",
        search_query=f"{_interest_text(request)} official free public domain",
        reason="请求里包含盗版、破解或绕过付费限制的意图，只能提供合法替代来源。",
        alternative=f"{_interest_text(request)} official channel YouTube",
        estimated_time=_time_label(request.time_available),
    )
    return EntertainmentCuratorResult(
        title="娱乐策划已切换到合法替代方案",
        mood=request.mood,
        time_available=request.time_available,
        company=request.company,
        recommendations=[alternative],
        notebooklm_pack=NotebookLMPack(enabled=False, title="版权边界触发，未生成资料包"),
        copyright_boundary=boundary,
        channel="telegram",
        account_profile={},
        status="rejected",
        summary="检测到盗版、破解或付费绕过诉求，已改为合法替代建议。",
    )


def _strip_entertain_command(text: str) -> str:
    normalized = " ".join(str(text or "").split())
    lowered = normalized.lower()
    if lowered == "/entertain":
        return "娱乐计划"
    if lowered.startswith("/entertain "):
        return normalized.split(" ", 1)[1].strip() or "娱乐计划"
    return normalized or "娱乐计划"


def _detect_mood(text: str) -> Mood:
    lowered = text.lower()
    for tokens, mood in _MOOD_ALIASES:
        if _contains_any(lowered, tokens):
            return mood
    return "relax"


def _detect_time(text: str) -> str:
    lowered = text.lower()
    if "周末" in text or "weekend" in lowered:
        return "周末"
    match = _TIME_RE.search(text)
    if not match:
        if "半小时" in text:
            return "30分钟"
        return "1小时"
    num = match.group("num").rstrip("0").rstrip(".")
    unit = match.group("unit").lower()
    if unit in {"小时", "h", "hr", "hour", "hours"}:
        return f"{num}小时"
    return f"{num}分钟"


def _detect_interests(text: str) -> list[str]:
    hits = [hint for hint in _INTEREST_HINTS if hint.lower() in text.lower()]
    if hits:
        return hits
    if text.strip() and text.strip() != "娱乐计划":
        return [text.strip()[:40]]
    return ["电影", "音乐"]


def _detect_focus(lowered: str) -> FocusLevel:
    for tokens, focus in _FOCUS_ALIASES:
        if _contains_any(lowered, tokens):
            return focus
    if _contains_any(lowered, ("学习", "资料", "研究", "notebooklm", "notebook lm")):
        return "high"
    return "medium"


def _detect_company(text: str) -> Company:
    lowered = text.lower()
    for tokens, company in _COMPANY_ALIASES:
        if _contains_any(lowered, tokens):
            return company
    return "solo"


def _contains_piracy_intent(text: str) -> bool:
    return _contains_any(str(text or "").lower(), _PIRACY_HINTS)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)


def _interest_text(request: EntertainmentCuratorRequest) -> str:
    return " ".join(request.interest[:3]) or "电影 音乐"


def _music_first(request: EntertainmentCuratorRequest) -> bool:
    interest_blob = " ".join(request.interest).lower()
    return request.mood in {"relax", "companion", "mixed"} or _contains_any(
        interest_blob,
        ("音乐", "歌单", "music"),
    )


def _wants_reading_or_archive(request: EntertainmentCuratorRequest) -> bool:
    blob = " ".join(request.interest).lower()
    return _contains_any(blob, ("电影", "纪录片", "学习", "书", "reading"))


def _wants_games(request: EntertainmentCuratorRequest) -> bool:
    return _contains_any(" ".join(request.interest).lower(), ("游戏", "game"))


def _time_label(value: str) -> str:
    return str(value or "1小时").strip() or "1小时"


def _slot(total: str, index: int) -> str:
    if total == "周末":
        return ("60-90分钟", "45-60分钟", "30-45分钟", "可选")[min(index, 3)]
    if "30" in total:
        return ("15分钟", "10分钟", "5分钟", "备用")[min(index, 3)]
    if "2小时" in total or "2h" in total.lower():
        return ("45分钟", "35分钟", "25分钟", "15分钟")[min(index, 3)]
    return ("30分钟", "20分钟", "10分钟", "备用")[min(index, 3)]


def _company_reason(company: Company, base: str) -> str:
    suffix = {
        "solo": "一个人时可以按精力随时切换。",
        "friends": "和朋友一起更适合低门槛、好接话的内容。",
        "boss": "和老板同场时优先选择安全、体面、可讨论的内容。",
        "family": "和家人一起时优先选择全年龄、节奏稳的内容。",
    }[company]
    return f"{base}{suffix}"


def _result_title(request: EntertainmentCuratorRequest) -> str:
    mood_label = {
        "relax": "放松",
        "funny": "搞笑",
        "exciting": "刺激",
        "learning": "学习",
        "companion": "陪伴",
        "mixed": "混合",
    }[request.mood]
    return f"{mood_label}娱乐策划 · {request.time_available}"


def _summary_for(
    request: EntertainmentCuratorRequest,
    recommendations: list[EntertainmentRecommendation],
) -> str:
    lead = recommendations[0].title if recommendations else "合法娱乐计划"
    return f"{request.time_available} 计划已生成，主线：{lead}。"


_DEFAULT_COPYRIGHT_BOUNDARY = (
    "Only recommend legal, official, public, free, or normal paid-account entitlements. "
    "Do not suggest piracy, cracks, or paid-platform bypasses."
)
