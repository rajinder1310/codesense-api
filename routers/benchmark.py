import logging
from fastapi import APIRouter, HTTPException, status
from models.schemas import BenchmarkRequest, BenchmarkResponse, ErrorResponse
from services.benchmark_engine import run_benchmark

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Benchmark"],
    responses={
        422: {"model": ErrorResponse, "description": "Solution has syntax errors"},
        400: {"model": ErrorResponse, "description": "No function found in solution"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.post("/benchmark", response_model=BenchmarkResponse, status_code=200, summary="Benchmark a solution")
async def benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    """Runs the submitted solution against auto-generated test cases."""

    try:
        result = await run_benchmark(request.problem, request.solution_code)
    except SyntaxError as exc:
        logger.warning("Syntax error in solution: %s", exc)
        raise HTTPException(status_code=422, detail=f"Syntax error in solution: {exc}")
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during benchmarking")
        raise HTTPException(status_code=500, detail="Internal error while benchmarking.") from exc

    return BenchmarkResponse(
        passed_tests=result.passed_tests,
        failed_tests=result.failed_tests,
        correctness_score=result.correctness_score,
        edge_cases_handled=result.edge_cases_handled,
        execution_time_ms=result.execution_time_ms,
        feedback=result.feedback,
    )
