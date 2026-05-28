from pydantic import BaseModel, Field
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    code: str = Field(
        ...,
        min_length=1,
        description="Source code to analyze",
        examples=["def add(a, b):\n    return a + b"],
    )
    language: str = Field(
        default="python",
        description="Programming language (only 'python' supported for now)",
        examples=["python"],
    )


class AnalyzeResponse(BaseModel):
    complexity_score: int = Field(..., ge=0, description="Complexity score from AST analysis")
    edge_cases_missing: List[str] = Field(default_factory=list, description="Detected edge-case gaps")
    quality_score: int = Field(..., ge=0, le=100, description="Code quality score (0-100)")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    lines_of_code: int = Field(..., ge=0, description="Non-blank, non-comment line count")


class BenchmarkRequest(BaseModel):
    problem: str = Field(
        ...,
        min_length=1,
        description="Problem description",
        examples=["Write a function called 'factorial' that returns the factorial of a non-negative integer."],
    )
    solution_code: str = Field(
        ...,
        min_length=1,
        description="Python solution code",
        examples=["def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"],
    )


class BenchmarkResponse(BaseModel):
    passed_tests: int = Field(..., ge=0, description="Number of passed test cases")
    failed_tests: int = Field(..., ge=0, description="Number of failed test cases")
    correctness_score: int = Field(..., ge=0, le=100, description="Correctness percentage")
    edge_cases_handled: bool = Field(..., description="Whether edge cases passed")
    execution_time_ms: float = Field(..., ge=0.0, description="Total execution time in ms")
    feedback: str = Field(..., description="Human-readable feedback")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")
