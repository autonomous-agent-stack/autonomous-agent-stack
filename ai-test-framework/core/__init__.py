"""
AI-Driven Test Framework - Core Module

Core AI test generation logic with intelligent test case discovery and generation.
"""

from .generator import AITestGenerator
from .analyzer import CodeAnalyzer
from .discovery import TestScenarioDiscovery

__version__ = "0.1.0"
__all__ = ["AITestGenerator", "CodeAnalyzer", "TestScenarioDiscovery"]
