"""
Noise Filter for Market Pain Point Extractor.
Filters out low-quality content and spam.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class NoiseFilter:
    """Filter out spam, marketing content, and low-quality posts."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize noise filter with configuration.

        Args:
            config: Configuration dictionary containing:
                - min_length: Minimum text length
                - exclude_keywords: Keywords to exclude
                - spam_patterns: Regex patterns for spam detection
        """
        self.min_length = config.get("min_length", 10)
        self.exclude_keywords = config.get("exclude_keywords", [])
        self.spam_patterns = config.get("spam_patterns", [])

        # Compile regex patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.spam_patterns
        ]

    def filter_spam(self, text: str) -> bool:
        """
        Check if text is spam/marketing content.

        Args:
            text: Text to analyze

        Returns:
            True if text is spam (should be filtered out), False otherwise
        """
        if not text or len(text.strip()) < self.min_length:
            return True

        # Check for exclude keywords
        text_lower = text.lower()
        for keyword in self.exclude_keywords:
            if keyword.lower() in text_lower:
                logger.debug(f"[NoiseFilter] Filtered by keyword '{keyword}': {text[:50]}...")
                return True

        # Check for spam patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # Additional check: don't filter if it contains pain points
                # Some legitimate complaints may have URLs
                if self._has_legitimate_complaint(text):
                    return False
                logger.debug(f"[NoiseFilter] Filtered by pattern: {text[:50]}...")
                return True

        # Check for excessive repetition (spam characteristic)
        if self._has_excessive_repetition(text):
            logger.debug(f"[NoiseFilter] Filtered by repetition: {text[:50]}...")
            return True

        # Check for excessive emoji spam
        if self._has_emoji_spam(text):
            logger.debug(f"[NoiseFilter] Filtered by emoji spam: {text[:50]}...")
            return True

        return False

    def _has_legitimate_complaint(self, text: str) -> bool:
        """
        Check if text contains legitimate complaint indicators.

        Args:
            text: Text to analyze

        Returns:
            True if text appears to be a legitimate complaint
        """
        complaint_indicators = [
            "为什么", "怎么回事", "太差了", "很难用", "不能用",
            "不好用", "垃圾", "失望", "问题", "bug",
            "why", "broken", "doesn't work", "worst", "hate"
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in complaint_indicators)

    def _has_excessive_repetition(self, text: str) -> bool:
        """
        Check for excessive character/word repetition (spam indicator).

        Args:
            text: Text to analyze

        Returns:
            True if excessive repetition detected
        """
        # Check for repeated characters (more than 5 same chars in a row)
        if re.search(r'(.)\1{5,}', text):
            return True

        # Check for repeated words (same word appears more than 5 times)
        words = text.split()
        if len(words) > 0:
            most_common = max(set(words), key=words.count)
            if words.count(most_common) > 5 and len(most_common) > 1:
                return True

        return False

    def _has_emoji_spam(self, text: str) -> bool:
        """
        Check for excessive emoji usage (spam indicator).

        Args:
            text: Text to analyze

        Returns:
            True if excessive emoji detected
        """
        # Unicode ranges for emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )

        emojis = emoji_pattern.findall(text)
        # If more than 5 emojis in a short text (< 50 chars), likely spam
        if len(emojis) > 5 and len(text) < 50:
            return True

        return False

    def quality_score(self, text: str) -> float:
        """
        Calculate quality score for text (0-1).

        Args:
            text: Text to score

        Returns:
            Quality score between 0 (low quality) and 1 (high quality)
        """
        score = 1.0

        # Length factor
        length = len(text.strip())
        if length < self.min_length:
            score *= 0.3
        elif length < 20:
            score *= 0.7
        elif length > 100:
            score *= 1.1  # Longer posts often have more detail

        # Repetition penalty
        if self._has_excessive_repetition(text):
            score *= 0.2

        # Emoji spam penalty
        if self._has_emoji_spam(text):
            score *= 0.4

        # Keyword presence penalty
        text_lower = text.lower()
        for keyword in self.exclude_keywords:
            if keyword.lower() in text_lower:
                score *= 0.5
                break

        # Bonus for legitimate complaint indicators
        if self._has_legitimate_complaint(text):
            score *= 1.3

        # Spam pattern penalty
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                if not self._has_legitimate_complaint(text):
                    score *= 0.6
                break

        # Ensure score is within [0, 1]
        return max(0.0, min(1.0, score))

    def filter_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Filter a batch of texts and return results with quality scores.

        Args:
            texts: List of texts to filter

        Returns:
            List of dictionaries containing:
                - text: Original text
                - is_spam: Whether it's spam
                - quality_score: Quality score (0-1)
                - filtered: Whether it should be filtered out
        """
        results = []

        for text in texts:
            is_spam = self.filter_spam(text)
            quality_score = self.quality_score(text)
            filtered = is_spam or quality_score < 0.3

            results.append({
                "text": text,
                "is_spam": is_spam,
                "quality_score": quality_score,
                "filtered": filtered
            })

        filtered_count = sum(1 for r in results if r["filtered"])
        logger.info(f"[NoiseFilter] Filtered {filtered_count}/{len(texts)} items")

        return results
