"""
Test suite for NoiseFilter class.
Run with: pytest tests/skills/test_noise_filter.py -v
"""

import pytest
from src.skills.utils.noise_filter import NoiseFilter


@pytest.fixture
def noise_filter_config():
    """Default noise filter configuration for testing."""
    return {
        "min_length": 10,
        "exclude_keywords": ["广告", "推广", "优惠", "代购"],
        "spam_patterns": [
            "http://",
            "https://",
            "www\\.",
            ".com"
        ]
    }


@pytest.fixture
def noise_filter(noise_filter_config):
    """Create a NoiseFilter instance for testing."""
    return NoiseFilter(noise_filter_config)


class TestNoiseFilter:
    """Test suite for NoiseFilter functionality."""

    def test_filter_short_text(self, noise_filter):
        """Test that short text is filtered out."""
        short_text = "太短了"
        assert noise_filter.filter_spam(short_text) == True

    def test_filter_exclude_keywords(self, noise_filter):
        """Test filtering of excluded keywords."""
        spam_text = "这是一条广告内容"
        assert noise_filter.filter_spam(spam_text) == True

    def test_filter_url_spam(self, noise_filter):
        """Test filtering of URL spam."""
        url_spam = "Check this out http://spam.com buy now!"
        assert noise_filter.filter_spam(url_spam) == True

    def test_allow_legitimate_complaint_with_url(self, noise_filter):
        """Test that legitimate complaints with URLs are not filtered."""
        complaint = "这个app一直崩溃，我在https://support.com上报过问题了"
        # Should not be filtered because it has legitimate complaint indicators
        assert noise_filter.filter_spam(complaint) == False

    def test_filter_excessive_repetition(self, noise_filter):
        """Test filtering of text with excessive repetition."""
        repetitive = "买买买买买买买买买买买"
        assert noise_filter.filter_spam(repetitive) == True

    def test_filter_emoji_spam(self, noise_filter):
        """Test filtering of emoji spam."""
        emoji_spam = "🎁🎁🎁🎁🎁🎁🎁🎁关注有礼"
        assert noise_filter.filter_spam(emoji_spam) == True

    def test_quality_score_short_text(self, noise_filter):
        """Test quality score for short text."""
        short = "太短了"
        score = noise_filter.quality_score(short)
        assert score < 0.5  # Should be low

    def test_quality_score_legitimate_complaint(self, noise_filter):
        """Test quality score for legitimate complaint."""
        complaint = "这个产品太卡了，体验很差，为什么这么慢？"
        score = noise_filter.quality_score(complaint)
        assert score > 0.7  # Should be high

    def test_quality_score_with_spam_keyword(self, noise_filter):
        """Test quality score reduction for spam keywords."""
        spam = "这是推广内容"
        score = noise_filter.quality_score(spam)
        assert score < 0.7  # Should be reduced

    def test_filter_batch(self, noise_filter):
        """Test batch filtering."""
        texts = [
            "这是一条正常的用户反馈",
            "广告内容推广优惠",
            "太短",
            "产品很好用，没有问题"
        ]

        results = noise_filter.filter_batch(texts)

        assert len(results) == 4
        assert results[0]["filtered"] == False  # Normal feedback
        assert results[1]["filtered"] == True   # Spam
        assert results[2]["filtered"] == True   # Too short
        assert results[3]["filtered"] == False  # Normal feedback

    def test_has_legitimate_complaint(self, noise_filter):
        """Test detection of legitimate complaint indicators."""
        assert noise_filter._has_legitimate_complaint("为什么这么卡") == True
        assert noise_filter._has_legitimate_complaint("broken app") == True
        assert noise_filter._has_legitimate_complaint("很好用") == False

    def test_custom_config(self):
        """Test NoiseFilter with custom configuration."""
        custom_config = {
            "min_length": 5,
            "exclude_keywords": ["test"],
            "spam_patterns": []
        }

        custom_filter = NoiseFilter(custom_config)

        # "短文本" is 3 chars, should be filtered (min_length is 5)
        assert custom_filter.filter_spam("短文本") == True

        # Should filter based on custom keyword
        assert custom_filter.filter_spam("this is a test") == True


class TestQualityScore:
    """Test suite for quality scoring."""

    @pytest.fixture
    def filter(self):
        """Create filter for quality tests."""
        return NoiseFilter({"min_length": 10, "exclude_keywords": [], "spam_patterns": []})

    def test_quality_score_range(self, filter):
        """Test that quality scores are always between 0 and 1."""
        test_texts = [
            "短",
            "这是一个正常的文本内容，应该有不错的评分",
            "重复重复重复重复重复重复重复",
            "Great product! No issues at all."
        ]

        for text in test_texts:
            score = filter.quality_score(text)
            assert 0.0 <= score <= 1.0, f"Score {score} for '{text}' is out of range"

    def test_quality_score_benefits_length(self, filter):
        """Test that longer, detailed content gets bonus."""
        short = "这是一个短文本"
        long = "这是一个很长的文本内容，包含了详细的描述和反馈信息，应该获得更高的质量评分"

        assert filter.quality_score(long) > filter.quality_score(short)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
