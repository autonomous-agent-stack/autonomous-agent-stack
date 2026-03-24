# knowledge/agents/ai-autonomous-agent-framework/experiments/__init__.py

"""
实验模块

包含各种自主 Agent 的实验场景
"""

from .data_analysis import DataAnalysisAgent, run_data_analysis_experiment
from .code_generation import CodeGenerationAgent, run_code_generation_experiment
from .research import ResearchAgent, run_research_experiment

__all__ = [
    "DataAnalysisAgent",
    "run_data_analysis_experiment",
    "CodeGenerationAgent",
    "run_code_generation_experiment",
    "ResearchAgent",
    "run_research_experiment",
]
