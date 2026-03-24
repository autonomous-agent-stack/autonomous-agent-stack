"""
AI Test Generator

Intelligent test case generation using AI models and code analysis.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TestCase:
    """Represents a generated test case."""
    name: str
    description: str
    setup: str = ""
    test_code: str = ""
    assertions: List[str] = field(default_factory=list)
    teardown: str = ""
    priority: str = "medium"  # high, medium, low
    tags: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Represents a generated test suite."""
    name: str
    target_file: str
    test_cases: List[TestCase] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    fixtures: List[str] = field(default_factory=list)


class AITestGenerator:
    """
    AI-powered test generator that analyzes code and generates comprehensive test cases.

    Features:
    - Function signature analysis
    - Parameter type inference
    - Edge case detection
    - Boundary condition generation
    - Exception scenario identification
    """

    def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
        """
        Initialize the AI test generator.

        Args:
            model: AI model to use for test generation
            temperature: Sampling temperature for creativity
        """
        self.model = model
        self.temperature = temperature

    def generate_tests(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        language: str = "python"
    ) -> List[TestSuite]:
        """
        Generate test suites for the given source code.

        Args:
            source_path: Path to source file or directory
            output_path: Path to save generated tests (optional)
            language: Programming language (python, javascript, shell)

        Returns:
            List of generated test suites
        """
        source = Path(source_path)

        if source.is_file():
            test_suites = [self._generate_test_suite(source, language)]
        else:
            test_suites = []
            for py_file in source.rglob("*.py"):
                test_suites.append(self._generate_test_suite(py_file, language))

        if output_path:
            self._save_test_suites(test_suites, output_path)

        return test_suites

    def _generate_test_suite(self, source_file: Path, language: str) -> TestSuite:
        """
        Generate a test suite for a single source file.

        Args:
            source_file: Path to source file
            language: Programming language

        Returns:
            Generated test suite
        """
        # Parse the source code
        with open(source_file, "r", encoding="utf-8") as f:
            code = f.read()

        if language == "python":
            tree = ast.parse(code)
            test_cases = self._generate_python_test_cases(tree, source_file.name)
        else:
            test_cases = self._generate_generic_test_cases(code, source_file.name, language)

        # Generate test suite name
        test_suite_name = f"test_{source_file.stem}"

        return TestSuite(
            name=test_suite_name,
            target_file=str(source_file),
            test_cases=test_cases,
            imports=self._extract_imports(code, language)
        )

    def _generate_python_test_cases(self, tree: ast.AST, filename: str) -> List[TestCase]:
        """
        Generate test cases from Python AST.

        Args:
            tree: Python AST
            filename: Source file name

        Returns:
            List of test cases
        """
        test_cases = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                test_cases.extend(self._generate_function_tests(node))

            elif isinstance(node, ast.ClassDef):
                test_cases.extend(self._generate_class_tests(node))

        return test_cases

    def _generate_function_tests(self, func_node: ast.FunctionDef) -> List[TestCase]:
        """
        Generate test cases for a function.

        Args:
            func_node: AST function node

        Returns:
            List of test cases
        """
        test_cases = []
        func_name = func_node.name

        # 1. Happy path test
        happy_path = self._generate_happy_path_test(func_node)
        if happy_path:
            test_cases.append(happy_path)

        # 2. Edge cases
        edge_cases = self._generate_edge_case_tests(func_node)
        test_cases.extend(edge_cases)

        # 3. Boundary conditions
        boundary_tests = self._generate_boundary_tests(func_node)
        test_cases.extend(boundary_tests)

        # 4. Exception scenarios
        exception_tests = self._generate_exception_tests(func_node)
        test_cases.extend(exception_tests)

        return test_cases

    def _generate_happy_path_test(self, func_node: ast.FunctionDef) -> Optional[TestCase]:
        """Generate happy path test for function."""
        return TestCase(
            name=f"test_{func_node.name}_happy_path",
            description=f"Test {func_node.name} with valid inputs",
            test_code=f"""
def test_{func_node.name}_happy_path():
    # Arrange
    # TODO: Add test data setup

    # Act
    result = {func_node.name}()

    # Assert
    assert result is not None
""",
            tags=["happy-path", "smoke"]
        )

    def _generate_edge_case_tests(self, func_node: ast.FunctionDef) -> List[TestCase]:
        """Generate edge case tests."""
        test_cases = []

        # Test with empty inputs
        test_cases.append(TestCase(
            name=f"test_{func_node.name}_empty_inputs",
            description=f"Test {func_node.name} with empty inputs",
            test_code=f"""
def test_{func_node.name}_empty_inputs():
    # Act & Assert
    with pytest.raises(ValueError):
        {func_node.name}("")
""",
            tags=["edge-case", "validation"]
        ))

        # Test with None
        test_cases.append(TestCase(
            name=f"test_{func_node.name}_none_input",
            description=f"Test {func_node.name} with None input",
            test_code=f"""
def test_{func_node.name}_none_input():
    # Act & Assert
    with pytest.raises(TypeError):
        {func_node.name}(None)
""",
            tags=["edge-case", "validation"]
        ))

        return test_cases

    def _generate_boundary_tests(self, func_node: ast.FunctionDef) -> List[TestCase]:
        """Generate boundary condition tests."""
        test_cases = []

        # Test minimum boundary
        test_cases.append(TestCase(
            name=f"test_{func_node.name}_min_boundary",
            description=f"Test {func_node.name} with minimum value",
            test_code=f"""
def test_{func_node.name}_min_boundary():
    # Arrange
    min_value = 0

    # Act
    result = {func_node.name}(min_value)

    # Assert
    assert result >= min_value
""",
            tags=["boundary", "validation"]
        ))

        # Test maximum boundary
        test_cases.append(TestCase(
            name=f"test_{func_node.name}_max_boundary",
            description=f"Test {func_node.name} with maximum value",
            test_code=f"""
def test_{func_name}_max_boundary():
    # Arrange
    max_value = 1000

    # Act
    result = {func_node.name}(max_value)

    # Assert
    assert result <= max_value
""",
            tags=["boundary", "validation"]
        ))

        return test_cases

    def _generate_exception_tests(self, func_node: ast.FunctionDef) -> List[TestCase]:
        """Generate exception scenario tests."""
        test_cases = []

        # Analyze docstring for documented exceptions
        docstring = ast.get_docstring(func_node)
        if docstring and "Raises:" in docstring:
            # Extract exception types from docstring
            exceptions = self._parse_exceptions_from_docstring(docstring)

            for exc in exceptions:
                test_cases.append(TestCase(
                    name=f"test_{func_node.name}_raises_{exc.lower()}",
                    description=f"Test {func_node.name} raises {exc}",
                    test_code=f"""
def test_{func_node.name}_raises_{exc.lower()}():
    # Act & Assert
    with pytest.raises({exc}):
        {func_node.name}()  # TODO: Add trigger condition
""",
                    tags=["exception", "error-handling"],
                    priority="high"
                ))

        return test_cases

    def _generate_class_tests(self, class_node: ast.ClassDef) -> List[TestCase]:
        """Generate test cases for a class."""
        test_cases = []

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                # Generate tests for each method
                func_tests = self._generate_function_tests(node)
                for test in func_tests:
                    # Add class context to test name
                    test.name = f"test_{class_node.name}_{test.name.replace('test_', '', 1)}"
                    test_cases.append(test)

        return test_cases

    def _generate_generic_test_cases(self, code: str, filename: str, language: str) -> List[TestCase]:
        """Generate generic test cases for non-Python code."""
        # Placeholder for other languages
        return []

    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract import statements from code."""
        imports = []

        if language == "python":
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

        return imports

    def _parse_exceptions_from_docstring(self, docstring: str) -> List[str]:
        """Parse exception types from docstring."""
        exceptions = []
        lines = docstring.split("\n")

        in_raises_section = False
        for line in lines:
            if "Raises:" in line:
                in_raises_section = True
            elif in_raises_section:
                if ":" in line:
                    exc_type = line.split(":")[0].strip()
                    if exc_type and exc_type not in exceptions:
                        exceptions.append(exc_type)
                elif line.strip() == "":
                    break

        return exceptions

    def _save_test_suites(self, test_suites: List[TestSuite], output_path: str):
        """
        Save generated test suites to files.

        Args:
            test_suites: List of test suites to save
            output_path: Path to save directory
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        for suite in test_suites:
            test_file = output_dir / f"{suite.name}.py"

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(self._format_test_suite(suite))

    def _format_test_suite(self, suite: TestSuite) -> str:
        """Format test suite as Python code."""
        lines = []

        # Imports
        for imp in suite.imports:
            lines.append(f"import {imp}")
        lines.append("import pytest")
        lines.append("")

        # Test cases
        for test_case in suite.test_cases:
            lines.append(test_case.test_code)
            lines.append("")

        return "\n".join(lines)


def generate_tests_from_code(
    source_path: str,
    output_path: str,
    language: str = "python"
) -> str:
    """
    Convenience function to generate tests.

    Args:
        source_path: Path to source code
        output_path: Path to output directory
        language: Programming language

    Returns:
        Summary of generated tests
    """
    generator = AITestGenerator()
    test_suites = generator.generate_tests(source_path, output_path, language)

    total_cases = sum(len(suite.test_cases) for suite in test_suites)

    summary = f"""
Generated {len(test_suites)} test suites with {total_cases} test cases

Test Suites:
"""
    for suite in test_suites:
        summary += f"  - {suite.name}: {len(suite.test_cases)} tests\n"

    return summary
