"""
Benchmark engine - evaluates candidate solutions by running them
against pre-built test suites for common algorithm problems.

Note: code runs via exec() in a limited namespace. For real production,
use a container sandbox instead.
"""

import ast
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class TestCase:
    description: str
    args: Tuple[Any, ...]
    expected: Any
    is_edge_case: bool = False


@dataclass
class BenchmarkResult:
    passed_tests: int = 0
    failed_tests: int = 0
    correctness_score: int = 0
    edge_cases_handled: bool = True
    execution_time_ms: float = 0.0
    feedback: str = ""


# test suites for supported problem types

def _factorial_tests() -> List[TestCase]:
    return [
        TestCase("factorial(0)", (0,), 1, is_edge_case=True),
        TestCase("factorial(1)", (1,), 1, is_edge_case=True),
        TestCase("factorial(5)", (5,), 120),
        TestCase("factorial(10)", (10,), 3628800),
        TestCase("factorial(3)", (3,), 6),
    ]


def _fibonacci_tests() -> List[TestCase]:
    return [
        TestCase("fibonacci(0)", (0,), 0, is_edge_case=True),
        TestCase("fibonacci(1)", (1,), 1, is_edge_case=True),
        TestCase("fibonacci(2)", (2,), 1),
        TestCase("fibonacci(5)", (5,), 5),
        TestCase("fibonacci(10)", (10,), 55),
    ]


def _is_palindrome_tests() -> List[TestCase]:
    return [
        TestCase("is_palindrome('')", ("",), True, is_edge_case=True),
        TestCase("is_palindrome('a')", ("a",), True, is_edge_case=True),
        TestCase("is_palindrome('racecar')", ("racecar",), True),
        TestCase("is_palindrome('hello')", ("hello",), False),
        TestCase("is_palindrome('madam')", ("madam",), True),
    ]


def _reverse_string_tests() -> List[TestCase]:
    return [
        TestCase("reverse_string('')", ("",), "", is_edge_case=True),
        TestCase("reverse_string('a')", ("a",), "a", is_edge_case=True),
        TestCase("reverse_string('hello')", ("hello",), "olleh"),
        TestCase("reverse_string('Python')", ("Python",), "nohtyP"),
    ]


def _two_sum_tests() -> List[TestCase]:
    return [
        TestCase("two_sum([], 1)", ([], 1), [], is_edge_case=True),
        TestCase("two_sum([2,7,11,15], 9)", ([2, 7, 11, 15], 9), [0, 1]),
        TestCase("two_sum([3,2,4], 6)", ([3, 2, 4], 6), [1, 2]),
        TestCase("two_sum([3,3], 6)", ([3, 3], 6), [0, 1]),
    ]


def _is_prime_tests() -> List[TestCase]:
    return [
        TestCase("is_prime(0)", (0,), False, is_edge_case=True),
        TestCase("is_prime(1)", (1,), False, is_edge_case=True),
        TestCase("is_prime(2)", (2,), True, is_edge_case=True),
        TestCase("is_prime(17)", (17,), True),
        TestCase("is_prime(4)", (4,), False),
        TestCase("is_prime(97)", (97,), True),
    ]


def _max_subarray_tests() -> List[TestCase]:
    return [
        TestCase("max_subarray([])", ([],), 0, is_edge_case=True),
        TestCase("max_subarray([-1])", ([-1],), -1, is_edge_case=True),
        TestCase("max_subarray([-2,1,-3,4,-1,2,1,-5,4])", ([-2, 1, -3, 4, -1, 2, 1, -5, 4],), 6),
        TestCase("max_subarray([1,2,3])", ([1, 2, 3],), 6),
    ]


# maps function names / keywords to their test suite generator
_TEST_REGISTRY: Dict[str, Callable[[], List[TestCase]]] = {
    "factorial": _factorial_tests,
    "fibonacci": _fibonacci_tests,
    "fib": _fibonacci_tests,
    "palindrome": _is_palindrome_tests,
    "is_palindrome": _is_palindrome_tests,
    "reverse_string": _reverse_string_tests,
    "reverse": _reverse_string_tests,
    "two_sum": _two_sum_tests,
    "twosum": _two_sum_tests,
    "is_prime": _is_prime_tests,
    "prime": _is_prime_tests,
    "max_subarray": _max_subarray_tests,
    "kadane": _max_subarray_tests,
}


