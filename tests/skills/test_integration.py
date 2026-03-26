"""
Integration tests for the complete Market Pain Point extraction workflow.
Run with: pytest tests/skills/test_integration.py -v
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from src.skills.market_pain_point_extractor import MarketPainPointExtractor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def integration_extractor(temp_dir):
    """Create an extractor for integration testing."""
    config_path = temp_dir / "config.json"
    db_path = temp_dir / "test.db"

    # Create test config
    import json
    config = {
        "pain_points": ["卡顿", "报错", "崩溃", "慢", "体验差"],
        "platforms": ["twitter", "reddit", "weibo"],
        "noise_filter": {
            "min_length": 5,
            "exclude_keywords": ["广告", "推广", "代购"],
            "spam_patterns": ["http://", "https://", "代"]
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config, f)

    return MarketPainPointExtractor(
        config_path=str(config_path),
        db_path=str(db_path)
    )


class TestEndToEndWorkflow:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_extraction_workflow(self, integration_extractor):
        """Test the complete extraction workflow."""
        context = {
            "platforms": ["twitter", "reddit", "weibo"],
            "keywords": ["卡顿", "崩溃", "报错"],
            "limit": 20
        }

        # Execute extraction
        result = await integration_extractor.execute(context)

        # Verify results
        assert result["success"] == True
        assert len(result["reports"]) > 0
        assert result["stats"]["platforms_processed"] == 3
        assert result["stats"]["total_fetched"] > 0

        # Verify report structure
        report = result["reports"][0]
        required_fields = [
            "timestamp", "platform", "keyword",
            "sentiment", "score", "text", "metadata"
        ]
        for field in required_fields:
            assert field in report

        # Verify data was stored in database
        stored_reports = integration_extractor.get_reports(limit=100)
        assert len(stored_reports) > 0

    @pytest.mark.asyncio
    async def test_noise_filtering_in_workflow(self, integration_extractor):
        """Test that noise is properly filtered in the workflow."""
        context = {
            "platforms": ["weibo"],  # Weibo has spam examples
            "keywords": ["卡顿"],
            "limit": 20
        }

        result = await integration_extractor.execute(context)

        # Should have filtered some spam
        stats = result["stats"]
        assert stats["filtered_noise"] >= 0

        # Remaining reports should be legitimate
        for report in result["reports"]:
            assert "广告" not in report["text"]
            assert "推广" not in report["text"]

    @pytest.mark.asyncio
    async def test_sentiment_distribution(self, integration_extractor):
        """Test sentiment analysis across different platforms."""
        context = {
            "platforms": ["twitter", "reddit"],
            "keywords": ["崩溃"],
            "limit": 10
        }

        result = await integration_extractor.execute(context)

        # Analyze sentiment distribution
        sentiments = [r["sentiment"] for r in result["reports"]]
        assert len(sentiments) > 0

        # Most should be negative for pain points
        negative_count = sentiments.count("negative")
        assert negative_count > 0

    @pytest.mark.asyncio
    async def test_platform_specific_analysis(self, integration_extractor):
        """Test extraction and analysis by platform."""
        platforms = ["twitter", "reddit", "weibo"]
        all_results = {}

        for platform in platforms:
            context = {
                "platforms": [platform],
                "keywords": ["卡顿"],
                "limit": 10
            }

            result = await integration_extractor.execute(context)
            all_results[platform] = result

            # Verify each platform produced results
            assert result["stats"]["platforms_processed"] == 1
            assert result["stats"]["total_fetched"] > 0

        # Compare results across platforms
        for platform, result in all_results.items():
            assert result["success"]
            print(f"{platform}: {len(result['reports'])} reports generated")

    @pytest.mark.asyncio
    async def test_database_query_and_filtering(self, integration_extractor):
        """Test database storage and querying."""
        # First, populate database
        context = {
            "platforms": ["twitter", "reddit"],
            "keywords": ["卡顿", "报错"],
            "limit": 15
        }

        await integration_extractor.execute(context)

        # Query by platform
        twitter_reports = integration_extractor.get_reports(platform="twitter")
        assert all(r["platform"] == "twitter" for r in twitter_reports)

        # Query by keyword
        lag_reports = integration_extractor.get_reports(keyword="卡顿")
        assert all(r["keyword"] == "卡顿" for r in lag_reports)

        # Query by sentiment
        negative_reports = integration_extractor.get_reports(sentiment="negative")
        assert all(r["sentiment"] == "negative" for r in negative_reports)

        # Test limit
        limited_reports = integration_extractor.get_reports(limit=5)
        assert len(limited_reports) <= 5

    @pytest.mark.asyncio
    async def test_custom_parameters_override(self, integration_extractor):
        """Test that custom parameters override defaults."""
        # Use different keywords than in config
        custom_keywords = ["崩溃", "慢"]
        context = {
            "platforms": ["twitter"],
            "keywords": custom_keywords,
            "limit": 5
        }

        result = await integration_extractor.execute(context)

        # Verify that matching keywords were found in reports
        # Note: Not all reports may have keywords due to filtering, but if they do,
        # they should be from our custom list
        for report in result["reports"]:
            if report["keyword"]:  # Only check if a keyword was found
                assert report["keyword"] in custom_keywords

    @pytest.mark.asyncio
    async def test_error_handling(self, integration_extractor):
        """Test error handling for invalid platforms."""
        context = {
            "platforms": ["nonexistent_platform"],
            "keywords": ["卡顿"],
            "limit": 10
        }

        result = await integration_extractor.execute(context)

        # Should still succeed, just with no data for that platform
        assert result["success"] == True
        assert result["stats"]["platforms_processed"] == 0


class TestReportQuality:
    """Test quality of generated reports."""

    @pytest.mark.asyncio
    async def test_report_completeness(self, integration_extractor):
        """Test that all reports have required fields."""
        context = {
            "platforms": ["twitter"],
            "keywords": ["卡顿"],
            "limit": 10
        }

        result = await integration_extractor.execute(context)

        for report in result["reports"]:
            # Check required fields exist
            assert report["timestamp"] is not None
            assert report["platform"] is not None
            assert report["text"] is not None
            assert report["sentiment"] in ["positive", "negative", "neutral"]
            assert 0.0 <= report["score"] <= 1.0

            # Check metadata
            assert isinstance(report["metadata"], dict)

    @pytest.mark.asyncio
    async def test_no_spam_in_reports(self, integration_extractor):
        """Test that spam content doesn't make it into reports."""
        context = {
            "platforms": ["weibo"],
            "keywords": ["卡顿"],
            "limit": 20
        }

        result = await integration_extractor.execute(context)

        spam_keywords = ["广告", "推广", "代购", "刷单", "优惠"]
        for report in result["reports"]:
            text = report["text"]
            for spam_word in spam_keywords:
                # Reports should not contain spam keywords
                assert spam_word not in text, f"Spam found in report: {text}"

    @pytest.mark.asyncio
    async def test_sentiment_confidence_scores(self, integration_extractor):
        """Test that sentiment confidence scores are reasonable."""
        context = {
            "platforms": ["reddit"],
            "keywords": ["崩溃"],
            "limit": 10
        }

        result = await integration_extractor.execute(context)

        # Negative sentiment about crashes should have high confidence
        negative_reports = [
            r for r in result["reports"]
            if r["sentiment"] == "negative"
        ]

        if negative_reports:
            avg_confidence = sum(r["score"] for r in negative_reports) / len(negative_reports)
            assert avg_confidence > 0.5, "Negative reports should have > 0.5 confidence"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
