"""
Code Analyzer

Analyzes source code to extract information for intelligent test generation.
"""

import ast
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    complexity: int = 1
    has_side_effects: bool = False
    dependencies: Set[str] = field(default_factory=set)
    raises: List[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ModuleInfo:
    """Information about a module."""
    name: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    lines_of_code: int = 0
    complexity: int = 1


class CodeAnalyzer:
    """
    Analyzes source code to extract information for test generation.

    Features:
    - Function signature analysis
    - Complexity metrics
    - Dependency tracking
    - Side effect detection
    - Exception identification
    """

    def __init__(self):
        """Initialize the code analyzer."""
        self.current_module: Optional[ModuleInfo] = None

    def analyze(self, source_path: str) -> Dict[str, Any]:
        """
        Analyze source code and return analysis results.

        Args:
            source_path: Path to source file or directory

        Returns:
            Dictionary containing analysis results
        """
        source = Path(source_path)

        if source.is_file():
            return self._analyze_file(source)
        else:
            results = {}
            for py_file in source.rglob("*.py"):
                results[str(py_file)] = self._analyze_file(py_file)
            return results

    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a single Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary containing analysis results
        """
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)

        # Create module info
        module_info = ModuleInfo(
            name=file_path.stem,
            lines_of_code=len(code.splitlines())
        )

        # Analyze imports
        module_info.imports = self._extract_imports(tree)

        # Analyze functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and self._is_top_level_function(node, tree):
                func_info = self._analyze_function(node)
                module_info.functions.append(func_info)
                module_info.complexity += func_info.complexity

            elif isinstance(node, ast.AsyncFunctionDef) and self._is_top_level_function(node, tree):
                func_info = self._analyze_function(node, is_async=True)
                module_info.functions.append(func_info)
                module_info.complexity += func_info.complexity

            elif isinstance(node, ast.ClassDef) and self._is_top_level_class(node, tree):
                class_info = self._analyze_class(node)
                module_info.classes.append(class_info)
                module_info.complexity += sum(m.complexity for m in class_info.methods)

        # Calculate dependencies
        module_info.dependencies = self._calculate_dependencies(module_info)

        return {
            "module": module_info.name,
            "functions": [self._function_to_dict(f) for f in module_info.functions],
            "classes": [self._class_to_dict(c) for c in module_info.classes],
            "imports": module_info.imports,
            "dependencies": list(module_info.dependencies),
            "lines_of_code": module_info.lines_of_code,
            "complexity": module_info.complexity,
            "testability_score": self._calculate_testability_score(module_info)
        }

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        return imports

    def _analyze_function(self, func_node: ast.FunctionDef, is_async: bool = False) -> FunctionInfo:
        """
        Analyze a function node.

        Args:
            func_node: Function AST node
            is_async: Whether this is an async function

        Returns:
            FunctionInfo object
        """
        func_info = FunctionInfo(
            name=func_node.name,
            decorators=self._extract_decorators(func_node),
            docstring=ast.get_docstring(func_node),
            is_async=is_async
        )

        # Extract parameters
        for arg in func_node.args.args:
            func_info.parameters.append(arg.arg)

        # Extract return type annotation
        if func_node.returns:
            func_info.return_type = ast.unparse(func_node.returns)

        # Calculate complexity (McCabe's cyclomatic complexity)
        func_info.complexity = self._calculate_function_complexity(func_node)

        # Detect side effects
        func_info.has_side_effects = self._detect_side_effects(func_node)

        # Extract exceptions raised
        func_info.raises = self._extract_raised_exceptions(func_node)

        return func_info

    def _analyze_class(self, class_node: ast.ClassDef) -> ClassInfo:
        """
        Analyze a class node.

        Args:
            class_node: Class AST node

        Returns:
            ClassInfo object
        """
        class_info = ClassInfo(
            name=class_node.name,
            docstring=ast.get_docstring(class_node)
        )

        # Extract base classes
        for base in class_node.bases:
            class_info.bases.append(ast.unparse(base))

        # Analyze methods
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = self._analyze_function(node)
                class_info.methods.append(method_info)
            elif isinstance(node, ast.AsyncFunctionDef):
                method_info = self._analyze_function(node, is_async=True)
                class_info.methods.append(method_info)
            elif isinstance(node, ast.Assign):
                # Extract class attributes
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        class_info.attributes.append(target.id)

        return class_info

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity of a function.

        Args:
            func_node: Function AST node

        Returns:
            Complexity score
        """
        complexity = 1  # Base complexity

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _detect_side_effects(self, func_node: ast.FunctionDef) -> bool:
        """
        Detect if a function has side effects.

        Args:
            func_node: Function AST node

        Returns:
            True if function has side effects
        """
        side_effect_indicators = [
            ast.Assign,  # Assignment
            ast.AugAssign,  # Augmented assignment
            ast.Delete,  # Deletion
            ast.Call,  # Function calls (potential side effects)
        ]

        for node in ast.walk(func_node):
            # Check for I/O operations
            if isinstance(node, ast.Call):
                func_name = ast.unparse(node.func)
                if any(keyword in func_name.lower() for keyword in ["print", "write", "read", "open"]):
                    return True

            # Check for mutations
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.Delete)):
                return True

        return False

    def _extract_raised_exceptions(self, func_node: ast.FunctionDef) -> List[str]:
        """
        Extract exceptions raised by a function.

        Args:
            func_node: Function AST node

        Returns:
            List of exception types
        """
        exceptions = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Name):
                    exceptions.append(node.exc.id)
                elif isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        exceptions.append(node.exc.func.id)

        # Also check docstring
        docstring = ast.get_docstring(func_node)
        if docstring:
            lines = docstring.split("\n")
            in_raises = False
            for line in lines:
                if "Raises:" in line:
                    in_raises = True
                elif in_raises and ":" in line:
                    exc = line.split(":")[0].strip()
                    if exc and exc not in exceptions:
                        exceptions.append(exc)

        return exceptions

    def _extract_decorators(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract decorator names from function."""
        decorators = []
        for decorator in func_node.decorator_list:
            decorators.append(ast.unparse(decorator))
        return decorators

    def _is_top_level_function(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is defined at module level."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item == func_node:
                        return False
        return True

    def _is_top_level_class(self, class_node: ast.ClassDef, tree: ast.AST) -> bool:
        """Check if class is defined at module level."""
        for node in ast.iter_child_nodes(tree):
            if node == class_node:
                return True
        return False

    def _calculate_dependencies(self, module_info: ModuleInfo) -> Set[str]:
        """Calculate module dependencies."""
        deps = set()

        for func in module_info.functions:
            deps.update(func.dependencies)

        for cls in module_info.classes:
            for method in cls.methods:
                deps.update(method.dependencies)

        return deps

    def _calculate_testability_score(self, module_info: ModuleInfo) -> float:
        """
        Calculate testability score (0-100).

        Factors:
        - Low complexity = higher score
        - No side effects = higher score
        - Good documentation = higher score
        """
        score = 100.0

        # Penalty for high complexity
        avg_complexity = module_info.complexity / max(1, len(module_info.functions) + len(module_info.classes))
        if avg_complexity > 10:
            score -= 30
        elif avg_complexity > 5:
            score -= 15

        # Penalty for side effects
        side_effect_count = sum(1 for f in module_info.functions if f.has_side_effects)
        for cls in module_info.classes:
            side_effect_count += sum(1 for m in cls.methods if m.has_side_effects)

        if side_effect_count > len(module_info.functions) * 0.5:
            score -= 20

        # Penalty for missing documentation
        documented = sum(1 for f in module_info.functions if f.docstring)
        for cls in module_info.classes:
            documented += sum(1 for m in cls.methods if m.docstring)

        total_funcs = len(module_info.functions) + sum(len(c.methods) for c in module_info.classes)
        if total_funcs > 0 and documented / total_funcs < 0.5:
            score -= 20

        return max(0.0, min(100.0, score))

    def _function_to_dict(self, func: FunctionInfo) -> Dict[str, Any]:
        """Convert FunctionInfo to dictionary."""
        return {
            "name": func.name,
            "parameters": func.parameters,
            "return_type": func.return_type,
            "decorators": func.decorators,
            "docstring": func.docstring,
            "complexity": func.complexity,
            "has_side_effects": func.has_side_effects,
            "raises": func.raises,
            "is_async": func.is_async
        }

    def _class_to_dict(self, cls: ClassInfo) -> Dict[str, Any]:
        """Convert ClassInfo to dictionary."""
        return {
            "name": cls.name,
            "bases": cls.bases,
            "methods": [self._function_to_dict(m) for m in cls.methods],
            "attributes": cls.attributes,
            "docstring": cls.docstring
        }


def analyze_code(source_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze code.

    Args:
        source_path: Path to source code

    Returns:
        Analysis results
    """
    analyzer = CodeAnalyzer()
    return analyzer.analyze(source_path)