async def run_benchmark(problem: str, solution_code: str) -> BenchmarkResult:
    """
    Execute the candidate solution against matching test cases.
    Raises SyntaxError if code can't parse, ValueError if no function found.
    """

    result = BenchmarkResult()

    tree = ast.parse(solution_code)
    func_name = _extract_function_name(tree)
    if func_name is None:
        raise ValueError("No function definition found in the submitted solution.")

    test_cases = _select_test_cases(problem, func_name)
    if not test_cases:
        result.feedback = (
            "Could not generate test cases for this problem. "
            "Make sure the problem description mentions a recognisable function name."
        )
        result.correctness_score = 0
        return result

    # load the solution into a namespace
    namespace: Dict[str, Any] = {"__builtins__": __builtins__}
    try:
        exec(compile(tree, "<solution>", "exec"), namespace)
    except Exception as exc:
        result.feedback = f"Solution failed to load: {exc}"
        result.failed_tests = len(test_cases)
        return result

    func = namespace.get(func_name)
    if not callable(func):
        raise ValueError(f"'{func_name}' is not callable in the solution.")

    edge_failures = 0
    total_edge = 0
    start_time = time.perf_counter()

    for tc in test_cases:
        if tc.is_edge_case:
            total_edge += 1
        try:
            actual = func(*tc.args)
            if _compare_results(actual, tc.expected):
                result.passed_tests += 1
            else:
                result.failed_tests += 1
                if tc.is_edge_case:
                    edge_failures += 1
        except Exception:
            result.failed_tests += 1
            if tc.is_edge_case:
                edge_failures += 1

    end_time = time.perf_counter()
    result.execution_time_ms = round((end_time - start_time) * 1000, 3)

    total = result.passed_tests + result.failed_tests
    result.correctness_score = int((result.passed_tests / total) * 100) if total else 0
    result.edge_cases_handled = edge_failures == 0 and total_edge > 0
    result.feedback = _build_feedback(result, total, total_edge, edge_failures)

    return result


def _extract_function_name(tree: ast.Module) -> Optional[str]:
    """Get the name of the first top-level function in the AST."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return None


def _select_test_cases(problem: str, func_name: str) -> List[TestCase]:
    """Try matching by function name first, then by keywords in the problem text."""

    lowered = func_name.lower()
    if lowered in _TEST_REGISTRY:
        return _TEST_REGISTRY[lowered]()

    problem_lower = problem.lower()
    for keyword, factory in _TEST_REGISTRY.items():
        if keyword in problem_lower:
            return factory()

    return []


def _compare_results(actual: Any, expected: Any) -> bool:
    """Flexible comparison - handles exact match, float tolerance, and unordered lists."""
    if actual == expected:
        return True

    if isinstance(actual, float) and isinstance(expected, float):
        return math.isclose(actual, expected, rel_tol=1e-6)

    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        try:
            return sorted(actual) == sorted(expected)
        except TypeError:
            return False

    return False


def _build_feedback(result: BenchmarkResult, total: int, total_edge: int, edge_failures: int) -> str:
    """Put together a readable feedback string based on the results."""

    parts: List[str] = []

    if result.correctness_score == 100:
        parts.append("All test cases passed.")
    elif result.correctness_score >= 80:
        parts.append(f"Good - {result.passed_tests}/{total} tests passed ({result.correctness_score}%).")
    elif result.correctness_score >= 50:
        parts.append(f"Partial - {result.passed_tests}/{total} tests passed. Check failing cases.")
    else:
        parts.append(f"Needs work - only {result.passed_tests}/{total} tests passed.")

    if total_edge > 0:
        if edge_failures == 0:
            parts.append("Edge cases handled correctly.")
        else:
            parts.append(
                f"{edge_failures}/{total_edge} edge case(s) failed - "
                f"check boundary inputs like empty values, zero, negatives."
            )

    if result.execution_time_ms > 500:
        parts.append(f"Slow execution ({result.execution_time_ms:.1f}ms) - consider optimizing.")

    return " ".join(parts)
