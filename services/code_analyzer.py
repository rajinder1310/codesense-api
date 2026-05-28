"""
Static code analyzer using Python's ast module.
Computes complexity, quality score, edge-case gaps, and suggestions.
"""

import ast
from dataclasses import dataclass, field
from typing import List


@dataclass
class AnalysisResult:
    complexity_score: int = 0
    quality_score: int = 100
    edge_cases_missing: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    lines_of_code: int = 0


class _ComplexityVisitor(ast.NodeVisitor):
    """
    Walks the AST and builds up a weighted complexity score.
    Loops get +2, conditionals/functions/classes get +1, nesting adds a multiplier.
    """

    def __init__(self) -> None:
        self.complexity: int = 0
        self._depth: int = 0

        # counters used later for quality scoring
        self.function_count: int = 0
        self.class_count: int = 0
        self.has_docstrings: int = 0
        self.has_type_hints: int = 0
        self.try_except_count: int = 0
        self.bare_except_count: int = 0
        self.assert_count: int = 0
        self.total_function_lines: int = 0
        self.long_functions: int = 0
        self.nested_function_count: int = 0
        self.global_count: int = 0
        self.star_import_count: int = 0

    def _add(self, weight: int = 1) -> None:
        # nesting adds 20% per level
        depth_multiplier = 1 + (self._depth * 0.2)
        self.complexity += int(weight * depth_multiplier)

    def _enter_scope(self) -> None:
        self._depth += 1

    def _exit_scope(self) -> None:
        self._depth -= 1

    def _has_docstring(self, node) -> bool:
        return (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add(1)
        self.function_count += 1

        if self._depth > 0:
            self.nested_function_count += 1

        if self._has_docstring(node):
            self.has_docstrings += 1

        if node.returns is not None:
            self.has_type_hints += 1

        func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        self.total_function_lines += func_lines
        if func_lines > 50:
            self.long_functions += 1

        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add(1)
        self.class_count += 1

        if self._has_docstring(node):
            self.has_docstrings += 1

        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def visit_If(self, node: ast.If) -> None:
        self._add(1)
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._add(1)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._add(2)
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self._add(2)
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def visit_Try(self, node: ast.Try) -> None:
        self._add(1)
        self.try_except_count += 1
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    visit_TryStar = visit_Try

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._add(1)
        if node.type is None:
            self.bare_except_count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self._add(len(node.values) - 1)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._add(1)
        self.generic_visit(node)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._add(1)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._add(1)
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    visit_AsyncWith = visit_With

    def visit_Assert(self, node: ast.Assert) -> None:
        self.assert_count += 1
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.global_count += len(node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.names and any(alias.name == "*" for alias in node.names):
            self.star_import_count += 1
        self.generic_visit(node)


async def analyze_code(source: str) -> AnalysisResult:
    """Run full static analysis on Python source code. Raises SyntaxError if unparseable."""

    result = AnalysisResult()

    # count logical lines (skip blanks and comments)
    lines = source.splitlines()
    result.lines_of_code = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

    # parse and walk the AST
    tree = ast.parse(source)
    visitor = _ComplexityVisitor()
    visitor.visit(tree)
    result.complexity_score = max(1, visitor.complexity)

    # run the sub-analyses
    result.edge_cases_missing = _detect_missing_edge_cases(source, tree, visitor)
    result.suggestions = _generate_suggestions(source, visitor)
    result.quality_score = _compute_quality_score(source, visitor, result)

    return result


def _detect_missing_edge_cases(source: str, tree: ast.Module, visitor: _ComplexityVisitor) -> List[str]:
    """Check for common gaps: missing guards, division by zero, recursion without base case, etc."""

    issues: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = node.args
            param_count = len(params.args) + len(params.posonlyargs) + len(params.kwonlyargs)
            if params.args and params.args[0].arg in ("self", "cls"):
                param_count -= 1

            if param_count > 0:
                has_guard = any(isinstance(c, (ast.If, ast.Raise, ast.Assert)) for c in ast.walk(node))
                if not has_guard:
                    issues.append(f"Function '{node.name}' accepts parameters but has no input validation")

    # check for division without zero guard
    for node in ast.walk(tree):
        if isinstance(node, (ast.Div, ast.FloorDiv)):
            if "ZeroDivisionError" not in source and "!= 0" not in source and "== 0" not in source:
                issues.append("Division operation found without zero-division guard")
                break

    # recursion without base case
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_recursion(node, issues)

    if visitor.try_except_count == 0 and visitor.function_count > 2:
        issues.append("No try/except blocks found - consider adding error handling")

    if visitor.bare_except_count > 0:
        issues.append(f"Found {visitor.bare_except_count} bare 'except:' clause(s) - catch specific exceptions")

    return issues


def _check_recursion(func_node, issues: List[str]) -> None:
    """Flag recursive functions that don't have an obvious base case."""
    func_name = func_node.name
    is_recursive = False
    has_base_case = False

    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == func_name:
            is_recursive = True
        if isinstance(node, ast.If):
            for child in ast.walk(node):
                if isinstance(child, ast.Return):
                    has_base_case = True

    if is_recursive and not has_base_case:
        issues.append(f"Function '{func_name}' looks recursive but has no conditional base-case return")


def _generate_suggestions(source: str, visitor: _ComplexityVisitor) -> List[str]:
    """Build actionable improvement suggestions based on what the visitor found."""

    suggestions: List[str] = []
    documentable = visitor.function_count + visitor.class_count

    if documentable > 0 and (visitor.has_docstrings / documentable) < 0.5:
        suggestions.append(
            f"Only {visitor.has_docstrings}/{documentable} functions/classes have docstrings - add more"
        )

    if visitor.function_count > 0 and (visitor.has_type_hints / visitor.function_count) < 0.5:
        suggestions.append("Add return-type annotations for better readability")

    if visitor.long_functions > 0:
        suggestions.append(f"{visitor.long_functions} function(s) exceed 50 lines - break them up")

    if visitor.global_count > 0:
        suggestions.append(f"Avoid 'global' ({visitor.global_count} usage(s)) - pass state via params instead")

    if visitor.star_import_count > 0:
        suggestions.append("Replace 'from X import *' with explicit imports")

    if visitor.bare_except_count > 0:
        suggestions.append("Replace bare 'except:' with specific exception types")

    if visitor.complexity > 20:
        suggestions.append("High complexity - refactor nested logic into helper functions")

    if visitor.try_except_count == 0 and visitor.function_count >= 1:
        suggestions.append("Consider adding try/except for potential runtime errors")

    if visitor.nested_function_count > 2:
        suggestions.append(f"{visitor.nested_function_count} nested functions found - consider moving to module level")

    if visitor.assert_count > 0 and "test_" not in source[:200]:
        suggestions.append("Prefer raising exceptions over assert in production code")

    return suggestions


def _compute_quality_score(source: str, visitor: _ComplexityVisitor, result: AnalysisResult) -> int:
    """
    Quality score (0-100) based on:
      - documentation coverage (20 pts)
      - complexity penalty (25 pts)
      - edge case issues (20 pts)
      - best practices (20 pts)
      - code structure (15 pts)
    """

    score = 100
    documentable = visitor.function_count + visitor.class_count

    # documentation: up to -20
    if documentable > 0:
        doc_ratio = visitor.has_docstrings / documentable
        score -= int((1 - doc_ratio) * 12)
        if visitor.function_count > 0:
            hint_ratio = visitor.has_type_hints / visitor.function_count
            score -= int((1 - hint_ratio) * 8)

    # complexity: up to -25
    if visitor.complexity > 10:
        score -= min(25, (visitor.complexity - 10) * 2)

    # edge cases: up to -20
    score -= min(20, len(result.edge_cases_missing) * 5)

    # best practices: up to -20
    if visitor.global_count > 0:
        score -= min(6, visitor.global_count * 2)
    if visitor.star_import_count > 0:
        score -= min(6, visitor.star_import_count * 3)
    if visitor.bare_except_count > 0:
        score -= min(8, visitor.bare_except_count * 4)

    # structure: up to -15
    if visitor.long_functions > 0:
        score -= min(10, visitor.long_functions * 5)
    if visitor.nested_function_count > 2:
        score -= 5

    return max(0, min(100, score))
