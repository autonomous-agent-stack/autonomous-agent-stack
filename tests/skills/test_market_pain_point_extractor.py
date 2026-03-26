"""
Test suite for MarketPainPointExtractor class.
Run with: pytest tests/skills/test_market_pain_point_extractor.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.skills.market_pain_point_extractor import MarketPainPointExtractor


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing."""
    config = {
        "pain_points": ["卡顿", "报错", "崩溃"],
        "platforms": ["twitter", "reddit"],
        "noise_filter": {
            "min_length": 5,
            "exclude_keywords": ["广告", "推广"]
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def extractor(temp_config, temp_db):
    """Create a MarketPainPointExtractor instance for testing."""
    return MarketPainPointExtractor(config_path=temp_config, db_path=temp_db)


class TestMarketPainPointExtractor:
    """Test suite for MarketPainPointExtractor."""

    def test_initialization(self, extractor):
        """Test that extractor initializes correctly."""
        assert extractor is not None
        assert len(extractor.pain_points) == 3
        assert "twitter" in extractor.platforms
        assert "reddit" in extractor.platforms

    def test_load_config(self, extractor):
        """Test configuration loading."""
        assert "卡顿" in extractor.pain_points
        assert "报错" in extractor.pain_points
        assert extractor.noise_filter_config["min_length"] == 5

    def test_database_initialization(self, extractor):
        """Test that database and tables are created."""
        assert extractor.db_path.exists()

    def test_mock_twitter_data(self, extractor):
        """Test mock Twitter data generation."""
        data = extractor._mock_twitter_data(["卡顿"], 10)
        assert len(data) > 0
        assert "text" in data[0]
        assert "user_id" in data[0]
        assert "post_id" in data[0]

    def test_mock_reddit_data(self, extractor):
        """Test mock Reddit data generation."""
        data = extractor._mock_reddit_data(["崩溃"], 10)
        assert len(data) > 0
        assert "text" in data[0]

    def test_mock_weibo_data(self, extractor):
        """Test mock Weibo data generation."""
        data = extractor._mock_weibo_data(["慢"], 10)
        assert len(data) > 0
        assert "text" in data[0]

    def test_find_matching_keyword(self, extractor):
        """Test keyword matching."""
        text1 = "这个app很卡，卡顿严重"
        assert extractor._find_matching_keyword(text1, extractor.pain_points) == "卡顿"

        text2 = "一直崩溃，无法使用"
        assert extractor._find_matching_keyword(text2, extractor.pain_points) == "崩溃"

        text3 = "没有关键词"
        assert extractor._find_matching_keyword(text3, extractor.pain_points) == ""

    def test_sentiment_analysis_negative(self, extractor):
        """Test sentiment analysis for negative text."""
        text = "这个app太卡了，体验很差，崩溃了好几次"
        sentiment, score = extractor._analyze_sentiment(text, "卡顿")
        assert sentiment == "negative"
        assert score > 0.6

    def test_sentiment_analysis_positive(self, extractor):
        """Test sentiment analysis for positive text."""
        text = "很好用，很喜欢，没有任何问题"
        sentiment, score = extractor._analyze_sentiment(text, "")
        assert sentiment == "positive"
        assert score >= 0.6

    def test_sentiment_analysis_neutral(self, extractor):
        """Test sentiment analysis for neutral text."""
        text = "这个app还行"
        sentiment, score = extractor._analyze_sentiment(text, "")
        assert sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_execute_basic(self, extractor):
        """Test basic execution of the extractor."""
        context = {
            "platforms": ["twitter"],
            "keywords": ["卡顿"],
            "limit": 10
        }

        result = await extractor.execute(context)

        assert "success" in result
        assert "reports" in result
        assert "stats" in result
        assert isinstance(result["reports"], list)

    @pytest.mark.asyncio
    async def test_execute_multiple_platforms(self, extractor):
        """Test execution with multiple platforms."""
        context = {
            "platforms": ["twitter", "reddit"],
            "keywords": ["崩溃"],
            "limit": 5
        }

        result = await extractor.execute(context)

        assert result["success"] == True
        assert result["stats"]["platforms_processed"] == 2

    def test_store_and_retrieve_reports(self, extractor):
        """Test storing and retrieving reports from database."""
        reports = [
            {
                "timestamp": "2026-03-26T08:00:00Z",
                "platform": "twitter",
                "keyword": "卡顿",
                "sentiment": "negative",
                "score": 0.85,
                "text": "Test complaint about lag",
                "metadata": {"user_id": "test1", "post_id": "post1"}
            }
        ]

        extractor._store_reports(reports)

        # Retrieve reports
        retrieved = extractor.get_reports(platform="twitter", keyword="卡顿")

        assert len(retrieved) == 1
        assert retrieved[0]["text"] == "Test complaint about lag"
        assert retrieved[0]["sentiment"] == "negative"

    def test_get_reports_with_filters(self, extractor):
        """Test filtering reports when retrieving."""
        reports = [
            {
                "timestamp": "2026-03-26T08:00:00Z",
                "platform": "twitter",
                "keyword": "卡顿",
                "sentiment": "negative",
                "score": 0.8,
                "text": "Test 1",
                "metadata": {}
            },
            {
                "timestamp": "2026-03-26T09:00:00Z",
                "platform": "reddit",
                "keyword": "报错",
                "sentiment": "negative",
                "score": 0.7,
                "text": "Test 2",
                "metadata": {}
            }
        ]

        extractor._store_reports(reports)

        # Filter by platform
        twitter_reports = extractor.get_reports(platform="twitter")
        assert len(twitter_reports) == 1
        assert twitter_reports[0]["platform"] == "twitter"

        # Filter by keyword
        keyword_reports = extractor.get_reports(keyword="卡顿")
        assert len(keyword_reports) == 1
        assert keyword_reports[0]["keyword"] == "卡顿"

    def test_filter_noise(self, extractor):
        """Test noise filtering."""
        data = [
            {"text": "这是一条正常反馈", "user_id": "u1"},
            {"text": "广告推广", "user_id": "u2"},
            {"text": "产品报错了", "user_id": "u3"}
        ]

        filtered = extractor._filter_noise(data)

        # Should filter out the spam but keep the legitimate content
        assert len(filtered) <= len(data)
        # At least one legitimate item should remain
        assert len(filtered) >= 1

    @pytest.mark.asyncio
    async def test_analyze_and_generate_reports(self, extractor):
        """Test report generation."""
        data = [
            {
                "text": "这个app太卡了，卡顿严重",
                "user_id": "user1",
                "post_id": "post1",
                "quality_score": 0.8
            }
        ]

        reports = await extractor._analyze_and_generate_reports(
            data, "twitter", ["卡顿"]
        )

        assert len(reports) == 1
        assert reports[0]["platform"] == "twitter"
        assert reports[0]["keyword"] == "卡顿"
        assert reports[0]["sentiment"] == "negative"
        assert "text" in reports[0]

    def test_invalid_config_path(self):
        """Test handling of invalid config path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_config = Path(tmpdir) / "nonexistent.json"
            temp_db = Path(tmpdir) / "test.db"

            # Should not raise exception, should use default config
            extractor = MarketPainPointExtractor(
                config_path=str(invalid_config),
                db_path=str(temp_db)
            )

            assert extractor is not None


class TestMCPMarketPainPointExtractor:
    """Test suite for MCP wrapper."""

    def test_mcp_wrapper_properties(self):
        """Test MCP wrapper has correct properties."""
        from src.skills.market_pain_point_extractor import MCPMarketPainPointExtractor

        wrapper = MCPMarketPainPointExtractor()
        assert wrapper.name == "market_pain_point_extractor"
        assert "市场痛点" in wrapper.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
