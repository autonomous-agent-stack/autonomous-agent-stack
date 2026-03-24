"""
Performance Analyzer

Analyzes performance data and provides AI-powered insights.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .benchmark import BenchmarkStats


@dataclass
class PerformanceInsight:
    """AI-generated performance insight."""
    type: str  # regression, improvement, outlier, bottleneck
    severity: str  # high, medium, low
    message: str
    recommendation: str
    benchmark_name: str
    details: Dict[str, Any]


class PerformanceAnalyzer:
    """
    Analyzes performance data with AI insights.

    Features:
    - Trend analysis
    - Bottleneck identification
    - Outlier detection
    - Performance regression detection
    - Optimization recommendations
    """

    def __init__(self):
        """Initialize performance analyzer."""
        self.history: List[Dict[str, BenchmarkStats]] = []

    def analyze(
        self,
        current_results: Dict[str, BenchmarkStats],
        baseline_results: Optional[Dict[str, BenchmarkStats]] = None,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Analyze performance results.

        Args:
            current_results: Current benchmark results
            baseline_results: Baseline results for comparison (optional)
            threshold: Regression threshold (10% default)

        Returns:
            Analysis results
        """
        insights = []

        # Analyze each benchmark
        for name, stats in current_results.items():
            # Compare with baseline if available
            if baseline_results and name in baseline_results:
                baseline = baseline_results[name]
                insights.extend(self._compare_with_baseline(stats, baseline, threshold))

            # Detect outliers
            insights.extend(self._detect_outliers(stats))

            # Identify bottlenecks
            insights.extend(self._identify_bottlenecks(stats))

        # Overall analysis
        summary = self._generate_summary(current_results, baseline_results, insights)

        return {
            "summary": summary,
            "insights": [self._insight_to_dict(i) for i in insights],
            "metrics": self._calculate_metrics(current_results),
            "trends": self._analyze_trends(current_results)
        }

    def _compare_with_baseline(
        self,
        current: BenchmarkStats,
        baseline: BenchmarkStats,
        threshold: float
    ) -> List[PerformanceInsight]:
        """Compare current results with baseline."""
        insights = []

        # Check for regression
        duration_diff = ((current.mean_duration - baseline.mean_duration) /
                        baseline.mean_duration)

        if duration_diff > threshold:
            insights.append(PerformanceInsight(
                type="regression",
                severity="high",
                message=f"Performance regression detected: {current.name} is {duration_diff*100:.1f}% slower",
                recommendation="Investigate recent changes that may have impacted performance",
                benchmark_name=current.name,
                details={
                    "current_mean": current.mean_duration,
                    "baseline_mean": baseline.mean_duration,
                    "diff_percent": duration_diff * 100
                }
            ))
        elif duration_diff < -threshold:
            insights.append(PerformanceInsight(
                type="improvement",
                severity="low",
                message=f"Performance improvement: {current.name} is {abs(duration_diff)*100:.1f}% faster",
                recommendation="Consider documenting what caused the improvement",
                benchmark_name=current.name,
                details={
                    "current_mean": current.mean_duration,
                    "baseline_mean": baseline.mean_duration,
                    "diff_percent": duration_diff * 100
                }
            ))

        # Check memory usage
        memory_diff = ((current.memory_mb - baseline.memory_mb) /
                      baseline.memory_mb)

        if memory_diff > threshold:
            insights.append(PerformanceInsight(
                type="memory_increase",
                severity="medium",
                message=f"Memory usage increased by {memory_diff*100:.1f}%",
                recommendation="Review recent changes for memory leaks or inefficient allocations",
                benchmark_name=current.name,
                details={
                    "current_memory": current.memory_mb,
                    "baseline_memory": baseline.memory_mb,
                    "diff_percent": memory_diff * 100
                }
            ))

        return insights

    def _detect_outliers(self, stats: BenchmarkStats) -> List[PerformanceInsight]:
        """Detect outliers in benchmark runs."""
        insights = []

        # Check standard deviation
        cv = stats.std_dev / stats.mean_duration  # Coefficient of variation

        if cv > 0.2:
            insights.append(PerformanceInsight(
                type="high_variance",
                severity="medium",
                message=f"High variance detected: Coefficient of variation is {cv:.2f}",
                recommendation="Investigate sources of variability (e.g., external dependencies, GC)",
                benchmark_name=stats.name,
                details={
                    "std_dev": stats.std_dev,
                    "mean": stats.mean_duration,
                    "cv": cv
                }
            ))

        # Check for extreme outliers (beyond 3 std dev)
        durations = [r.duration for r in stats.results]
        mean = stats.mean_duration
        std_dev = stats.std_dev

        outliers = [d for d in durations if abs(d - mean) > 3 * std_dev]

        if outliers:
            insights.append(PerformanceInsight(
                type="outliers",
                severity="low",
                message=f"Found {len(outliers)} outlier runs beyond 3 standard deviations",
                recommendation="Consider removing outliers or investigating their cause",
                benchmark_name=stats.name,
                details={
                    "outliers": outliers,
                    "count": len(outliers)
                }
            ))

        return insights

    def _identify_bottlenecks(self, stats: BenchmarkStats) -> List[PerformanceInsight]:
        """Identify potential performance bottlenecks."""
        insights = []

        # Check for slow benchmarks (> 1 second)
        if stats.mean_duration > 1.0:
            insights.append(PerformanceInsight(
                type="slow_performance",
                severity="medium",
                message=f"Slow performance: Mean duration is {stats.mean_duration:.3f}s",
                recommendation="Consider optimization: profiling, caching, or algorithm improvements",
                benchmark_name=stats.name,
                details={
                    "mean_duration": stats.mean_duration,
                    "p95_duration": stats.p95_duration,
                    "p99_duration": stats.p99_duration
                }
            ))

        # Check for P99 spikes
        if stats.p99_duration > stats.mean_duration * 2:
            insights.append(PerformanceInsight(
                type="tail_latency",
                severity="medium",
                message=f"High tail latency: P99 is {stats.p99_duration / stats.mean_duration:.1f}x mean",
                recommendation="Investigate tail latency issues (e.g., lock contention, I/O)",
                benchmark_name=stats.name,
                details={
                    "mean": stats.mean_duration,
                    "p95": stats.p95_duration,
                    "p99": stats.p99_duration,
                    "ratio_p99_mean": stats.p99_duration / stats.mean_duration
                }
            ))

        return insights

    def _generate_summary(
        self,
        current_results: Dict[str, BenchmarkStats],
        baseline_results: Optional[Dict[str, BenchmarkStats]],
        insights: List[PerformanceInsight]
    ) -> str:
        """Generate performance summary."""
        total_benchmarks = len(current_results)
        regressive_count = sum(1 for i in insights if i.type == "regression")
        improvement_count = sum(1 for i in insights if i.type == "improvement")
        high_severity_count = sum(1 for i in insights if i.severity == "high")

        summary = f"""
Performance Analysis Summary
Generated: {datetime.now().isoformat()}

Benchmark Overview:
- Total Benchmarks: {total_benchmarks}
- Regressions: {regressive_count}
- Improvements: {improvement_count}
- High Severity Issues: {high_severity_count}
"""

        if baseline_results:
            total_time = sum(s.mean_duration for s in current_results.values())
            baseline_time = sum(s.mean_duration for s in baseline_results.values())
            if baseline_time > 0:
                time_change = ((total_time - baseline_time) / baseline_time) * 100
                summary += f"\nOverall Time Change: {time_change:+.1f}%"

        return summary.strip()

    def _calculate_metrics(self, results: Dict[str, BenchmarkStats]) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        total_duration = sum(s.mean_duration for s in results.values())
        total_memory = sum(s.memory_mb for s in results.values())
        total_runs = sum(s.runs for s in results.values())

        return {
            "total_benchmarks": len(results),
            "total_duration": total_duration,
            "average_duration": total_duration / len(results) if results else 0,
            "total_memory_mb": total_memory,
            "average_memory_mb": total_memory / len(results) if results else 0,
            "total_runs": total_runs
        }

    def _analyze_trends(self, results: Dict[str, BenchmarkStats]) -> Dict[str, Any]:
        """Analyze performance trends."""
        # This would require historical data
        return {
            "message": "Trend analysis requires historical data",
            "available": False
        }

    def load_history(self, path: str) -> None:
        """
        Load historical performance data.

        Args:
            path: Path to historical data file
        """
        if Path(path).exists():
            with open(path, "r") as f:
                self.history = json.load(f)

    def save_history(self, path: str) -> None:
        """
        Save historical performance data.

        Args:
            path: Path to save historical data
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.history, f, indent=2)

    def add_to_history(self, results: Dict[str, BenchmarkStats]) -> None:
        """
        Add current results to history.

        Args:
            results: Current benchmark results
        """
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "results": {}
        }

        for name, stats in results.items():
            history_entry["results"][name] = {
                "mean_duration": stats.mean_duration,
                "memory_mb": stats.memory_mb,
                "runs": stats.runs
            }

        self.history.append(history_entry)

    def _insight_to_dict(self, insight: PerformanceInsight) -> Dict[str, Any]:
        """Convert insight to dictionary."""
        return {
            "type": insight.type,
            "severity": insight.severity,
            "message": insight.message,
            "recommendation": insight.recommendation,
            "benchmark_name": insight.benchmark_name,
            "details": insight.details
        }


def analyze_performance(
    current_results: Dict[str, BenchmarkStats],
    baseline_results: Optional[Dict[str, BenchmarkStats]] = None,
    threshold: float = 0.1
) -> Dict[str, Any]:
    """
    Convenience function to analyze performance.

    Args:
        current_results: Current benchmark results
        baseline_results: Baseline results (optional)
        threshold: Regression threshold

    Returns:
        Analysis results
    """
    analyzer = PerformanceAnalyzer()
    return analyzer.analyze(current_results, baseline_results, threshold)
