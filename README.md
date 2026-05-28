# CodeSense — AI Code Evaluation Service

> A production-grade REST API that analyses Python code quality and benchmarks solutions against auto-generated test suites.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Health Check](#get-health)
  - [Analyze Code](#post-analyze)
  - [Benchmark Solution](#post-benchmark)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [License](#license)

---

## Features

| Capability | Description |
|---|---|
| **Static Analysis** | AST-based complexity scoring, quality rating (0–100), edge-case detection |
| **Benchmarking** | Auto-generated test suites for common algorithms with timing |
| **Production-ready** | Structured logging, CORS, global error handlers, Pydantic v2 validation |
| **Interactive Docs** | Swagger UI at `/docs`, ReDoc at `/redoc` |
| **Fully Tested** | pytest suite covering happy paths, error conditions, and edge cases |

---

## Architecture

```
Client ──► FastAPI App ──► Routers ──► Services
               │                        ├── code_analyzer.py  (ast-based)
               │                        └── benchmark_engine.py (exec + test suites)
               ├── models/schemas.py    (Pydantic v2 models)
               └── Middleware           (CORS, error handlers)
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
cd codeSense

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Run the Server

```bash
# Development (with auto-reload)
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API is now available at **http://localhost:8000**.

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## API Reference

### `GET /health`

Returns the service health status.

**Response** `200 OK`

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### `POST /analyze`

Analyse Python source code for complexity, quality, and potential issues.

**Request Body**

```json
{
  "code": "def add(a, b):\n    return a + b",
  "language": "python"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `code` | string | ✅ | — | Python source code to analyse |
| `language` | string | ❌ | `"python"` | Programming language (only `python` supported) |

**Response** `200 OK`

```json
{
  "complexity_score": 2,
  "edge_cases_missing": [
    "Function 'add' accepts parameters but has no input validation or guard clauses"
  ],
  "quality_score": 72,
  "suggestions": [
    "Only 0/1 functions/classes have docstrings — aim for ≥ 80 % coverage",
    "Add return-type annotations to your functions for better readability and tooling support"
  ],
  "lines_of_code": 2
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | Unsupported language |
| `422` | Syntax error in code or validation failure |
| `500` | Internal server error |

---

### `POST /benchmark`

Evaluate a candidate solution against auto-generated test cases.

**Request Body**

```json
{
  "problem": "Write a function called 'factorial' that returns the factorial of a non-negative integer.",
  "solution_code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `problem` | string | ✅ | Natural-language problem description |
| `solution_code` | string | ✅ | Python solution code |

**Supported Problem Types**

The benchmark engine recognises the following problem types by keyword or function name:

- `factorial` — Factorial computation
- `fibonacci` / `fib` — Fibonacci sequence
- `is_palindrome` / `palindrome` — Palindrome checking
- `reverse_string` / `reverse` — String reversal
- `two_sum` / `twosum` — Two Sum problem
- `is_prime` / `prime` — Primality test
- `max_subarray` / `kadane` — Maximum subarray sum

**Response** `200 OK`

```json
{
  "passed_tests": 5,
  "failed_tests": 0,
  "correctness_score": 100,
  "edge_cases_handled": true,
  "execution_time_ms": 0.123,
  "feedback": "Excellent! All test cases passed. All edge cases were handled correctly."
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | No function definition found in solution |
| `422` | Syntax error in solution or validation failure |
| `500` | Internal server error |

---

## Running Tests

```bash
# Run all tests
pytest -v

# Run only analyze tests
pytest tests/test_analyze.py -v

# Run only benchmark tests
pytest tests/test_benchmark.py -v

# Run with coverage
pytest --cov=. --cov-report=term-missing
```

---

## Project Structure

```
codeSense/
├── main.py                    # FastAPI app entry point, middleware, error handlers
├── routers/
│   ├── __init__.py
│   ├── analyze.py             # POST /analyze endpoint
│   ├── benchmark.py           # POST /benchmark endpoint
│   └── health.py              # GET /health endpoint
├── services/
│   ├── __init__.py
│   ├── code_analyzer.py       # AST-based static analysis engine
│   └── benchmark_engine.py    # Solution benchmarking engine
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic request/response models
├── tests/
│   ├── __init__.py
│   ├── test_analyze.py        # Tests for /analyze
│   └── test_benchmark.py      # Tests for /benchmark
├── requirements.txt           # Pinned dependencies
└── README.md                  # This file
```

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `WORKERS` | `1` | Number of uvicorn workers |

---

## License

MIT © 2026
