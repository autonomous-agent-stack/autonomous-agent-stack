from __future__ import annotations

from autoresearch.core.services.standby_youtube_autoflow import (
    extract_urls_from_text,
    extract_youtube_urls_from_text,
)


def _classify_telegram_youtube_ingress(text: str) -> tuple[str, str | None, str | None]:
    normalized_text = text.strip()
    if not normalized_text:
        return ("skip", None, None)

    all_urls = extract_urls_from_text(normalized_text)
    youtube_urls = extract_youtube_urls_from_text(normalized_text)
    has_youtube_hint = "youtu" in normalized_text.lower()

    if not all_urls:
        if has_youtube_hint:
            return ("reject", None, "未找到合法的 YouTube URL。")
        return ("skip", None, None)

    if len(all_urls) > 1:
        if youtube_urls or has_youtube_hint:
            return ("reject", None, "当前只支持每条消息提交 1 条 YouTube 链接。")
        return ("skip", None, None)

    only_url = all_urls[0]
    if len(youtube_urls) == 1 and youtube_urls[0] == only_url:
        return ("accept", only_url, None)
    if has_youtube_hint:
        return ("reject", None, "消息里必须只包含 1 条合法的 YouTube URL。")
    return ("skip", None, None)
