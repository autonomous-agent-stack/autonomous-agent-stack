"""
Performance Benchmark

Automated performance testing with baseline comparison.
"""

import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class BenchmarkResult:
    """Represents a single benchmark result."""
    name: str
    duration: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkStats:
    """Statistics for multiple benchmark runs."""
    name: str
    runs: int
    min_duration: float
    max_duration: float
    mean_duration: float
    median_duration: float
    std_dev: float
    p95_duration: float
    p99_duration: float
    memory_mb: float
    results: List[BenchmarkResult] = field(default_factory=list)


class PerformanceBenchmark:
    """
    Performance benchmarking tool.

    Features:
    - Automated benchmark execution
    - Statistical analysis
    - Baseline comparison
    - Performance regression detection
    - Resource usage monitoring
    """

    def __init__(self, baseline_path: Optional[str] = None):
        """
        Initialize performance benchmark.

        Args:
            baseline_path: Path to baseline results file (optional)
        """
        self.baseline_path = baseline_path
        self.baselines: Dict[str, BenchmarkStats] = {}
        self.current_results: Dict[str, BenchmarkStats] = {}

        if baseline_path and Path(baseline_path).exists():
            self._load_baselines()

    def run_benchmark(
        self,
        name: str,
        func: Callable,
        runs: int = 10,
        warmup_runs: int = 2
    ) -> BenchmarkStats:
        """
        Run a performance benchmark.

        Args:
            name: Benchmark name
            func: Function to benchmark
            runs: Number of benchmark runs
            warmup_runs: Number of warmup runs

        Returns:
            Benchmark statistics
        """
        results = []

        # Warmup runs (not counted)
        for _ in range(warmup_runs):
            func()

        # Actual benchmark runs
        for i in range(runs):
            # Measure memory before
            import tracemalloc
            tracemalloc.start()

            # Measure time
            start_time = time.perf_counter()
            result = func()
            end_time = time.perf_counter()

            # Measure memory
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            duration = end_time - start_time

            # Create result
            benchmark_result = BenchmarkResult(
                name=name,
                duration=duration,
                memory_mb=peak / 1024 / 1024,
                timestamp=datetime.now().isoformat(),
                metadata={"run": i + 1}
            )

            results.append(benchmark_result)

        # Calculate statistics
        durations = [r.duration for r in results]
        stats = BenchmarkStats(
            name=name,
            runs=runs,
            min_duration=min(durations),
            max_duration=max(durations),
            mean_duration=statistics.mean(durations),
            median_duration=statistics.median(durations),
            std_dev=statistics.stdev(durations) if len(durations) > 1 else 0.0,
            p95_duration=percentile(durations, 95),
            p99_duration=percentile(durations, 99),
            memory_mb=sum(r.memory_mb for r in results) / len(results),
            results=results
        )

        self.current_results[name] = stats
        return stats

    def run_suite(
        self,
        benchmarks: Dict[str, Callable],
        runs: int = 10,
        warmup_runs: int = 2
    ) -> Dict[str, BenchmarkStats]:
        """
        Run a suite of benchmarks.

        Args:
            benchmarks: Dictionary of benchmark names to functions
            runs: Number of runs per benchmark
            warmup_runs: Number of warmup runs

        Returns:
            Dictionary of benchmark statistics
        """
        results = {}

        for name, func in benchmarks.items():
            print(f"Running benchmark: {name}...")
            results[name] = self.run_benchmark(name, func, runs, warmup_runs)

        return results

    def compare_with_baseline(self, name: str, threshold: float = 0.1) -> Dict[str, Any]:
        """
        Compare current results with baseline.

        Args:
            name: Benchmark name
            threshold: Performance regression threshold (10% default)

        Returns:
            Comparison results
        """
        if name not in self.current_results:
            return {"error": f"No current results for {name}"}

        if name not in self.baselines:
            return {"error": f"No baseline found for {name}"}

        current = self.current_results[name]
        baseline = self.baselines[name]

        # Calculate difference
        duration_diff = ((current.mean_duration - baseline.mean_duration) /
                        baseline.mean_duration * 100)
        memory_diff = ((current.memory_mb - baseline.memory_mb) /
                      baseline.memory_mb * 100)

        # Check for regression
        has_regression = duration_diff > (threshold * 100)

        return {
            "name": name,
            "current_mean": current.mean_duration,
            "baseline_mean": baseline.mean_duration,
            "duration_diff_percent": duration_diff,
            "current_memory": current.memory_mb,
            "baseline_memory": baseline.memory_mb,
            "memory_diff_percent": memory_diff,
            "has_regression": has_regression,
            "threshold_percent": threshold * 100
        }

    def save_baselines(self, path: str) -> None:
        """
        Save current results as baselines.

        Args:
            path: Path to save baselines
        """
        data = {}
        for name, stats in self.current_results.items():
            data[name] = {
                "name": stats.name,
                "runs": stats.runs,
                "min_duration": stats.min_duration,
                "max_duration": stats.max_duration,
                "mean_duration": stats.mean_duration,
                "median_duration": stats.median_duration,
                "std_dev": stats.std_dev,
                "p95_duration": stats.p95_duration,
                "p99_duration": stats.p99_duration,
                "memory_mb": stats.memory_mb
            }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_baselines(self) -> None:
        """Load baseline results from file."""
        with open(self.baseline_path, "r") as f:
            data = json.load(f)

        for name, stats_data in data.items():
            self.baselines[name] = BenchmarkStats(
                name=stats_data["name"],
                runs=stats_data["runs"],
                min_duration=stats_data["min_duration"],
                max_duration=stats_data["max_duration"],
                mean_duration=stats_data["mean_duration"],
                median_duration=stats_data["median_duration"],
                std_dev=stats_data["std_dev"],
                p95_duration=stats_data["p95_duration"],
                p99_duration=stats_data["p99_duration"],
                memory_mb=stats_data["memory_mb"]
            )


def percentile(data: List[float], p: float) -> float:
    """Calculate percentile of data."""
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def benchmark_function(func: Callable, name: str = None, runs: int = 10) -> BenchmarkStats:
    """
    Convenience function to benchmark a function.

    Args:
        func: Function to benchmark
        name: Benchmark name (defaults to function name)
        runs: Number of runs

    Returns:
        Benchmark statistics
    """
    benchmark = PerformanceBenchmark()
    return benchmark.run_benchmark(name or func.__name__, func, runs)
