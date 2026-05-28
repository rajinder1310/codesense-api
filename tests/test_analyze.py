import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestAnalyzeSuccess:

    def test_simple_function(self, client: TestClient) -> None:
        payload = {"code": "def add(a, b):\n    return a + b\n", "language": "python"}
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "complexity_score" in data
        assert "quality_score" in data
        assert "edge_cases_missing" in data
        assert "suggestions" in data
        assert "lines_of_code" in data
        assert data["complexity_score"] >= 1
        assert 0 <= data["quality_score"] <= 100
        assert data["lines_of_code"] == 2

    def test_complex_function_has_higher_complexity(self, client: TestClient) -> None:
        complex_code = (
            "def process(items):\n"
            "    result = []\n"
            "    for item in items:\n"
            "        if item > 0:\n"
            "            for sub in item:\n"
            "                if sub != 0:\n"
            "                    result.append(sub)\n"
            "    return result\n"
        )
        response = client.post("/analyze", json={"code": complex_code, "language": "python"})
        assert response.status_code == 200
        assert response.json()["complexity_score"] > 5

    def test_well_documented_code_scores_higher(self, client: TestClient) -> None:
        good_code = (
            'def greet(name: str) -> str:\n'
            '    """Return a greeting for the given name."""\n'
            '    if not name:\n'
            '        raise ValueError("Name must not be empty")\n'
            '    return f"Hello, {name}!"\n'
        )
        response = client.post("/analyze", json={"code": good_code, "language": "python"})
        assert response.status_code == 200
        assert response.json()["quality_score"] >= 70

    def test_default_language_is_python(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"code": "x = 1\n"})
        assert response.status_code == 200

    def test_multiline_code(self, client: TestClient) -> None:
        code = (
            "class Calculator:\n"
            '    """A simple calculator."""\n'
            "\n"
            "    def add(self, a: int, b: int) -> int:\n"
            '        """Add two numbers."""\n'
            "        return a + b\n"
            "\n"
            "    def subtract(self, a: int, b: int) -> int:\n"
            '        """Subtract b from a."""\n'
            "        return a - b\n"
        )
        response = client.post("/analyze", json={"code": code, "language": "python"})
        assert response.status_code == 200
        data = response.json()
        assert data["lines_of_code"] >= 6
        assert data["quality_score"] >= 70


class TestAnalyzeErrors:

    def test_syntax_error_returns_422(self, client: TestClient) -> None:
        payload = {"code": "def broken(:\n    pass\n", "language": "python"}
        response = client.post("/analyze", json=payload)
        assert response.status_code == 422

    def test_unsupported_language_returns_400(self, client: TestClient) -> None:
        payload = {"code": "int main() {}", "language": "cpp"}
        response = client.post("/analyze", json=payload)
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()

    def test_empty_code_returns_422(self, client: TestClient) -> None:
        payload = {"code": "", "language": "python"}
        response = client.post("/analyze", json=payload)
        assert response.status_code == 422

    def test_missing_code_field_returns_422(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"language": "python"})
        assert response.status_code == 422


class TestEdgeCaseDetection:

    def test_no_guard_clause_detected(self, client: TestClient) -> None:
        code = "def divide(a, b):\n    return a / b\n"
        response = client.post("/analyze", json={"code": code, "language": "python"})
        assert response.status_code == 200
        assert len(response.json()["edge_cases_missing"]) > 0

    def test_bare_except_detected(self, client: TestClient) -> None:
        code = (
            "def risky():\n"
            "    try:\n"
            "        do_something()\n"
            "    except:\n"
            "        pass\n"
        )
        response = client.post("/analyze", json={"code": code, "language": "python"})
        assert response.status_code == 200
        data = response.json()
        combined = " ".join(data["edge_cases_missing"] + data["suggestions"]).lower()
        assert "except" in combined
