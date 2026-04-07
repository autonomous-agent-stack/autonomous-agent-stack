"""Topic classifier — keyword-based classification for content_kb.

This is the deterministic fallback classifier. The primary classification
should be done by the LLM agent using the classify_topic prompt.
"""

from __future__ import annotations

from content_kb.contracts import (
    VALID_TOPICS,
    ContentTopic,
    TopicCandidate,
    TopicClassificationResult,
)

_KEYWORD_MAP: dict[str, list[str]] = {
    ContentTopic.AI_STATUS_AND_OUTLOOK.value: [
        "ai",
        "人工智能",
        "llm",
        "gpt",
        "claude",
        "模型",
        "大模型",
        "openai",
        "anthropic",
        "gemini",
        "deepseek",
        "transformer",
        "neural",
        "机器学习",
        "深度学习",
        "machine learning",
    ],
    ContentTopic.VIBE_CODING.value: [
        "vibe coding",
        "编程",
        "代码",
        "coding",
        "开发",
        "workflow",
        "ide",
        "copilot",
        "cursor",
        "vscode",
        "typescript",
        "python",
        "react",
        "框架",
        "调试",
        "部署",
    ],
    ContentTopic.ENTERTAINMENT_STANDUP.value: [
        "脱口秀",
        "standup",
        "搞笑",
        "综艺",
        "entertainment",
        "段子",
        "喜剧",
        "comedy",
        "幽默",
        "笑点",
    ],
    ContentTopic.FILM_TV_RECOMMENDATION.value: [
        "电影",
        "推荐",
        "剧集",
        "影视",
        "film",
        "movie",
        "电视剧",
        "netflix",
        "豆瓣",
        "评分",
        "导演",
        "actor",
        "演员",
    ],
    ContentTopic.ECONOMY.value: [
        "经济",
        "金融",
        "股市",
        "投资",
        "economy",
        "市场",
        "gdp",
        "通胀",
        "利率",
        "基金",
        "股票",
        "央行",
        "federal reserve",
    ],
    ContentTopic.WORLDVIEW.value: [
        "世界观",
        "哲学",
        "思考",
        "观点",
        "认知",
        "社会",
        "人生",
        "价值观",
        "意义",
        "存在",
        "道德",
        "伦理",
    ],
    ContentTopic.WELLNESS.value: [
        "健康",
        "养生",
        "wellness",
        "运动",
        "心理",
        "睡眠",
        "饮食",
        "冥想",
        "压力",
        "焦虑",
        "fitness",
        "nutrition",
    ],
}


def classify_by_keywords(text: str) -> TopicClassificationResult:
    """Classify text into a topic using keyword matching.

    Returns the primary topic, confidence score, and up to 3 alternatives.
    Confidence is computed as the topic's keyword hit count divided by total hits.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for topic_value, keywords in _KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[topic_value] = score

    if not scores:
        return TopicClassificationResult(
            primary_topic=ContentTopic.AI_STATUS_AND_OUTLOOK.value,
            confidence=0.0,
            alternatives=[],
        )

    sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_topic, primary_score = sorted_topics[0]
    total = sum(s for _, s in sorted_topics)

    alternatives = [
        TopicCandidate(topic=t, confidence=round(s / total, 2)) for t, s in sorted_topics[1:4]
    ]

    return TopicClassificationResult(
        primary_topic=primary_topic,
        confidence=round(primary_score / total, 2) if total > 0 else 0.0,
        alternatives=alternatives,
    )


def validate_topic(topic: str) -> str:
    """Validate and normalize a topic string. Raises ValueError if unknown."""
    if topic not in VALID_TOPICS:
        raise ValueError(f"unknown topic '{topic}'. valid: {', '.join(VALID_TOPICS)}")
    return topic
