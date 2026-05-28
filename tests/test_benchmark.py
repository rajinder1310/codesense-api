import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestBenchmarkSuccess:

    def test_correct_factorial(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function called 'factorial' that returns the factorial of a non-negative integer.",
            "solution_code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["correctness_score"] == 100
        assert data["failed_tests"] == 0
        assert data["edge_cases_handled"] is True

    def test_correct_fibonacci(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function called 'fibonacci' that returns the n-th Fibonacci number.",
            "solution_code": (
                "def fibonacci(n):\n"
                "    if n <= 0:\n        return 0\n"
                "    if n == 1:\n        return 1\n"
                "    a, b = 0, 1\n"
                "    for _ in range(2, n + 1):\n        a, b = b, a + b\n"
                "    return b\n"
            ),
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["correctness_score"] == 100
        assert data["edge_cases_handled"] is True

    def test_correct_is_palindrome(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function called 'is_palindrome' that checks if a string is a palindrome.",
            "solution_code": "def is_palindrome(s):\n    return s == s[::-1]\n",
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        assert response.json()["correctness_score"] == 100

    def test_execution_time_measured(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function 'factorial' that returns n!.",
            "solution_code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        assert response.json()["execution_time_ms"] >= 0


class TestBenchmarkFailures:

    def test_wrong_factorial(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function called 'factorial' that returns the factorial.",
            "solution_code": "def factorial(n):\n    return n\n",
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["failed_tests"] > 0
        assert data["correctness_score"] < 100

    def test_iterative_factorial_handles_zero(self, client: TestClient) -> None:
        payload = {
            "problem": "Write a function called 'factorial' that returns n!.",
            "solution_code": (
                "def factorial(n):\n"
                "    result = 1\n"
                "    for i in range(2, n + 1):\n        result *= i\n"
                "    return result\n"
            ),
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        assert response.json()["correctness_score"] == 100


class TestBenchmarkErrors:

    def test_syntax_error_returns_422(self, client: TestClient) -> None:
        payload = {"problem": "Write a factorial function.", "solution_code": "def factorial(n\n    return 1\n"}
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 422

    def test_no_function_returns_400(self, client: TestClient) -> None:
        payload = {"problem": "Write a factorial function.", "solution_code": "x = 42\nprint(x)\n"}
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 400
        assert "function" in response.json()["detail"].lower()

    def test_empty_solution_returns_422(self, client: TestClient) -> None:
        payload = {"problem": "Write a factorial function.", "solution_code": ""}
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 422

    def test_missing_problem_returns_422(self, client: TestClient) -> None:
        response = client.post("/benchmark", json={"solution_code": "def f(): pass"})
        assert response.status_code == 422


class TestBenchmarkUnknownProblem:

    def test_unknown_problem_gives_feedback(self, client: TestClient) -> None:
        payload = {
            "problem": "Solve the travelling salesman problem.",
            "solution_code": "def solve(graph):\n    return []\n",
        }
        response = client.post("/benchmark", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["correctness_score"] == 0
        assert "could not generate" in data["feedback"].lower()
