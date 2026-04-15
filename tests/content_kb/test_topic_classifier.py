"""Tests for content_kb topic classifier."""
from __future__ import annotations

import pytest

from content_kb.topic_classifier import classify_by_keywords
from content_kb.contracts import ContentTopic


class TestTopicClassifier:
    def test_ai_keywords(self) -> None:
        result = classify_by_keywords("讨论AI和大模型的最新发展")
        assert result.primary_topic == ContentTopic.AI_STATUS_AND_OUTLOOK.value

    def test_coding_keywords(self) -> None:
        result = classify_by_keywords("vibe coding 工作流分享")
        assert result.primary_topic == ContentTopic.VIBE_CODING.value

    def test_economy_keywords(self) -> None:
        result = classify_by_keywords("股市投资策略分析")
        assert result.primary_topic == ContentTopic.ECONOMY.value

    def test_unknown_returns_default(self) -> None:
        result = classify_by_keywords("完全无关的文本内容xyz")
        assert result.confidence == 0.0

    def test_alternatives_populated(self) -> None:
        result = classify_by_keywords("AI编程开发大模型代码")
        assert len(result.alternatives) > 0
