"""
Test Scenario Discovery

Discovers test scenarios from code analysis and documentation.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TestScenario:
    """Represents a discovered test scenario."""
    name: str
    description: str
    category: str  # functional, integration, performance, security
    priority: str  # critical, high, medium, low
    preconditions: List[str] = field(default_factory=list)
    test_steps: List[str] = field(default_factory=list)
    expected_results: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    test_type: str = "unit"  # unit, integration, e2e


@dataclass
class TestRequirement:
    """Represents a test requirement from documentation."""
    id: str
    description: str
    source: str  # docstring, comment, external doc
    priority: str
    test_scenarios: List[TestScenario] = field(default_factory=list)


class TestScenarioDiscovery:
    """
    Discovers test scenarios from code and documentation.

    Features:
    - Documentation extraction
    - Requirement identification
    - Test scenario generation
    - Test type classification
    """

    def __init__(self):
        """Initialize test scenario discovery."""
        self.requirements: List[TestRequirement] = []

    def discover_scenarios(
        self,
        source_path: str,
        doc_paths: Optional[List[str]] = None
    ) -> Dict[str, List[TestScenario]]:
        """
        Discover test scenarios from code and documentation.

        Args:
            source_path: Path to source code
            doc_paths: Optional list of documentation paths

        Returns:
            Dictionary mapping category to test scenarios
        """
        scenarios = defaultdict(list)

        # Analyze source code
        if Path(source_path).exists():
            code_scenarios = self._discover_from_code(source_path)
            for scenario in code_scenarios:
                scenarios[scenario.category].append(scenario)

        # Analyze documentation
        if doc_paths:
            for doc_path in doc_paths:
                doc_scenarios = self._discover_from_docs(doc_path)
                for scenario in doc_scenarios:
                    scenarios[scenario.category].append(scenario)

        return dict(scenarios)

    def _discover_from_code(self, source_path: str) -> List[TestScenario]:
        """
        Discover test scenarios from source code.

        Args:
            source_path: Path to source code

        Returns:
            List of test scenarios
        """
        scenarios = []
        source = Path(source_path)

        if source.is_file():
            scenarios.extend(self._analyze_source_file(source))
        else:
            for py_file in source.rglob("*.py"):
                scenarios.extend(self._analyze_source_file(py_file))

        return scenarios

    def _analyze_source_file(self, file_path: Path) -> List[TestScenario]:
        """
        Analyze a source file for test scenarios.

        Args:
            file_path: Path to source file

        Returns:
            List of test scenarios
        """
        scenarios = []

        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)

        # Discover scenarios from docstrings
        for node in ast.walk(tree):
            docstring = ast.get_docstring(node)

            if docstring:
                scenarios.extend(self._extract_scenarios_from_docstring(docstring, node))

        # Discover scenarios from TODO/FIXME comments
        scenarios.extend(self._extract_scenarios_from_comments(code))

        # Discover scenarios from type hints
        scenarios.extend(self._extract_scenarios_from_type_hints(tree))

        return scenarios

    def _extract_scenarios_from_docstring(self, docstring: str, node: ast.AST) -> List[TestScenario]:
        """
        Extract test scenarios from docstring.

        Args:
            docstring: Function/class docstring
            node: AST node

        Returns:
            List of test scenarios
        """
        scenarios = []

        # Extract Examples section
        examples_match = re.search(r"Examples?:\s*(.*?)(?=\n\n|\Z)", docstring, re.DOTALL | re.IGNORECASE)
        if examples_match:
            example_text = examples_match.group(1)
            scenario = TestScenario(
                name=f"example_{self._get_node_name(node)}",
                description="Test based on docstring example",
                category="functional",
                priority="high",
                test_steps=[f"Run code example:\n{example_text}"],
                expected_results=["Output matches documented example"],
                tags=["documentation", "example"]
            )
            scenarios.append(scenario)

        # Extract "Note:" sections for edge cases
        note_matches = re.finditer(r"Note:\s*(.*?)(?=\n\n|\n[A-Z]|\Z)", docstring, re.IGNORECASE)
        for i, match in enumerate(note_matches):
            note_text = match.group(1).strip()
            if any(keyword in note_text.lower() for keyword in ["edge", "boundary", "corner", "special"]):
                scenario = TestScenario(
                    name=f"edge_case_{self._get_node_name(node)}_{i}",
                    description=f"Test edge case: {note_text}",
                    category="functional",
                    priority="medium",
                    test_steps=[f"Test edge case: {note_text}"],
                    expected_results=["Correct handling of edge case"],
                    tags=["edge-case", "documentation"]
                )
                scenarios.append(scenario)

        return scenarios

    def _extract_scenarios_from_comments(self, code: str) -> List[TestScenario]:
        """
        Extract test scenarios from code comments.

        Args:
            code: Source code

        Returns:
            List of test scenarios
        """
        scenarios = []

        # Find TODO/FIXME/XXX comments
        todo_pattern = r"#\s*(TODO|FIXME|XXX):\s*(.*?)(?=\n|$)"
        for match in re.finditer(todo_pattern, code):
            tag, description = match.groups()
            scenario = TestScenario(
                name=f"comment_test_{len(scenarios)}",
                description=f"Test for: {description}",
                category="functional",
                priority="medium",
                test_steps=[f"Verify: {description}"],
                expected_results=["Expected behavior implemented"],
                tags=[tag.lower(), "comment"]
            )
            scenarios.append(scenario)

        return scenarios

    def _extract_scenarios_from_type_hints(self, tree: ast.AST) -> List[TestScenario]:
        """
        Extract test scenarios from type hints.

        Args:
            tree: Python AST

        Returns:
            List of test scenarios
        """
        scenarios = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Generate scenarios for type validation
                if node.args.args:
                    scenario = TestScenario(
                        name=f"type_validation_{node.name}",
                        description=f"Validate type hints for {node.name}",
                        category="functional",
                        priority="high",
                        test_steps=[
                            f"Call {node.name} with incorrect type",
                            f"Call {node.name} with correct type"
                        ],
                        expected_results=[
                            "TypeError raised for incorrect type",
                            "Correct behavior for correct type"
                        ],
                        tags=["type-hint", "validation"]
                    )
                    scenarios.append(scenario)

        return scenarios

    def _discover_from_docs(self, doc_path: str) -> List[TestScenario]:
        """
        Discover test scenarios from documentation files.

        Args:
            doc_path: Path to documentation file

        Returns:
            List of test scenarios
        """
        scenarios = []
        doc_file = Path(doc_path)

        if not doc_file.exists():
            return scenarios

        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract scenarios from markdown
        if doc_file.suffix == ".md":
            scenarios.extend(self._extract_scenarios_from_markdown(content))

        # Extract scenarios from requirements documents
        if "requirement" in doc_file.name.lower() or "spec" in doc_file.name.lower():
            scenarios.extend(self._extract_scenarios_from_requirements(content))

        return scenarios

    def _extract_scenarios_from_markdown(self, content: str) -> List[TestScenario]:
        """
        Extract test scenarios from markdown.

        Args:
            content: Markdown content

        Returns:
            List of test scenarios
        """
        scenarios = []

        # Extract test cases marked with "Test:" or "Scenario:"
        pattern = r"###\s*(?:Test|Scenario):\s*(.*?)(?=###|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL):
            title = match.group(1).strip()
            scenario = TestScenario(
                name=f"doc_test_{len(scenarios)}",
                description=title,
                category="functional",
                priority="medium",
                tags=["documentation", "markdown"]
            )
            scenarios.append(scenario)

        return scenarios

    def _extract_scenarios_from_requirements(self, content: str) -> List[TestScenario]:
        """
        Extract test scenarios from requirements.

        Args:
            content: Requirements content

        Returns:
            List of test scenarios
        """
        scenarios = []

        # Extract requirement statements
        req_pattern = r"(\d+\.\d+)?\s*(The system|User|Application)\s+(should|shall|must)\s+(.*?)(?=\n|$)"
        for match in re.finditer(req_pattern, content):
            req_id, actor, modal, description = match.groups()
            requirement = TestRequirement(
                id=req_id or f"req_{len(scenarios)}",
                description=f"{actor} {modal} {description}",
                source="requirements"
            )

            # Generate test scenario from requirement
            scenario = TestScenario(
                name=f"req_{requirement.id}",
                description=f"Verify requirement: {requirement.description}",
                category="functional",
                priority="high",
                test_steps=[
                    f"Precondition: Setup as described in requirement",
                    f"Action: {description}",
                    f"Verify: System {modal} as specified"
                ],
                expected_results=["Requirement satisfied"],
                tags=["requirement", "verification"]
            )

            requirement.test_scenarios.append(scenario)
            scenarios.append(scenario)
            self.requirements.append(requirement)

        return scenarios

    def _get_node_name(self, node: ast.AST) -> str:
        """Get the name of an AST node."""
        if isinstance(node, ast.FunctionDef):
            return node.name
        elif isinstance(node, ast.ClassDef):
            return node.name
        else:
            return "unknown"

    def categorize_scenarios(self, scenarios: List[TestScenario]) -> Dict[str, List[TestScenario]]:
        """
        Categorize scenarios by type.

        Args:
            scenarios: List of test scenarios

        Returns:
            Dictionary mapping category to scenarios
        """
        categorized = defaultdict(list)
        for scenario in scenarios:
            categorized[scenario.category].append(scenario)
        return dict(categorized)

    def prioritize_scenarios(self, scenarios: List[TestScenario]) -> List[TestScenario]:
        """
        Sort scenarios by priority.

        Args:
            scenarios: List of test scenarios

        Returns:
            Sorted list of scenarios
        """
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            scenarios,
            key=lambda s: (priority_order.get(s.priority, 4), -len(s.tags))
        )


def discover_test_scenarios(
    source_path: str,
    doc_paths: Optional[List[str]] = None
) -> Dict[str, List[TestScenario]]:
    """
    Convenience function to discover test scenarios.

    Args:
        source_path: Path to source code
        doc_paths: Optional list of documentation paths

    Returns:
        Dictionary mapping category to test scenarios
    """
    discovery = TestScenarioDiscovery()
    return discovery.discover_scenarios(source_path, doc_paths)
