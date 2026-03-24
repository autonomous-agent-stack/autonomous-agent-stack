"""
GitHub Actions Generator

Generates GitHub Actions workflows for automated testing.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional


class GitHubActionsGenerator:
    """
    Generates GitHub Actions workflows for automated testing.

    Features:
    - Multi-language support
    - Test matrix configurations
    - Coverage reports
    - Performance tests
    - Notification integration
    """

    def __init__(self):
        """Initialize GitHub Actions generator."""
        self.workflows: Dict[str, str] = {}

    def generate_workflow(
        self,
        name: str,
        language: str,
        test_command: str,
        coverage_command: Optional[str] = None,
        python_version: Optional[List[str]] = None,
        trigger_events: Optional[List[str]] = None
    ) -> str:
        """
        Generate GitHub Actions workflow.

        Args:
            name: Workflow name
            language: Programming language (python, javascript, etc.)
            test_command: Command to run tests
            coverage_command: Command to run coverage (optional)
            python_version: Python versions for matrix (optional)
            trigger_events: Trigger events (optional)

        Returns:
            Generated workflow YAML
        """
        if trigger_events is None:
            trigger_events = ["push", "pull_request"]

        workflow = f"""name: {name}

on:
"""

        for event in trigger_events:
            workflow += f"  {event}:\n"
            if isinstance(event, list) and len(event) == 1 and event[0] == "schedule":
                workflow += "    - cron: '0 0 * * 0'\n"

        workflow += f"""

jobs:
"""

        if language == "python":
            workflow += self._generate_python_job(
                test_command,
                coverage_command,
                python_version
            )
        elif language == "javascript":
            workflow += self._generate_javascript_job(test_command, coverage_command)
        else:
            workflow += self._generate_generic_job(test_command, coverage_command)

        return workflow

    def _generate_python_job(
        self,
        test_command: str,
        coverage_command: Optional[str],
        python_version: Optional[List[str]]
    ) -> str:
        """Generate Python job."""
        versions = python_version or ["3.8", "3.9", "3.10", "3.11", "3.12"]

        job = f"""  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: {versions}

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}

    - name: Cache pip packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{{{ runner.os }}}}-pip-${{{{ hashFiles('**/requirements.txt') }}}}
        restore-keys: |
          ${{{{ runner.os }}}}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

"""

        if coverage_command:
            job += f"""    - name: Run tests with coverage
      run: {coverage_command}

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        token: ${{{{ secrets.CODECOV_TOKEN }}}}
        files: ./coverage.xml
        flags: unittests

"""
        else:
            job += f"""    - name: Run tests
      run: {test_command}

"""

        return job

    def _generate_javascript_job(
        self,
        test_command: str,
        coverage_command: Optional[str]
    ) -> str:
        """Generate JavaScript job."""
        job = """  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16, 18, 20]

    steps:
    - uses: actions/checkout@v4

    - name: Use Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}

    - name: Cache node modules
      uses: actions/cache@v3
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-

    - name: Install dependencies
      run: npm ci

"""

        if coverage_command:
            job += f"""    - name: Run tests with coverage
      run: {coverage_command}

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        token: ${{ secrets.CODECOV_TOKEN }}}
        files: ./coverage/lcov.info
        flags: unittests

"""
        else:
            job += f"""    - name: Run tests
      run: {test_command}

"""

        return job

    def _generate_generic_job(
        self,
        test_command: str,
        coverage_command: Optional[str]
    ) -> str:
        """Generate generic job."""
        job = """  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Run tests
      run: """ + test_command + "\n"

        if coverage_command:
            job += f"""
    - name: Run coverage
      run: {coverage_command}

"""

        return job

    def generate_performance_workflow(
        self,
        benchmark_command: str,
        baseline_threshold: float = 0.1
    ) -> str:
        """
        Generate performance testing workflow.

        Args:
            benchmark_command: Command to run benchmarks
            baseline_threshold: Performance regression threshold

        Returns:
            Generated workflow YAML
        """
        return f"""name: Performance Tests

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run benchmarks
      run: {benchmark_command}

    - name: Check for performance regression
      run: |
        python -c "import json; data = json.load(open('benchmark_results.json')); exit(0 if not data.get('has_regression', False) else 1)"

    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmark_results.json

    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('benchmark_results.json', 'utf8'));
          const comment = `## Performance Test Results\\n\\nAverage Duration: ${{results.mean_duration.toFixed(3)}}s\\nRegression Detected: ${{results.has_regression ? 'Yes' : 'No'}}`;
          github.rest.issues.createComment({{
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          }});
"""

    def generate_ci_pipeline(
        self,
        language: str,
        test_command: str,
        lint_command: Optional[str] = None,
        coverage_command: Optional[str] = None,
        security_command: Optional[str] = None
    ) -> str:
        """
        Generate complete CI pipeline workflow.

        Args:
            language: Programming language
            test_command: Test command
            lint_command: Linting command (optional)
            coverage_command: Coverage command (optional)
            security_command: Security scan command (optional)

        Returns:
            Generated workflow YAML
        """
        workflow = f"""name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
"""

        # Lint job
        if lint_command:
            workflow += """  lint:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

"""
            if language == "python":
                workflow += """    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"

    - name: Install dependencies
      run: |
        pip install flake8 pylint black isort

"""
            elif language == "javascript":
                workflow += """    - name: Use Node.js
      uses: actions/setup-node@v3
      with:
        node-version: "18"

    - name: Install dependencies
      run: npm ci

"""

            workflow += f"""    - name: Run linter
      run: {lint_command}

"""

        # Test job
        workflow += """  test:
    runs-on: ubuntu-latest

    steps:
"""

        if language == "python":
            workflow += self._python_setup_steps()
        elif language == "javascript":
            workflow += self._javascript_setup_steps()

        workflow += f"""    - name: Run tests
      run: {test_command}

"""

        # Coverage job
        if coverage_command:
            workflow += f"""    - name: Run coverage
      run: {coverage_command}

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        token: ${{ secrets.CODECOV_TOKEN }}}
        files: ./coverage.xml
        flags: unittests
        fail_ci_if_error: false

"""

        # Security job
        if security_command:
            workflow += f"""  security:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Run security scan
      run: {security_command}

"""

        return workflow

    def _python_setup_steps(self) -> str:
        """Generate Python setup steps."""
        return """    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"

    - name: Cache pip packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

"""

    def _javascript_setup_steps(self) -> str:
        """Generate JavaScript setup steps."""
        return """    - name: Use Node.js
      uses: actions/setup-node@v3
      with:
        node-version: "18"

    - name: Cache node modules
      uses: actions/cache@v3
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-

    - name: Install dependencies
      run: npm ci

"""

    def save_workflow(
        self,
        workflow_name: str,
        workflow_yaml: str,
        output_dir: str = ".github/workflows"
    ) -> None:
        """
        Save workflow to file.

        Args:
            workflow_name: Name of workflow file
            workflow_yaml: Workflow YAML content
            output_dir: Output directory
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        workflow_path = Path(output_dir) / workflow_name

        with open(workflow_path, "w") as f:
            f.write(workflow_yaml)


def generate_github_workflow(
    name: str,
    language: str,
    test_command: str,
    coverage_command: Optional[str] = None
) -> str:
    """
    Convenience function to generate GitHub workflow.

    Args:
        name: Workflow name
        language: Programming language
        test_command: Test command
        coverage_command: Coverage command (optional)

    Returns:
        Generated workflow YAML
    """
    generator = GitHubActionsGenerator()
    return generator.generate_workflow(name, language, test_command, coverage_command)
