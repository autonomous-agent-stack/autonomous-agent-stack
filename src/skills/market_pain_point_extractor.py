"""
Market Pain Point Extractor - MCP Tool
Extracts and analyzes market pain points from multiple platforms.
"""

import json
import logging
import sqlite3
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

# Imports will be adjusted based on actual project structure
# from .utils.noise_filter import NoiseFilter
# from .sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class MarketPainPointExtractor:
    """
    Market Pain Point Extractor - Multi-platform sentiment analysis tool.

    This tool:
    1. Fetches content from multiple platforms (Twitter, Reddit, Weibo)
    2. Filters out spam and low-quality content
    3. Analyzes sentiment for pain point detection
    4. Generates JSON reports
    5. Stores results in SQLite database
    """

    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            config_path: Path to keywords configuration JSON file
            db_path: Path to SQLite database file
        """
        # Default paths
        if config_path is None:
            config_path = Path(__file__).parent / "config" / "keywords.json"
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "market_pain_points.db"

        self.config_path = Path(config_path)
        self.db_path = Path(db_path)

        # Load configuration
        self.config = self._load_config()
        self.pain_points = self.config.get("pain_points", [])
        self.platforms = self.config.get("platforms", [])
        self.noise_filter_config = self.config.get("noise_filter", {})

        # Initialize noise filter (deferred import to avoid circular dependency)
        try:
            from .utils.noise_filter import NoiseFilter
            self.noise_filter = NoiseFilter(self.noise_filter_config)
        except ImportError:
            logger.warning("[Agent-Stack-Bridge] NoiseFilter not available, using basic filtering")
            self.noise_filter = None

        # Initialize database
        self._init_database()

        logger.info(f"[Agent-Stack-Bridge] Market skill initialized with {len(self.pain_points)} keywords")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"[Agent-Stack-Bridge] Config file not found: {self.config_path}")
            return {
                "pain_points": ["卡顿", "报错", "体验差"],
                "platforms": ["twitter"],
                "noise_filter": {"min_length": 10}
            }
        except json.JSONDecodeError as e:
            logger.error(f"[Agent-Stack-Bridge] Invalid JSON in config: {e}")
            return {"pain_points": [], "platforms": [], "noise_filter": {}}

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create main reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pain_point_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                platform TEXT NOT NULL,
                keyword TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                score REAL NOT NULL,
                text TEXT NOT NULL,
                user_id TEXT,
                post_id TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_platform_keyword
            ON pain_point_reports(platform, keyword)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON pain_point_reports(timestamp)
        ''')

        conn.commit()
        conn.close()

        logger.info(f"[Agent-Stack-Bridge] Database initialized: {self.db_path}")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method for MCP tool.

        Args:
            context: Execution context containing optional parameters:
                - platforms: List of platforms to fetch from (overrides config)
                - keywords: List of keywords to search for (overrides config)
                - limit: Maximum number of posts per platform (default: 100)
                - since_date: Only fetch posts after this date (ISO format)

        Returns:
            Dictionary containing:
                - success: bool
                - reports: List of generated reports
                - stats: Statistics about the run
        """
        logger.info("[Agent-Stack-Bridge] Starting market pain point extraction")

        # Extract parameters from context
        platforms = context.get("platforms", self.platforms)
        keywords = context.get("keywords", self.pain_points)
        limit = context.get("limit", 100)
        since_date = context.get("since_date")

        all_reports = []
        stats = {
            "total_fetched": 0,
            "filtered_noise": 0,
            "reports_generated": 0,
            "platforms_processed": 0,
            "errors": []
        }

        # Process each platform
        for platform in platforms:
            try:
                logger.info(f"[Agent-Stack-Bridge] Fetching data from {platform}")
                platform_data = await self._fetch_from_platform(
                    platform, keywords, limit, since_date
                )
                stats["total_fetched"] += len(platform_data)

                # Skip if no data returned
                if not platform_data:
                    logger.info(f"[Agent-Stack-Bridge] {platform}: No data returned")
                    continue

                # Filter noise
                if self.noise_filter:
                    filtered_data = self._filter_noise(platform_data)
                    stats["filtered_noise"] += len(platform_data) - len(filtered_data)
                else:
                    filtered_data = platform_data

                # Analyze sentiment and generate reports
                reports = await self._analyze_and_generate_reports(
                    filtered_data, platform, keywords
                )
                all_reports.extend(reports)
                stats["reports_generated"] += len(reports)

                # Store in database
                self._store_reports(reports)
                stats["platforms_processed"] += 1

                logger.info(f"[Agent-Stack-Bridge] {platform}: {len(reports)} reports generated")

            except Exception as e:
                error_msg = f"{platform}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(f"[Agent-Stack-Bridge] Error processing {platform}: {e}")

        # Generate summary
        logger.info(f"[Agent-Stack-Bridge] Extraction complete: {stats['reports_generated']} reports")
        logger.info(f"[Agent-Stack-Bridge] Filtered {stats['filtered_noise']} noise items")

        return {
            "success": len(stats["errors"]) == 0,
            "reports": all_reports,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _fetch_from_platform(
        self, platform: str, keywords: List[str], limit: int, since_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from a specific platform.

        This is a placeholder implementation. In production, you would integrate
        with actual platform APIs (Twitter API, Reddit API, Weibo API, etc.)
        """
        # Placeholder: Return mock data
        # In production, this would call actual platform APIs

        mock_data = []

        if platform == "twitter":
            mock_data = self._mock_twitter_data(keywords, limit)
        elif platform == "reddit":
            mock_data = self._mock_reddit_data(keywords, limit)
        elif platform == "weibo":
            mock_data = self._mock_weibo_data(keywords, limit)
        else:
            logger.warning(f"[Agent-Stack-Bridge] Unknown platform: {platform}")
            # Return empty list for unknown platforms instead of raising error
            return []

        return mock_data

    def _mock_twitter_data(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Generate mock Twitter data for testing."""
        examples = [
            {"text": "This app keeps crashing every time I open it", "keyword": "崩溃", "user_id": "user1", "post_id": "tweet1"},
            {"text": "广告太多了，严重影响使用体验 #ads", "keyword": "广告", "user_id": "user2", "post_id": "tweet2"},
            {"text": "为什么这么卡？根本加载不出来", "keyword": "卡顿", "user_id": "user3", "post_id": "tweet3"},
            {"text": "Best product ever! Buy now with discount!", "keyword": "", "user_id": "spam1", "post_id": "tweet4"},
            {"text": "报错了怎么办？一直显示error", "keyword": "报错", "user_id": "user4", "post_id": "tweet5"},
        ]
        return examples[:min(limit, len(examples))]

    def _mock_reddit_data(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Generate mock Reddit data for testing."""
        examples = [
            {"text": "Is anyone else experiencing lag? This is unbearable", "keyword": "卡顿", "user_id": "redditor1", "post_id": "post1"},
            {"text": "FREE GIFT CARD CLICK HERE http://spam.com", "keyword": "", "user_id": "spammer1", "post_id": "post2"},
            {"text": "The app keeps freezing on my device", "keyword": "卡死", "user_id": "redditor2", "post_id": "post3"},
            {"text": "Worst user experience I've ever had", "keyword": "体验差", "user_id": "redditor3", "post_id": "post4"},
            {"text": "Constant error messages, can't use the app", "keyword": "报错", "user_id": "redditor4", "post_id": "post5"},
        ]
        return examples[:min(limit, len(examples))]

    def _mock_weibo_data(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Generate mock Weibo data for testing."""
        examples = [
            {"text": "这也太慢了吧，等了半天没反应", "keyword": "慢", "user_id": "weibo1", "post_id": "wb1"},
            {"text": "关注有礼！转发抽奖！🎁🎁🎁🎁🎁", "keyword": "", "user_id": "weibospam1", "post_id": "wb2"},
            {"text": "崩溃了，刚才好好的突然就退出了", "keyword": "崩溃", "user_id": "weibo2", "post_id": "wb3"},
            {"text": "体验太差了，想卸载", "keyword": "体验差", "user_id": "weibo3", "post_id": "wb4"},
            {"text": "一直连不上服务器，什么问题？", "keyword": "连不上", "user_id": "weibo4", "post_id": "wb5"},
            {"text": "代购专享优惠价，加微信xxx", "keyword": "", "user_id": "weibospam2", "post_id": "wb6"},
        ]
        return examples[:min(limit, len(examples))]

    def _filter_noise(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out spam and low-quality content.

        Args:
            data: List of post data dictionaries

        Returns:
            Filtered list of data
        """
        if not self.noise_filter:
            return data

        filtered = []
        for item in data:
            text = item.get("text", "")
            if not self.noise_filter.filter_spam(text):
                # Add quality score to item
                item["quality_score"] = self.noise_filter.quality_score(text)
                filtered.append(item)

        logger.info(f"[Agent-Stack-Bridge] Filtered {len(data) - len(filtered)} noise items")
        return filtered

    async def _analyze_and_generate_reports(
        self, data: List[Dict[str, Any]], platform: str, keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment and generate reports.

        Args:
            data: Filtered post data
            platform: Platform name
            keywords: List of keywords to search for

        Returns:
            List of report dictionaries
        """
        reports = []

        for item in data:
            text = item.get("text", "")
            if not text:
                continue

            # Find matching keyword
            matched_keyword = self._find_matching_keyword(text, keywords)

            # Only generate reports if a keyword was matched or if sentiment is negative
            sentiment, score = self._analyze_sentiment(text, matched_keyword)

            # Skip if no keyword matched and sentiment is neutral/positive
            if not matched_keyword and sentiment != "negative":
                continue

            # Generate report
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "platform": platform,
                "keyword": matched_keyword,
                "sentiment": sentiment,
                "score": score,
                "text": text,
                "metadata": {
                    "user_id": item.get("user_id"),
                    "post_id": item.get("post_id"),
                    "quality_score": item.get("quality_score", 0.5)
                }
            }

            reports.append(report)

        return reports

    def _find_matching_keyword(self, text: str, keywords: List[str]) -> str:
        """
        Find the first matching keyword in text.

        Args:
            text: Text to search
            keywords: List of keywords

        Returns:
            Matched keyword or empty string
        """
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return keyword
        return ""

    def _analyze_sentiment(self, text: str, keyword: str) -> tuple[str, float]:
        """
        Analyze sentiment of text.

        This is a simple rule-based implementation. In production,
        you would use a proper sentiment analysis model.

        Args:
            text: Text to analyze
            keyword: Matched pain point keyword

        Returns:
            Tuple of (sentiment_label, confidence_score)
        """
        # Simple heuristic-based sentiment analysis
        text_lower = text.lower()

        # Negative indicators (increase negative sentiment score)
        negative_words = [
            "不", "没", "别", "难", "差", "坏", "垃圾", "糟糕", "卡", "慢",
            "not", "bad", "worst", "terrible", "awful", "hate",
            "error", "broken", "crash", "fail", "bug", "lag", "slow"
        ]

        # Positive indicators (decrease negative sentiment score)
        positive_words = [
            "好", "棒", "喜欢", "爱", "优秀", "不错",
            "good", "great", "love", "excellent", "amazing", "best"
        ]

        negative_score = sum(1 for word in negative_words if word in text_lower)
        positive_score = sum(1 for word in positive_words if word in text_lower)

        # Calculate net sentiment
        net_score = negative_score - positive_score

        # Determine sentiment label
        if net_score >= 2:
            sentiment = "negative"
            confidence = min(0.95, 0.6 + net_score * 0.1)
        elif net_score >= 1:
            sentiment = "negative"
            confidence = 0.6
        elif net_score <= -2:
            sentiment = "positive"
            confidence = min(0.95, 0.6 + abs(net_score) * 0.1)
        elif net_score <= -1:
            sentiment = "positive"
            confidence = 0.6
        else:
            sentiment = "neutral"
            confidence = 0.5

        # Boost confidence if keyword is present
        if keyword:
            confidence = min(0.98, confidence + 0.2)

        return sentiment, round(confidence, 2)

    def _store_reports(self, reports: List[Dict[str, Any]]):
        """
        Store reports in SQLite database.

        Args:
            reports: List of report dictionaries
        """
        if not reports:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for report in reports:
            cursor.execute('''
                INSERT INTO pain_point_reports
                (timestamp, platform, keyword, sentiment, score, text, user_id, post_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report["timestamp"],
                report["platform"],
                report["keyword"],
                report["sentiment"],
                report["score"],
                report["text"],
                report["metadata"].get("user_id"),
                report["metadata"].get("post_id"),
                json.dumps(report["metadata"])
            ))

        conn.commit()
        conn.close()

        logger.info(f"[Agent-Stack-Bridge] Stored {len(reports)} reports in database")

    def get_reports(
        self, platform: Optional[str] = None, keyword: Optional[str] = None,
        sentiment: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query stored reports from database.

        Args:
            platform: Filter by platform
            keyword: Filter by keyword
            sentiment: Filter by sentiment
            limit: Maximum number of results

        Returns:
            List of report dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM pain_point_reports WHERE 1=1"
        params = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if keyword:
            query += " AND keyword = ?"
            params.append(keyword)
        if sentiment:
            query += " AND sentiment = ?"
            params.append(sentiment)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        # Convert rows to dictionaries
        columns = [
            "id", "timestamp", "platform", "keyword", "sentiment",
            "score", "text", "user_id", "post_id", "metadata", "created_at"
        ]

        reports = []
        for row in rows:
            report = dict(zip(columns, row))
            # Parse metadata JSON
            if report.get("metadata"):
                try:
                    report["metadata"] = json.loads(report["metadata"])
                except json.JSONDecodeError:
                    report["metadata"] = {}
            reports.append(report)

        return reports


# MCP Tool wrapper class for integration with MCP framework
class MCPMarketPainPointExtractor:
    """MCP Tool wrapper for MarketPainPointExtractor."""

    name = "market_pain_point_extractor"
    description = "通用市场痛点探测器 - Extract and analyze market pain points from social media"

    def __init__(self):
        self.extractor = None

    async def __call__(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the market pain point extraction.

        Args:
            context: MCP execution context

        Returns:
            Dictionary with extraction results
        """
        if self.extractor is None:
            self.extractor = MarketPainPointExtractor()

        return await self.extractor.execute(context)
