"""
GitLab CI Generator

Generates GitLab CI pipelines for automated testing.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional


class GitLabCIGenerator:
    """
    Generates GitLab CI pipelines for automated testing.

    Features:
    - Multi-language support
    - Staged pipelines
    - Coverage reports
    - Performance tests
    - Artifact management
    """

    def __init__(self):
        """Initialize GitLab CI generator."""
        self.pipelines: Dict[str, str] = {}

    def generate_pipeline(
        self,
        language: str,
        test_command: str,
        coverage_command: Optional[str] = None,
        stages: Optional[List[str]] = None,
        image: Optional[str] = None
    ) -> str:
        """
        Generate GitLab CI pipeline.

        Args:
            language: Programming language
            test_command: Test command
            coverage_command: Coverage command (optional)
            stages: Pipeline stages (optional)
            image: Docker image to use (optional)

        Returns:
            Generated GitLab CI YAML
        """
        if stages is None:
            stages = ["test", "report"]

        pipeline = f"""image: {image or 'python:3.10'}

stages:
"""

        for stage in stages:
            pipeline += f"  - {stage}\n"

        pipeline += f"""
variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m pip install --upgrade pip
  - pip install -r requirements.txt

"""

        # Test job
        pipeline += self._generate_test_job(language, test_command, coverage_command)

        # Report job (if coverage)
        if coverage_command:
            pipeline += self._generate_report_job()

        return pipeline

    def _generate_test_job(
        self,
        language: str,
        test_command: str,
        coverage_command: Optional[str]
    ) -> str:
        """Generate test job."""
        if coverage_command:
            test_cmd = coverage_command
            coverage_report = "artifacts:\n    reports:\n      coverage_report:\n        coverage_format: cobertura\n        path: coverage.xml\n    paths:\n      - coverage.xml\n      - htmlcov/\n    expire_in: 1 week\n"
        else:
            test_cmd = test_command
            coverage_report = ""

        return f"""test:
  stage: test
  script:
    - {test_cmd}
  {coverage_report}  coverage: '/^TOTAL.*\\s+(\\d+\\.\\d+%)/'
  only:
    - branches
    - merge_requests
  tags:
    - docker

"""

    def _generate_report_job(self) -> str:
        """Generate report job."""
        return """report:
  stage: report
  script:
    - echo "Generating test reports..."
  dependencies:
    - test
  artifacts:
    paths:
      - htmlcov/
    expire_in: 30 days
  only:
    - main
    - master
  tags:
    - docker

"""

    def generate_performance_pipeline(
        self,
        benchmark_command: str,
        baseline_threshold: float = 0.1
    ) -> str:
        """
        Generate performance testing pipeline.

        Args:
            benchmark_command: Command to run benchmarks
            baseline_threshold: Regression threshold

        Returns:
            Generated pipeline YAML
        """
        return f"""image: python:3.10

stages:
  - benchmark
  - compare

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m pip install --upgrade pip
  - pip install -r requirements.txt

benchmark:
  stage: benchmark
  script:
    - {benchmark_command}
    - python -c "import json; data = json.load(open('benchmark_results.json')); print(f'Average Duration: {{data[\"mean_duration\"]:.3f}}s')"
  artifacts:
    paths:
      - benchmark_results.json
      - benchmark_history.json
    expire_in: 30 days
  only:
    - branches
    - merge_requests
  tags:
    - docker

compare:
  stage: compare
  script:
    - python -c "
import json
import sys

# Load current results
with open('benchmark_results.json', 'r') as f:
    current = json.load(f)

# Load baseline if exists
try:
    with open('benchmark_history.json', 'r') as f:
        history = json.load(f)
    baseline = history[-1]
except:
    baseline = None

if baseline:
    duration_diff = ((current['mean_duration'] - baseline['mean_duration']) / baseline['mean_duration'])
    threshold = {baseline_threshold}

    if duration_diff > threshold:
        print(f'PERFORMANCE REGRESSION: {{duration_diff * 100:.1f}}% slower than baseline')
        sys.exit(1)
    else:
        print(f'Performance OK: {{duration_diff * 100:+.1f}}% change')
else:
    print('No baseline found, saving current results')

# Add current results to history
history.append(current)
with open('benchmark_history.json', 'w') as f:
    json.dump(history, f, indent=2)
"
  dependencies:
    - benchmark
  artifacts:
    paths:
      - benchmark_history.json
    expire_in: 90 days
  only:
    - main
    - master
  tags:
    - docker

"""

    def generate_matrix_pipeline(
        self,
        language: str,
        versions: List[str],
        test_command: str
    ) -> str:
        """
        Generate matrix testing pipeline.

        Args:
            language: Programming language
            versions: List of versions to test
            test_command: Test command

        Returns:
            Generated pipeline YAML
        """
        jobs = ""
        for version in versions:
            image = self._get_image(language, version)
            jobs += f"""test-{version.replace('.', '-')}:
  stage: test
  image: {image}
  script:
    - python -m pip install --upgrade pip
    - pip install -r requirements.txt
    - {test_command}
  only:
    - branches
    - merge_requests
  tags:
    - docker

"""

        return f"""stages:
  - test

{jobs}
"""

    def _get_image(self, language: str, version: str) -> str:
        """Get Docker image for language version."""
        if language == "python":
            return f"python:{version}"
        elif language == "node":
            return f"node:{version}"
        elif language == "ruby":
            return f"ruby:{version}"
        else:
            return f"{language}:{version}"

    def save_pipeline(
        self,
        pipeline_yaml: str,
        output_path: str = ".gitlab-ci.yml"
    ) -> None:
        """
        Save pipeline to file.

        Args:
            pipeline_yaml: Pipeline YAML content
            output_path: Output file path
        """
        with open(output_path, "w") as f:
            f.write(pipeline_yaml)


def generate_gitlab_pipeline(
    language: str,
    test_command: str,
    coverage_command: Optional[str] = None
) -> str:
    """
    Convenience function to generate GitLab CI pipeline.

    Args:
        language: Programming language
        test_command: Test command
        coverage_command: Coverage command (optional)

    Returns:
        Generated pipeline YAML
    """
    generator = GitLabCIGenerator()
    return generator.generate_pipeline(language, test_command, coverage_command)
